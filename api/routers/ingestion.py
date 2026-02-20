"""Ingestion API router."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path

from api.services.process_manager import process_manager
from api.services.database import DatabaseService
from api.websocket.manager import manager

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


class GetStatsRequest(BaseModel):
    db_path: str


@router.post("/start")
async def start_ingestion(request: IngestionStartRequest):
    try:
        db_path = Path(request.db_path) if request.db_path else None
        job_id = await process_manager.start_ingestion(db_path=db_path, collection_name=request.collection_name, ingestor_host=request.ingestor_host, ingestor_port=request.ingestor_port, batch_size=request.batch_size, checkpoint_interval=request.checkpoint_interval, create_collection=request.create_collection, resume=request.resume, log_level=request.log_level)
        await manager.send_event("ingestion:started", {"job_id": job_id, "config": process_manager.get_ingestion_config()})
        return {"job_id": job_id, "status": "started"}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_ingestion():
    try:
        stopped = await process_manager.stop_ingestion()
        if stopped:
            await manager.send_event("ingestion:stopped", {"message": "Ingestion stopped by user"})
        return {"stopped": stopped}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_ingestion_status():
    status = process_manager.ingestion_status
    return {"running": status.running, "job_id": status.job_id, "process_id": status.process_id, "start_time": status.start_time, "config": process_manager.get_ingestion_config()}

@router.post("/stats")
async def get_ingestion_stats(request: GetStatsRequest):
    return DatabaseService(db_path=Path(request.db_path)).get_ingestion_stats()