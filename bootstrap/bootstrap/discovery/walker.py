"""Directory walker with permission handling and symlink detection."""

import asyncio
import os
from collections.abc import AsyncGenerator
from pathlib import Path

import structlog

from bootstrap.models.file_record import ACLResult, FileRecord, FileStatus

from .acl_extractor import extract_acl

logger = structlog.get_logger()


class DirectoryWalker:
    """Walks directories asynchronously with proper error handling."""
    
    def __init__(
        self,
        timeout_seconds: float = 300.0,
        max_retries: int = 3,
    ):
        """Initialize walker.
        
        Args:
            timeout_seconds: Timeout per file operation
            max_retries: Max retries for transient errors
        """
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
    
    async def walk(
        self,
        root_path: Path,
    ) -> AsyncGenerator[FileRecord, None]:
        """Walk directory tree recursively.
        
        Yields FileRecord for each file/directory found.
        Handles permission errors by yielding error records.
        Skips symlinks to avoid cycles.
        
        Args:
            root_path: Root directory to start from
            
        Yields:
            FileRecord for each file/directory/error
        """
        # Resolve to absolute path
        root_path = root_path.resolve()
        
        # Check if root exists and is accessible
        try:
            if not root_path.exists():
                logger.error(
                    "root_path_not_found",
                    path=str(root_path),
                )
                yield FileRecord.create_permission_error(
                    root_path,
                    is_directory=True,
                    error_message="Root path does not exist",
                )
                return
            
            # Test read access
            os.listdir(root_path)
            
        except PermissionError:
            logger.error(
                "root_permission_denied",
                path=str(root_path),
                error_type="PermissionError",
                likely_cause="Service account lacks read permissions on root",
                developer_action="Check DFS share ACLs and mount options for service account",
            )
            yield FileRecord.create_permission_error(
                root_path,
                is_directory=True,
                error_message="Root directory permission denied",
            )
            return
        
        # Start recursive walk
        async for record in self._walk_recursive(root_path):
            yield record
    
    async def _walk_recursive(
        self,
        current_dir: Path,
    ) -> AsyncGenerator[FileRecord, None]:
        """Recursively walk directory."""
        entries = []
        
        # Try to scan directory with retry logic
        for attempt in range(self.max_retries):
            try:
                entries = list(os.scandir(current_dir))
                break
            except PermissionError as e:
                logger.warning(
                    "directory_permission_denied",
                    path=str(current_dir),
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error_type="PermissionError",
                    likely_cause="Service account lacks read permissions",
                    developer_action="Check DFS share ACLs and mount options for service account",
                )
                
                if attempt == self.max_retries - 1:
                    # Final attempt failed - yield error record
                    yield FileRecord.create_permission_error(
                        current_dir,
                        is_directory=True,
                        error_message=f"Permission denied after {self.max_retries} retries: {e}",
                    )
                    return
                
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except OSError as e:
                logger.warning(
                    "directory_access_error",
                    path=str(current_dir),
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    error=str(e),
                    likely_cause="DFS mount may be unstable",
                    developer_action="Check network connectivity and DFS mount status",
                )
                
                if attempt == self.max_retries - 1:
                    yield FileRecord.create_permission_error(
                        current_dir,
                        is_directory=True,
                        error_message=f"OS error after {self.max_retries} retries: {e}",
                    )
                    return
                
                await asyncio.sleep(2 ** attempt)
        
        # Process entries
        for entry in entries:
            entry_path = Path(entry.path)
            
            try:
                # Check if symlink - skip to avoid cycles
                if entry.is_symlink():
                    logger.info(
                        "symlink_skipped",
                        path=str(entry_path),
                        reason="Prevent cycles",
                    )
                    yield FileRecord.create_skipped(entry_path, "Symlink skipped to prevent cycles")
                    continue
                
                # Handle directories
                if entry.is_dir(follow_symlinks=False):
                    # First yield the directory record itself
                    dir_record = await self._process_entry(entry, entry_path, is_dir=True)
                    if dir_record:
                        yield dir_record
                    
                    # Then recurse into it
                    async for record in self._walk_recursive(entry_path):
                        yield record
                
                # Handle files
                elif entry.is_file(follow_symlinks=False):
                    record = await self._process_entry(entry, entry_path, is_dir=False)
                    if record:
                        yield record
                
                else:
                    # Unknown entry type
                    logger.debug(
                        "unknown_entry_type",
                        path=str(entry_path),
                        entry_type=entry.stat().st_mode if hasattr(entry, 'stat') else 'unknown',
                    )
                    yield FileRecord.create_skipped(entry_path, "Unknown entry type")
                    
            except PermissionError as e:
                logger.warning(
                    "entry_permission_denied",
                    path=str(entry_path),
                    error=str(e),
                    likely_cause="File locked or ACL prevents read",
                    developer_action="Check file permissions and ensure file is not locked",
                )
                yield FileRecord.create_permission_error(
                    entry_path,
                    is_directory=entry.is_dir(follow_symlinks=False),
                    error_message=f"Permission denied: {e}",
                )
                
            except OSError as e:
                logger.warning(
                    "entry_access_error",
                    path=str(entry_path),
                    error=str(e),
                    likely_cause="DFS transient error or corrupted file",
                    developer_action="Check DFS health and file integrity",
                )
                yield FileRecord.create_permission_error(
                    entry_path,
                    is_directory=entry.is_dir(follow_symlinks=False),
                    error_message=f"OS error: {e}",
                )
    
    async def _process_entry(
        self,
        entry: os.DirEntry,
        entry_path: Path,
        is_dir: bool,
    ) -> FileRecord | None:
        """Process a single file or directory entry.
        
        Returns:
            FileRecord or None if error
        """
        try:
            # Get stat info with timeout
            loop = asyncio.get_event_loop()
            
            def _get_stat():
                return entry.stat(follow_symlinks=False)
            
            try:
                stat_info = await asyncio.wait_for(
                    loop.run_in_executor(None, _get_stat),
                    timeout=self.timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "stat_timeout",
                    path=str(entry_path),
                    timeout_seconds=self.timeout_seconds,
                    likely_cause="File operation hung",
                    developer_action="Check DFS health and network stability",
                )
                return FileRecord(
                    file_path=entry_path.resolve(),
                    file_name=entry.name,
                    parent_dir=entry_path.parent,
                    status=FileStatus.ERROR,
                    error=f"Stat timeout after {self.timeout_seconds}s",
                    is_directory=is_dir,
                )
            
            # Extract ACL (for files only, not directories)
            acl_result = ACLResult()
            if not is_dir:
                acl_result = await extract_acl(entry_path, self.timeout_seconds)
            
            # Determine status based on ACL extraction
            if is_dir:
                status = FileStatus.DISCOVERED
            elif acl_result.captured:
                status = FileStatus.DISCOVERED
            else:
                status = FileStatus.ACL_FAILED
            
            return FileRecord(
                file_path=entry_path.resolve(),
                file_name=entry.name,
                parent_dir=entry_path.parent,
                size=stat_info.st_size if not is_dir else None,
                mtime=stat_info.st_mtime,
                raw_acl=acl_result.raw_acl,
                acl_captured=acl_result.captured,
                status=status,
                error=acl_result.error if not acl_result.captured else None,
                is_directory=is_dir,
            )
            
        except Exception as e:
            logger.error(
                "entry_processing_error",
                path=str(entry_path),
                error=str(e),
                exc_info=True,
            )
            return FileRecord(
                file_path=entry_path.resolve(),
                file_name=entry.name,
                parent_dir=entry_path.parent,
                status=FileStatus.ERROR,
                error=f"Processing error: {e}",
                is_directory=is_dir,
            )