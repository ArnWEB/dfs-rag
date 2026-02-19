"""Database connection management with SQLite optimizations."""

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool


def create_database_engine(db_path: Path, cache_size_mb: int = 64) -> Engine:
    """Create optimized SQLite engine with WAL mode.
    
    Args:
        db_path: Path to SQLite database file
        cache_size_mb: Cache size in MB (default: 64)
        
    Returns:
        Configured SQLAlchemy engine
    """
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create engine with connection pooling
    engine = create_engine(
        f"sqlite:///{db_path}",
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    
    # Apply SQLite pragmas for performance
    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(conn, _):
        """Set SQLite pragmas for better performance."""
        cursor = conn.cursor()
        
        # WAL mode for concurrent reads during writes
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # Synchronous mode: NORMAL is safe with WAL, good performance
        cursor.execute("PRAGMA synchronous=NORMAL")
        
        # Cache size in pages (negative = KB)
        cache_kb = cache_size_mb * 1024
        cursor.execute(f"PRAGMA cache_size=-{cache_kb}")
        
        # Store temp tables in memory
        cursor.execute("PRAGMA temp_store=MEMORY")
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys=ON")
        
        # Memory-mapped I/O for faster reads
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
        
        cursor.close()
    
    return engine