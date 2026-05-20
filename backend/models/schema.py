"""
backend/schema.py
=================
All Pydantic request / response models for the BRLF v4.0 API.

One file — every model is here.
Callers import what they need:
    from models.schema import ProcessRequest, ProcessResponse, FileReviewRequest
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# PIPELINE  —  /api/process
# ─────────────────────────────────────────────────────────────────────────────

class FarmerRecord(BaseModel):
    """One row of input farmer data."""
    farmer_name:       str
    father_or_spouse:  str  = ""
    contact_number:    str  = ""
    mgnrega_card:      str  = ""
    gender:            str  = ""   # existing value — blank means infer
    category:          str  = ""   # existing value — blank means infer


class ValidationDetail(BaseModel):
    """Result of one validator on one field."""
    field:         str
    original:      str
    corrected:     str
    was_changed:   bool
    is_valid:      bool
    reason:        str


class InferenceDetail(BaseModel):
    """Result of one inference call."""
    field:       str           # "gender" or "category"
    value:       str           # inferred value
    confidence:  int           # 0–100
    tier:        int           # 1–4, 0 = undetermined
    label:       str           # "High" / "Medium" / "Low" / "Undetermined"
    reason:      str


class ProcessedRecord(BaseModel):
    """One fully-processed row returned to the caller."""
    row_index:           int
    farmer_name:         str
    contact_number:      str
    mgnrega_card:        str
    gender:              str
    category:            str
    validations:         List[ValidationDetail] = []
    inferences:          List[InferenceDetail]  = []
    has_corrections:     bool = False
    has_invalid_fields:  bool = False
    has_inferences:      bool = False


class ProcessRequest(BaseModel):
    """POST /api/process — process a batch of farmer records."""
    records:     List[FarmerRecord]
    dry_run:     bool = False   # if True, return analysis but don't modify anything


class ProcessResponse(BaseModel):
    """Response from POST /api/process."""
    total:           int
    corrected:       int
    invalid:         int
    inferred_gender: int
    inferred_category: int
    records:         List[ProcessedRecord]


class JobStatus(BaseModel):
    """Response shape for GET /api/status/{job_id}."""
    job_id:      str
    status:      str
    progress:    int
    message:     str
    created_at:  str
    finished_at: Optional[str] = None
    type:        str = "single"


# ─────────────────────────────────────────────────────────────────────────────
# FILE ROUTING  —  /api/admin/files/*
# ─────────────────────────────────────────────────────────────────────────────

class FileReviewRequest(BaseModel):
    """Body for approve / reject / hold / promote / revoke."""
    admin: str = Field(..., description="Admin username — logged in audit trail")
    note:  str = Field("",  description="Optional reason or comment")


class FileSummaryResponse(BaseModel):
    """Response from GET /api/admin/files/summary."""
    total:          int
    pending:        int
    held:           int
    approved:       int
    rejected:       int
    promoted:       int
    revoked:        int
    in_verified:    int
    in_unverified:  int
    needs_review:   int


# ─────────────────────────────────────────────────────────────────────────────
# LIBRARY REBUILD  —  /api/admin/gender-library/*
# ─────────────────────────────────────────────────────────────────────────────

class RebuildResponse(BaseModel):
    """Response from POST /api/admin/gender-library/rebuild."""
    status:          str   # "success" | "partial" | "dry_run" | "no_changes"
    strict_entries:  int
    prob_entries:    int
    strict_new:      int
    prob_new:        int
    strict_skipped:  bool
    prob_skipped:    bool
    strict_error:    Optional[str] = None
    prob_error:      Optional[str] = None
    files_read:      List[str] = []
    built_at:        str


class LibraryStatusResponse(BaseModel):
    """Response from GET /api/admin/gender-library/status."""
    new_verified:    List[List[str]]   # [[filename, "NEW"|"MODIFIED"], ...]
    new_unverified:  List[List[str]]
    last_strict:     Optional[str]
    last_prob:       Optional[str]


# ─────────────────────────────────────────────────────────────────────────────
# GENERIC
# ─────────────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status:   str = "ok"
    version:  str = "4.0.0"
    service:  str = "BRLF Data Migration API"


# ─────────────────────────────────────────────────────────────────────────────
# PROCESSING OPTIONS  —  shared by /api/process and /api/upload/bulk
# ─────────────────────────────────────────────────────────────────────────────

class ProcessingOptions(BaseModel):
    """
    Configuration for a single-file or bulk pipeline run.

    Execution mode fields
    ---------------------
    execution_mode : str
        "GLOBAL"    — all rules + all columns run (default, v4.0 behaviour)
        "ADVISORY"  — all rules run, nothing written to disk  (safe audit run)
        "SELECTIVE" — only the columns/rules in selected_columns/selected_rules run

    selected_columns : list[str]
        Columns that may be mutated in SELECTIVE mode.
        Ignored in GLOBAL and ADVISORY.
        Example: ["gender"] → only the gender column is touched.

    selected_rules : list[str]
        Rule names that may execute in SELECTIVE mode.
        Ignored in GLOBAL and ADVISORY.
        Full rule registry:
          "format_name", "validate_contact", "validate_mgnrega",
          "infer_gender", "infer_category",
          "deduplicate",
          "auto_correct", "auto_correct_gender", "auto_correct_category",
          "spell_check"
    """
    # ── Column configuration ──────────────────────────────────────────────────
    unique_key_column:       str       = "Unique Key"
    farmer_name_column:      str       = "farmer_name"
    father_spouse_column:    str       = "father_spouse_name"
    submission_date_column:  str       = "SubmissionDate"
    survey_date_column:      str       = "date_of_survey"
    mgnrega_column:          str       = "mgnrega"         # FIX: actual column name in BRLF data

    # ── Pipeline switches ─────────────────────────────────────────────────────
    remove_duplicates:       bool      = True
    auto_correct:            bool      = True
    correct_fields:          List[str] = Field(default_factory=lambda: ["gender", "category"])
    min_confidence:          int       = 75
    spell_enabled:           bool      = True
    spell_min_confidence:    int       = 70
    spell_high_confidence:   int       = 90   # FIX: raised from 80 to avoid false positives
    spell_max_edit_distance: int       = 2

    # ── Execution mode ────────────────────────────────────────────────────────
    execution_mode:   str            = "GLOBAL"     # "GLOBAL" | "ADVISORY" | "SELECTIVE"
    selected_columns: List[str]      = Field(default_factory=list)
    selected_rules:   List[str]      = Field(default_factory=list)

    def to_engine_config(self) -> Dict[str, Any]:
        """Build the dict DataMigrationEngine.__init__() expects."""
        return {
            "unique_key_column":      self.unique_key_column,
            "mgnrega_column":         self.mgnrega_column,
            "farmer_name_column":     self.farmer_name_column,
            "father_spouse_column":   self.father_spouse_column,
            "submission_date_column": self.submission_date_column,
            "survey_date_column":     self.survey_date_column,
            "auto_correct_fields":    self.correct_fields if self.auto_correct else [],
            "keep_duplicate":         "first",
            "min_confidence":         self.min_confidence,
            "spell_check": {
                "enabled":           self.spell_enabled,
                "columns":           [self.farmer_name_column, self.father_spouse_column],
                "min_confidence":    self.spell_min_confidence,
                "high_confidence":   self.spell_high_confidence,
                "max_edit_distance": self.spell_max_edit_distance,
            },
            "bulk": {
                "max_workers":            4,
                "skip_already_processed": False,
            },
        }

    def to_execution_context(self):
        """
        Build an ExecutionContext from these options.
        Import is deferred to avoid circular imports at module level.
        """
        from core.execution_context import ExecutionContext, ExecutionMode

        mode_str = (self.execution_mode or "GLOBAL").upper().strip()

        cols  = set(self.selected_columns)  if self.selected_columns  else set()
        rules = set(self.selected_rules)    if self.selected_rules    else set()

        if mode_str == "ADVISORY":
            return ExecutionContext.advisory_mode(columns=cols if cols else None, rules=rules if rules else None)

        if mode_str == "SELECTIVE":
            return ExecutionContext.selective_mode(columns=cols, rules=rules)

        # Default: GLOBAL (backward-compatible)
        return ExecutionContext.global_mode()


# ─────────────────────────────────────────────────────────────────────────────
# CROSS-VERSION ALIASES
# Docs and callers use different names for the same concepts.
# All aliases point to the canonical model above.
# ─────────────────────────────────────────────────────────────────────────────

# Admin file-routing body (doc uses "ReviewRequest", we have "FileReviewRequest")
ReviewRequest  = FileReviewRequest

# Library rebuild body — doc calls it RebuildRequest, result RebuildResult
class RebuildRequest(BaseModel):
    """Body for POST /api/admin/gender-library/rebuild."""
    full:    bool = Field(default=False, description="Ignore manifest, re-read all files")
    dry_run: bool = Field(default=False, description="Preview only — write nothing")

# Result alias
RebuildResult = RebuildResponse

# Status alias
LibraryStatus = LibraryStatusResponse