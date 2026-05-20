"""
BRLF v4.0 - MGNREGA Card Validator (Production)
================================================
Validates Maharashtra MGNREGA job card numbers.

Format:  MH-DD-BBB-GGG-NNN/NNNNNN
Where:
  MH    = Maharashtra state code (fixed)
  DD    = District code         (2 digits)
  BBB   = Block code            (3 digits)
  GGG   = GP / Village code     (3 digits)
  NNN   = Household number      (3 digits)
  NNNNNN= Member number         (6 digits)

Examples:
  "MH-07-001-023-045/000012"  → Valid
  "mh-07-001-023-045/000012"  → Auto-corrected (uppercased)
  "MH07001023045000012"        → Auto-corrected (separators inserted)
  "GJ-07-001-023-045/000012"  → Invalid (wrong state)
  ""                           → Blank (optional field, not an error)
"""

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# Canonical regex for a fully-formed Maharashtra MGNREGA card
_VALID_PATTERN = re.compile(r"^MH-(\d{2})-(\d{3})-(\d{3})-(\d{3})/(\d{6})$")

# All digits that would appear in a stripped card (no separators): 2+3+3+3+6 = 17
_DIGIT_COUNT = 17


@dataclass
class MGNREGAResult:
    card: str           # Final value to store (corrected if auto-fixed, else original)
    original: str       # Raw input as received
    is_valid: bool
    was_corrected: bool # True only when card != original AND is_valid
    reason: str


