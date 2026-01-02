# ========================================================================
# Recurring Task Service - Dapr-powered background worker
# ========================================================================
# Consumes task.completed events from Kafka and creates next occurrences.
# ========================================================================

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from dapr.clients import DaprClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .scheduler import NextOccurrenceScheduler
from .client import BackendAPIClient
from .consumer import TaskEventConsumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

consumer: Optional[TaskEventConsumer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer
    logger.info("Starting Recurring Task Service...")

    dapr_client = DaprClient()
    scheduler = NextOccurrenceScheduler()
    api_client = BackendAPIClient(dapr_client)
    consumer = TaskEventConsumer(dapr_client, scheduler, api_client)

    asyncio.create_task(consumer.start_consuming())
    logger.info("Recurring Task Service started")
    yield
    if consumer:
        await consumer.stop()
    logger.info("Recurring Task Service stopped")


app = FastAPI(title="Recurring Task Service", version="1.0.0", lifespan=lifespan)


class HealthResponse(BaseModel):
    status: str
    consumer_running: bool


@app.get("/health")
async def health_check():
    global consumer
    running = consumer is not None and consumer.is_running if consumer else False
    return HealthResponse(status="healthy" if running else "degraded", consumer_running=running)


@app.get("/stats")
async def get_stats():
    global consumer
    if consumer:
        s = consumer.get_stats()
        return {
            "events_processed": s.events_processed,
            "tasks_created": s.tasks_created,
            "errors_count": s.errors_count
        }
    return {"events_processed": 0, "tasks_created": 0, "errors_count": 0}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
