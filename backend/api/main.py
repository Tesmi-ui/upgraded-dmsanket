"""
BRLF-Sanket Unified API  v5.0
==============================
Lean orchestrator — all route logic lives in api/routes/*.
This file handles only:
  - App creation + middleware
  - Router wiring
  - Lifespan management
  - Rate limiting setup

Routes are served by modular routers:
  api/routes/health.py     → / , /health
  api/routes/upload.py     → /api/upload, /api/upload/bulk
  api/routes/process.py    → /api/process, /api/process/{job_id}
  api/routes/engine.py     → /api/engine/run/{job_id}
  api/routes/status.py     → /api/status/{job_id}, /api/download/{job_id}/{file_type}
  api/routes/jobs.py       → /api/jobs, /api/jobs/{job_id}
  api/routes/admin.py      → /api/admin/*

Security:
  - Configurable CORS origins via ALLOWED_ORIGINS env var
  - Upload size limits via MAX_UPLOAD_BYTES env var
  - Rate limiting on upload/process endpoints via slowapi
  - Path traversal protection on download endpoints (Path.is_relative_to)
  - API key authentication via BRLF_API_KEY env var (optional)
  - Non-root Docker user
  - Structured logging with request correlation
"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .core.config import (
    ALLOWED_ORIGINS,
    APP_DESCRIPTION,
    APP_TITLE,
    APP_VERSION,
    GENDER_LIB_DIR,
    LOG_LEVEL,
)
from .core.dependencies import get_gender_library, get_file_router
from .core.security import limiter, RATE_LIMITING_AVAILABLE

# ── Route imports ─────────────────────────────────────────────────────────
from .routes.health import router as health_router
from .routes.upload import router as upload_router
from .routes.process import router as process_router
from .routes.engine import router as engine_router
from .routes.status import router as status_router
from .routes.jobs import router as jobs_router
from .routes.admin import router as admin_router

# ─────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("brlf-api")


# ─────────────────────────────────────────────────────────────────────────
# LIFESPAN
# ─────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_app: FastAPI):
    log.info("=" * 60)
    log.info("  BRLF-Sanket Unified API  v%s", APP_VERSION)
    log.info("  Docs          : http://localhost:8000/docs")
    log.info("  Upload        : POST /api/upload")
    log.info("  Bulk          : POST /api/upload/bulk")
    log.info("  Process       : POST /api/process/{job_id}")
    log.info("  Quick Engine  : POST /api/engine/run/{job_id}")
    log.info("  Gender lib    : %s", GENDER_LIB_DIR)
    log.info("  CORS origins  : %s", ALLOWED_ORIGINS)
    log.info("  Rate limiting : %s", "enabled" if RATE_LIMITING_AVAILABLE else "disabled")
    log.info("=" * 60)
    # Warm up singletons so first request is fast
    get_gender_library()
    get_file_router()
    yield
    log.info("Shutting down.")


# ─────────────────────────────────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-API-Key"],
)

# ── Rate Limiting ─────────────────────────────────────────────────────────

if RATE_LIMITING_AVAILABLE and limiter:
    from slowapi.errors import RateLimitExceeded
    from slowapi import _rate_limit_exceeded_handler

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    log.info("Rate limiting enabled via slowapi")

# ── Request-ID Middleware ─────────────────────────────────────────────────

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Inject X-Request-ID for correlation logging."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# ── Global Exception Handler ──────────────────────────────────────────────

from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please contact support. Error logged remotely."},
    )



# ─────────────────────────────────────────────────────────────────────────
# REGISTER ROUTERS
# ─────────────────────────────────────────────────────────────────────────

app.include_router(health_router)
app.include_router(upload_router)
app.include_router(process_router)
app.include_router(engine_router)
app.include_router(status_router)
app.include_router(jobs_router)
app.include_router(admin_router)


# ═════════════════════════════════════════════════════════════════════════
# EXTENSIBILITY HOOKS — reserved for future services
# ═════════════════════════════════════════════════════════════════════════
#
# To add a new service/system:
#   1. Create a new module under backend/services/<service_name>/
#   2. Create a router:  from fastapi import APIRouter; router = APIRouter()
#   3. Include it here:  app.include_router(router, prefix="/api/<service_name>")
#
# Example for a future "compliance" service:
#   from services.compliance.router import router as compliance_router
#   app.include_router(compliance_router, prefix="/api/compliance", tags=["Compliance"])
#
# This keeps the main file clean while allowing unlimited extensions.
# ═════════════════════════════════════════════════════════════════════════


# ─────────────────────────────────────────────────────────────────────────
# ENTRY POINT (for direct execution — use `main:app` via gunicorn/uvicorn)
# ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True, workers=1)