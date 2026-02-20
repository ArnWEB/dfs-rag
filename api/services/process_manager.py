"""Process manager for running bootstrap and ingestion."""
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Get the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Bootstrap and ingestion directories
BOOTSTRAP_DIR = PROJECT_ROOT / "bootstrap"
INGESTION_DIR = PROJECT_ROOT / "ingestion"


class ProcessStatus(BaseModel):
    running: bool = False
    job_id: str | None = None
    process_id: int | None = None
    start_time: float | None = None


class ProcessManager:
    def __init__(self):
        self._bootstrap_process: asyncio.subprocess.Process | None = None
        self._ingestion_process: asyncio.subprocess.Process | None = None
        self._bootstrap_status = ProcessStatus()
        self._ingestion_status = ProcessStatus()
        self._bootstrap_config: dict[str, Any] = {}
        self._ingestion_config: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    @property
    def bootstrap_status(self) -> ProcessStatus:
        return self._bootstrap_status

    @property
    def ingestion_status(self) -> ProcessStatus:
        return self._ingestion_status

    async def start_bootstrap(
        self,
        dfs_path: Path,
        db_path: Path | None = None,
        workers: int = 8,
        batch_size: int = 500,
        timeout: int = 5,
        log_level: str = "INFO",
        acl_extractor: str = "getfacl",
    ) -> str:
        async with self._lock:
            if self._bootstrap_status.running:
                raise RuntimeError("Bootstrap process already running")
            
            job_id = str(uuid4())
            
            # Run bootstrap from bootstrap directory using uv
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
            
            self._bootstrap_status = ProcessStatus(
                running=True,
                job_id=job_id,
                process_id=self._bootstrap_process.pid,
                start_time=asyncio.get_event_loop().time(),
            )
            
            self._bootstrap_config = {
                "dfs_path": str(dfs_path),
                "db_path": str(db_path) if db_path else "manifest.db",
                "workers": workers,
                "batch_size": batch_size,
                "timeout": timeout,
                "log_level": log_level,
                "acl_extractor": acl_extractor,
            }
            
            return job_id

    async def stop_bootstrap(self) -> bool:
        async with self._lock:
            if not self._bootstrap_status.running:
                return False
            if self._bootstrap_process:
                try:
                    if sys.platform == "win32":
                        self._bootstrap_process.terminate()
                        await asyncio.wait_for(self._bootstrap_process.wait(), timeout=10.0)
                    else:
                        self._bootstrap_process.send_signal(signal.SIGTERM)
                        await asyncio.wait_for(self._bootstrap_process.wait(), timeout=10.0)
                except asyncio.TimeoutError:
                    self._bootstrap_process.kill()
                    await self._bootstrap_process.wait()
                except Exception as e:
                    logger.error(f"Error stopping bootstrap: {e}")
            self._bootstrap_status = ProcessStatus()
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
        **kwargs,
    ) -> str:
        async with self._lock:
            if self._ingestion_status.running:
                raise RuntimeError("Ingestion process already running")
            
            job_id = str(uuid4())
            
            # Run ingestion from ingestion directory using uv
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
                cmd.extend(["--db-path", str(db_path)])
            
            if create_collection:
                cmd.append("--create-collection")
            
            if resume:
                cmd.append("--resume")
            
            logger.info(f"Starting ingestion: {' '.join(cmd)}")
            logger.info(f"Working directory: {INGESTION_DIR}")
            
            self._ingestion_process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(INGESTION_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            
            self._ingestion_status = ProcessStatus(
                running=True,
                job_id=job_id,
                process_id=self._ingestion_process.pid,
                start_time=asyncio.get_event_loop().time(),
            )
            
            self._ingestion_config = {
                "db_path": str(db_path) if db_path else "manifest.db",
                "collection_name": collection_name,
                "ingestor_host": ingestor_host,
                "ingestor_port": ingestor_port,
                "batch_size": batch_size,
                "checkpoint_interval": checkpoint_interval,
                "create_collection": create_collection,
                "resume": resume,
                "log_level": log_level,
            }
            
            return job_id

    async def stop_ingestion(self) -> bool:
        async with self._lock:
            if not self._ingestion_status.running:
                return False
            if self._ingestion_process:
                try:
                    if sys.platform == "win32":
                        self._ingestion_process.terminate()
                        await asyncio.wait_for(self._ingestion_process.wait(), timeout=10.0)
                    else:
                        self._ingestion_process.send_signal(signal.SIGTERM)
                        await asyncio.wait_for(self._ingestion_process.wait(), timeout=10.0)
                except asyncio.TimeoutError:
                    self._ingestion_process.kill()
                    await self._ingestion_process.wait()
                except Exception as e:
                    logger.error(f"Error stopping ingestion: {e}")
            self._ingestion_status = ProcessStatus()
            return True

    async def check_process_health(self):
        async with self._lock:
            if self._bootstrap_process and self._bootstrap_status.running:
                if self._bootstrap_process.returncode is not None:
                    self._bootstrap_status.running = False
            if self._ingestion_process and self._ingestion_status.running:
                if self._ingestion_process.returncode is not None:
                    self._ingestion_status.running = False

    def get_bootstrap_config(self) -> dict[str, Any]:
        return self._bootstrap_config

    def get_ingestion_config(self) -> dict[str, Any]:
        return self._ingestion_config


process_manager = ProcessManager()
