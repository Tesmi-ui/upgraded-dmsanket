"""
BRLF Services Package
=====================
Modular service architecture for extensibility.

Each service lives in its own subdirectory with:
  - __init__.py      — package exports
  - router.py        — FastAPI APIRouter (mounted in api/main.py)
  - transformer.py   — Core business logic
  - schemas.py       — Pydantic models for the service

Current services:
  - format_transform  — NRM, PM-KISAN, Custom format converters

To add a new service:
  1. Create backend/services/<service_name>/
  2. Add router.py with an APIRouter
  3. Register in api/main.py:
     from services.<name>.router import router as <name>_router
     app.include_router(<name>_router, prefix="/api/<name>", tags=["<Name>"])
"""
