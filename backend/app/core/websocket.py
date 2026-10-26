"""
websocket.py — Real-time WebSocket connection manager for live application updates.
Enables real-time notifications when officers send applications for rectification or update statuses.
"""

from __future__ import annotations

import logging
from typing import Dict, List
from fastapi import WebSocket

logger = logging.getLogger("aicte.websocket")


class ConnectionManager:
    """Manages active WebSocket connections subscribed to specific applications."""

    def __init__(self) -> None:
        # Map: application_id -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, application_id: str) -> None:
        await websocket.accept()
        self.active_connections.setdefault(application_id, []).append(websocket)
        logger.info("WebSocket client connected to application %s", application_id)

    def disconnect(self, websocket: WebSocket, application_id: str) -> None:
        if application_id in self.active_connections:
            if websocket in self.active_connections[application_id]:
                self.active_connections[application_id].remove(websocket)
            if not self.active_connections[application_id]:
                del self.active_connections[application_id]
        logger.info("WebSocket client disconnected from application %s", application_id)

    async def broadcast_to_application(self, application_id: str, message: dict) -> None:
        """Send a real-time message to all subscribers of a specific application."""
        if application_id not in self.active_connections:
            return

        dead_connections = []
        for connection in self.active_connections[application_id]:
            try:
                await connection.send_json(message)
            except Exception as exc:
                logger.warning("Failed to deliver WebSocket message: %s", exc)
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead, application_id)

    async def broadcast_to_all(self, message: dict) -> None:
        """Broadcast a message to every connected client across all applications."""
        for app_id in list(self.active_connections.keys()):
            await self.broadcast_to_application(app_id, message)


manager = ConnectionManager()
