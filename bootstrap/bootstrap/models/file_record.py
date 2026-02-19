"""Data models for file records."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_serializer


class FileStatus(str, Enum):
    """Status of a file/directory in the manifest."""
    PENDING = "pending"
    DISCOVERED = "discovered"
    PERMISSION_DENIED = "permission_denied"
    ACL_FAILED = "acl_failed"
    ERROR = "error"
    SKIPPED = "skipped"


class ACLResult(BaseModel):
    """Result of ACL extraction attempt."""
    raw_acl: str | None = None
    captured: bool = False
    method: str = "unknown"  # 'getfacl', 'stat', 'failed'
    error: str | None = None


class FileRecord(BaseModel):
    """Complete record for a file or directory."""
    
    file_path: Path = Field(description="Absolute path to file/directory")
    file_name: str = Field(description="Base name of file/directory")
    parent_dir: Path = Field(description="Parent directory path")
    size: int | None = Field(default=None, description="File size in bytes")
    mtime: float | None = Field(default=None, description="Modification time (Unix timestamp)")
    raw_acl: str | None = Field(default=None, description="Raw ACL string or JSON")
    acl_captured: bool = Field(default=False, description="Whether ACL was successfully captured")
    status: FileStatus = Field(default=FileStatus.PENDING, description="Discovery status")
    error: str | None = Field(default=None, description="Error message if any")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts")
    is_directory: bool = Field(default=False, description="Whether this is a directory")
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    schema_version: int = Field(default=1, description="Schema version for migrations")
    
    @field_serializer("file_path", "parent_dir")
    def serialize_path(self, path: Path) -> str:
        """Serialize Path objects to strings."""
        return str(path)
    
    @field_serializer("first_seen", "last_seen")
    def serialize_datetime(self, dt: datetime) -> str:
        """Serialize datetime to ISO format."""
        return dt.isoformat()
    
    def to_db_dict(self) -> dict[str, Any]:
        """Convert to dictionary suitable for database insertion."""
        return {
            "file_path": str(self.file_path),
            "file_name": self.file_name,
            "parent_dir": str(self.parent_dir),
            "size": self.size,
            "mtime": self.mtime,
            "raw_acl": self.raw_acl,
            "acl_captured": self.acl_captured,
            "status": self.status.value,
            "error": self.error,
            "retry_count": self.retry_count,
            "is_directory": self.is_directory,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "schema_version": self.schema_version,
        }
    
    @classmethod
    def create_permission_error(
        cls,
        path: Path,
        is_directory: bool = False,
        error_message: str = "Permission denied",
    ) -> "FileRecord":
        """Create a record for a permission error."""
        return cls(
            file_path=path.resolve(),
            file_name=path.name,
            parent_dir=path.parent,
            status=FileStatus.PERMISSION_DENIED,
            error=error_message,
            is_directory=is_directory,
        )
    
    @classmethod
    def create_skipped(
        cls,
        path: Path,
        reason: str,
    ) -> "FileRecord":
        """Create a record for a skipped entry (e.g., symlink)."""
        return cls(
            file_path=path.resolve(),
            file_name=path.name,
            parent_dir=path.parent,
            status=FileStatus.SKIPPED,
            error=reason,
        )


class BootstrapStats(BaseModel):
    """Statistics for bootstrap run."""
    
    total_discovered: int = 0
    total_added: int = 0
    total_skipped: int = 0
    acl_captured: int = 0
    acl_failed: int = 0
    permission_errors: int = 0
    other_errors: int = 0
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    
    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds."""
        end = self.end_time or datetime.utcnow()
        return (end - self.start_time).total_seconds()
    
    @property
    def records_per_second(self) -> float:
        """Calculate processing rate."""
        duration = self.duration_seconds
        if duration <= 0:
            return 0.0
        return self.total_discovered / duration
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            "Bootstrap complete",
            f"  Total files discovered: {self.total_discovered:,}",
            f"  Records added: {self.total_added:,}",
            f"  Records skipped (already existed): {self.total_skipped:,}",
            f"  ACL captured: {self.acl_captured:,} ({self.acl_capture_rate:.1f}%)",
            f"  ACL failed: {self.acl_failed:,}",
            f"  Permission errors: {self.permission_errors:,}",
            f"  Other errors: {self.other_errors:,}",
            f"  Time elapsed: {self.duration_seconds:.1f}s",
            f"  Records/second: {self.records_per_second:.1f}",
        ]
        return "\n".join(lines)
    
    @property
    def acl_capture_rate(self) -> float:
        """Calculate ACL capture success rate."""
        total = self.acl_captured + self.acl_failed
        if total == 0:
            return 0.0
        return (self.acl_captured / total) * 100