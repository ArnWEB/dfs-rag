"""Repository for ingestion database operations."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class FileRecord:
    """Represents a file record from the manifest."""
    file_path: str
    file_name: str
    parent_dir: str
    size: int | None
    mtime: int | None
    raw_acl: str | None
    acl_captured: bool
    status: str
    

class IngestionRepository:
    """Repository for ingestion operations on manifest database."""
    
    def __init__(self, db_path: Path):
        """Initialize repository.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_pending_files(
        self,
        batch_size: int,
        offset: int = 0,
    ) -> list[FileRecord]:
        """Get batch of pending/failed files from database.
        
        Args:
            batch_size: Number of records to fetch
            offset: Database offset for pagination
            
        Returns:
            List of FileRecord objects
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Query files with status='discovered' that haven't been ingested
            # Include pending and failed for retry
            cursor.execute("""
                SELECT file_path, file_name, parent_dir, size, mtime, 
                       raw_acl, acl_captured, status
                FROM manifest
                WHERE status = 'discovered'
                  AND (ingestion_status IS NULL 
                       OR ingestion_status = 'pending' 
                       OR ingestion_status = 'failed')
                ORDER BY file_path
                LIMIT ? OFFSET ?
            """, (batch_size, offset))
            
            records = []
            for row in cursor.fetchall():
                records.append(FileRecord(
                    file_path=row["file_path"],
                    file_name=row["file_name"],
                    parent_dir=row["parent_dir"],
                    size=row["size"],
                    mtime=row["mtime"],
                    raw_acl=row["raw_acl"],
                    acl_captured=bool(row["acl_captured"]),
                    status=row["status"],
                ))
            
            return records
            
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error fetching pending files: {e}") from e
        finally:
            conn.close()
    
    def update_ingestion_status(
        self,
        file_path: str,
        status: str,
        error: str | None = None,
    ) -> None:
        """Update ingestion status for a file.
        
        Args:
            file_path: Path to the file
            status: New status (ingesting/completed/failed)
            error: Optional error message
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE manifest
                SET ingestion_status = ?,
                    ingestion_attempts = COALESCE(ingestion_attempts, 0) + 1,
                    ingestion_error = ?,
                    ingested_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE ingested_at END
                WHERE file_path = ?
            """, (status, error, status, file_path))
            
            conn.commit()
            
        except sqlite3.Error as e:
            conn.rollback()
            raise RuntimeError(f"Database error updating status: {e}") from e
        finally:
            conn.close()
    
    def get_ingestion_stats(self) -> dict[str, Any]:
        """Get ingestion statistics from database.
        
        Returns:
            Dictionary with count statistics
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if ingestion_status column exists
            cursor.execute("PRAGMA table_info(manifest)")
            columns = [row["name"] for row in cursor.fetchall()]
            
            if "ingestion_status" not in columns:
                # Fallback: count discovered files vs files with any ingestion attempt
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_discovered,
                        SUM(CASE WHEN status = 'discovered' THEN 1 ELSE 0 END) as discovered,
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
                    FROM manifest
                    WHERE is_directory = 0
                """)
                row = cursor.fetchone()
                return {
                    "total": row["total_discovered"] or 0,
                    "pending": row["pending"] or 0,
                    "completed": 0,
                    "failed": 0,
                    "ingesting": 0,
                }
            
            # Full stats with ingestion_status
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN ingestion_status IS NULL OR ingestion_status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN ingestion_status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN ingestion_status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN ingestion_status = 'ingesting' THEN 1 ELSE 0 END) as ingesting
                FROM manifest
                WHERE is_directory = 0
                  AND status = 'discovered'
            """)
            
            row = cursor.fetchone()
            return {
                "total": row["total"] or 0,
                "pending": row["pending"] or 0,
                "completed": row["completed"] or 0,
                "failed": row["failed"] or 0,
                "ingesting": row["ingesting"] or 0,
            }
            
        except sqlite3.Error as e:
            raise RuntimeError(f"Database error getting stats: {e}") from e
        finally:
            conn.close()
    
    def verify_file_exists(self, file_path: str) -> bool:
        """Verify that a file exists on disk.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file exists
        """
        return Path(file_path).exists()
