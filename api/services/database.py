"""Database service for reading manifest SQLite database."""
from pathlib import Path
from typing import Any
import sqlite3
import logging

class DatabaseService:
    def __init__(self, db_path: Path | None = None):
        logging.info(f"Initializing DatabaseService with db_path: {db_path}")
        self.db_path = db_path or Path("./manifest.db")

    def _get_connection(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found at {self.db_path}")
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def get_bootstrap_stats(self) -> dict[str, Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_directory = 1 THEN 1 ELSE 0 END) as directories,
                    SUM(CASE WHEN is_directory = 0 THEN 1 ELSE 0 END) as files,
                    SUM(CASE WHEN status = 'discovered' THEN 1 ELSE 0 END) as discovered,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors,
                    SUM(CASE WHEN acl_captured = 1 THEN 1 ELSE 0 END) as acl_captured
                FROM manifest
            """)
            row = cursor.fetchone()
            if row is None or row["total"] == 0:
                return {"total": 0, "directories": 0, "files": 0, "discovered": 0, "errors": 0, "acl_captured": 0}
            return {"total": row["total"] or 0, "directories": row["directories"] or 0, "files": row["files"] or 0, "discovered": row["discovered"] or 0, "errors": row["errors"] or 0, "acl_captured": row["acl_captured"] or 0}
        except sqlite3.Error as e:
            return {"error": str(e)}
        finally:
            conn.close()

    def get_ingestion_stats(self) -> dict[str, Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(manifest)")
            columns = [row[1] for row in cursor.fetchall()]
            if "ingestion_status" not in columns:
                cursor.execute("SELECT COUNT(*) as total_discovered, SUM(CASE WHEN status = 'discovered' THEN 1 ELSE 0 END) as discovered FROM manifest WHERE is_directory = 0")
                row = cursor.fetchone()
                return {"total": row["total_discovered"] or 0, "pending": row["discovered"] or 0, "completed": 0, "failed": 0, "ingesting": 0}
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN ingestion_status IS NULL OR ingestion_status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN ingestion_status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN ingestion_status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN ingestion_status = 'ingesting' THEN 1 ELSE 0 END) as ingesting
                FROM manifest WHERE is_directory = 0 AND status = 'discovered'
            """)
            row = cursor.fetchone()
            return {"total": row["total"] or 0, "pending": row["pending"] or 0, "completed": row["completed"] or 0, "failed": row["failed"] or 0, "ingesting": row["ingesting"] or 0}
        except sqlite3.Error as e:
            return {"error": str(e)}
        finally:
            conn.close()

    def get_files(self, search: str | None = None, status: str | None = None, ingestion_status: str | None = None, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT id, file_path, file_name, parent_dir, size, mtime, status, ingestion_status, ingestion_error, ingested_at, error, is_directory, first_seen, last_seen FROM manifest WHERE 1=1"
            params = []
            if search:
                query += " AND (file_name LIKE ? OR file_path LIKE ?)"
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern])
            if status:
                query += " AND status = ?"
                params.append(status)
            if ingestion_status:
                query += " AND ingestion_status = ?"
                params.append(ingestion_status)
            query += " ORDER BY last_seen DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [{"id": r["id"], "file_path": r["file_path"], "file_name": r["file_name"], "parent_dir": r["parent_dir"], "size": r["size"], "mtime": r["mtime"], "status": r["status"], "ingestion_status": r["ingestion_status"], "ingestion_error": r["ingestion_error"], "ingested_at": r["ingested_at"], "error": r["error"], "is_directory": bool(r["is_directory"]), "first_seen": r["first_seen"], "last_seen": r["last_seen"]} for r in rows]
        except sqlite3.Error as e:
            return [{"error": str(e)}]
        finally:
            conn.close()

    def get_total_file_count(self, search: str | None = None, status: str | None = None, ingestion_status: str | None = None) -> int:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            query = "SELECT COUNT(*) as count FROM manifest WHERE 1=1"
            params = []
            if search:
                query += " AND (file_name LIKE ? OR file_path LIKE ?)"
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern])
            if status:
                query += " AND status = ?"
                params.append(status)
            if ingestion_status:
                query += " AND ingestion_status = ?"
                params.append(ingestion_status)
            cursor.execute(query, params)
            return cursor.fetchone()["count"] or 0
        except sqlite3.Error:
            return 0
        finally:
            conn.close()

# db_service = DatabaseService()
