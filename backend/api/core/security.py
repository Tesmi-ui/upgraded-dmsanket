"""
Security utilities: API key auth, rate limiting, path traversal protection.
===========================================================================
- verify_api_key: FastAPI dependency for protected endpoints
- safe_path_check: Fixed path traversal protection (uses Path.is_relative_to)
- limiter: slowapi rate limiter instance (wired into main.py)
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

log = logging.getLogger(__name__)

# ── API Key Authentication ────────────────────────────────────────────────
# Set BRLF_API_KEY env var to enable. Empty/unset = no auth (dev mode).

API_KEY = os.environ.get("BRLF_API_KEY", "").strip()
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: Optional[str] = Security(_api_key_header),
) -> Optional[str]:
    """
    FastAPI dependency: verify API key from X-API-Key header.

    If BRLF_API_KEY is not set, authentication is disabled (dev mode).
    If set, all requests must include a matching X-API-Key header.
    """
    if not API_KEY:
        return None  # Auth disabled — dev mode

    if not api_key or api_key != API_KEY:
        log.warning("Unauthorized request — invalid or missing API key")
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Provide X-API-Key header.",
        )
    return api_key


async def verify_admin_key(
    api_key: Optional[str] = Security(_api_key_header),
) -> Optional[str]:
    """
    FastAPI dependency for admin endpoints.
    Same as verify_api_key but can be extended for role-based access.
    """
    return await verify_api_key(api_key)


# ── Rate Limiting ─────────────────────────────────────────────────────────

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    RATE_LIMITING_AVAILABLE = True
except ImportError:
    limiter = None
    RATE_LIMITING_AVAILABLE = False
    log.warning("slowapi not installed — rate limiting disabled")


# ── Path Traversal Protection ─────────────────────────────────────────────

def safe_path_check(base_dir: Path, target_path: str) -> Path:
    """
    Validate that target_path resolves within base_dir.

    FIX: Uses Path.is_relative_to() instead of str.startswith() which
    was vulnerable to prefix attacks (e.g. /app/outputs_evil starts
    with /app/outputs).
    """
    resolved = Path(target_path).resolve()
    base_resolved = base_dir.resolve()

    try:
        # Python 3.9+ — proper containment check
        if not resolved.is_relative_to(base_resolved):
            raise HTTPException(403, "Access denied — path traversal detected")
    except AttributeError:
        # Python 3.8 fallback — use parts comparison
        if not str(resolved).startswith(str(base_resolved) + os.sep):
            raise HTTPException(403, "Access denied — path traversal detected")

    return resolved


# ── Filename Sanitisation ─────────────────────────────────────────────────

_SAFE_FILENAME_RE = re.compile(r"[^\w\-. ]", re.ASCII)


def sanitize_filename(name: str) -> str:
    """Strip path separators and suspicious characters to prevent path traversal."""
    name = Path(name).name  # Remove any directory components
    return _SAFE_FILENAME_RE.sub("_", name) or "upload"
