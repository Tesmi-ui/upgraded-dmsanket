"""
Health check and root endpoints.
"""
from datetime import datetime, timezone
from fastapi import APIRouter

from ..core.config import APP_VERSION

router = APIRouter(tags=["health"])

# Quick-engine availability
try:
    from engines import (
        NameFormattingEngine,
        ContactValidationEngine,
        DuplicateRemovalEngine,
        GenderInferenceEngine,
    )
    ENGINES_AVAILABLE = True
except ImportError:
    ENGINES_AVAILABLE = False


@router.get("/")
async def root():
    """Root endpoint — service info."""
    return {
        "service": "BRLF-Sanket Govt. Compliance Data Migration System",
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "systems": {
            "production":         "intelligence_engine.py (full pipeline)",
            "check_intelligence": "GLOBAL / ADVISORY / SELECTIVE modes",
            "quick_engines":      "available" if ENGINES_AVAILABLE else "not loaded",
        },
    }


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engines_available": ENGINES_AVAILABLE,
    }