"""ACL extractor interface and implementations."""

import asyncio
import json
import os
import platform
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger()


@dataclass
class ACLResult:
    """Result of ACL extraction attempt."""
    raw_acl: str | None = None
    captured: bool = False
    method: str = "unknown"
    error: str | None = None


class ACLExtractor(ABC):
    """Abstract base class for ACL extractors.
    
    Implement this interface to create custom ACL extraction strategies.
    """
    
    @abstractmethod
    async def extract(self, file_path: Path, timeout_seconds: float = 300.0) -> ACLResult:
        """Extract ACL from a file.
        
        Args:
            file_path: Path to the file
            timeout_seconds: Timeout for the extraction operation
            
        Returns:
            ACLResult containing the extracted ACL or error information
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this extractor implementation."""
        pass


class GetfaclACLExtractor(ACLExtractor):
    """ACL extractor using getfacl command with stat fallback.
    
    This is the default implementation that:
    1. Tries getfacl first (best for CIFS/NTFS mounts on Linux)
    2. Falls back to stat-based info if getfacl fails
    """
    
    @property
    def name(self) -> str:
        return "getfacl+stat"
    
    async def extract(self, file_path: Path, timeout_seconds: float = 300.0) -> ACLResult:
        """Extract ACL using getfacl with stat fallback."""
        # Try getfacl first
        result = await self._try_getfacl(file_path, timeout_seconds)
        if result.captured:
            return result
        
        # Fall back to stat
        return await self._try_stat(file_path, timeout_seconds)
    
    async def _try_getfacl(self, file_path: Path, timeout_seconds: float) -> ACLResult:
        """Try to get ACL using getfacl command."""
        system = platform.system()
        
        if system != "Linux":
            return ACLResult(
                captured=False,
                method="getfacl",
                error=f"getfacl not available on {system}",
            )
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "getfacl",
                "-c",
                str(file_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                logger.warning(
                    "acl_extraction_timeout",
                    path=str(file_path),
                    method="getfacl",
                    timeout_seconds=timeout_seconds,
                )
                return ACLResult(
                    captured=False,
                    method="getfacl",
                    error=f"Timeout after {timeout_seconds}s",
                )
            
            if proc.returncode == 0:
                acl_text = stdout.decode("utf-8", errors="replace").strip()
                return ACLResult(
                    raw_acl=acl_text,
                    captured=True,
                    method="getfacl",
                )
            else:
                error_text = stderr.decode("utf-8", errors="replace").strip()
                return ACLResult(
                    captured=False,
                    method="getfacl",
                    error=error_text or f"Exit code {proc.returncode}",
                )
                
        except FileNotFoundError:
            return ACLResult(
                captured=False,
                method="getfacl",
                error="getfacl command not found",
            )
        except Exception as e:
            logger.warning(
                "acl_extraction_error",
                path=str(file_path),
                method="getfacl",
                error=str(e),
            )
            return ACLResult(
                captured=False,
                method="getfacl",
                error=str(e),
            )
    
    async def _try_stat(self, file_path: Path, timeout_seconds: float) -> ACLResult:
        """Fallback: Get basic ACL info from stat."""
        try:
            loop = asyncio.get_event_loop()
            
            def _get_stat_info():
                try:
                    stat_info = os.stat(file_path)
                    return {
                        "mode": oct(stat_info.st_mode),
                        "uid": stat_info.st_uid,
                        "gid": stat_info.st_gid,
                        "size": stat_info.st_size,
                        "mtime": stat_info.st_mtime,
                        "atime": stat_info.st_atime,
                        "ctime": stat_info.st_ctime,
                    }
                except (OSError, IOError) as e:
                    return {"error": str(e)}
            
            try:
                stat_info = await asyncio.wait_for(
                    loop.run_in_executor(None, _get_stat_info),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "stat_timeout",
                    path=str(file_path),
                    timeout_seconds=timeout_seconds,
                )
                return ACLResult(
                    captured=False,
                    method="stat",
                    error=f"Stat timeout after {timeout_seconds}s",
                )
            
            if "error" in stat_info:
                return ACLResult(
                    captured=False,
                    method="stat",
                    error=stat_info["error"],
                )
            
            acl_text = json.dumps(stat_info, indent=2)
            
            return ACLResult(
                raw_acl=acl_text,
                captured=True,
                method="stat",
            )
            
        except Exception as e:
            logger.warning(
                "stat_acl_error",
                path=str(file_path),
                error=str(e),
            )
            return ACLResult(
                captured=False,
                method="stat",
                error=str(e),
            )


class StatOnlyACLExtractor(ACLExtractor):
    """ACL extractor using only stat information.
    
    This is a lightweight implementation that only uses os.stat()
    without trying getfacl. Useful when getfacl is not available
    or when you want faster processing without ACL details.
    """
    
    @property
    def name(self) -> str:
        return "stat-only"
    
    async def extract(self, file_path: Path, timeout_seconds: float = 300.0) -> ACLResult:
        """Extract ACL using only stat."""
        try:
            loop = asyncio.get_event_loop()
            
            def _get_stat():
                stat_info = os.stat(file_path)
                return {
                    "mode": oct(stat_info.st_mode),
                    "uid": stat_info.st_uid,
                    "gid": stat_info.st_gid,
                    "size": stat_info.st_size,
                    "mtime": stat_info.st_mtime,
                    "atime": stat_info.st_atime,
                    "ctime": stat_info.st_ctime,
                }
            
            try:
                stat_info = await asyncio.wait_for(
                    loop.run_in_executor(None, _get_stat),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                return ACLResult(
                    captured=False,
                    method="stat",
                    error=f"Stat timeout after {timeout_seconds}s",
                )
            
            acl_text = json.dumps(stat_info, indent=2)
            
            return ACLResult(
                raw_acl=acl_text,
                captured=True,
                method="stat",
            )
            
        except Exception as e:
            return ACLResult(
                captured=False,
                method="stat",
                error=str(e),
            )


class NoOpACLExtractor(ACLExtractor):
    """No-op ACL extractor that always returns empty.
    
    Use this when you don't need ACL information at all.
    This is the fastest option as it performs no extraction.
    """
    
    @property
    def name(self) -> str:
        return "noop"
    
    async def extract(self, file_path: Path, timeout_seconds: float = 300.0) -> ACLResult:
        """Return empty ACL result immediately."""
        return ACLResult(
            raw_acl=None,
            captured=False,
            method="noop",
            error="ACL extraction disabled",
        )


# Factory function for creating extractors
def create_acl_extractor(extractor_type: str = "getfacl") -> ACLExtractor:
    """Create an ACL extractor by type.
    
    Args:
        extractor_type: Type of extractor to create
            - "getfacl": Default, tries getfacl then stat (default)
            - "stat": Stat only, no getfacl
            - "noop": No extraction, always returns empty
            
    Returns:
        ACLExtractor instance
        
    Raises:
        ValueError: If extractor_type is not recognized
    """
    extractors = {
        "getfacl": GetfaclACLExtractor,
        "stat": StatOnlyACLExtractor,
        "noop": NoOpACLExtractor,
    }
    
    if extractor_type not in extractors:
        raise ValueError(
            f"Unknown extractor type: {extractor_type}. "
            f"Available types: {list(extractors.keys())}"
        )
    
    return extractors[extractor_type]()


# Backward compatibility - keep the old function name
def extract_acl(file_path: Path, timeout_seconds: float = 300.0) -> ACLResult:
    """Legacy function for backward compatibility.
    
    Uses GetfaclACLExtractor by default.
    """
    extractor = GetfaclACLExtractor()
    # Note: This is a sync wrapper for the async method
    # In real usage, use the class directly with async/await
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(extractor.extract(file_path, timeout_seconds))
    except RuntimeError:
        # No event loop running, create one
        return asyncio.run(extractor.extract(file_path, timeout_seconds))