class MGNREGAValidator:
    """
    Validate and auto-correct Maharashtra MGNREGA job card numbers.

    Auto-corrections attempted (in order):
      1. Strip surrounding whitespace
      2. Uppercase the string
      3. Re-insert standard separators when only digits remain (or spaces/dashes are misplaced)

    Usage:
        validator = MGNREGAValidator()
        result = validator.validate("mh-07-001-023-045/000012")
        print(result.card, result.is_valid)   # MH-07-001-023-045/000012  True
    """

    def validate(self, card) -> MGNREGAResult:
        """
        Validate (and attempt to correct) a single MGNREGA card number.

        Args:
            card: Raw value — str, float NaN, None, int — all handled safely.

        Returns:
            MGNREGAResult dataclass.
        """
        # ── Null / blank (this is an optional field — blank is NOT an error) ──
        if card is None or (isinstance(card, float) and pd.isna(card)):
            return MGNREGAResult("", "", True, False, "Blank — optional field")

        try:
            original = str(card).strip()
        except Exception as exc:
            logger.warning("Cannot convert MGNREGA value to string: %r — %s", card, exc)
            return MGNREGAResult(str(card), str(card), False, False, f"Unparseable value: {exc}")

        if not original:
            return MGNREGAResult("", "", True, False, "Blank — optional field")

        # ── Step 1: uppercase + strip ──
        candidate = original.upper().strip()

        # ── Step 2: check if already valid ──
        if _VALID_PATTERN.match(candidate):
            was_corrected = candidate != original
            return MGNREGAResult(
                card=candidate,
                original=original,
                is_valid=True,
                was_corrected=was_corrected,
                reason="Valid MGNREGA format" if not was_corrected else f"Uppercased from '{original}'",
            )

        # ── Step 3: attempt auto-correction ──
        corrected, correction_note = self._try_correct(candidate)
        if corrected and _VALID_PATTERN.match(corrected):
            return MGNREGAResult(
                card=corrected,
                original=original,
                is_valid=True,
                was_corrected=True,
                reason=f"{correction_note} (from '{original}')",
            )

        # ── Step 4: invalid — diagnose why ──
        reason = self._diagnose(candidate)
        return MGNREGAResult(
            card=original,
            original=original,
            is_valid=False,
            was_corrected=False,
            reason=reason,
        )

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _try_correct(card: str) -> Tuple[Optional[str], str]:
        """
        Try common corrections. Returns (corrected_string_or_None, description).
        """
        digits_only = re.sub(r"\D", "", card)

        # Rebuild only when the card is purely numeric (no state code letters present).
        # If letters exist, the state code is already specified — trust it.
        has_letters = bool(re.search(r"[A-Z]", card))

        # If we have exactly 17 digits and no letters, rebuild the canonical format
        if not has_letters and len(digits_only) == _DIGIT_COUNT:
            d = digits_only
            rebuilt = f"MH-{d[0:2]}-{d[2:5]}-{d[5:8]}-{d[8:11]}/{d[11:17]}"
            return rebuilt, "Separators inserted"

        # Wrong slash position with any member number length (pad to 6 digits)
        # e.g. MH-33-008-030-001-240 → MH-33-008-030-001/000240
        import re as _re
        dash_slash = _re.match(r"^(MH-\d{2}-\d{3}-\d{3}-\d{3})-(\d{1,6})$", card)
        if dash_slash:
            padded = dash_slash.group(2).zfill(6)
            fixed = f"{dash_slash.group(1)}/{padded}"
            if _VALID_PATTERN.match(fixed):
                return fixed, f"Replaced '-' with '/' and zero-padded member number"

        # Standard 6-digit dash fix
        slash_fixed = re.sub(r"-(\d{6})$", r"/\1", card)
        if slash_fixed != card and _VALID_PATTERN.match(slash_fixed):
            return slash_fixed, "Replaced trailing '-' with '/'"

        # Extra spaces around separators: "MH - 07 - 001 - 023 - 045/000012"
        space_fixed = re.sub(r"\s*-\s*", "-", card)
        space_fixed = re.sub(r"\s*/\s*", "/", space_fixed)
        if _VALID_PATTERN.match(space_fixed):
            return space_fixed, "Removed spaces around separators"

        # Short member number after slash — zero-pad to 6 digits
        # e.g. MH-33-008-022-001/248 → MH-33-008-022-001/000248
        short_m = _re.match(r"^(MH-\d{2}-\d{3}-\d{3}-\d{3})/(\d{1,5})$", card)
        if short_m:
            padded = short_m.group(2).zfill(6)
            padded_fixed = f"{short_m.group(1)}/{padded}"
            if _VALID_PATTERN.match(padded_fixed):
                return padded_fixed, f"Zero-padded member number to 6 digits"

        return None, ""

    @staticmethod
    def _diagnose(card: str) -> str:
        """Return a human-readable reason why the card is invalid."""
        if not card.startswith("MH"):
            prefix = card[:2] if len(card) >= 2 else card
            return f"Invalid state code '{prefix}' — must be 'MH' (Maharashtra)"

        parts = card.split("-")
        if len(parts) != 5:
            return f"Expected 5 dash-separated parts, found {len(parts)}"

        # Validate each part individually
        labels = [
            ("District (DD)",         2, None),
            ("Block (BBB)",           3, None),
            ("GP/Village (GGG)",      3, None),
        ]
        # parts[0]="MH", parts[1]=DD, parts[2]=BBB, parts[3]=GGG, parts[4]="NNN/NNNNNN"
        for idx, (label, expected_len, _) in enumerate(labels, start=1):
            seg = parts[idx]
            if not seg.isdigit():
                return f"{label} segment '{seg}' must be numeric"
            if len(seg) != expected_len:
                return f"{label} segment '{seg}' must be {expected_len} digit(s), got {len(seg)}"

        last = parts[4]
        if "/" not in last:
            return f"Last segment '{last}' must contain '/' separating household and member numbers"

        nnn, nnnnnn = last.split("/", 1)
        if not nnn.isdigit() or len(nnn) != 3:
            return f"Household number '{nnn}' must be exactly 3 digits"
        if not nnnnnn.isdigit() or len(nnnnnn) != 6:
            return f"Member number '{nnnnnn}' must be exactly 6 digits"

        return "Invalid MGNREGA card format"

    # -----------------------------------------------------------------------
    # DataFrame helpers
    # -----------------------------------------------------------------------

    def validate_dataframe(
        self,
        df: pd.DataFrame,
        column: str = "mgnrega",
    ) -> Tuple[pd.DataFrame, List[Dict], List[Dict]]:
        """
        Validate (and auto-correct) all MGNREGA cards in a DataFrame column.

        Returns:
            (updated_df, corrections_list, issues_list)

            corrections_list — rows where the value was auto-fixed (valid after correction)
            issues_list      — rows that remain invalid after all correction attempts
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

            if result.was_corrected:
                df.at[idx, column] = result.card
                corrections.append({
                    "DataFrame_Index": idx,
                    "Excel_Row": excel_row,
                    "Column": column,
                    "Original": result.original,
                    "Corrected": result.card,
                    "Reason": result.reason,
                })

            elif not result.is_valid:
                issues.append({
                    "DataFrame_Index": idx,
                    "Excel_Row": excel_row,
                    "Column": column,
                    "Original": result.original,
                    "Issue": result.reason,
                    "Expected_Format": "MH-DD-BBB-GGG-NNN/NNNNNN",
                })

        logger.info(
            "validate_dataframe('%s'): %d corrected, %d invalid, out of %d records.",
            column, len(corrections), len(issues), len(df),
        )
        return df, corrections, issues

    def get_statistics(self, df: pd.DataFrame, column: str = "mgnrega") -> Dict:
        """Return a validation summary dict in a single pass."""
        if column not in df.columns:
            return {}

        total = len(df)
        blank = valid = corrected = invalid = 0

        for raw in df[column]:
            result = self.validate(raw)
            if not result.original:
                blank += 1
            elif result.is_valid and result.was_corrected:
                valid += 1
                corrected += 1
            elif result.is_valid:
                valid += 1
            else:
                invalid += 1

        filled = total - blank
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
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    validator = MGNREGAValidator()

    # (input, expected_card, expected_is_valid)
    test_cases = [
        # ── Valid as-is ──
        ("MH-07-001-023-045/000012",   "MH-07-001-023-045/000012", True),
        # ── Auto-correctable ──
        ("mh-07-001-023-045/000012",   "MH-07-001-023-045/000012", True),   # lowercase
        ("MH-07-001-023-045-000012",   "MH-07-001-023-045/000012", True),   # dash→slash
        ("MH - 07 - 001 - 023 - 045/000012", "MH-07-001-023-045/000012", True),  # spaces
        ("07001023045000012",           "MH-07-001-023-045/000012", True),   # digits only (17 digits assumed MH)
        # ── Invalid ──
        ("GJ-07-001-023-045/000012",   "GJ-07-001-023-045/000012", False),  # wrong state
        ("MH-7-001-023-045/000012",    "MH-7-001-023-045/000012",  False),  # DD too short
        ("MH-07-001-023-045/00012",    "MH-07-001-023-045/00012",  False),  # member# too short
        ("MH-07-001-023/000012",       "MH-07-001-023/000012",     False),  # missing a part
        ("ABCDEFG",                    "ABCDEFG",                  False),  # gibberish
        # ── Blank / null ──
        ("",                           "",    True),
        (None,                         "",    True),
        (float("nan"),                 "",    True),
    ]

    print("MGNREGA Validator — Self-Test")
    print("=" * 70)
    all_passed = True
    for raw, exp_card, exp_valid in test_cases:
        result = validator.validate(raw)
        ok = result.card == exp_card and result.is_valid == exp_valid
        if not ok:
            all_passed = False
        status = "✅ PASS" if ok else "❌ FAIL"
        validity = "VALID  " if result.is_valid else "INVALID"
        corrected_tag = " [auto-fixed]" if result.was_corrected else ""
        print(f"{status}  [{validity}]  {repr(raw)!s:<42} → {repr(result.card)}{corrected_tag}")
        if not ok:
            print(f"       Expected card={repr(exp_card)}, is_valid={exp_valid}")
        if not result.is_valid:
            print(f"       Reason: {result.reason}")

    print()
    print("All tests passed ✅" if all_passed else "Some tests FAILED ❌")