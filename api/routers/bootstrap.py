"""Bootstrap API router."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path

from api.services.process_manager import process_manager
from api.services.database import DatabaseService

router = APIRouter(prefix="/api/bootstrap", tags=["bootstrap"])

class BootstrapStartRequest(BaseModel):
    dfs_path: str
    db_path: str | None = None
    workers: int = 8
    batch_size: int = 500
    timeout: int = 5
    log_level: str = "INFO"
    acl_extractor: str = "getfacl"
    session_id: str | None = None

class GetStatsRequest(BaseModel):
    db_path: str

@router.post("/start")
async def start_bootstrap(request: BootstrapStartRequest):
    try:
        dfs_path = Path(request.dfs_path).resolve()
        if not dfs_path.exists():
            raise HTTPException(status_code=400, detail=f"Path does not exist: {request.dfs_path}")
        db_path = Path(request.db_path).resolve() if request.db_path else None
        job_id = await process_manager.start_bootstrap(dfs_path=dfs_path, db_path=db_path, workers=request.workers, batch_size=request.batch_size, timeout=request.timeout, log_level=request.log_level, acl_extractor=request.acl_extractor, session_id=request.session_id)
        return {"job_id": job_id, "status": "started"}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stop")
async def stop_bootstrap():
    try:
        stopped = await process_manager.stop_bootstrap()
        return {"stopped": stopped}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_bootstrap_status():
    status = process_manager.bootstrap_status
    return {"running": status.running, "job_id": status.job_id, "process_id": status.process_id, "start_time": status.start_time, "config": process_manager.get_bootstrap_config()}

@router.post("/stats")
async def get_bootstrap_stats(request: GetStatsRequest):
    try:
        return DatabaseService(db_path=Path(request.db_path)).get_bootstrap_stats()
    except FileNotFoundError:
        return {"total": 0, "directories": 0, "files": 0, "discovered": 0, "errors": 0, "acl_captured": 0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))