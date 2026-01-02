# ========================================================================
# Notification Service - WebSocket real-time notifications
# ========================================================================

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Set

from dapr.clients import DaprClient
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from .consumer import ReminderEventConsumer
from .websocket import ConnectionManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

consumer: Optional[ReminderEventConsumer] = None
connection_manager: Optional[ConnectionManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer, connection_manager
    logger.info("Starting Notification Service...")

    dapr_client = DaprClient()
    connection_manager = ConnectionManager()
    consumer = ReminderEventConsumer(dapr_client, connection_manager)

    asyncio.create_task(consumer.start_consuming())
    logger.info("Notification Service started")
    yield
    if consumer:
        await consumer.stop()
    logger.info("Notification Service stopped")


app = FastAPI(title="Notification Service", version="1.0.0", lifespan=lifespan)


class HealthResponse(BaseModel):
    status: str
    consumer_running: bool
    active_connections: int


@app.get("/health")
async def health_check():
    global consumer, connection_manager
    running = consumer is not None and consumer.is_running if consumer else False
    connections = len(connection_manager.active_connections) if connection_manager else 0
    return HealthResponse(
        status="healthy" if running else "degraded",
        consumer_running=running,
        active_connections=connections
    )


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    global connection_manager
    if not connection_manager:
        raise HTTPException(status_code=503, detail="Service not ready")

    await connection_manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await connection_manager.send_personal_message({"type": "pong"}, user_id)
    except WebSocketDisconnect:
        connection_manager.disconnect(user_id)


@app.post("/notify/{user_id}")
async def send_notification(user_id: str, payload: dict):
    global connection_manager
    if not connection_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    sent = await connection_manager.send_personal_message(payload, user_id)
    return {"status": "sent", "deliveries": sent}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
