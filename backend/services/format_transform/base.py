"""
Base Format Transformer
========================
Abstract base class that all format transformers must implement.

This enforces a consistent interface so:
  - Any new format (NRM, PM-KISAN, Custom, future schemas) plugs in identically
  - The API router doesn't need to change when adding new formats
  - Each transformer is independently testable

Usage:
    class NRMTransformer(BaseTransformer):
        FORMAT_NAME = "nrm"
        def get_field_mapping(self): ...
        def transform(self, df): ...
        def validate_compliance(self, df): ...
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

log = logging.getLogger("brlf.services.format_transform")


# ── Result containers ────────────────────────────────────────────────────────

@dataclass
class FieldMapping:
    """One source → target field mapping."""
    source_field: str
    target_field: str
    transform_fn: Optional[str] = None   # e.g. "uppercase", "date_format"
    required: bool = False
    status: str = "pending"              # "mapped" | "pending" | "unmapped"


@dataclass
class ComplianceIssue:
    """One compliance validation failure."""
    field: str
    issue_type: str          # "missing", "invalid_format", "out_of_range"
    severity: str            # "critical", "warning", "info"
    message: str
    row_count: int = 0
    sample_values: List[str] = field(default_factory=list)


@dataclass
class TransformResult:
    """Output from a format transformation run."""
    success: bool
    format_name: str
    records_in: int
    records_out: int
    fields_mapped: int
    fields_unmapped: int
    compliance_checks: int
    compliance_passed: int
    compliance_issues: List[ComplianceIssue] = field(default_factory=list)
    output_path: Optional[str] = None
    mapping_report_path: Optional[str] = None
    compliance_report_path: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "format_name": self.format_name,
            "records_in": self.records_in,
            "records_out": self.records_out,
            "fields_mapped": self.fields_mapped,
            "fields_unmapped": self.fields_unmapped,
            "compliance_checks": self.compliance_checks,
            "compliance_passed": self.compliance_passed,
            "compliance_issues": [
                {"field": i.field, "type": i.issue_type,
                 "severity": i.severity, "message": i.message,
                 "row_count": i.row_count}
                for i in self.compliance_issues
            ],
            "output_path": self.output_path,
            "compliance_report_path": self.compliance_report_path,
            "error": self.error,
        }


# ── Abstract base ────────────────────────────────────────────────────────────

class BaseTransformer(ABC):
    """
    Abstract base class for format transformers.

    Every format (NRM, PM-KISAN, Custom) extends this.
    The router calls these methods without knowing which format
    is being used — pure polymorphism.
    """

    FORMAT_NAME: str = "base"        # Override in subclass
    FORMAT_VERSION: str = "1.0"

    @abstractmethod
    def get_field_mapping(self) -> List[FieldMapping]:
        """
        Return the full list of source→target field mappings for this format.
        Used by the frontend to show the mapping table.
        """
        ...

    @abstractmethod
    def transform(
        self,
        df: pd.DataFrame,
        output_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> TransformResult:
        """
        Transform input DataFrame into this format and save to output_path.
        Returns a TransformResult with stats and file path.
        """
        ...

    @abstractmethod
    def validate_compliance(
        self,
        df: pd.DataFrame,
    ) -> List[ComplianceIssue]:
        """
        Check whether the DataFrame meets this format's compliance requirements.
        Returns list of issues (empty = fully compliant).
        """
        ...

    def get_schema_info(self) -> Dict[str, Any]:
        """Return metadata about this format for the API."""
        mappings = self.get_field_mapping()
        return {
            "format_name": self.FORMAT_NAME,
            "format_version": self.FORMAT_VERSION,
            "total_fields": len(mappings),
            "required_fields": sum(1 for m in mappings if m.required),
            "fields": [
                {
                    "source": m.source_field,
                    "target": m.target_field,
                    "required": m.required,
                    "transform": m.transform_fn,
                }
                for m in mappings
            ],
        }
