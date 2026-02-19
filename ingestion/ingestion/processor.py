"""Ingestion processor with retry logic and batch handling."""

import json
import logging
import time
from pathlib import Path
from typing import Any

from ingestion.checkpoint import CheckpointManager
from ingestion.client import IngestionClient, IngestionError
from ingestion.config import Settings
from ingestion.repository import FileRecord, IngestionRepository

logger = logging.getLogger(__name__)


class IngestionStats:
    """Statistics for ingestion run."""
    
    def __init__(self):
        self.total_processed = 0
        self.total_failed = 0
        self.total_completed = 0
        self.total_skipped = 0
        self.batch_count = 0
        self.start_time = time.time()
    
    @property
    def duration(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.total_completed + self.total_failed
        if total == 0:
            return 0.0
        return (self.total_completed / total) * 100


class IngestionProcessor:
    """Processes files in batches with retry logic."""
    
    def __init__(
        self,
        repository: IngestionRepository,
        client: IngestionClient,
        checkpoint_manager: CheckpointManager,
        settings: Settings,
        existing_docs: set[str] | None = None,
    ):
        """Initialize processor.
        
        Args:
            repository: Database repository
            client: NVIDIA RAG API client
            checkpoint_manager: Checkpoint manager
            settings: Application settings
            existing_docs: Set of already ingested document names to skip
        """
        self.repository = repository
        self.client = client
        self.checkpoint_manager = checkpoint_manager
        self.settings = settings
        self.existing_docs = existing_docs or set()
        self.stats = IngestionStats()
    
    def process_batch(
        self,
        files: list[FileRecord],
        batch_num: int,
    ) -> tuple[list[str], list[tuple[str, str]]]:
        """Process a single batch of files.
        
        Args:
            files: List of files to process
            batch_num: Current batch number
            
        Returns:
            Tuple of (successful_paths, failed_paths_with_errors)
        """
        logger.info(f"Processing batch {batch_num}: {len(files)} files")
        
        successful = []
        failed = []
        
        # Filter out already ingested files
        files_to_upload = []
        for file_record in files:
            if file_record.file_name in self.existing_docs:
                logger.info(f"Skipping already ingested: {file_record.file_name}")
                self.repository.update_ingestion_status(
                    file_record.file_path,
                    status="completed"
                )
                self.stats.total_skipped += 1
                successful.append(file_record.file_path)
            else:
                files_to_upload.append(file_record)
        
        if not files_to_upload:
            logger.info(f"Batch {batch_num}: All files already ingested")
            return successful, failed
        
        # Mark files as ingesting
        for file_record in files_to_upload:
            self.repository.update_ingestion_status(
                file_record.file_path,
                status="ingesting"
            )
        
        # Verify files exist
        existing_files = []
        missing_files = []
        
        for file_record in files_to_upload:
            if self.repository.verify_file_exists(file_record.file_path):
                existing_files.append(file_record)
            else:
                missing_files.append(file_record)
                logger.warning(f"File not found: {file_record.file_path}")
                self.repository.update_ingestion_status(
                    file_record.file_path,
                    status="failed",
                    error="File not found on disk"
                )
                failed.append((file_record.file_path, "File not found"))
        
        if not existing_files:
            logger.warning(f"Batch {batch_num}: No existing files to process")
            return successful, failed
        
        # Build payload with ACL metadata
        payload = self._build_payload(existing_files)
        
        # Prepare file paths
        file_paths = [Path(f.file_path) for f in existing_files]
        
        # Upload with retry logic
        try:
            response = self._upload_with_retry(file_paths, payload)
            
            # Get task_id from response
            task_id = (
                (response or {}).get("task_id")
                or (response or {}).get("task")
                or (response or {}).get("id")
            )
            
            if task_id:
                # Poll for task completion
                self.client.poll_task_status(task_id)
                logger.info(f"Batch {batch_num}: Task {task_id} completed")
            
            # Mark all as completed
            for file_record in existing_files:
                self.repository.update_ingestion_status(
                    file_record.file_path,
                    status="completed"
                )
                successful.append(file_record.file_path)
            
            logger.info(f"Batch {batch_num}: {len(successful)} files uploaded successfully")
            
        except IngestionError as e:
            logger.error(f"Batch {batch_num} upload failed: {e}")
            
            # Mark all as failed
            for file_record in existing_files:
                self.repository.update_ingestion_status(
                    file_record.file_path,
                    status="failed",
                    error=str(e)
                )
                failed.append((file_record.file_path, str(e)))
        
        return successful, failed
    
    def _upload_with_retry(
        self,
        file_paths: list[Path],
        payload: dict,
    ) -> dict:
        """Upload files with retry logic.
        
        Args:
            file_paths: List of file paths
            payload: Upload payload
            
        Returns:
            Response JSON from API
            
        Raises:
            IngestionError: If all retries exhausted
        """
        last_error = None
        
        for attempt in range(self.settings.max_retries):
            try:
                response = self.client.upload_documents(
                    files=file_paths,
                    payload=payload,
                    timeout=self.settings.request_timeout,
                )
                logger.debug(f"Upload successful after {attempt + 1} attempt(s)")
                return response
                
            except IngestionError as e:
                last_error = e
                logger.warning(
                    f"Upload attempt {attempt + 1}/{self.settings.max_retries} failed: {e}"
                )
                
                if attempt < self.settings.max_retries - 1:
                    # Exponential backoff
                    delay = self.settings.retry_delay * (2 ** attempt)
                    logger.debug(f"Retrying in {delay}s...")
                    time.sleep(delay)
        
        # All retries exhausted
        raise IngestionError(
            f"Upload failed after {self.settings.max_retries} attempts: {last_error}"
        )
    
    def _build_payload(self, files: list[FileRecord]) -> dict:
        """Build upload payload.
        
        Args:
            files: List of file records
            
        Returns:
            Payload dictionary
        """
        # Build custom metadata with ACL data from raw_acl column
        custom_metadata = []
        
        for file_record in files:
            metadata = {}
            
            # Include ACL data if available
            if file_record.raw_acl:
                try:
                    # Try to parse as JSON
                    acl_data = json.loads(file_record.raw_acl)
                    if isinstance(acl_data, dict):
                        metadata.update(acl_data)
                    else:
                        metadata["acl"] = str(acl_data)
                except (json.JSONDecodeError, TypeError):
                    metadata["acl"] = file_record.raw_acl
            
            custom_metadata.append(metadata)
        
        return {
            "collection_name": self.settings.collection_name,
            "blocking": self.settings.blocking,
            "split_options": {
                "chunk_size": self.settings.split_chunk_size,
                "chunk_overlap": self.settings.split_chunk_overlap,
            },
            "custom_metadata": custom_metadata,
            "generate_summary": self.settings.generate_summary,
        }
    
    def run(
        self,
        offset: int = 0,
        batch_num: int = 0,
    ) -> IngestionStats:
        """Run ingestion process.
        
        Args:
            offset: Starting database offset
            batch_num: Starting batch number
            
        Returns:
            Ingestion statistics
        """
        self.stats = IngestionStats()
        self.stats.total_skipped = 0  # Reset skipped count
        current_offset = offset
        current_batch = batch_num
        
        logger.info(f"Starting ingestion from offset={offset}, batch={batch_num}")
        logger.info(f"Batch size: {self.settings.batch_size}, "
                   f"Checkpoint interval: {self.settings.checkpoint_interval}")
        
        if self.existing_docs:
            logger.info(f"Skipping {len(self.existing_docs)} already ingested documents")
        
        try:
            while True:
                # Get batch of pending files
                files = self.repository.get_pending_files(
                    batch_size=self.settings.batch_size,
                    offset=current_offset,
                )
                
                if not files:
                    logger.info("No more pending files. Ingestion complete!")
                    break
                
                current_batch += 1
                self.stats.batch_count += 1
                
                # Process batch
                successful, failed = self.process_batch(files, current_batch)
                
                self.stats.total_completed += len(successful)
                self.stats.total_failed += len(failed)
                self.stats.total_processed += len(files)
                
                # Update offset for next batch
                current_offset += len(files)
                
                # Save checkpoint periodically
                if current_batch % self.settings.checkpoint_interval == 0:
                    self.checkpoint_manager.save(
                        offset=current_offset,
                        batch_num=current_batch,
                        total_processed=self.stats.total_processed,
                        total_failed=self.stats.total_failed,
                    )
                    logger.info(
                        f"Checkpoint saved: processed={self.stats.total_processed}, "
                        f"failed={self.stats.total_failed}, "
                        f"skipped={self.stats.total_skipped}, "
                        f"success_rate={self.stats.success_rate:.1f}%"
                    )
                
                # Delay between batches if configured
                if self.settings.batch_delay > 0:
                    time.sleep(self.settings.batch_delay)
                
                # Check if we should continue on error
                if failed and not self.settings.continue_on_error:
                    logger.error("Stopping due to errors (continue_on_error=False)")
                    break
        
        except KeyboardInterrupt:
            logger.warning("Interrupted by user. Saving checkpoint...")
            self.checkpoint_manager.save(
                offset=current_offset,
                batch_num=current_batch,
                total_processed=self.stats.total_processed,
                total_failed=self.stats.total_failed,
            )
            logger.info(
                f"Checkpoint saved. Resume with: --resume "
                f"--checkpoint-file {self.settings.checkpoint_file}"
            )
            raise
        
        # Final checkpoint
        self.checkpoint_manager.save(
            offset=current_offset,
            batch_num=current_batch,
            total_processed=self.stats.total_processed,
            total_failed=self.stats.total_failed,
        )
        
        return self.stats
    
    def print_summary(self) -> None:
        """Print ingestion summary."""
        stats = self.stats
        
        print("\n" + "=" * 60)
        print("INGESTION COMPLETE")
        print("=" * 60)
        print(f"Total processed: {stats.total_processed}")
        print(f"Completed: {stats.total_completed}")
        print(f"Skipped (already ingested): {stats.total_skipped}")
        print(f"Failed: {stats.total_failed}")
        print(f"Success rate: {stats.success_rate:.1f}%")
        print(f"Batches: {stats.batch_count}")
        print(f"Duration: {stats.duration:.1f}s")
        if stats.duration > 0:
            print(f"Files/second: {stats.total_processed / stats.duration:.1f}")
        print("=" * 60)
