"""
gender_lib.gender
=================
Standalone gender-inference library for Marathi / Vidarbha personal names.

Indian Naming Convention (BRLF dataset)
-----------------------------------------
farmer_name = "FirstName FatherFirstName Surname"
                ^^^^^^^^^^^
                ONLY this token determines gender.

Gender is determined solely by the farmer's own first name.
The father/spouse column is completely irrelevant and is not used.

Tier logic:
  Tier 1 (95%) — first name found in FEMALE_NAMES / MALE_NAMES dictionary
  Tier 2 (82%) — first name matches a known Marathi gender suffix
                  (bai, tai, devi, wati → female | rao, das, nath, nanda, singh → male)
  Undetermined  — cannot determine from first name alone; do not guess
"""

import logging
import math
from dataclasses import dataclass
from typing import Optional

from .knowledge_base import (
    FEMALE_NAMES,
    MALE_NAMES,
    FEMALE_SUFFIXES,
    MALE_SUFFIXES,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GenderResult:
    """Immutable result returned by infer_gender()."""
    gender: str       # "male" | "female" | ""
    confidence: int   # 0–100
    reason: str
    tier: int         # 1–2, or 0 if undetermined

    @property
    def is_determined(self) -> bool:
        return self.gender != ""

    @property
    def label(self) -> str:
        if self.confidence >= 90:
            return "High"
        if self.confidence >= 75:
            return "Medium"
        if self.confidence >= 60:
            return "Low"
        return "Undetermined"


UNDETERMINED = GenderResult(
    gender="", confidence=0,
    reason="Gender cannot be determined from first name alone",
    tier=0,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def infer_gender(
    farmer_name: str,
    spouse_or_father: str = "",   # accepted for API compatibility, never used
) -> GenderResult:
    """
    Infer gender from the farmer's OWN first name only.

    The spouse_or_father parameter is intentionally ignored.
    In Indian naming: "Vedant Pravin Madavi" → only "Vedant" determines gender.
    Father/spouse columns carry zero information about the farmer's own gender.
    """
    first = _first_token(farmer_name)
    if not first:
        return UNDETERMINED

    # Tier 1: Direct dictionary lookup
    result = _tier1_dict(first)
    if result:
        return result

    # Tier 2: Marathi name suffix pattern
    result = _tier2_suffix(first)
    if result:
        return result

    return UNDETERMINED


# ---------------------------------------------------------------------------
# Tier implementations
# ---------------------------------------------------------------------------

def _tier1_dict(first: str) -> Optional[GenderResult]:
    """Exact match against curated name dictionaries — most reliable signal."""
    if first in FEMALE_NAMES:
        return GenderResult(
            gender="female", confidence=95, tier=1,
            reason=f"First name '{first}' is a known female name (Vidarbha/Maharashtra)",
        )
    if first in MALE_NAMES:
        return GenderResult(
            gender="male", confidence=95, tier=1,
            reason=f"First name '{first}' is a known male name (Vidarbha/Maharashtra)",
        )
    return None


def _tier2_suffix(first: str) -> Optional[GenderResult]:
    """
    Marathi name suffix patterns.
    Only fires when the name is longer than the suffix (avoids matching the
    suffix itself as a standalone name).
    """
    for sfx in FEMALE_SUFFIXES:
        if first.endswith(sfx) and len(first) > len(sfx):
            return GenderResult(
                gender="female", confidence=82, tier=2,
                reason=f"First name '{first}' ends with female suffix '-{sfx}' (Marathi convention)",
            )
    for sfx in MALE_SUFFIXES:
        if first.endswith(sfx) and len(first) > len(sfx):
            return GenderResult(
                gender="male", confidence=82, tier=2,
                reason=f"First name '{first}' ends with male suffix '-{sfx}' (Marathi convention)",
            )
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    try:
        return str(v).strip().lower()
    except Exception:
        return ""


def _first_token(name) -> str:
    parts = _clean(name).split()
    return parts[0] if parts else ""