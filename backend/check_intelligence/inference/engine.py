"""
BRLF Data Migration System v4.1 - Inference Module (Production)
================================================================
AI inference functions for gender and category prediction.

This module is a thin orchestration layer over gender_lib.
All name-matching logic lives in gender_lib — keep it that way.

Public functions
----------------
    infer_gender(farmer_name, father_spouse="")  → InferenceResult
    infer_category(farmer_name, district="")     → InferenceResult

Both return a frozen InferenceResult dataclass with
  .value, .confidence, .reason, .tier, .is_determined, .label

CHANGELOG v4.1
--------------
  FIX 1: infer_category() — 4-tier confidence (was flat 62 for all surnames).
          T1 exact unambiguous = 88, T1 exact ambiguous = 62,
          T2 fuzzy             = 74, T3 all-token scan   = 68.
  FIX 2: AMBIGUOUS_SURNAMES imported and checked — ambiguous surnames are
          capped at conf=62 and labelled "Ambiguous" to prevent auto-write.
  FIX 3: Tier-2 fuzzy match via stdlib difflib (no external dependency).
          cutoff=0.83, max_len_diff=1 — validated against 14 test cases.
  FIX 4: Tier-3 all-token scan — catches community surname in middle position
          e.g. "Nandkumar Madavi Uike" correctly identified as ST via Madavi.
  FIX 5: DISTRICT_ST_BELT imported for optional Tier-4 geographic hint.
  FIX 6: Reason strings now include actual surname and matched key.
  FIX 7: district parameter added to infer_category() for Tier-4 context.
"""

import difflib
import logging
import math
from dataclasses import dataclass
from typing import Optional

import pandas as pd

# ── gender_lib: the standalone inference engine ──
from gender_lib import infer_gender as _lib_infer_gender, GenderResult
from gender_lib.knowledge_base import (
    SURNAME_CATEGORY,
    AMBIGUOUS_SURNAMES,
    DISTRICT_ST_BELT,
)

logger = logging.getLogger(__name__)

# ── Category confidence constants ────────────────────────────────────────────
# These must be understood together with CAT_MIN_CONFIDENCE in intelligence_engine.py
# (currently 60).  Only T1-unambiguous and T2-fuzzy exceed 75 and trigger auto-write.
# T1-ambiguous (62) and T3-all-token (68) exceed 60 but stay below 75 — they
# are written but flagged in the Review sheet as low-confidence changes.
# T4-geographic (55) is below 60 — never auto-written, review hint only.

_CONF_T1_UNAMBIGUOUS = 88   # exact match, unambiguous surname  → auto-write
_CONF_T1_AMBIGUOUS   = 62   # exact match, ambiguous surname     → write + flag
_CONF_T2_FUZZY       = 74   # fuzzy match (edit dist ≤ 1)        → write + flag
_CONF_T3_ALL_TOKEN   = 68   # non-surname token exact match      → write + flag
_CONF_T4_GEO         = 55   # geographic prior (district only)   → review hint, never write

# Fuzzy match parameters (tuned, validated against 14 test cases)
_FUZZY_CUTOFF      = 0.83   # SequenceMatcher ratio threshold
_FUZZY_MAX_LEN_DIFF = 1     # max absolute len difference between query and candidate

# Pre-build the keys list once at import time — difflib needs an iterable of candidates
_SURNAME_KEYS: list = list(SURNAME_CATEGORY.keys())


# ---------------------------------------------------------------------------
# Shared result type for this module
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InferenceResult:
    """
    Unified result for both gender and category inference.

    Mirrors GenderResult's shape so callers don't need two different types.
    """
    value:      str    # inferred value ("male"/"female" or "sc"/"obc"/…)
    confidence: int    # 0–100
    reason:     str
    tier:       int    # tier that produced this result (0 = undetermined)

    @property
    def is_determined(self) -> bool:
        return bool(self.value)

    @property
    def label(self) -> str:
        if self.confidence >= 90: return "High"
        if self.confidence >= 75: return "Medium"
        if self.confidence >= 60: return "Low"
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


def _category_undetermined(surname: str = "") -> InferenceResult:
    reason = (
        f"Surname '{surname}' not in regional caste reference list"
        if surname
        else "No recognisable surname found in name"
    )
    return InferenceResult(value="", confidence=0, reason=reason, tier=0)


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


