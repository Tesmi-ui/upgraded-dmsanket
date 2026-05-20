"""
BRLF-Sanket Data Migration System — application entry point.

This file re-exports the FastAPI ``app`` from ``api.main`` so that
gunicorn / uvicorn can discover it via ``main:app``.
"""
from api.main import app  # noqa: F401
