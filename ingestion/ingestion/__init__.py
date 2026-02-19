"""Ingestion module for NVIDIA RAG."""

from ingestion.checkpoint import CheckpointManager
from ingestion.client import IngestionClient, IngestionError
from ingestion.config import Settings, settings
from ingestion.main import IngestionRunner, main
from ingestion.processor import IngestionProcessor, IngestionStats
from ingestion.repository import FileRecord, IngestionRepository

__version__ = "1.0.0"

__all__ = [
    "CheckpointManager",
    "IngestionClient",
    "IngestionError",
    "Settings",
    "settings",
    "IngestionRunner",
    "main",
    "IngestionProcessor",
    "IngestionStats",
    "FileRecord",
    "IngestionRepository",
]
