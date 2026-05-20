"""
BRLF Data Migration System v4.0 - Inference Module (Production)
================================================================
AI inference functions for gender and category prediction.

This module is a thin orchestration layer over gender_lib.
All name-matching logic lives in gender_lib — keep it that way.

Public functions
----------------
    infer_gender(farmer_name, father_spouse="")  → InferenceResult
    infer_category(farmer_name)                  → InferenceResult

Both return a frozen InferenceResult dataclass with
  .value, .confidence, .reason, .tier, .is_determined, .label
"""

import logging
import math
from dataclasses import dataclass
from typing import Optional

import pandas as pd

# ── gender_lib: the standalone inference engine ──
from gender_lib import infer_gender as _lib_infer_gender, GenderResult
from gender_lib.knowledge_base import SURNAME_CATEGORY

logger = logging.getLogger(__name__)

# Maximum confidence cap for category inference (surname is a weak signal)
CATEGORY_MAX_CONFIDENCE = 62


# ---------------------------------------------------------------------------
# Shared result type for this module
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InferenceResult:
    """
    Unified result for both gender and category inference.

    Mirrors GenderResult's shape so callers don't need two different types.
    """
    value: str          # inferred value ("male"/"female"  or  "sc"/"obc"/…)
    confidence: int     # 0–100
    reason: str
    tier: int           # tier that produced this result (0 = undetermined)

    @property
    def is_determined(self) -> bool:
        return self.value != ""

    @property
    def label(self) -> str:
        if self.confidence >= 90:
            return "High"
        if self.confidence >= 75:
            return "Medium"
        if self.confidence >= 60:
            return "Low"
        return "Undetermined"

    def as_tuple(self) -> tuple:
        """
        Compatibility shim for code that still unpacks (value, confidence, reason).
        Drop this once all callers are updated to use the dataclass directly.
        """
        return (self.value, self.confidence, self.reason)


