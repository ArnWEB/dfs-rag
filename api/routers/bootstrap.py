"""Bootstrap API router."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path

from api.services.process_manager import process_manager
from api.services.database import DatabaseService
from api.websocket.manager import manager

router = APIRouter(prefix="/api/bootstrap", tags=["bootstrap"])

class BootstrapStartRequest(BaseModel):
    dfs_path: str
    db_path: str | None = None
    workers: int = 8
    batch_size: int = 500
    timeout: int = 5
    log_level: str = "INFO"
    acl_extractor: str = "getfacl"

class GetStatsRequest(BaseModel):
    db_path: str

@router.post("/start")
async def start_bootstrap(request: BootstrapStartRequest):
    try:
        dfs_path = Path(request.dfs_path)
        if not dfs_path.exists():
            raise HTTPException(status_code=400, detail=f"Path does not exist: {request.dfs_path}")
        db_path = Path(request.db_path) if request.db_path else None
        job_id = await process_manager.start_bootstrap(dfs_path=dfs_path, db_path=db_path, workers=request.workers, batch_size=request.batch_size, timeout=request.timeout, log_level=request.log_level, acl_extractor=request.acl_extractor)
        await manager.send_event("bootstrap:started", {"job_id": job_id, "config": process_manager.get_bootstrap_config()})
        return {"job_id": job_id, "status": "started"}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_bootstrap():
    try:
        stopped = await process_manager.stop_bootstrap()
        if stopped:
            await manager.send_event("bootstrap:stopped", {"message": "Bootstrap stopped by user"})
        return {"stopped": stopped}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_bootstrap_status():
    status = process_manager.bootstrap_status
    return {"running": status.running, "job_id": status.job_id, "process_id": status.process_id, "start_time": status.start_time, "config": process_manager.get_bootstrap_config()}

@router.post("/stats")
async def get_bootstrap_stats(request: GetStatsRequest):
    return DatabaseService(db_path=Path(request.db_path)).get_bootstrap_stats()