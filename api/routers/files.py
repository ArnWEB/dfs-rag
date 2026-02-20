"""Files API router."""
from fastapi import APIRouter, Query
from typing import Any

from api.services.database import DatabaseService
from pathlib import Path

router = APIRouter(prefix="/api/files", tags=["files"])

@router.get("")
async def get_files(
    search: str | None = Query(None),
    status: str | None = Query(None),
    ingestion_status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    page: int = Query(1, ge=1),
    db_path: str | None = Query(None),
) -> dict[str, Any]:
    offset = (page - 1) * limit
    files = DatabaseService(db_path=Path(db_path)).get_files(search=search, status=status, ingestion_status=ingestion_status, limit=limit, offset=offset)
    total = DatabaseService(db_path=Path(db_path)).get_total_file_count(search=search, status=status, ingestion_status=ingestion_status)
    return {"files": files, "pagination": {"page": page, "limit": limit, "total": total, "pages": (total + limit - 1) // limit if total > 0 else 0}}

@router.get("/{file_id}")
async def get_file(file_id: int,db_path: str | None = Query(None) ) -> dict[str, Any]:
    files = DatabaseService(db_path=Path(db_path)).get_files(limit=1, offset=file_id - 1)
    if not files:
        return {"error": "File not found"}
    return files[0]
