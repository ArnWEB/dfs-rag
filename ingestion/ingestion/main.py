"""Main orchestrator for ingestion process."""

import logging
import sys
from pathlib import Path

from ingestion.checkpoint import CheckpointManager
from ingestion.client import IngestionClient
from ingestion.config import Settings, settings
from ingestion.processor import IngestionProcessor
from ingestion.repository import IngestionRepository


def setup_logging(log_level: str, log_file: Path | None = None) -> logging.Logger:
    """Configure logging.
    
    Args:
        log_level: Logging level string
        log_file: Optional log file path
        
    Returns:
        Configured logger
    """
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return logging.getLogger(__name__)


class IngestionRunner:
    """Orchestrates the ingestion process."""
    
    def __init__(self, config: Settings | None = None):
        """Initialize runner.
        
        Args:
            config: Settings instance (uses global settings if None)
        """
        self.config = config or settings
        self.logger = logging.getLogger(__name__)
    
    def run(self) -> int:
        """Run the ingestion process.
        
        Returns:
            Exit code (0 for success, 1 for error)
        """
        # Setup logging
        logger = setup_logging(
            self.config.log_level,
            self.config.log_file if self.config.log_file else None
        )
        
        logger.info("=" * 60)
        logger.info("NVIDIA RAG Ingestion Started")
        logger.info("=" * 60)
        logger.info(f"Database: {self.config.db_path}")
        logger.info(f"Ingestor: {self.config.base_url}")
        logger.info(f"Collection: {self.config.collection_name}")
        logger.info(f"Batch size: {self.config.batch_size}")
        if self.config.proxies:
            logger.info(f"Proxy HTTP: {self.config.proxy_http or 'Not set'}")
            logger.info(f"Proxy HTTPS: {self.config.proxy_https or 'Not set'}")
        
        # Verify database exists
        if not self.config.db_path.exists():
            logger.error(f"Database not found: {self.config.db_path}")
            return 1
        
        try:
            # Initialize components
            repository = IngestionRepository(self.config.db_path)
            client = IngestionClient(
                base_url=self.config.base_url,
                logger=logger,
                poll_timeout=self.config.poll_timeout,
                proxies=self.config.proxies,
            )
            checkpoint_manager = CheckpointManager(self.config.checkpoint_file)
            
            # Get initial stats
            stats = repository.get_ingestion_stats()
            logger.info(f"Database stats: {stats}")
            
            # Create collection if requested
            if self.config.create_collection:
                try:
                    logger.info(f"Creating collection: {self.config.collection_name}")
                    client.create_collection(
                        collection_name=self.config.collection_name,
                        embedding_dimension=self.config.embedding_dimension,
                    )
                except Exception as e:
                    logger.warning(f"Collection creation failed (may already exist): {e}")
            
            # Fetch existing documents to skip already ingested files
            existing_docs: set[str] = set()
            try:
                logger.info(
                    f"Fetching existing documents from collection '{self.config.collection_name}' "
                    f"to skip already ingested files..."
                )
                existing_docs = set(client.list_documents(self.config.collection_name))
                if existing_docs:
                    logger.info(f"Found {len(existing_docs)} already ingested documents")
            except Exception as e:
                logger.warning(f"Could not fetch existing documents: {e}")
            
            # Load checkpoint if resuming
            offset = 0
            batch_num = 0
            
            if self.config.resume:
                checkpoint = checkpoint_manager.load()
                if checkpoint:
                    offset = checkpoint.get("offset", 0)
                    batch_num = checkpoint.get("batch_num", 0)
                    logger.info(f"Resuming from checkpoint: offset={offset}, batch={batch_num}")
                else:
                    logger.warning("No checkpoint found, starting from beginning")
            
            # Create processor and run
            processor = IngestionProcessor(
                repository=repository,
                client=client,
                checkpoint_manager=checkpoint_manager,
                settings=self.config,
                existing_docs=existing_docs,
            )
            
            final_stats = processor.run(offset=offset, batch_num=batch_num)
            
            # Print summary
            processor.print_summary()
            
            # Delete collection if requested
            if self.config.delete_collection:
                try:
                    logger.info(f"Deleting collection: {self.config.collection_name}")
                    client.delete_collections([self.config.collection_name])
                except Exception as e:
                    logger.error(f"Failed to delete collection: {e}")
            
            logger.info("Ingestion completed successfully")
            return 0
            
        except KeyboardInterrupt:
            logger.warning("Ingestion interrupted by user")
            return 130  # Standard exit code for Ctrl+C
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            return 1


