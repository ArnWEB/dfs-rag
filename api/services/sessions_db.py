import sqlite3
import logging
from pathlib import Path
from typing import Any, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# Central database for tracking sessions
API_DIR = Path(__file__).resolve().parent.parent
SESSIONS_DB_PATH = API_DIR / "data" / "sessions.db"
SESSIONS_DIR = API_DIR / "data" / "sessions"

class SessionsDBService:
    def __init__(self, db_path: Path = SESSIONS_DB_PATH):
        self.db_path = db_path
        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                dfs_path TEXT,
                db_path TEXT NOT NULL,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Migration: Add user_id column if it doesn't exist
        cursor.execute("PRAGMA table_info(sessions)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "user_id" not in columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT")
            
        conn.commit()
        conn.close()

    def create_session(self, name: str, user_id: str, dfs_path: str = "") -> dict[str, Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        session_id = str(uuid.uuid4())
        # Autogenerate specific manifest DB path for this session
        session_dir = SESSIONS_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        db_path = (session_dir / "manifest.db").as_posix()
        
        now = datetime.utcnow().isoformat()
        
        try:
            cursor.execute(
                "INSERT INTO sessions (id, name, status, dfs_path, db_path, user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, name, "created", dfs_path, db_path, user_id, now, now)
            )
            conn.commit()
            return self.get_session(session_id, user_id)
        finally:
            conn.close()

    def get_session(self, session_id: str, user_id: str | None = None) -> Optional[dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if user_id:
                cursor.execute("SELECT * FROM sessions WHERE id = ? AND (user_id = ? OR user_id IS NULL)", (session_id, user_id))
            else:
                cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def list_sessions(self, user_id: str, limit: int = 50, offset: int = 0) -> List[dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM sessions WHERE user_id = ? OR user_id IS NULL ORDER BY created_at DESC LIMIT ? OFFSET ?", (user_id, limit, offset))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_session(self, session_id: str, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if not updates:
                return self.get_session(session_id)
                
            updates["updated_at"] = datetime.utcnow().isoformat()
            
            set_clauses = []
            values = []
            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)
                
            values.append(session_id)
            
            query = f"UPDATE sessions SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            
            return self.get_session(session_id)
        finally:
            conn.close()

sessions_db = SessionsDBService()
