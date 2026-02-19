"""Database schema definitions."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Manifest(Base):
    """Manifest table for file discovery records."""
    
    __tablename__ = "manifest"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String, nullable=False, unique=True, index=True)
    file_name = Column(String, nullable=False, index=True)
    parent_dir = Column(String, nullable=False, index=True)
    size = Column(Integer, nullable=True)
    mtime = Column(Integer, nullable=True)  # Store as Unix timestamp
    raw_acl = Column(Text, nullable=True)
    acl_captured = Column(Boolean, default=False, index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    ingestion_status = Column(String, nullable=False, default="pending", index=True)
    ingestion_attempts = Column(Integer, default=0)
    ingestion_error = Column(Text, nullable=True)
    ingested_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    is_directory = Column(Boolean, default=False, index=True)
    first_seen = Column(DateTime, server_default=func.now())
    last_seen = Column(DateTime, server_default=func.now(), onupdate=func.now())
    schema_version = Column(Integer, default=1)
    
    __table_args__ = (
        Index("idx_manifest_status_path", "status", "file_path"),
        Index("idx_manifest_ingestion_status", "ingestion_status"),
        Index("idx_manifest_parent", "parent_dir", "file_name"),
        Index("idx_manifest_error", "status", "error"),
    )


# SQL for creating the table and indexes separately
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS manifest (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    file_name TEXT NOT NULL,
    parent_dir TEXT NOT NULL,
    size INTEGER,
    mtime INTEGER,
    raw_acl TEXT,
    acl_captured BOOLEAN DEFAULT FALSE,
    status TEXT DEFAULT 'pending' NOT NULL,
    ingestion_status TEXT DEFAULT 'pending' NOT NULL,
    ingestion_attempts INTEGER DEFAULT 0,
    ingestion_error TEXT,
    ingested_at TIMESTAMP,
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    is_directory BOOLEAN DEFAULT FALSE,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    schema_version INTEGER DEFAULT 1
)
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_manifest_path ON manifest(file_path)",
    "CREATE INDEX IF NOT EXISTS idx_manifest_name ON manifest(file_name)",
    "CREATE INDEX IF NOT EXISTS idx_manifest_parent ON manifest(parent_dir)",
    "CREATE INDEX IF NOT EXISTS idx_manifest_status ON manifest(status)",
    "CREATE INDEX IF NOT EXISTS idx_manifest_ingestion_status ON manifest(ingestion_status)",
    "CREATE INDEX IF NOT EXISTS idx_manifest_acl ON manifest(acl_captured)",
    "CREATE INDEX IF NOT EXISTS idx_manifest_dir ON manifest(is_directory)",
    "CREATE INDEX IF NOT EXISTS idx_manifest_status_path ON manifest(status, file_path)",
    "CREATE INDEX IF NOT EXISTS idx_manifest_parent_name ON manifest(parent_dir, file_name)",
]