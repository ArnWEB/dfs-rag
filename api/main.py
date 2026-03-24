"""FastAPI backend for DFS RAG application."""

import sys
import os

# Add api directory to path
api_path = os.path.dirname(os.path.abspath(__file__))
parent_path = os.path.dirname(api_path)
sys.path.insert(0, api_path)
sys.path.insert(0, parent_path)

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.services.process_manager import process_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DFS RAG API server")
    asyncio.create_task(monitor_processes())
    yield
    logger.info("Shutting down DFS RAG API server")
    await process_manager.stop_bootstrap()
    await process_manager.stop_ingestion()


async def monitor_processes():
    while True:
        await asyncio.sleep(2)
        await process_manager.check_process_health()


app = FastAPI(title="DFS RAG API", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

from api.routers import bootstrap, ingestion, files, collections, sessions

app.include_router(bootstrap.router, tags=["bootstrap"])
app.include_router(ingestion.router, tags=["ingestion"])
app.include_router(files.router, tags=["files"])
app.include_router(collections.router, tags=["collections"])
app.include_router(sessions.router, tags=["sessions"])


@app.get("/api/health")
async def health_check():
    active_ingestions = process_manager.list_active_ingestions()
    return {
        "status": "healthy",
        "bootstrap_running": process_manager.bootstrap_status.running,
        "ingestion_running": len(active_ingestions) > 0,
        "active_ingestions_count": len(active_ingestions)
    }



@app.get("/")
async def root():
    return {"name": "DFS RAG API", "version": "1.0.0", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8040)
