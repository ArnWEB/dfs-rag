"""Manifest repository for database operations."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import insert, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from bootstrap.models.file_record import FileRecord

from .schema import CREATE_INDEXES_SQL, CREATE_TABLE_SQL, Manifest


class ManifestRepository:
    """Repository for manifest database operations."""
    
    def __init__(self, engine: Engine):
        """Initialize repository with database engine.
        
        Args:
            engine: SQLAlchemy engine instance
        """
        self.engine = engine
        self.Session = sessionmaker(bind=engine)
    
    def init_schema(self) -> None:
        """Initialize database schema (create tables if not exists)."""
        with self.engine.connect() as conn:
            # Create table
            conn.execute(text(CREATE_TABLE_SQL))
            # Create indexes
            for index_sql in CREATE_INDEXES_SQL:
                conn.execute(text(index_sql))
            conn.commit()
    
    def bulk_upsert(
        self,
        records: Sequence[FileRecord],
    ) -> tuple[int, int]:
        """Bulk insert or ignore records.
        
        Uses INSERT OR IGNORE for SQLite (INSERT ... ON CONFLICT DO NOTHING).
        Updates last_seen timestamp for existing records.
        
        Args:
            records: List of FileRecord objects to insert
            
        Returns:
            Tuple of (inserted_count, skipped_count)
        """
        if not records:
            return 0, 0
        
        session: Session = self.Session()
        inserted = 0
        skipped = 0
        
        try:
            # Convert records to dicts
            record_dicts = [r.to_db_dict() for r in records]
            
            # Try bulk insert with ignore
            try:
                stmt = insert(Manifest).values(record_dicts)
                # SQLite supports ON CONFLICT DO NOTHING
                stmt = stmt.prefix_with("OR IGNORE")
                result = session.execute(stmt)
                inserted = result.rowcount
                
                # For records that already existed, update last_seen
                # We need to do this separately since we don't know which ones failed
                paths = [str(r.file_path) for r in records]
                update_stmt = (
                    update(Manifest)
                    .where(Manifest.file_path.in_(paths))
                    .values(last_seen=text("CURRENT_TIMESTAMP"))
                )
                session.execute(update_stmt)
                
                session.commit()
                
                # Calculate skipped (those we tried to insert minus actually inserted)
                skipped = len(records) - inserted
                
            except IntegrityError:
                # Fallback: insert one by one
                session.rollback()
                for record in records:
                    try:
                        stmt = insert(Manifest).values(record.to_db_dict())
                        stmt = stmt.prefix_with("OR IGNORE")
                        result = session.execute(stmt)
                        if result.rowcount > 0:
                            inserted += 1
                        else:
                            skipped += 1
                    except IntegrityError:
                        skipped += 1
                        session.rollback()
                
                session.commit()
                
        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(f"Database error during bulk upsert: {e}") from e
        finally:
            session.close()
        
        return inserted, skipped
    
    def record_permission_error(
        self,
        file_path: str,
        file_name: str,
        parent_dir: str,
        is_directory: bool,
        error_message: str,
    ) -> bool:
        """Record a permission error in the manifest.
        
        Args:
            file_path: Absolute path
            file_name: Base name
            parent_dir: Parent directory
            is_directory: Whether it's a directory
            error_message: Error description
            
        Returns:
            True if inserted/updated, False if skipped
        """
        session: Session = self.Session()
        
        try:
            # Try to insert, ignore if exists
            stmt = insert(Manifest).values(
                file_path=file_path,
                file_name=file_name,
                parent_dir=parent_dir,
                status="permission_denied",
                error=error_message,
                is_directory=is_directory,
            )
            stmt = stmt.prefix_with("OR IGNORE")
            result = session.execute(stmt)
            
            # If it existed, update the error info
            if result.rowcount == 0:
                update_stmt = (
                    update(Manifest)
                    .where(Manifest.file_path == file_path)
                    .values(
                        status="permission_denied",
                        error=error_message,
                        is_directory=is_directory,
                        retry_count=Manifest.retry_count + 1,
                        last_seen=text("CURRENT_TIMESTAMP"),
                    )
                )
                session.execute(update_stmt)
            
            session.commit()
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            raise DatabaseError(f"Failed to record permission error: {e}") from e
        finally:
            session.close()
    
    def get_stats(self) -> dict[str, Any]:
        """Get statistics from manifest.
        
        Returns:
            Dictionary with count statistics
        """
        session: Session = self.Session()
        
        try:
            result = session.execute(
                text("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'discovered' THEN 1 ELSE 0 END) as discovered,
                        SUM(CASE WHEN status = 'permission_denied' THEN 1 ELSE 0 END) as permission_denied,
                        SUM(CASE WHEN status = 'acl_failed' THEN 1 ELSE 0 END) as acl_failed,
                        SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors,
                        SUM(CASE WHEN acl_captured = 1 THEN 1 ELSE 0 END) as acl_captured
                    FROM manifest
                """)
            ).fetchone()
            
            return {
                "total": (result[0] if result else 0) or 0,
                "discovered": (result[1] if result else 0) or 0,
                "permission_denied": (result[2] if result else 0) or 0,
                "acl_failed": (result[3] if result else 0) or 0,
                "errors": (result[4] if result else 0) or 0,
                "acl_captured": (result[5] if result else 0) or 0,
            }
        finally:
            session.close()


class DatabaseError(Exception):
    """Custom exception for database errors."""
    pass