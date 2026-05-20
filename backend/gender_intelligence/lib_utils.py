"""
gender_intelligence/lib_utils.py
=================================
Shared utilities for build_strict, build_prob, rebuild, and file_router.

Previously these helpers were copy-pasted across 3–4 files.
Now there is ONE copy.  Every module imports from here.

Public API
----------
  SUPPORTED_EXTENSIONS  : frozenset[str]
  now_utc()             : str   — ISO-8601 UTC timestamp
  checksum(path)        : str   — "sha256:<16hex>"
  load_manifest(path)   : dict
  save_manifest(d, path): None  — atomic write (temp-file + rename)
  extract_first(name)   : str   — cleaned lowercase first token
  read_pairs(path, farmer_col, gender_col) → (pairs, total_rows)
"""

import hashlib
import json
import logging
import os
import re
import tempfile
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".xlsx", ".xls", ".csv"})

# ── Backward-compatible aliases ───────────────────────────────────────────────
# Older modules (lib_utils.py doc, build scripts) may use these shorter names.
# All point to the same implementation above.
SUPPORTED_EXT = SUPPORTED_EXTENSIONS   # alias: set-style name used in doc

_VALID_FIRST_RE = re.compile(r"^[a-z]{3,}$")   # at least 3 alpha chars, no digits


# ── Timestamps ────────────────────────────────────────────────────────────────

def now_utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# Alias: doc code uses utc_now(), existing callers use now_utc()
utc_now = now_utc


# ── Checksum ──────────────────────────────────────────────────────────────────

def checksum(path: Path) -> str:
    """First 16 hex chars of SHA-256 — sufficient to detect file changes."""
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{h[:16]}"


# Alias: doc code uses file_checksum(), existing callers use checksum()
file_checksum = checksum


# ── Manifest ──────────────────────────────────────────────────────────────────

_MANIFEST_SKELETON: dict = {
    "verified_files":    {},
    "unverified_files":  {},
    "last_strict_build": None,
    "last_prob_build":   None,
}


def load_manifest(path: Path) -> dict:
    """Load manifest JSON. Returns a fresh skeleton if missing or corrupt."""
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("Manifest at '%s' is corrupt — starting fresh", path)
    return {k: (v.copy() if isinstance(v, dict) else v)
            for k, v in _MANIFEST_SKELETON.items()}


def save_manifest(manifest: dict, path: Path) -> None:
    """
    Atomically write the manifest JSON.

    Writes to a temp file in the same directory, then renames over the target.
    This guarantees the file is never half-written, even if the process dies.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, indent=2, ensure_ascii=False)

    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent, prefix=".manifest_tmp_", suffix=".json"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, path)   # atomic on POSIX; best-effort on Windows
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ── Name parsing ──────────────────────────────────────────────────────────────

def extract_first(full_name) -> str:
    """
    Return the cleaned lowercase first token of a full name.

    Returns '' for:
      - blank / None / NaN values
      - tokens shorter than 3 characters  (filters initials like "A.", "Sk")
      - tokens that contain digits         (filters "Sk1", "Ram2")
      - tokens that are not purely alpha   (filters "R.K.", "123")
    """
    if full_name is None:
        return ""
    import math
    if isinstance(full_name, float) and math.isnan(full_name):
        return ""
    tokens = str(full_name).strip().split()
    if not tokens:
        return ""
    first = tokens[0].lower().strip(".,;:-'\"")
    return first if _VALID_FIRST_RE.match(first) else ""


# ── Gender normalisation ──────────────────────────────────────────────────────

def normalise_gender(gender: str) -> str:
    """
    Return lowercased, stripped gender string.
    Returns '' for None / NaN / non-string input.
    Used by read_pairs() and gender_lib.gender inference.
    """
    if gender is None:
        return ""
    import math
    if isinstance(gender, float) and math.isnan(gender):
        return ""
    return str(gender).strip().lower()


# ── DataFrame reading ─────────────────────────────────────────────────────────

def read_pairs(
    file_path: Path,
    farmer_col: str,
    gender_col: str,
) -> tuple[list[tuple[str, str]], int]:
    """
    Read (first_name, gender) pairs from one Excel or CSV file.

    Accepts 'male'/'female' in any capitalisation (normalised to lowercase).
    Returns (pairs_list, total_row_count).
    Raises ValueError if required columns are missing.

    Performance: uses vectorised pandas operations, NOT iterrows().
    """
    if file_path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(str(file_path), dtype=str)
    else:
        df = pd.read_csv(str(file_path), dtype=str)

    df = df.fillna("")
    total = len(df)

    missing = [c for c in (farmer_col, gender_col) if c not in df.columns]
    if missing:
        raise ValueError(
            f"Column(s) {missing} not found in '{file_path.name}'. "
            f"Available: {list(df.columns)}"
        )

    # Vectorised — ~100x faster than iterrows() on large DataFrames
    first_names = df[farmer_col].map(extract_first)
    genders     = df[gender_col].str.lower().str.strip()

    mask  = (first_names != "") & (genders.isin({"male", "female"}))
    pairs = list(zip(first_names[mask], genders[mask]))

    return pairs, total