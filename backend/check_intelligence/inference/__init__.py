"""
check_intelligence.inference
=============================
Runtime inference layer — gender/category prediction and schema validation.

  engine.py          — infer_gender(), infer_category(), apply_gender_intelligence()
  schema_validator.py — BRLFSchemaValidator, ValidationIssue, ValidationContext
"""
from check_intelligence.inference.engine import (
    infer_gender,
    infer_category,
    apply_gender_intelligence,
    InferenceResult,
)
from check_intelligence.inference.schema_validator import (
    BRLFSchemaValidator,
    ValidationIssue,
    ValidationContext,
    SanketField,
)

__all__ = [
    # Inference
    "infer_gender",
    "infer_category",
    "apply_gender_intelligence",
    "InferenceResult",
    # Schema validation
    "BRLFSchemaValidator",
    "ValidationIssue",
    "ValidationContext",
    "SanketField",
]