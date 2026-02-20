"""WebSocket connection manager for real-time updates."""
import asyncio
import json
import logging
from datetime import datetime
from uuid import uuid4
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: str | None = None) -> str:
        await websocket.accept()
        client_id = client_id or str(uuid4())
        async with self._lock:
            self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client connected: {client_id}")
        return client_id

    async def disconnect(self, client_id: str):
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
                logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_personal(self, client_id: str, message: dict[str, Any]):
        async with self._lock:
            websocket = self.active_connections.get(client_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to {client_id}: {e}")

    async def broadcast(self, message: dict[str, Any], exclude: set[str] | None = None):
        exclude = exclude or set()
        async with self._lock:
            connections = list(self.active_connections.items())
        for client_id, websocket in connections:
            if client_id not in exclude:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to {client_id}: {e}")

    async def send_event(self, event_type: str, data: dict[str, Any], client_id: str | None = None):
        message = {"type": event_type, "data": data, "timestamp": datetime.utcnow().isoformat()}
        if client_id:
            await self.send_personal(client_id, message)
        else:
            await self.broadcast(message)

    @property
    def connected_count(self) -> int:
        return len(self.active_connections)

manager = ConnectionManager()