_GENDER_UNDETERMINED = InferenceResult(
    value="", confidence=0,
    reason="Gender cannot be determined from name alone", tier=0,
)
_CATEGORY_UNDETERMINED = InferenceResult(
    value="", confidence=0,
    reason="Surname not in regional caste reference list", tier=0,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def infer_gender(farmer_name: str, father_spouse: str = "") -> InferenceResult:
    """
    Infer gender from farmer name, optionally cross-referenced with
    spouse / father field.

    Delegates entirely to gender_lib; wraps the result in InferenceResult
    so the rest of BRLF only deals with one result type.

    Args:
        farmer_name:   Full name of the farmer (any casing).
        father_spouse: Optional spouse or father name for cross-reference.

    Returns:
        InferenceResult with .value ("male"/"female"/""), .confidence, .reason
    """
    if not farmer_name and not father_spouse:
        return _GENDER_UNDETERMINED

    try:
        result: GenderResult = _lib_infer_gender(
            farmer_name=farmer_name,
            spouse_or_father=father_spouse,
        )
    except Exception as exc:
        logger.error(
            "gender_lib.infer_gender raised unexpectedly for name=%r: %s",
            farmer_name, exc,
        )
        return _GENDER_UNDETERMINED

    return InferenceResult(
        value=result.gender,
        confidence=result.confidence,
        reason=result.reason,
        tier=result.tier,
    )


def infer_category(farmer_name: str) -> InferenceResult:
    """
    Infer caste/category from the farmer's surname.

    Uses the last whitespace-separated token as the surname key.
    Max confidence is capped at CATEGORY_MAX_CONFIDENCE (62%) — surname
    is a weak heuristic; use only to fill blank fields for human review.

    Args:
        farmer_name: Full name of the farmer.

    Returns:
        InferenceResult with .value (e.g. "sc", "obc", "open", "st", "nt"),
        .confidence, .reason.
    """
    surname = _last_token(farmer_name)
    if not surname:
        return _CATEGORY_UNDETERMINED

    cat = SURNAME_CATEGORY.get(surname)
    if cat:
        return InferenceResult(
            value=cat,
            confidence=CATEGORY_MAX_CONFIDENCE,
            tier=1,
            reason=(
                f"Surname '{surname}' is traditionally {cat.upper()} in Vidarbha "
                f"(surname heuristic — fill blank only, verify before finalising)"
            ),
        )

    return _CATEGORY_UNDETERMINED


# ---------------------------------------------------------------------------
# Internal helpers (private to this module)
# ---------------------------------------------------------------------------

def _clean(v) -> str:
    """Return stripped lowercase string, or '' for None / NaN."""
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    try:
        return str(v).strip().lower()
    except Exception:
        return ""


def _last_token(name) -> str:
    parts = _clean(name).split()
    return parts[-1] if parts else ""


# ---------------------------------------------------------------------------
# apply_gender_intelligence — Admin / batch pipeline function
# ---------------------------------------------------------------------------
# This function is the entry point used by the admin pipeline and any
# batch-processing code that needs full audit columns added to a DataFrame.
#
# It differs from infer_gender() above (which is the per-record API used by
# intelligence_engine.py) in two ways:
#   1. It operates on a whole DataFrame, not a single record.
#   2. It writes three audit columns back into the DataFrame and returns
#      structured correction/suggestion logs for the Excel audit report.
#
# The doc version calls gender_lib.gender.infer_gender(name, cur_g, library)
# — a 3-arg build-pipeline variant that doesn't exist in our gender.py.
# We use the existing 2-arg infer_gender from gender_lib instead, which
# produces a compatible GenderResult with .gender and .confidence.
# ---------------------------------------------------------------------------

import pandas as _pd
from gender_lib.knowledge_base import GenderLibrary
from gender_lib import infer_gender as _lib_infer_gender
from gender_intelligence.lib_utils import extract_first as _extract_first

# Audit column names written into the DataFrame
COL_SUGGESTED = "__SUGGESTED_GENDER__"
COL_FLAGS     = "__REVIEW_FLAGS__"
COL_REVIEW_ID = "__REVIEW_ID__"

# Confidence thresholds
_AUTO_CORRECT_MIN  = 80   # tier 1 (95%) and tier 2 (82%) → auto-correct
_SUGGESTION_MIN    = 60   # tier 3 (72%) and tier 4 (62%) → suggest only

_log_agi = logging.getLogger("brlf.check_intelligence.apply_gender_intelligence")


def apply_gender_intelligence(
    df:             _pd.DataFrame,
    library:        GenderLibrary,
    farmer_col:     str = "farmer_name",
    gender_col:     str = "gender",
) -> tuple:
    """
    Apply two-layer gender inference to every row in the DataFrame.

    Writes three audit columns:
      __SUGGESTED_GENDER__  — suggested value (suggestions only, not corrections)
      __REVIEW_FLAGS__      — comma-separated review flag codes
      __REVIEW_ID__         — unique per-row review identifier

    High-confidence results (tier 1–2, ≥80%) → auto-corrected in df.
    Lower-confidence results (tier 3–4, ≥60%) → logged as suggestions only.

    Parameters
    ----------
    df         : Input DataFrame (strict corrections applied in-place).
    library    : Loaded GenderLibrary (used for contextual lookup metadata).
    farmer_col : Column name containing full farmer name.
    gender_col : Column name containing current gender value.

    Returns
    -------
    (df, corrections, suggestions)
      df          : DataFrame with audit columns added.
      corrections : List[dict] for the audit report "Gender Corrections" sheet.
      suggestions : List[dict] for the audit report "Gender Suggestions" sheet.
    """
    # Ensure audit columns exist
    for col in (COL_SUGGESTED, COL_FLAGS, COL_REVIEW_ID):
        if col not in df.columns:
            df[col] = ""

    if farmer_col not in df.columns or gender_col not in df.columns:
        _log_agi.warning(
            "Columns '%s' or '%s' not found — gender intelligence step skipped",
            farmer_col, gender_col,
        )
        return df, [], []

    corrections: list = []
    suggestions: list = []

    for idx, row in df.iterrows():
        src_row   = int(idx) + 2          # 1-based Excel row (header = row 1)
        full_name = str(row.get(farmer_col, "") or "")
        cur_g     = str(row.get(gender_col,  "") or "").strip().lower()
        first     = _extract_first(full_name)

        # Run inference using existing 2-arg API
        result = _lib_infer_gender(full_name, spouse_or_father="")

        # Build flags string
        flags: list = []
        if not cur_g:
            flags.append("blank_gender")
        if result.is_determined and cur_g and result.gender != cur_g:
            if result.confidence >= _AUTO_CORRECT_MIN:
                flags.append("strict_mismatch")
            else:
                flags.append("probable_mismatch")
        flags_str = ", ".join(flags) if flags else ""

        review_id = f"GREV-{src_row}-{first}" if first else ""

        # Write audit columns
        df.at[idx, COL_FLAGS]     = flags_str
        df.at[idx, COL_REVIEW_ID] = review_id

        if not result.is_determined:
            continue

        if result.confidence >= _AUTO_CORRECT_MIN and result.gender != cur_g:
            # Auto-correct: strict or near-strict confidence
            df.at[idx, gender_col] = result.gender
            corrections.append({
                "Row":              src_row,
                "Farmer_Name":      full_name,
                "First_Name":       first,
                "Original_Gender":  cur_g,
                "Corrected_Gender": result.gender,
                "Method":           f"Tier {result.tier}: {result.label}",
                "Confidence":       result.confidence,
                "Review_Flags":     flags_str,
            })

        elif result.confidence >= _SUGGESTION_MIN and result.gender != cur_g:
            # Suggest only: probabilistic confidence — do not mutate df
            df.at[idx, COL_SUGGESTED] = result.gender
            suggestions.append({
                "Row":              src_row,
                "Farmer_Name":      full_name,
                "First_Name":       first,
                "Current_Gender":   cur_g,
                "Suggested_Gender": result.gender,
                "Confidence":       result.confidence,
                "Method":           f"Tier {result.tier}: {result.label}",
                "Review_Flags":     flags_str,
                "Review_ID":        review_id,
            })

    _log_agi.info(
        "Gender intelligence: %d auto-corrected, %d suggestions flagged",
        len(corrections), len(suggestions),
    )
    return df, corrections, suggestions