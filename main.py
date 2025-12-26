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
configure_logging()
logger = logging.getLogger("app")

from limiter import limiter
DEFAULT_RATE_LIMIT = "5/minute"
RATE_LIMIT = os.getenv("BACKEND_RATE_LIMIT", DEFAULT_RATE_LIMIT)

# CORS Configuration with explicit Vercel URL
DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "https://todo-phase-3-frontend.vercel.app"
]

cors_origins_str = os.environ.get("BACKEND_CORS_ORIGINS")
if cors_origins_str:
    try:
        allowed_origins = json.loads(cors_origins_str.replace("'", '"'))
        logger.info(f"Loaded CORS origins from env: {allowed_origins}")
    except json.JSONDecodeError:
        logger.warning(f"Could not parse BACKEND_CORS_ORIGINS: {cors_origins_str}")
        allowed_origins = DEFAULT_CORS_ORIGINS
else:
    allowed_origins = DEFAULT_CORS_ORIGINS

logger.info(f"CORS allowed origins: {allowed_origins}")

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enhanced CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],  # Add this
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    logger.info(f"Origin: {request.headers.get('origin')}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

@app.on_event("startup")
async def on_startup():
    create_tables()
    logger.info("Application started successfully")

@app.get("/")
@limiter.limit(RATE_LIMIT)
async def read_root(request: Request):
    """A simple health check endpoint."""
    return {"status": "ok"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes."""
    return {"status": "ok", "service": "todo-backend"}

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