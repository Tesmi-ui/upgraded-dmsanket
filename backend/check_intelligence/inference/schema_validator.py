
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# DATACLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SanketField:
    """BRLF Sanket field definition with government compliance rules."""
    name:         str
    field_type:   str            # string | integer | decimal | date | enum
    required:     bool
    max_length:   Optional[int]  = None
    pattern:      Optional[str]  = None
    enum_values:  Optional[List[str]] = None
    lgd_mapped:   bool           = False   # requires eGramSwaraj LGD lookup
    pii:          bool           = False   # Personally Identifiable Information
   
    brlf_section: Optional[str]  = None   # baseline | geo | farm | financial | …
    nrlm_mapped:  Optional[str]  = None   # NRLM MIS field mapping


@dataclass
class ValidationIssue:
   
    type:     str
    severity: str        # CRITICAL | HIGH | MEDIUM | LOW | INFO
    field:    str
    message:  str
    count:    int                 = 0
    rows:     List[int]           = field(default_factory=list)
    extra:    Dict[str, Any]      = field(default_factory=dict)


@dataclass
class ValidationContext:
   
    encryption_enabled: bool = False
    user_id:            str  = "system"
    purpose:            str  = "upload"


# ─────────────────────────────────────────────────────────────────────────────
# PII DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

class PIIDetector:
    """
    Detects Personally Identifiable Information patterns in Series data.
   
    """

    _PATTERNS: Dict[str, re.Pattern] = {
        "aadhaar":      re.compile(r"\b\d{12}\b"),
        "mobile":       re.compile(r"\b[6-9]\d{9}\b"),
        "email":        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        "bank_account": re.compile(r"\b\d{9,18}\b"),
    }

    def scan_column(self, series: pd.Series, pii_type: str = "aadhaar") -> int:
       
        pattern = self._PATTERNS.get(pii_type)
        if pattern is None:
            return 0
        sample = series.dropna().astype(str).head(200)
        return int(sample.str.match(pattern).sum())

    def has_pii_fields(self, columns: List[str], schema: Dict[str, SanketField]) -> List[str]:
      
        return [c for c in columns if schema.get(c, SanketField("", "", False)).pii]


# ─────────────────────────────────────────────────────────────────────────────
# LGD VALIDATOR
# ─────────────────────────────────────────────────────────────────────────────

class LGDValidator:


    def validate_column(self, series: pd.Series, code_name: str) -> List[ValidationIssue]:
        
        issues: List[ValidationIssue] = []
        if series.empty:
            return issues

        numeric = pd.to_numeric(series, errors="coerce")

        # Non-numeric values
        non_numeric = series[numeric.isna() & series.notna()]
        if not non_numeric.empty:
            issues.append(ValidationIssue(
                type="INVALID_LGD_CODE_TYPE",
                severity="HIGH",
                field=code_name,
                message=f"'{code_name}' contains non-numeric values — LGD codes must be integers",
                count=len(non_numeric),
                rows=non_numeric.index.tolist()[:20],
            ))

        # Zero or negative
        bad_range = series[(numeric <= 0) & series.notna()]
        if not bad_range.empty:
            issues.append(ValidationIssue(
                type="INVALID_LGD_CODE_RANGE",
                severity="MEDIUM",
                field=code_name,
                message=f"'{code_name}' has zero or negative values — LGD codes must be positive",
                count=len(bad_range),
                rows=bad_range.index.tolist()[:20],
            ))

        return issues

    def validate_hierarchy(self, codes: Dict[str, Any]) -> Tuple[bool, str]:
       
        for name, code in codes.items():
            try:
                if int(code) <= 0:
                    return False, f"'{name}' must be a positive integer (got {code})"
            except (TypeError, ValueError):
                return False, f"'{name}' is not a valid integer (got {code!r})"
        return True, "Valid"


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA VALIDATOR
# ─────────────────────────────────────────────────────────────────────────────

