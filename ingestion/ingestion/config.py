"""Configuration management for ingestion module."""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_prefix="INGESTION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # Paths - reuse bootstrap manifest database
    db_path: Path = Field(
        default=Path("./manifest.db"),
        description="Path to bootstrap manifest database",
    )
    checkpoint_file: Path = Field(
        default=Path("./ingestion_checkpoint.json"),
        description="Checkpoint file for resumable ingestion",
    )
    log_file: Path = Field(
        default=Path("./logs/ingestion.log"),
        description="Log file path",
    )
    
    # NVIDIA RAG Ingestor settings
    ingestor_host: str = Field(
        default="localhost",
        description="NVIDIA RAG ingestor host",
    )
    ingestor_port: int = Field(
        default=8082,
        description="NVIDIA RAG ingestor port",
    )
    collection_name: str = Field(
        default="documents",
        description="RAG collection name",
    )
    embedding_dimension: int = Field(
        default=2048,
        description="Embedding dimension for collection",
    )
    
    # Processing settings
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Files per batch",
    )
    checkpoint_interval: int = Field(
        default=10,
        ge=1,
        description="Save checkpoint every N batches",
    )
    batch_delay: float = Field(
        default=0.0,
        ge=0.0,
        description="Delay between batches in seconds",
    )
    
    # Retry settings
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts per file",
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        description="Initial retry delay in seconds",
    )
    
    # Timeouts
    poll_timeout: int = Field(
        default=3600,  # 1 hour
        ge=60,
        le=86400,  # 24 hours
        description="Polling timeout in seconds",
    )
    request_timeout: int = Field(
        default=300,  # 5 minutes
        ge=30,
        le=1800,  # 30 minutes
        description="HTTP request timeout in seconds",
    )
    
    # Content processing
    split_chunk_size: int = Field(
        default=512,
        ge=100,
        le=2048,
        description="Chunk size for document splitting",
    )
    split_chunk_overlap: int = Field(
        default=150,
        ge=0,
        le=512,
        description="Chunk overlap for document splitting",
    )
    generate_summary: bool = Field(
        default=True,
        description="Generate document summary",
    )
    blocking: bool = Field(
        default=False,
        description="Wait for ingestion to complete (async by default)",
    )
    skip_existing: bool = Field(
        default=True,
        description="Skip files already ingested in the collection",
    )
    
    # Feature flags
    create_collection: bool = Field(
        default=True,
        description="Create collection if it doesn't exist",
    )
    delete_collection: bool = Field(
        default=False,
        description="Delete collection after ingestion (for testing)",
    )
    resume: bool = Field(
        default=False,
        description="Resume from checkpoint",
    )
    continue_on_error: bool = Field(
        default=True,
        description="Continue processing on individual file errors",
    )
    
    # Proxy settings
    proxy_http: str | None = Field(
        default=None,
        description="HTTP proxy URL (e.g., http://10.10.1.10:3128)",
    )
    proxy_https: str | None = Field(
        default=None,
        description="HTTPS proxy URL (e.g., http://10.10.1.10:1080)",
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )
    verbose: bool = Field(
        default=False,
        description="Verbose output",
    )
    
    @property
    def proxies(self) -> dict[str, str] | None:
        """Get proxies dictionary for requests library."""
        proxies = {}
        if self.proxy_http:
            proxies["http"] = self.proxy_http
        if self.proxy_https:
            proxies["https"] = self.proxy_https
        return proxies if proxies else None
    
    @property
    def base_url(self) -> str:
        """Get base URL for NVIDIA RAG API."""
        return f"http://{self.ingestor_host}:{self.ingestor_port}"


# Global settings instance
settings = Settings()
