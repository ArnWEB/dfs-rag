"""Batch processor for bulk database operations."""

from collections.abc import AsyncGenerator
from typing import Any

import structlog

from bootstrap.database.repository import ManifestRepository
from bootstrap.models.file_record import BootstrapStats, FileRecord

logger = structlog.get_logger()


class BatchProcessor:
    """Processes records in batches for efficient database writes."""
    
    def __init__(
        self,
        repository: ManifestRepository,
        batch_size: int = 500,
        progress_interval: int = 10000,
    ):
        """Initialize batch processor.
        
        Args:
            repository: Manifest repository instance
            batch_size: Number of records per batch
            progress_interval: Report progress every N records
        """
        self.repository = repository
        self.batch_size = batch_size
        self.progress_interval = progress_interval
        self.stats = BootstrapStats()
        self._batch: list[FileRecord] = []
    
    async def process_stream(
        self,
        record_stream: AsyncGenerator[FileRecord, None],
    ) -> BootstrapStats:
        """Process a stream of records in batches.
        
        Args:
            record_stream: Async generator yielding FileRecord objects
            
        Returns:
            BootstrapStats with final statistics
        """
        self.stats = BootstrapStats()
        self._batch = []
        
        logger.info(
            "batch_processing_started",
            batch_size=self.batch_size,
            progress_interval=self.progress_interval,
        )
        
        try:
            async for record in record_stream:
                await self._process_record(record)
            
            # Flush remaining batch
            if self._batch:
                await self._flush_batch()
            
        except Exception as e:
            logger.error(
                "batch_processing_error",
                error=str(e),
                records_processed=self.stats.total_discovered,
            )
            raise
        
        finally:
            self.stats.end_time = __import__("datetime").datetime.utcnow()
        
        return self.stats
    
    async def _process_record(self, record: FileRecord) -> None:
        """Process a single record."""
        self.stats.total_discovered += 1
        
        # Update stats based on status
        if record.status.value == "permission_denied":
            self.stats.permission_errors += 1
        elif record.status.value == "error":
            self.stats.other_errors += 1
        elif record.acl_captured:
            self.stats.acl_captured += 1
        else:
            self.stats.acl_failed += 1
        
        # Add to batch
        self._batch.append(record)
        
        # Flush if batch is full
        if len(self._batch) >= self.batch_size:
            await self._flush_batch()
        
        # Report progress
        if self.stats.total_discovered % self.progress_interval == 0:
            self._report_progress()
    
    async def _flush_batch(self) -> None:
        """Write current batch to database."""
        if not self._batch:
            return
        
        batch_to_write = self._batch
        self._batch = []
        
        try:
            # Run database operation in thread pool
            loop = __import__("asyncio").get_event_loop()
            inserted, skipped = await loop.run_in_executor(
                None,
                self.repository.bulk_upsert,
                batch_to_write,
            )
            
            self.stats.total_added += inserted
            self.stats.total_skipped += skipped
            
            logger.debug(
                "batch_flushed",
                batch_size=len(batch_to_write),
                inserted=inserted,
                skipped=skipped,
            )
            
        except Exception as e:
            logger.error(
                "batch_flush_error",
                batch_size=len(batch_to_write),
                error=str(e),
                likely_cause="Database write failure - disk full or locked",
                developer_action="Check disk space, DB permissions, and file locks",
            )
            # Re-raise to stop processing
            raise
    
    def _report_progress(self) -> None:
        """Report current progress."""
        duration = self.stats.duration_seconds
        rate = self.stats.records_per_second
        
        logger.info(
            "progress_report",
            total_discovered=self.stats.total_discovered,
            total_added=self.stats.total_added,
            total_skipped=self.stats.total_skipped,
            permission_errors=self.stats.permission_errors,
            acl_captured=self.stats.acl_captured,
            acl_failed=self.stats.acl_failed,
            duration_seconds=f"{duration:.1f}",
            records_per_second=f"{rate:.1f}",
        )