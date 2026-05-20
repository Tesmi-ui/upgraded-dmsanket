"""
Centralized Configuration — All environment variables, directories, and constants.
===================================================================================
Single source of truth for all settings. Loads from environment / .env file.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

# ═══════════════════════════════════════════════════════════════════════════
# DIRECTORIES (configurable via environment)
# ═══════════════════════════════════════════════════════════════════════════

UPLOAD_DIR     = Path(os.environ.get("UPLOADS_DIR",     "/app/uploads"))
OUTPUT_DIR     = Path(os.environ.get("OUTPUTS_DIR",     "/app/outputs"))
BACKUP_DIR     = Path(os.environ.get("BACKUPS_DIR",     "/app/backups"))
LOGS_DIR       = Path(os.environ.get("LOGS_DIR",        "/app/logs"))
INBOX_DIR      = Path(os.environ.get("INBOX_DIR",       "/app/data/inbox"))
VERIFIED_DIR   = Path(os.environ.get("VERIFIED_DIR",    "/app/data/verified"))
UNVERIFIED_DIR = Path(os.environ.get("UNVERIFIED_DIR",  "/app/data/unverified"))
GENDER_LIB_DIR = Path(os.environ.get("GENDER_LIB_DIR",  "/app/gender_intelligence"))

# ═══════════════════════════════════════════════════════════════════════════
# SECURITY & LIMITS
# ═══════════════════════════════════════════════════════════════════════════

MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 100 * 1024 * 1024))
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".tsv"}

# ═══════════════════════════════════════════════════════════════════════════
# CORS — configurable via environment
# ═══════════════════════════════════════════════════════════════════════════

ALLOWED_ORIGINS: List[str] = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000"
    ).split(",")
    if origin.strip()
]

# ═══════════════════════════════════════════════════════════════════════════
# APPLICATION
# ═══════════════════════════════════════════════════════════════════════════

APP_VERSION = "5.0.0"
APP_TITLE = "BRLF-Sanket Govt. Compliance Data Migration API"
APP_DESCRIPTION = (
    "Intelligent data migration, cleaning, and compliance validation "
    "for Sanket Portal. Supports production pipeline, check intelligence, "
    "modular quick engines, and format transformation services."
)

# ═══════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# ═══════════════════════════════════════════════════════════════════════════
# CREATE DIRECTORIES
# ═══════════════════════════════════════════════════════════════════════════

for _d in [UPLOAD_DIR, OUTPUT_DIR, BACKUP_DIR, LOGS_DIR,
           INBOX_DIR, VERIFIED_DIR, UNVERIFIED_DIR, GENDER_LIB_DIR]:
    _d.mkdir(parents=True, exist_ok=True)