def infer_category(farmer_name: str, district: str = "") -> InferenceResult:
    """
    Infer caste/category from the farmer's name using a 4-tier pipeline.

    Tier 1 — Exact surname match (last token):
        Unambiguous surname (e.g. Meshram, Kamble, Madavi) → conf 88, auto-write.
        Ambiguous surname (e.g. Patil, Naik, Shinde) → conf 62, write + flag.

    Tier 2 — Fuzzy match (difflib, edit dist ≤ 1, score ≥ 0.83):
        Catches spelling variants: Mesharam→Meshram, Kambal→Kamble.
        conf 74 — write + flag in Review sheet.

    Tier 3 — All-token scan (non-surname tokens):
        If last-token lookup fails, scan all tokens left-to-right.
        "Nandkumar Madavi Uike" → Madavi=ST. conf 68.

    Tier 4 — Geographic hint (district in DISTRICT_ST_BELT):
        No name signal but district has ST% ≥ 25. conf 55 — review hint only,
        never auto-written (below CAT_MIN_CONFIDENCE=60).

    Args:
        farmer_name: Full name of the farmer.
        district:    Optional district name (lowercase) for Tier-4 context.

    Returns:
        InferenceResult with .value, .confidence, .reason, .tier
    """
    tokens = _clean(farmer_name).split()
    if not tokens:
        return _category_undetermined()

    surname = tokens[-1]

    # ── Tier 1: exact surname match ───────────────────────────────────────
    cat = SURNAME_CATEGORY.get(surname)
    if cat:
        is_ambiguous = surname in AMBIGUOUS_SURNAMES
        conf = _CONF_T1_AMBIGUOUS if is_ambiguous else _CONF_T1_UNAMBIGUOUS
        ambig_note = (
            " [AMBIGUOUS — same surname appears in multiple communities; "
            "verify with caste certificate]"
            if is_ambiguous else ""
        )
        return InferenceResult(
            value=cat,
            confidence=conf,
            tier=1,
            reason=(
                f"Surname '{surname}' → {cat.upper()} "
                f"(Vidarbha surname heuristic, T1 exact){ambig_note}"
            ),
        )

    # ── Tier 2: fuzzy surname match ───────────────────────────────────────
    fuzzy_match, fuzzy_score = _fuzzy_lookup(surname)
    if fuzzy_match:
        cat = SURNAME_CATEGORY[fuzzy_match]
        is_ambiguous = fuzzy_match in AMBIGUOUS_SURNAMES
        return InferenceResult(
            value=cat,
            confidence=_CONF_T2_FUZZY,
            tier=2,
            reason=(
                f"Surname '{surname}' → fuzzy match '{fuzzy_match}' "
                f"(score {fuzzy_score:.0%}) → {cat.upper()} "
                f"(T2 fuzzy, spelling variant{', AMBIGUOUS' if is_ambiguous else ''})"
            ),
        )

    # ── Tier 3: all-token scan (non-surname tokens only) ──────────────────
    for token in tokens[:-1]:   # already checked last token above
        cat = SURNAME_CATEGORY.get(token)
        if cat:
            is_ambiguous = token in AMBIGUOUS_SURNAMES
            return InferenceResult(
                value=cat,
                confidence=_CONF_T3_ALL_TOKEN,
                tier=3,
                reason=(
                    f"Token '{token}' in '{farmer_name}' → {cat.upper()} "
                    f"(T3 all-token scan{', AMBIGUOUS' if is_ambiguous else ''})"
                ),
            )

    # ── Tier 4: geographic prior ───────────────────────────────────────────
    dist_clean = _clean(district)
    if dist_clean and dist_clean in DISTRICT_ST_BELT:
        return InferenceResult(
            value="st",
            confidence=_CONF_T4_GEO,
            tier=4,
            reason=(
                f"No surname signal found; district '{dist_clean}' is in the "
                f"ST belt (≥25% ST population, Census 2011). "
                f"Geographic hint only — verify with caste certificate."
            ),
        )

    return _category_undetermined(surname)


# ---------------------------------------------------------------------------
# Internal helpers
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


def _fuzzy_lookup(surname: str) -> tuple:
    """
    Try to fuzzy-match surname against SURNAME_CATEGORY keys.

    Uses stdlib difflib — no external dependency.
    Parameters tuned and validated:
        cutoff=0.83, max_len_diff=1

    Returns (matched_key, score) or (None, 0.0) if no match found.
    """
    if len(surname) < 3:
        # Too short — fuzzy on 2-char strings produces too many false positives
        return None, 0.0

    candidates = [
        k for k in _SURNAME_KEYS
        if abs(len(k) - len(surname)) <= _FUZZY_MAX_LEN_DIFF
    ]
    if not candidates:
        return None, 0.0

    matches = difflib.get_close_matches(
        surname, candidates, n=1, cutoff=_FUZZY_CUTOFF
    )
    if matches:
        score = difflib.SequenceMatcher(None, surname, matches[0]).ratio()
        return matches[0], score

    return None, 0.0


# ---------------------------------------------------------------------------
# apply_gender_intelligence — Admin / batch pipeline function
# (unchanged from v4.0 — gender logic not modified in this release)
# ---------------------------------------------------------------------------

import pandas as _pd
from gender_lib.knowledge_base import GenderLibrary
from gender_lib import infer_gender as _lib_infer_gender
from gender_intelligence.lib_utils import extract_first as _extract_first

COL_SUGGESTED = "__SUGGESTED_GENDER__"
COL_FLAGS     = "__REVIEW_FLAGS__"
COL_REVIEW_ID = "__REVIEW_ID__"

_AUTO_CORRECT_MIN = 80
_SUGGESTION_MIN   = 60

_log_agi = logging.getLogger("brlf.check_intelligence.apply_gender_intelligence")


def apply_gender_intelligence(
    df:          _pd.DataFrame,
    library:     GenderLibrary,
    farmer_col:  str = "farmer_name",
    gender_col:  str = "gender",
) -> tuple:
    """
    Apply two-layer gender inference to every row in the DataFrame.

    Writes three audit columns:
      __SUGGESTED_GENDER__  — suggested value (suggestions only, not corrections)
      __REVIEW_FLAGS__      — comma-separated review flag codes
      __REVIEW_ID__         — unique per-row review identifier

    High-confidence results (tier 1–2, ≥80%) → auto-corrected in df.
    Lower-confidence results (tier 3–4, ≥60%) → logged as suggestions only.

    Returns (df, corrections, suggestions).
    """
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
        src_row   = int(idx) + 2
        full_name = str(row.get(farmer_col, "") or "")
        cur_g     = str(row.get(gender_col,  "") or "").strip().lower()
        first     = _extract_first(full_name)

        result = _lib_infer_gender(full_name, spouse_or_father="")

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

        df.at[idx, COL_FLAGS]     = flags_str
        df.at[idx, COL_REVIEW_ID] = review_id

        if not result.is_determined:
            continue

        if result.confidence >= _AUTO_CORRECT_MIN and result.gender != cur_g:
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