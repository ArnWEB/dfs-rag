"""Structured logging configuration."""

import logging
import sys
from pathlib import Path

import structlog

# Try to import colorama for Windows color support
try:
    import colorama
    colorama.init()
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False


def configure_logging(
    log_level: str = "INFO",
    log_file: Path | None = None,
    format_type: str = "console",
) -> structlog.BoundLogger:
    """Configure structured logging with file and console output.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (JSON format)
        format_type: 'console' for human-readable, 'json' for structured
        
    Returns:
        Configured structlog logger
    """
    # Ensure log directory exists
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Standard library logging setup
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Structlog processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.ExtraAdder(),
    ]
    
    if format_type == "json":
        # JSON format for file logging
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level.upper())
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Console format with colors (disable colors on Windows without colorama)
        use_colors = HAS_COLORAMA or sys.platform != "win32"
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=use_colors),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level.upper())
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    logger = structlog.get_logger()
    
    # Add file handler for JSON logs if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        # JSON formatter for file
        json_formatter = structlog.stdlib.ProcessorFormatter(
            processor=structlog.processors.JSONRenderer(),
            foreign_pre_chain=shared_processors,
        )
        file_handler.setFormatter(json_formatter)
        
        # Add to root logger
        logging.getLogger().addHandler(file_handler)
    
    return logger