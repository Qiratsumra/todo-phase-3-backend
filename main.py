import os
import json
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
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

# CRITICAL: Disable automatic trailing slash redirects to prevent CORS issues
app = FastAPI(redirect_slashes=False)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Configuration - Allow all Vercel preview URLs and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Logging middleware to track requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    origin = request.headers.get('origin', 'No origin')
    logger.info(f"📥 {request.method} {request.url.path} | Origin: {origin}")
    
    response = await call_next(request)
    
    logger.info(f"📤 Status: {response.status_code}")
    
    # Add CORS headers to any redirects (just in case)
    if response.status_code in (307, 308) and origin != 'No origin':
        if origin.endswith('.vercel.app') or 'localhost' in origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            logger.info(f"✅ Added CORS headers to redirect response")
    
    return response

@app.on_event("startup")
async def on_startup():
    create_tables()
    logger.info("🚀 Application started successfully")
    logger.info(f"📍 CORS enabled for Vercel domains and localhost")

@app.get("/")
@limiter.limit(RATE_LIMIT)
async def read_root(request: Request):
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Todo API is running"}

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

# Include routers - these are added AFTER middleware
app.include_router(api_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)