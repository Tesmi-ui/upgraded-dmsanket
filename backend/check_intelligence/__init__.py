"""
check_intelligence
==================
Admin intelligence layer for BRLF-Sanket.

Subpackages
-----------
  library/   — builds gender JSON libraries from verified/ and unverified/ folders
  routing/   — file lifecycle: upload → approve / reject / hold / promote / revoke
  inference/ — gender + category inference wrapper and BRLF schema validator

Public API (unchanged — all existing callers continue to work)
--------------------------------------------------------------
    from check_intelligence import apply_gender_intelligence, GenderLibrary
    from check_intelligence.inference import infer_gender, infer_category
    from check_intelligence.library   import run_rebuild, library_status
    from check_intelligence.routing   import FileRouter
"""

# ── inference ──────────────────────────────────────────────────────────────
from check_intelligence.inference.engine import (
    apply_gender_intelligence,
    infer_gender,
    infer_category,
    InferenceResult,
)

# ── schema validation ──────────────────────────────────────────────────────
from check_intelligence.inference.schema_validator import (
    BRLFSchemaValidator,
    ValidationIssue,
    ValidationContext,
    SanketField,
)

# ── library (GenderLibrary lives in gender_lib but is re-exported here) ───
from gender_lib.knowledge_base import GenderLibrary

# ── library build tools ────────────────────────────────────────────────────
from check_intelligence.library.rebuild      import run_rebuild, library_status
from check_intelligence.library.build_strict import build_strict_library
from check_intelligence.library.build_prob   import build_prob_library

# ── file routing ───────────────────────────────────────────────────────────
from check_intelligence.routing.file_router  import FileRouter

__all__ = [
    # inference
    "apply_gender_intelligence",
    "infer_gender",
    "infer_category",
    "InferenceResult",
    # schema validation
    "BRLFSchemaValidator",
    "ValidationIssue",
    "ValidationContext",
    "SanketField",
    # knowledge base
    "GenderLibrary",
    # library build
    "run_rebuild",
    "library_status",
    "build_strict_library",
    "build_prob_library",
    # file routing
    "FileRouter",
]