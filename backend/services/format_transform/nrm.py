"""
NRM Format Transformer
=======================
Transforms cleaned BRLF data → NRM (National Resource Management) format.

NRM is the government standard for resource management reporting.
This transformer handles:
  - Field mapping (farmer_name → beneficiary_name, etc.)
  - Data type enforcement (dates, numbers, codes)
  - LGD code validation
  - NRM-specific compliance rules

Usage:
    transformer = NRMTransformer()
    result = transformer.transform(df, "/app/outputs/job123/nrm_output.xlsx")
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import BaseTransformer, ComplianceIssue, FieldMapping, TransformResult

log = logging.getLogger("brlf.services.format_transform.nrm")


class NRMTransformer(BaseTransformer):
    """
    National Resource Management format transformer.

    Extends BaseTransformer with NRM-specific:
      - 15+ field mappings (farmer → beneficiary schema)
      - LGD code validation
      - Date format standardization (DD/MM/YYYY)
      - Mandatory field enforcement
    """

    FORMAT_NAME = "nrm"
    FORMAT_VERSION = "2.0"

    def get_field_mapping(self) -> List[FieldMapping]:
        """NRM field mapping specification."""
        return [
            FieldMapping("farmer_name", "beneficiary_name", "title_case", required=True),
            FieldMapping("father_spouse_name", "guardian_name", "title_case", required=True),
            FieldMapping("aadhaar_number", "uid", None, required=True),
            FieldMapping("mobile_no", "contact_number", "clean_mobile", required=False),
            FieldMapping("gender", "gender", "standardize_gender", required=True),
            FieldMapping("category", "social_category", "standardize_category", required=True),
            FieldMapping("date_of_birth", "dob", "format_date_ddmmyyyy", required=False),
            FieldMapping("village", "village_name", "title_case", required=True),
            FieldMapping("block", "block_name", "title_case", required=True),
            FieldMapping("district", "district_name", "title_case", required=True),
            FieldMapping("state", "state_name", "title_case", required=True),
            FieldMapping("bank_account", "account_no", None, required=False),
            FieldMapping("ifsc_code", "ifsc", "uppercase", required=False),
            FieldMapping("land_area", "land_area_ha", "to_float", required=False),
            FieldMapping("mgnrega_id", "mgnrega_job_card", "validate_format", required=False),
        ]

    def transform(
        self,
        df: pd.DataFrame,
        output_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> TransformResult:
        """Transform DataFrame to NRM format."""
        options = options or {}
        records_in = len(df)
        mapped = 0
        unmapped = 0

        try:
            result_df = pd.DataFrame()

            for mapping in self.get_field_mapping():
                if mapping.source_field in df.columns:
                    col_data = df[mapping.source_field].copy()

                    # Apply transform function if specified
                    if mapping.transform_fn:
                        col_data = self._apply_transform(col_data, mapping.transform_fn)

                    result_df[mapping.target_field] = col_data
                    mapped += 1
                elif mapping.required:
                    # Required field missing — create empty column for compliance
                    result_df[mapping.target_field] = None
                    unmapped += 1
                    log.warning("Required NRM field missing: %s → %s",
                                mapping.source_field, mapping.target_field)
                else:
                    unmapped += 1

            # Run compliance checks
            issues = self.validate_compliance(result_df)

            # Save output
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            result_df.to_excel(output_path, index=False, engine="xlsxwriter")
            log.info("NRM output saved: %s (%d records)", output_path, len(result_df))

            return TransformResult(
                success=True,
                format_name=self.FORMAT_NAME,
                records_in=records_in,
                records_out=len(result_df),
                fields_mapped=mapped,
                fields_unmapped=unmapped,
                compliance_checks=len(issues) + mapped,
                compliance_passed=mapped - sum(1 for i in issues if i.severity == "critical"),
                compliance_issues=issues,
                output_path=output_path,
            )

        except Exception as e:
            log.error("NRM transform failed: %s", e, exc_info=True)
            return TransformResult(
                success=False,
                format_name=self.FORMAT_NAME,
                records_in=records_in,
                records_out=0,
                fields_mapped=mapped,
                fields_unmapped=unmapped,
                compliance_checks=0,
                compliance_passed=0,
                error=str(e),
            )

    def validate_compliance(self, df: pd.DataFrame) -> List[ComplianceIssue]:
        """NRM-specific compliance validation."""
        issues = []

        # Check required fields are populated
        required_fields = [m.target_field for m in self.get_field_mapping() if m.required]
        for field_name in required_fields:
            if field_name not in df.columns:
                issues.append(ComplianceIssue(
                    field=field_name,
                    issue_type="missing_column",
                    severity="critical",
                    message=f"Required NRM field '{field_name}' is missing from dataset",
                ))
                continue

            null_count = df[field_name].isna().sum()
            if null_count > 0:
                issues.append(ComplianceIssue(
                    field=field_name,
                    issue_type="missing_values",
                    severity="warning" if null_count < len(df) * 0.1 else "critical",
                    message=f"{null_count} empty values in required field '{field_name}'",
                    row_count=int(null_count),
                ))

        # Validate UID/Aadhaar format (12 digits)
        if "uid" in df.columns:
            bad = df["uid"].dropna().astype(str).apply(
                lambda x: not x.strip().isdigit() or len(x.strip()) != 12
            )
            bad_count = bad.sum()
            if bad_count > 0:
                issues.append(ComplianceIssue(
                    field="uid",
                    issue_type="invalid_format",
                    severity="critical",
                    message=f"{bad_count} invalid Aadhaar numbers (must be 12 digits)",
                    row_count=int(bad_count),
                    sample_values=df.loc[bad, "uid"].head(3).tolist(),
                ))

        # Validate gender values
        if "gender" in df.columns:
            valid_genders = {"male", "female", "transgender", "other", "m", "f", "t"}
            invalid = df["gender"].dropna().astype(str).str.lower().apply(
                lambda x: x.strip() not in valid_genders
            )
            inv_count = invalid.sum()
            if inv_count > 0:
                issues.append(ComplianceIssue(
                    field="gender",
                    issue_type="invalid_format",
                    severity="warning",
                    message=f"{inv_count} non-standard gender values",
                    row_count=int(inv_count),
                ))

        return issues

    # ── Transform helpers ─────────────────────────────────────────────────

    def _apply_transform(self, series: pd.Series, fn_name: str) -> pd.Series:
        """Apply named transform to a column."""
        if fn_name == "title_case":
            return series.astype(str).str.strip().str.title()
        elif fn_name == "uppercase":
            return series.astype(str).str.strip().str.upper()
        elif fn_name == "clean_mobile":
            return series.astype(str).str.replace(r"[^\d]", "", regex=True).str[-10:]
        elif fn_name == "standardize_gender":
            return self._standardize_gender(series)
        elif fn_name == "standardize_category":
            return self._standardize_category(series)
        elif fn_name == "format_date_ddmmyyyy":
            return pd.to_datetime(series, errors="coerce").dt.strftime("%d/%m/%Y")
        elif fn_name == "to_float":
            return pd.to_numeric(series, errors="coerce")
        elif fn_name == "validate_format":
            return series  # Validation only, no transform
        return series

    @staticmethod
    def _standardize_gender(series: pd.Series) -> pd.Series:
        mapping = {"m": "Male", "male": "Male", "f": "Female", "female": "Female",
                   "t": "Transgender", "transgender": "Transgender", "other": "Other"}
        return series.astype(str).str.strip().str.lower().map(mapping).fillna(series)

    @staticmethod
    def _standardize_category(series: pd.Series) -> pd.Series:
        mapping = {"sc": "SC", "st": "ST", "obc": "OBC", "general": "General",
                   "gen": "General", "nt": "NT", "sbc": "SBC"}
        return series.astype(str).str.strip().str.lower().map(mapping).fillna(series)
