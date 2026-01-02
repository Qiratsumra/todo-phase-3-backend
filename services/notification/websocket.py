# ========================================================================
# WebSocket Connection Manager
# ========================================================================

import json
import logging
from typing import Dict, Set, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected. Total: {len(self.active_connections[user_id])}")

    def disconnect(self, user_id: str, websocket: Optional[WebSocket] = None):
        if user_id not in self.active_connections:
            return
        if websocket:
            self.active_connections[user_id].discard(websocket)
        else:
            self.active_connections[user_id].clear()
        if not self.active_connections[user_id]:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected")

    async def send_personal_message(self, message: dict, user_id: str) -> int:
        if user_id not in self.active_connections:
            return 0
        message_json = json.dumps(message) if isinstance(message, dict) else str(message)
        successful = 0
        disconnected = []
        for ws in list(self.active_connections[user_id]):
            try:
                await ws.send_text(message_json)
                successful += 1
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(user_id, ws)
        return successful

    def is_user_connected(self, user_id: str) -> bool:
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
