"""Process manager for running bootstrap and ingestion."""
import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BOOTSTRAP_DIR = PROJECT_ROOT / "bootstrap"
INGESTION_DIR = PROJECT_ROOT / "ingestion"

MAX_CONCURRENT_INGESTION = 5


class IngestionStatus(BaseModel):
    running: bool = False
    job_id: str | None = None
    process_id: int | None = None
    start_time: float | None = None
    session_id: str | None = None
    user_id: str | None = None
    user_name: str | None = None
    session_name: str | None = None


class ProcessManager:
    def __init__(self):
        self._bootstrap_process: asyncio.subprocess.Process | None = None
        self._bootstrap_status = IngestionStatus()
        self._bootstrap_config: dict[str, Any] = {}
        self._bootstrap_lock = asyncio.Lock()

        self._ingestion_processes: dict[str, asyncio.subprocess.Process] = {}
        self._ingestion_statuses: dict[str, IngestionStatus] = {}
        self._ingestion_configs: dict[str, dict[str, Any]] = {}
        self._ingestion_locks: dict[str, asyncio.Lock] = {}

    @property
    def bootstrap_status(self) -> IngestionStatus:
        return self._bootstrap_status

    def ingestion_status(self, session_id: str | None = None) -> IngestionStatus | None:
        if session_id:
            return self._ingestion_statuses.get(session_id)
        if self._ingestion_statuses:
            return next(iter(self._ingestion_statuses.values()))
        return None

    def list_active_ingestions(self) -> list[dict[str, Any]]:
        active = []
        for session_id, status in self._ingestion_statuses.items():
            if status.running:
                active.append({
                    "session_id": session_id,
                    "user_id": status.user_id,
                    "user_name": status.user_name,
                    "session_name": status.session_name,
                    "job_id": status.job_id,
                    "start_time": datetime.fromtimestamp(status.start_time).isoformat() if status.start_time else None,
                })
        return active

    def get_active_count(self) -> int:
        return sum(1 for s in self._ingestion_statuses.values() if s.running)

    def _get_or_create_lock(self, session_id: str) -> asyncio.Lock:
        if session_id not in self._ingestion_locks:
            self._ingestion_locks[session_id] = asyncio.Lock()
        return self._ingestion_locks[session_id]

    async def start_bootstrap(
        self,
        dfs_path: Path,
        db_path: Path | None = None,
        workers: int = 8,
        batch_size: int = 500,
        timeout: int = 5,
        log_level: str = "INFO",
        acl_extractor: str = "getfacl",
        session_id: str | None = None,
    ) -> str:
        async with self._bootstrap_lock:
            if self._bootstrap_status.running:
                raise RuntimeError("Bootstrap process already running")
            
            job_id = str(uuid4())
            
            cmd = [
                "uv", "run", "python", "-m", "bootstrap",
                str(rf"{dfs_path}"),
                "--workers", str(workers),
                "--batch-size", str(batch_size),
                "--timeout", str(timeout),
                "--log-level", log_level,
                "--acl-extractor", acl_extractor,
            ]
            
            if db_path:
                cmd.extend(["--db-path", str(rf"{db_path}")])
            
            logger.info(f"Starting bootstrap: {' '.join(cmd)}")
            logger.info(f"Working directory: {BOOTSTRAP_DIR}")
            
            self._bootstrap_process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(BOOTSTRAP_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            self._bootstrap_status = IngestionStatus(
                running=True,
                job_id=job_id,
                process_id=self._bootstrap_process.pid,
                start_time=asyncio.get_event_loop().time(),
                session_id=session_id,
            )
            
            self._bootstrap_config = {
                "dfs_path": str(dfs_path),
                "db_path": str(db_path) if db_path else "manifest.db",
                "workers": workers,
                "batch_size": batch_size,
                "timeout": timeout,
                "log_level": log_level,
                "acl_extractor": acl_extractor,
                "session_id": session_id,
            }
            
            if session_id:
                from api.services.sessions_db import sessions_db
                sessions_db.update_session(session_id, {"status": "bootstrapping"})
            
            return job_id

    async def stop_bootstrap(self) -> bool:
        async with self._bootstrap_lock:
            if not self._bootstrap_status.running:
                return False
            if self._bootstrap_process:
                try:
                    self._bootstrap_process.kill()
                    await self._bootstrap_process.wait()
                except Exception as e:
                    logger.error(f"Error stopping bootstrap: {e}")
            self._bootstrap_status = IngestionStatus()
            return True

    async def start_ingestion(
        self,
        db_path: Path | None = None,
        collection_name: str = "documents",
        ingestor_host: str = "localhost",
        ingestor_port: int = 8082,
        batch_size: int = 100,
        checkpoint_interval: int = 10,
        create_collection: bool = True,
        resume: bool = False,
        log_level: str = "INFO",
        session_id: str | None = None,
        user_id: str | None = None,
        user_name: str | None = None,
        **kwargs,
    ) -> str:
        if not session_id:
            session_id = str(uuid4())
        
        lock = self._get_or_create_lock(session_id)
        
        async with lock:
            if session_id in self._ingestion_statuses and self._ingestion_statuses[session_id].running:
                raise RuntimeError("Ingestion already running for this session")
            
            active_count = self.get_active_count()
            if active_count >= MAX_CONCURRENT_INGESTION:
                active_list = self.list_active_ingestions()
                raise MaxConcurrentError(
                    f"Maximum concurrent ingestions ({MAX_CONCURRENT_INGESTION}) reached",
                    active_ingestions=active_list
                )
            
            job_id = str(uuid4())
            
            cmd = [
                "uv", "run", "python", "-m", "ingestion",
                "--collection-name", collection_name,
                "--ingestor-host", ingestor_host,
                "--ingestor-port", str(ingestor_port),
                "--batch-size", str(batch_size),
                "--checkpoint-interval", str(checkpoint_interval),
                "--log-level", log_level,
            ]
            
            if db_path:
                cmd.extend(["--db-path", str(rf"{db_path}")])
            
            if create_collection:
                cmd.append("--create-collection")
            
            if resume:
                cmd.append("--resume")
            
            logger.info(f"Starting ingestion: {' '.join(cmd)}")
            logger.info(f"Working directory: {INGESTION_DIR}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(INGESTION_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            self._ingestion_processes[session_id] = process
            
            session_name = None
            if session_id:
                try:
                    from api.services.sessions_db import sessions_db
                    session = sessions_db.get_session(session_id)
                    if session:
                        session_name = session.get("name")
                except Exception:
                    pass
            
            self._ingestion_statuses[session_id] = IngestionStatus(
                running=True,
                job_id=job_id,
                process_id=process.pid,
                start_time=asyncio.get_event_loop().time(),
                session_id=session_id,
                user_id=user_id,
                user_name=user_name,
                session_name=session_name,
            )
            
            self._ingestion_configs[session_id] = {
                "db_path": str(db_path) if db_path else "manifest.db",
                "collection_name": collection_name,
                "ingestor_host": ingestor_host,
                "ingestor_port": ingestor_port,
                "batch_size": batch_size,
                "checkpoint_interval": checkpoint_interval,
                "create_collection": create_collection,
                "resume": resume,
                "log_level": log_level,
                "session_id": session_id,
            }
            
            if session_id:
                try:
                    from api.services.sessions_db import sessions_db
                    sessions_db.update_session(session_id, {"status": "ingesting"})
                except Exception:
                    pass
            
            return job_id

    async def stop_ingestion(self, session_id: str | None = None) -> bool:
        if not session_id:
            if len(self._ingestion_processes) == 1:
                session_id = next(iter(self._ingestion_processes))
            else:
                raise RuntimeError("session_id required when multiple ingestions are running")
        
        lock = self._get_or_create_lock(session_id)
        
        async with lock:
            if session_id not in self._ingestion_statuses or not self._ingestion_statuses[session_id].running:
                raise RuntimeError("No active ingestion for this session")
            
            process = self._ingestion_processes.get(session_id)
            if process:
                try:
                    logger.info(f"Force killing ingestion process {process.pid} for session {session_id}")
                    process.kill()
                    await process.wait()
                except Exception as e:
                    logger.error(f"Error stopping ingestion: {e}")
            
            self._ingestion_statuses[session_id] = IngestionStatus()
            self._ingestion_processes.pop(session_id, None)
            self._ingestion_configs.pop(session_id, None)
            
            if session_id:
                try:
                    from api.services.sessions_db import sessions_db
                    sessions_db.update_session(session_id, {"status": "completed"})
                except Exception:
                    pass
            
            return True

    async def check_process_health(self):
        # Check bootstrap status
        if self._bootstrap_status.running and self._bootstrap_process:
            if self._bootstrap_process.returncode is not None:
                logger.info(f"Bootstrap process has finished with code {self._bootstrap_process.returncode}")
                self._bootstrap_status.running = False
                if self._bootstrap_status.session_id:
                    try:
                        from api.services.sessions_db import sessions_db
                        new_status = "bootstrap_completed" if self._bootstrap_process.returncode == 0 else "failed"
                        sessions_db.update_session(self._bootstrap_status.session_id, {"status": new_status})
                    except Exception:
                        pass
        
        # Check ingestion statuses
        for session_id in list(self._ingestion_processes.keys()):
            status = self._ingestion_statuses.get(session_id)
            process = self._ingestion_processes.get(session_id)
            
            if status and process:
                if process.returncode is not None:
                    logger.info(f"Ingestion process for session {session_id} has finished with code {process.returncode}")
                    status.running = False
                    try:
                        from api.services.sessions_db import sessions_db
                        new_status = "completed" if process.returncode == 0 else "failed"
                        sessions_db.update_session(session_id, {"status": new_status})
                    except Exception:
                        pass

    def get_bootstrap_config(self) -> dict[str, Any]:
        return self._bootstrap_config

    def get_ingestion_config(self, session_id: str | None = None) -> dict[str, Any]:
        if session_id:
            return self._ingestion_configs.get(session_id, {})
        if self._ingestion_configs:
            return next(iter(self._ingestion_configs.values()))
        return {}


class MaxConcurrentError(RuntimeError):
    def __init__(self, message: str, active_ingestions: list[dict[str, Any]]):
        super().__init__(message)
        self.active_ingestions = active_ingestions


process_manager = ProcessManager()