def main():
    """Entry point for CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="NVIDIA RAG ingestion from bootstrap manifest database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run ingestion
  uv run python -m ingestion --db-path ./manifest.db --collection-name docs
  
  # Resume from checkpoint
  uv run python -m ingestion --resume --checkpoint-file ./checkpoint.json
  
  # With custom settings
  uv run python -m ingestion \\
    --db-path ./manifest.db \\
    --ingestor-host localhost \\
    --ingestor-port 8082 \\
    --collection-name secure_docs \\
    --batch-size 100
        """
    )
    
    # Database arguments
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Path to bootstrap manifest database",
    )
    
    # NVIDIA RAG arguments
    parser.add_argument(
        "--ingestor-host",
        type=str,
        default=None,
        help="NVIDIA RAG ingestor host",
    )
    parser.add_argument(
        "--ingestor-port",
        type=int,
        default=None,
        help="NVIDIA RAG ingestor port",
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default=None,
        help="RAG collection name",
    )
    parser.add_argument(
        "--embedding-dimension",
        type=int,
        default=None,
        help="Embedding dimension (default: 2048)",
    )
    
    # Proxy arguments
    parser.add_argument(
        "--proxy-http",
        type=str,
        default=None,
        help="HTTP proxy URL (e.g., http://10.10.1.10:3128)",
    )
    parser.add_argument(
        "--proxy-https",
        type=str,
        default=None,
        help="HTTPS proxy URL (e.g., http://10.10.1.10:1080)",
    )
    
    # Processing arguments
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Files per batch (default: 100)",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=None,
        help="Save checkpoint every N batches (default: 10)",
    )
    parser.add_argument(
        "--batch-delay",
        type=float,
        default=None,
        help="Delay between batches in seconds (default: 0)",
    )
    
    # Retry arguments
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Maximum retry attempts per file (default: 3)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=None,
        help="Initial retry delay in seconds (default: 1.0)",
    )
    
    # Feature flags
    parser.add_argument(
        "--create-collection",
        action="store_true",
        default=None,
        help="Create collection if it doesn't exist",
    )
    parser.add_argument(
        "--delete-collection",
        action="store_true",
        default=None,
        help="Delete collection after ingestion",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=None,
        help="Resume from checkpoint",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        default=None,
        help="Continue processing on individual file errors",
    )
    parser.add_argument(
        "--no-create-collection",
        action="store_false",
        dest="create_collection",
        help="Don't create collection",
    )
    parser.add_argument(
        "--no-continue-on-error",
        action="store_false",
        dest="continue_on_error",
        help="Stop on first error",
    )
    
    # Checkpoint
    parser.add_argument(
        "--checkpoint-file",
        type=Path,
        default=None,
        help="Checkpoint file path",
    )
    
    # Logging
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
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    
    args = parser.parse_args()
    
    # Override settings with CLI args
    if args.db_path:
        settings.db_path = args.db_path
    if args.ingestor_host:
        settings.ingestor_host = args.ingestor_host
    if args.ingestor_port:
        settings.ingestor_port = args.ingestor_port
    if args.collection_name:
        settings.collection_name = args.collection_name
    if args.embedding_dimension:
        settings.embedding_dimension = args.embedding_dimension
    if args.proxy_http:
        settings.proxy_http = args.proxy_http
    if args.proxy_https:
        settings.proxy_https = args.proxy_https
    if args.batch_size:
        settings.batch_size = args.batch_size
    if args.checkpoint_interval:
        settings.checkpoint_interval = args.checkpoint_interval
    if args.batch_delay:
        settings.batch_delay = args.batch_delay
    if args.max_retries:
        settings.max_retries = args.max_retries
    if args.retry_delay:
        settings.retry_delay = args.retry_delay
    if args.create_collection is not None:
        settings.create_collection = args.create_collection
    if args.delete_collection:
        settings.delete_collection = args.delete_collection
    if args.resume:
        settings.resume = args.resume
    if args.continue_on_error is not None:
        settings.continue_on_error = args.continue_on_error
    if args.checkpoint_file:
        settings.checkpoint_file = args.checkpoint_file
    if args.log_level:
        settings.log_level = args.log_level
    if args.log_file:
        settings.log_file = args.log_file
    if args.verbose:
        settings.verbose = args.verbose
        settings.log_level = "DEBUG"
    
    # Run
    runner = IngestionRunner()
    sys.exit(runner.run())


if __name__ == "__main__":
    main()
