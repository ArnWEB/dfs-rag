"""Configuration management for bootstrap manifest builder."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_prefix="BOOTSTRAP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Paths
    dfs_path: Path = Field(
        default=Path("/mnt/dfs_share"),
        description="Root path of DFS share to scan",
    )
    db_path: Path = Field(
        default=Path("./manifest.db"),
        description="SQLite database file path",
    )
    log_file: Path = Field(
        default=Path("./logs/bootstrap.log"),
        description="Log file path",
    )
    
    # Concurrency
    workers: int = Field(
        default=8,
        ge=1,
        le=32,
        description="Number of concurrent workers for file operations",
    )
    batch_size: int = Field(
        default=500,
        ge=100,
        le=5000,
        description="Number of records per batch insert",
    )
    
    # Timeouts
    file_timeout_minutes: int = Field(
        default=5,
        ge=1,
        le=30,
        description="Timeout per file operation in minutes",
    )
    
    # Retry settings
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retries for transient errors",
    )
    retry_delay_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Initial retry delay with exponential backoff",
    )
    
    # Progress reporting
    progress_interval: int = Field(
        default=10000,
        ge=1000,
        description="Report progress every N files",
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )
    log_format: str = Field(
        default="console",
        pattern="^(console|json)$",
        description="Log format: console or json",
    )
    
    # Database
    sqlite_cache_mb: int = Field(
        default=64,
        ge=16,
        le=512,
        description="SQLite cache size in MB",
    )
    
    @property
    def file_timeout_seconds(self) -> float:
        """Get file timeout in seconds."""
        return self.file_timeout_minutes * 60.0


# Global settings instance
settings = Settings()