import os
import json
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler

from slowapi.errors import RateLimitExceeded
from service import router as api_router
from routes.chat import router as chat_router
from database import create_tables
from logging_config import configure_logging
from dotenv import load_dotenv


load_dotenv()
# Configure logging at the application startup
configure_logging()
logger = logging.getLogger("app")

# Rate limiting
from limiter import limiter
DEFAULT_RATE_LIMIT = "5/minute"
RATE_LIMIT = os.getenv("BACKEND_RATE_LIMIT", DEFAULT_RATE_LIMIT)

# Default CORS origins
DEFAULT_CORS_ORIGINS = '["http://localhost:3000"]'

# Load CORS origins from environment variable
cors_origins_str = os.environ.get("BACKEND_CORS_ORIGINS", DEFAULT_CORS_ORIGINS)

# The environment variable might be a single-quoted string, 
# so we replace single quotes with double quotes for valid JSON.
try:
    allowed_origins = json.loads(cors_origins_str.replace("'", '"'))
except json.JSONDecodeError:
    logger.warning(f"Could not parse BACKEND_CORS_ORIGINS: {cors_origins_str}. Using default.")
    allowed_origins = json.loads(DEFAULT_CORS_ORIGINS)

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware to the application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use the parsed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    create_tables()

@app.get("/")
@limiter.limit(RATE_LIMIT)
async def read_root(request: Request):
    """A simple health check endpoint."""
    return {"status": "ok"}

from utils.api_monitor import api_monitor

@app.get("/api/admin/stats")
async def get_stats():
    return {
        "usage": api_monitor.get_usage_stats(hours=1),
        "health": api_monitor.get_quota_health()
    }

@app.get("/api/status")
async def system_status():
    stats = api_monitor.get_usage_stats(hours=1)
    return {
        "status": api_monitor.get_quota_health(),
        "requests_last_hour": stats["total_requests"],
        "success_rate": f"{stats['success_rate']:.1f}%",
        "quota_warnings": stats["quota_warnings"],
        "recommendation": (
            "All systems normal" if stats["quota_warnings"] == 0 
            else "Consider reducing usage or upgrading API plan"
        )
    }

app.include_router(api_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)