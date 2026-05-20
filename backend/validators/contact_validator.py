"""
BRLF v4.0 - Contact Number Validator (Production)
==================================================
Validates and corrects Indian mobile numbers (10 digits, starts with 6-9).

Handles:
  "+91 9876543210"   → "9876543210"  (strip country code)
  "09876543210"      → "9876543210"  (strip leading zero)
  "91-9876543210"    → "9876543210"  (strip country code + separator)
  "98765 43210"      → "9876543210"  (strip spaces)
  9.87654321e9       → "9876543210"  (scientific notation from Excel)
  "5876543210"       → invalid       (wrong starting digit)
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

VALID_START_DIGITS = frozenset("6789")


@dataclass
class ContactValidationResult:
    corrected: str
    original: str
    is_valid: bool
    reason: str
    was_changed: bool  # True only when corrected != original AND is_valid


class ContactValidator:
    """
    Validate and auto-correct Indian mobile numbers.

    Usage:
        validator = ContactValidator()
        result = validator.validate("91-9876543210")
        print(result.corrected, result.is_valid)  # 9876543210  True
    """

    def validate(self, number) -> ContactValidationResult:
        """
        Validate / correct a single contact number.

        Args:
            number: Raw value — str, int, float (including NaN / scientific notation)

        Returns:
            ContactValidationResult dataclass
        """
        original_repr = str(number)

        # --- Null handling ---
        if number is None or (isinstance(number, float) and pd.isna(number)):
            return ContactValidationResult("", "", False, "Blank / null value", False)

        # --- Numeric types (int / float) — handle scientific notation ---
        if isinstance(number, (int, float)):
            try:
                # Convert via int to avoid "9876543210.0" or "9.88e9"
                number = str(int(number))
            except (ValueError, OverflowError):
                return ContactValidationResult(
                    "", original_repr, False, f"Cannot convert numeric value: {original_repr}", False
                )

        try:
            raw = str(number).strip()
        except Exception as exc:
            return ContactValidationResult(
                "", original_repr, False, f"Unparseable: {exc}", False
            )

        if not raw:
            return ContactValidationResult("", "", False, "Empty after strip", False)

        # --- Strip prefixes and non-digit characters ---
        cleaned = self._remove_prefixes(raw)
        digits = re.sub(r"\D", "", cleaned)

        return self._classify(digits, raw)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _remove_prefixes(number: str) -> str:
        """Strip +91 / 91 / leading zeros."""
        s = number
        s = re.sub(r"^\+91[\s\-]?", "", s)   # +91 with optional separator
        s = re.sub(r"^91[\s\-]?", "", s)      # 91  with optional separator
        s = re.sub(r"^0+", "", s)             # leading zeros
        return s.strip()

    def _classify(self, digits: str, raw_original: str) -> ContactValidationResult:
        n = len(digits)

        if n == 0:
            return ContactValidationResult(
                "", raw_original, False, "No digits found after cleaning", False
            )

        if n == 10:
            return self._make_result(digits, raw_original, "Valid 10-digit number")

        if n < 10:
            return ContactValidationResult(
                digits, raw_original, False,
                f"Too short: {n} digit(s) found, need 10", False
            )

        # n > 10 — try to salvage (first 10 preferred: extra digits usually trail the number)
        for candidate, label in [
            (digits[:10],  "first 10 digits"),
            (digits[-10:], "last 10 digits"),
        ]:
            if candidate[0] in VALID_START_DIGITS:
                return self._make_result(
                    candidate, raw_original, f"Extracted {label} from {n}-digit string"
                )

        return ContactValidationResult(
            digits, raw_original, False,
            f"Too long ({n} digits) and no valid 10-digit window found", False,
        )

    @staticmethod
    def _make_result(
        digits: str, raw_original: str, base_reason: str
    ) -> ContactValidationResult:
        """Build a result for a 10-digit string — checks starting digit."""
        if digits[0] not in VALID_START_DIGITS:
            return ContactValidationResult(
                digits, raw_original, False,
                f"Must start with 6/7/8/9 — starts with '{digits[0]}'", False,
            )
        was_changed = digits != raw_original
        reason = base_reason if not was_changed else f"Corrected from '{raw_original}'"
        return ContactValidationResult(digits, raw_original, True, reason, was_changed)

    # ------------------------------------------------------------------
    # DataFrame helpers
    # ------------------------------------------------------------------

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        column: str = "contact_number",
    ) -> Tuple[pd.DataFrame, List[Dict], List[Dict]]:
        """
        Validate all contact numbers in a DataFrame column.

        Returns:
            (updated_df, corrections_list, issues_list)
        """
        if column not in df.columns:
            logger.error("Column '%s' not found. Available: %s", column, list(df.columns))
            return df, [], []

        df = df.copy()
        corrections: List[Dict] = []
        issues: List[Dict] = []

        for idx, raw in df[column].items():
            result = self.validate(raw)
            excel_row = df.index.get_loc(idx) + 2  # +1 header, +1 0-based

            if result.is_valid and result.was_changed:
                df.at[idx, column] = result.corrected
                corrections.append({
                    "DataFrame_Index": idx,
                    "Excel_Row": excel_row,
                    "Column": column,
                    "Original": result.original,
                    "Corrected": result.corrected,
                    "Reason": result.reason,
                })

            elif not result.is_valid and result.original:
                issues.append({
                    "DataFrame_Index": idx,
                    "Excel_Row": excel_row,
                    "Column": column,
                    "Original": result.original,
                    "Issue": result.reason,
                })

        logger.info(
            "validate_dataframe('%s'): %d corrected, %d invalid, out of %d records.",
            column, len(corrections), len(issues), len(df),
        )
        return df, corrections, issues

    def get_statistics(self, df: pd.DataFrame, column: str = "contact_number") -> Dict:
        """
        Return a summary dict — does a single pass (no double-validation).

        Note: call this AFTER validate_dataframe if you want post-correction stats.
        """
        if column not in df.columns:
            return {}

        total = len(df)
        blank = int(df[column].isna().sum())
        filled = total - blank

        valid = corrected = invalid = 0

        for raw in df[column]:
            r = self.validate(raw)
            if r.is_valid:
                valid += 1
                if r.was_changed:
                    corrected += 1
            elif r.original:      # non-blank but invalid
                invalid += 1

        return {
            "total_records": total,
            "blank": blank,
            "filled": filled,
            "valid": valid,
            "auto_corrected": corrected,
            "invalid": invalid,
            "validation_rate_pct": round(valid / max(filled, 1) * 100, 1),
        }


# ---------------------------------------------------------------------------
# Quick self-test (run with: python contact_validator.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    validator = ContactValidator()

    test_cases: List[Tuple] = [
        ("9876543210",         "9876543210",  True),
        ("+91 9876543210",     "9876543210",  True),
        ("91-9876543210",      "9876543210",  True),
        ("09876543210",        "9876543210",  True),
        ("98765 43210",        "9876543210",  True),
        (9876543210,           "9876543210",  True),   # integer input
        (9.87654321e9,         "9876543210",  True),   # float / scientific notation
        ("5876543210",         "5876543210",  False),  # wrong start digit
        ("98765",              "98765",       False),  # too short
        ("919876543210123",    "9876543210",  True),   # extract valid window after stripping 91 prefix
        (None,                 "",            False),
        ("",                   "",            False),
        (float("nan"),         "",            False),
    ]

    print("Contact Validator — Self-Test")
    print("=" * 65)
    all_passed = True
    for raw, exp_corrected, exp_valid in test_cases:
        result = validator.validate(raw)
        ok = result.corrected == exp_corrected and result.is_valid == exp_valid
        if not ok:
            all_passed = False
        status = "✅ PASS" if ok else "❌ FAIL"
        validity = "VALID  " if result.is_valid else "INVALID"
        print(f"{status}  [{validity}]  {repr(raw)!s:<28} → {repr(result.corrected)}")
        if not ok:
            print(f"       Expected corrected={repr(exp_corrected)}, is_valid={exp_valid}")
        if not result.is_valid:
            print(f"       Reason: {result.reason}")

    print()
    print("All tests passed ✅" if all_passed else "Some tests FAILED ❌")