class BRLFSchemaValidator:
   

    # ── BRLF field definitions ────────────────────────────────────────────────
    BRLF_SCHEMA: Dict[str, SanketField] = {
        # Household identification (NRLM aligned)
        "household_id": SanketField(
            name="household_id", field_type="string", required=True,
            pattern=r"^HH[A-Z]{2}\d{8}$",
            brlf_section="baseline", nrlm_mapped="shg_household_code",
        ),
        "family_head_name": SanketField(
            name="family_head_name", field_type="string", required=True,
            max_length=100, pii=True,
            brlf_section="baseline", nrlm_mapped="head_of_family",
        ),
        "social_category": SanketField(
            name="social_category", field_type="enum", required=True,
            enum_values=["SC", "ST", "OBC", "GENERAL", "MINORITY", "OTHER", "PVTG", "SBC", "NT", "EBC", "VJNT", "SCHEDULED CASTE", "SCHEDULED TRIBE", "OTHER BACKWARD CLASS", "GENERAL CATEGORY", "MINORITY COMMUNITY", "OTHER", "PARTICULARLY VULNERABLE TRIBAL GROUP", "SPECIAL BACKWARD CLASS", "NOTIFIED"],
            brlf_section="baseline", nrlm_mapped="social_category",
        ),

        # Geographic (LGD aligned for eGramSwaraj)
        "state_code":    SanketField("state_code",    "integer", True,  lgd_mapped=True, brlf_section="geo"),
        "district_code": SanketField("district_code", "integer", True,  lgd_mapped=True, brlf_section="geo"),
        "block_code":    SanketField("block_code",    "integer", True,  lgd_mapped=True, brlf_section="geo"),
        "gp_code":       SanketField("gp_code",       "integer", True,  lgd_mapped=True, brlf_section="geo"),
        "village_code":  SanketField("village_code",  "integer", True,  lgd_mapped=True, brlf_section="geo"),

        # GPS coordinates
        "latitude":          SanketField("latitude",          "decimal", True,  brlf_section="geo"),
        "longitude":         SanketField("longitude",         "decimal", True,  brlf_section="geo"),
        "location_accuracy": SanketField("location_accuracy", "decimal", False, brlf_section="geo"),

        # Farm livelihoods
        "land_holding_acres": SanketField("land_holding_acres", "decimal", False, brlf_section="farm"),
        "irrigation_source":  SanketField(
            "irrigation_source", "enum", False,
            enum_values=["CANAL", "TUBEWELL", "WELL", "TANK", "RAINFED", "OTHER"],
            brlf_section="farm",
        ),
        "primary_crop": SanketField("primary_crop", "string", False, max_length=50, brlf_section="farm"),

        # Livestock
        "cattle_count":  SanketField("cattle_count",  "integer", False, brlf_section="livestock"),
        "goat_count":    SanketField("goat_count",    "integer", False, brlf_section="livestock"),
        "poultry_count": SanketField("poultry_count", "integer", False, brlf_section="livestock"),

        # Financial inclusion (PFMS aligned)
        "bank_account_number": SanketField(
            "bank_account_number", "string", False,
            max_length=20, pii=True, pattern=r"^\d{9,18}$",
            brlf_section="financial",
        ),
        "ifsc_code": SanketField(
            "ifsc_code", "string", False,
            pattern=r"^[A-Z]{4}0[A-Z0-9]{6}$", brlf_section="financial",
        ),
        "shg_member": SanketField(
            "shg_member", "enum", True, enum_values=["YES", "NO"],
            brlf_section="financial", nrlm_mapped="shg_membership",
        ),
        "shg_name": SanketField("shg_name", "string", False, max_length=100, brlf_section="financial"),

        # DAY-NRLM
        "mahila_kisan":        SanketField("mahila_kisan",        "enum", False, enum_values=["YES","NO"], brlf_section="intervention"),
        "krishi_sakhi_trained": SanketField("krishi_sakhi_trained","enum", False, enum_values=["YES","NO"], brlf_section="intervention"),

        # Contact PII
        # NOTE FIX 10: pattern matches ContactValidator.MOBILE_PATTERN — keep in sync
        "mobile_number": SanketField(
            "mobile_number", "string", False,
            pattern=r"^[6-9]\d{9}$", pii=True, brlf_section="contact",
        ),
        "aadhaar_number": SanketField(
            "aadhaar_number", "string", False,
            pattern=r"^\d{12}$", pii=True, brlf_section="identity",
        ),
    }

    def __init__(self) -> None:
        self.lgd_validator = LGDValidator()
        self.pii_detector  = PIIDetector()   # FIX 3: instantiated AND used

    # ── Public API ────────────────────────────────────────────────────────────

    def validate_dataframe(
        self,
        df:      pd.DataFrame,
        context: ValidationContext,
    ) -> List[ValidationIssue]:
        """
        Validate df against BRLF schema.

        Returns a flat list of ValidationIssue objects.
        Filter by severity for errors vs warnings:
            critical = [i for i in issues if i.severity == "CRITICAL"]
            warnings = [i for i in issues if i.severity in ("MEDIUM","LOW")]

        Parameters
        ----------
        df      : DataFrame to validate
        context : ValidationContext — see dataclass for required fields
        """
        issues: List[ValidationIssue] = []

        issues += self._validate_schema_completeness(df)

        for field_name, field_def in self.BRLF_SCHEMA.items():
            if field_name in df.columns:
                issues += self._validate_field(df[field_name], field_def)
            elif field_def.required:
                issues.append(ValidationIssue(
                    type="MISSING_REQUIRED_FIELD", severity="CRITICAL",
                    field=field_name,
                    message=f"Required BRLF field '{field_name}' is missing from the data",
                ))

        issues += self._validate_cross_fields(df)
        issues += self._validate_lgd_codes(df)
        issues += self._validate_pii_compliance(df, context)

        return issues

    # ── Field-level validation ────────────────────────────────────────────────

    def _validate_field(
        self, series: pd.Series, field_def: SanketField
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # Required — null/empty check
        if field_def.required:
            null_mask = series.isna() | (series.astype(str).str.strip() == "")
            null_count = int(null_mask.sum())
            if null_count:
                issues.append(ValidationIssue(
                    type="NULL_IN_REQUIRED_FIELD", severity="HIGH",
                    field=field_def.name,
                    message=f"'{field_def.name}' has {null_count} null/empty values",
                    count=null_count,
                    rows=series[null_mask].index.tolist()[:20],
                ))

        # Numeric type check (integer / decimal)
        if field_def.field_type in ("integer", "decimal"):
            invalid_mask = pd.to_numeric(series, errors="coerce").isna() & series.notna()
            if invalid_mask.any():
                issues.append(ValidationIssue(
                    type="TYPE_MISMATCH", severity="MEDIUM",
                    field=field_def.name,
                    message=f"'{field_def.name}' has {invalid_mask.sum()} non-numeric values "
                            f"(expected {field_def.field_type})",
                    count=int(invalid_mask.sum()),
                    rows=series[invalid_mask].index.tolist()[:20],
                ))

        # Date type check — FIX 5: vectorised batch
        if field_def.field_type == "date":
            non_empty = series[series.notna() & (series.astype(str).str.strip() != "")]
            if not non_empty.empty:
                parsed = pd.to_datetime(non_empty, errors="coerce", dayfirst=True)
                bad_mask = parsed.isna()
                if bad_mask.any():
                    issues.append(ValidationIssue(
                        type="INVALID_DATE_FORMAT", severity="MEDIUM",
                        field=field_def.name,
                        message=f"'{field_def.name}' has {bad_mask.sum()} unparseable date values. "
                                f"Expected DD/MM/YYYY or YYYY-MM-DD",
                        count=int(bad_mask.sum()),
                        rows=non_empty[bad_mask].index.tolist()[:20],
                        extra={"sample_bad_values": non_empty[bad_mask].head(3).tolist()},
                    ))

        # Pattern check (string only)
        if field_def.pattern and field_def.field_type == "string":
            non_empty = series[series.notna() & (series != "")]
            bad_mask  = ~non_empty.astype(str).str.match(field_def.pattern)
            if bad_mask.any():
                sample_vals = non_empty[bad_mask].head(3).tolist()
                suggestion  = self._suggest_correction(field_def, str(sample_vals[0]))
                issues.append(ValidationIssue(
                    type="PATTERN_MISMATCH", severity="HIGH",
                    field=field_def.name,
                    message=f"'{field_def.name}' has {bad_mask.sum()} values not matching "
                            f"pattern {field_def.pattern}. {suggestion}",
                    count=int(bad_mask.sum()),
                    rows=non_empty[bad_mask].index.tolist()[:20],
                    extra={"sample_bad_values": sample_vals},
                ))

        # Enum check
        if field_def.enum_values:
            allowed = set(field_def.enum_values) | {"", None}
            invalid_mask = ~series.isin(allowed) & series.notna()
            if invalid_mask.any():
                bad_vals = series[invalid_mask].unique()[:5].tolist()
                issues.append(ValidationIssue(
                    type="INVALID_ENUM_VALUE", severity="MEDIUM",
                    field=field_def.name,
                    message=f"'{field_def.name}' has values not in allowed list "
                            f"{field_def.enum_values}",
                    count=int(invalid_mask.sum()),
                    rows=series[invalid_mask].index.tolist()[:20],
                    extra={"invalid_sample": bad_vals,
                           "allowed_values": field_def.enum_values},
                ))

        # Max length
        if field_def.max_length:
            over = series.dropna().astype(str).str.len() > field_def.max_length
            if over.any():
                issues.append(ValidationIssue(
                    type="MAX_LENGTH_EXCEEDED", severity="LOW",
                    field=field_def.name,
                    message=f"'{field_def.name}' has {over.sum()} values exceeding "
                            f"max length {field_def.max_length}",
                    count=int(over.sum()),
                ))

        return issues

    # ── Cross-field business rules ────────────────────────────────────────────

    def _validate_cross_fields(self, df: pd.DataFrame) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # SHG member YES → must have SHG name
        if "shg_member" in df.columns and "shg_name" in df.columns:
            mask = (df["shg_member"] == "YES") & (
                df["shg_name"].isna() | (df["shg_name"].astype(str).str.strip() == "")
            )
            if mask.any():
                issues.append(ValidationIssue(
                    type="BUSINESS_RULE_VIOLATION", severity="MEDIUM",
                    field="shg_name",
                    message="SHG members without a SHG name — 'shg_name' required when shg_member=YES",
                    count=int(mask.sum()),
                    rows=df[mask].index.tolist()[:20],
                ))

        # Aadhaar must be unique
        if "aadhaar_number" in df.columns:
            valid = df["aadhaar_number"].notna() & (df["aadhaar_number"] != "")
            dups  = df[valid]["aadhaar_number"].duplicated()
            if dups.any():
                issues.append(ValidationIssue(
                    type="DUPLICATE_AADHAAR", severity="CRITICAL",
                    field="aadhaar_number",
                    message=f"Duplicate Aadhaar numbers found — violates UIDAI uniqueness requirement",
                    count=int(dups.sum()),
                    rows=df[valid][dups].index.tolist()[:20],
                ))

        # Land > 0 but no irrigation source
        if "land_holding_acres" in df.columns and "irrigation_source" in df.columns:
            mask = (pd.to_numeric(df["land_holding_acres"], errors="coerce") > 0) & \
                   df["irrigation_source"].isna()
            if mask.any():
                issues.append(ValidationIssue(
                    type="DATA_INCONSISTENCY", severity="LOW",
                    field="irrigation_source",
                    message="Households with land_holding_acres > 0 but no irrigation_source",
                    count=int(mask.sum()),
                    rows=df[mask].index.tolist()[:20],
                ))

        return issues

    # ── LGD code validation ───────────────────────────────────────────────────

    def _validate_lgd_codes(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """
        FIX 4: vectorised — validates each LGD column as a whole, no iterrows().
        FIX 2: no cross-column prefix check (incorrect for Indian LGD structure).
        """
        issues: List[ValidationIssue] = []
        lgd_fields = ["state_code", "district_code", "block_code", "gp_code", "village_code"]
        available  = [f for f in lgd_fields if f in df.columns]

        if not available:
            issues.append(ValidationIssue(
                type="LGD_VALIDATION_SKIPPED", severity="INFO",
                field="",
                message="No LGD code fields found — eGramSwaraj compliance check skipped",
            ))
            return issues

        for col in available:
            issues += self.lgd_validator.validate_column(df[col], col)

        return issues

    # ── PII compliance ────────────────────────────────────────────────────────

    def _validate_pii_compliance(
        self, df: pd.DataFrame, context: ValidationContext
    ) -> List[ValidationIssue]:
        """
        FIX 3: delegates to self.pii_detector (previously never used).
        FIX 9: context is now a typed ValidationContext dataclass.
        """
        issues: List[ValidationIssue] = []

        pii_cols = self.pii_detector.has_pii_fields(list(df.columns), self.BRLF_SCHEMA)
        if pii_cols and not context.encryption_enabled:
            issues.append(ValidationIssue(
                type="PII_COMPLIANCE", severity="MEDIUM",
                field=", ".join(pii_cols),
                message="PII fields present but encryption_enabled=False in context. "
                        "Encrypt before storage.",
                extra={"pii_fields": pii_cols, "user_id": context.user_id},
            ))

        # Spillover: Aadhaar-like patterns in non-PII columns
        for col in df.columns:
            if col not in {s.name for s in self.BRLF_SCHEMA.values() if s.pii}:
                hits = self.pii_detector.scan_column(df[col], "aadhaar")
                if hits:
                    issues.append(ValidationIssue(
                        type="PII_SPILLOVER", severity="MEDIUM",
                        field=col,
                        message=f"Column '{col}' may contain Aadhaar numbers — "
                                f"{hits} match(es) in sample",
                        count=hits,
                        extra={"pii_type": "aadhaar"},
                    ))

        return issues

    # ── Schema completeness ───────────────────────────────────────────────────

    def _validate_schema_completeness(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """Warn if entire BRLF sections are missing from the dataframe."""
        issues: List[ValidationIssue] = []
        present_sections = {
            fdef.brlf_section
            for col, fdef in self.BRLF_SCHEMA.items()
            if col in df.columns and fdef.brlf_section
        }
        missing = {"baseline", "geo"} - present_sections
        if missing:
            issues.append(ValidationIssue(
                type="INCOMPLETE_SCHEMA", severity="HIGH",
                field="",
                message=f"Critical BRLF sections missing: {sorted(missing)}. "
                        f"'baseline' and 'geo' are required.",
                extra={"missing_sections": sorted(missing)},
            ))
        return issues

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _suggest_correction(field_def: SanketField, value: str) -> str:
        """
        FIX 1+6: replaced fuzz.ratio() with difflib.SequenceMatcher (stdlib).
        """
        if not field_def.enum_values:
            return f"Expected pattern: {field_def.pattern}"
        best = max(
            field_def.enum_values,
            key=lambda x: difflib.SequenceMatcher(
                None, x.lower(), value.lower()
            ).ratio(),
        )
        score = difflib.SequenceMatcher(None, best.lower(), value.lower()).ratio()
        if score > 0.6:
            return f"Did you mean '{best}'?"
        return f"Allowed values: {field_def.enum_values}"