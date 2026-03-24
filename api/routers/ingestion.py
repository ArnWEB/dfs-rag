"""Ingestion API router."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path
from typing import Any

from api.services.process_manager import process_manager, MaxConcurrentError
from api.services.database import DatabaseService

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])


class IngestionStartRequest(BaseModel):
    db_path: str | None = None
    collection_name: str = "documents"
    ingestor_host: str = "localhost"
    ingestor_port: int = 8082
    batch_size: int = 100
    checkpoint_interval: int = 10
    create_collection: bool = True
    resume: bool = False
    log_level: str = "INFO"
    session_id: str | None = None


class StopIngestionRequest(BaseModel):
    session_id: str | None = None


class GetStatsRequest(BaseModel):
    db_path: str


@router.post("/start")
async def start_ingestion(request: IngestionStartRequest):
    try:
        db_path = Path(request.db_path).resolve() if request.db_path else None
        job_id = await process_manager.start_ingestion(
            db_path=db_path,
            collection_name=request.collection_name,
            ingestor_host=request.ingestor_host,
            ingestor_port=request.ingestor_port,
            batch_size=request.batch_size,
            checkpoint_interval=request.checkpoint_interval,
            create_collection=request.create_collection,
            resume=request.resume,
            log_level=request.log_level,
            session_id=request.session_id,
        )
        return {"job_id": job_id, "session_id": request.session_id, "status": "started"}
    except MaxConcurrentError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": str(e),
                "active_ingestions": e.active_ingestions,
            }
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_ingestion(request: StopIngestionRequest):
    try:
        stopped = await process_manager.stop_ingestion(session_id=request.session_id)
        return {"stopped": stopped}
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_ingestion_status(session_id: str | None = Query(None)):
    status = process_manager.ingestion_status(session_id)
    if not status:
        return {"running": False, "session_id": session_id}
    return {
        "running": status.running,
        "session_id": status.session_id,
        "job_id": status.job_id,
        "process_id": status.process_id,
        "start_time": status.start_time,
        "user_id": status.user_id,
        "user_name": status.user_name,
        "session_name": status.session_name,
        "config": process_manager.get_ingestion_config(session_id),
    }


@router.get("/active")
async def get_active_ingestions():
    active = process_manager.list_active_ingestions()
    return {
        "count": len(active),
        "active_ingestions": active,
    }


@router.post("/stats")
async def get_ingestion_stats(request: GetStatsRequest):
    try:
        return DatabaseService(db_path=Path(request.db_path)).get_ingestion_stats()
    except FileNotFoundError:
        return {"total": 0, "pending": 0, "completed": 0, "failed": 0, "ingesting": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
