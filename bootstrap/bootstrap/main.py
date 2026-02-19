"""Main orchestrator for bootstrap manifest builder."""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import structlog

from bootstrap.config import Settings, settings
from bootstrap.database import create_database_engine, ManifestRepository
from bootstrap.discovery import BatchProcessor, DirectoryWalker, create_acl_extractor
from bootstrap.logging_config import configure_logging
from bootstrap.models import BootstrapStats

logger = structlog.get_logger()


class BootstrapRunner:
    """Orchestrates the bootstrap process."""
    
    def __init__(self, config: Settings | None = None):
        """Initialize runner with configuration.
        
        Args:
            config: Settings instance (uses global settings if None)
        """
        self.config = config or settings
        self.stats: BootstrapStats | None = None
        self._shutdown_event = asyncio.Event()
    
    @asynccontextmanager
    async def _setup(self):
        """Setup context manager for database and logging."""
        # Configure logging
        log = configure_logging(
            log_level=self.config.log_level,
            log_file=self.config.log_file,
            format_type="json" if self.config.log_format == "json" else "console",
        )
        
        # Setup database
        engine = create_database_engine(
            self.config.db_path,
            cache_size_mb=self.config.sqlite_cache_mb,
        )
        repository = ManifestRepository(engine)
        repository.init_schema()
        
        # Setup signal handlers (Unix only - Windows uses different signal handling)
        if sys.platform != "win32":
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self._signal_handler)
        
        try:
            yield log, repository
        finally:
            # Cleanup
            engine.dispose()
    
    def _signal_handler(self):
        """Handle shutdown signals."""
        logger.warning("shutdown_signal_received", signal="SIGINT/SIGTERM")
        self._shutdown_event.set()
    
    async def run(self) -> BootstrapStats:
        """Run the bootstrap process.
        
        Returns:
            BootstrapStats with final results
        """
        async with self._setup() as (log, repository):
            logger.info(
                "bootstrap_started",
                dfs_path=str(self.config.dfs_path),
                db_path=str(self.config.db_path),
                workers=self.config.workers,
                batch_size=self.config.batch_size,
            )
            
            # Verify DFS path exists
            if not self.config.dfs_path.exists():
                logger.error(
                    "dfs_path_not_found",
                    path=str(self.config.dfs_path),
                )
                raise FileNotFoundError(
                    f"DFS path not found: {self.config.dfs_path}"
                )
            
            # Create components
            acl_extractor = create_acl_extractor(self.config.acl_extractor)
            logger.info("acl_extractor_initialized", extractor_type=acl_extractor.name)
            
            walker = DirectoryWalker(
                timeout_seconds=self.config.file_timeout_seconds,
                max_retries=self.config.max_retries,
                acl_extractor=acl_extractor,
            )
            
            processor = BatchProcessor(
                repository=repository,
                batch_size=self.config.batch_size,
                progress_interval=self.config.progress_interval,
            )
            
            # Run discovery
            try:
                record_stream = walker.walk(self.config.dfs_path)
                self.stats = await processor.process_stream(record_stream)
                
            except Exception as e:
                logger.error(
                    "bootstrap_failed",
                    error=str(e),
                    exc_info=True,
                )
                raise
            
            # Print summary
            logger.info("bootstrap_completed")
            print("\n" + self.stats.summary())
            
            return self.stats


def main():
    """Entry point for CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Bootstrap manifest builder for DFS discovery",
    )
    parser.add_argument(
        "dfs_path",
        nargs="?",
        type=Path,
        default=None,
        help="Root path of DFS share to scan (default: from env/config)",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="SQLite database file path",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of concurrent workers (1-32)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Records per batch (100-5000)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Per-file timeout in minutes (1-30)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Logging level",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Log file path",
    )
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=None,
        help="Report progress every N files",
    )
    parser.add_argument(
        "--acl-extractor",
        choices=["getfacl", "stat", "noop"],
        default=None,
        help="ACL extractor type: getfacl (default - getfacl+stat), stat (stat only), noop (no ACL extraction)",
    )
    
    args = parser.parse_args()
    
    # Override settings with CLI args
    if args.dfs_path:
        settings.dfs_path = args.dfs_path
    if args.db_path:
        settings.db_path = args.db_path
    if args.workers:
        settings.workers = args.workers
    if args.batch_size:
        settings.batch_size = args.batch_size
    if args.timeout:
        settings.file_timeout_minutes = args.timeout
    if args.log_level:
        settings.log_level = args.log_level
    if args.log_file:
        settings.log_file = args.log_file
    if args.progress_interval:
        settings.progress_interval = args.progress_interval
    if args.acl_extractor:
        settings.acl_extractor = args.acl_extractor
    
    # Run
    try:
        runner = BootstrapRunner()
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()