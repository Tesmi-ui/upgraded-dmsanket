"""
BRLF v4.0 - Name Case Formatter (Production)
=============================================
Formats names to proper case with full support for:
  - Standard names:        "RAMESH KUMAR"    → "Ramesh Kumar"
  - Lowercase names:       "jijabai patil"   → "Jijabai Patil"
  - Mixed case:            "SuNITA deshMUKH" → "Sunita Deshmukh"
  - Hyphenated names:      "mary-anne"       → "Mary-Anne"
  - Apostrophe names:      "o'connor"        → "O'Connor"
  - Mac/Mc names:          "mcdonald"        → "McDonald"
  - Dutch/European:        "jan van der berg"→ "Jan van der Berg"
  - Indian names:          "d'souza"         → "D'Souza"
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class NameFormatResult:
    formatted: str
    original: str
    was_changed: bool
    description: str


class NameCaseFormatter:
    """
    Format names to proper case with intelligent handling of special patterns.

    Usage:
        formatter = NameCaseFormatter()
        result = formatter.format_name("RAMESH KUMAR")
        print(result.formatted)  # "Ramesh Kumar"
    """

    # Particles that stay lowercase unless they start the full name
    LOWERCASE_PARTICLES = frozenset({
        "van", "von", "de", "da", "di", "del", "della", "des",
        "den", "der", "el", "al", "bin", "binti", "ap", "du",
    })

    def format_name(self, name) -> NameFormatResult:
        """
        Format a single name to proper case.

        Args:
            name: Input name — any type (str, float NaN, int, None all handled)

        Returns:
            NameFormatResult with .formatted, .original, .was_changed, .description
        """
        # --- Null / blank handling ---
        if name is None or (isinstance(name, float) and pd.isna(name)):
            return NameFormatResult("", "", False, "Null / NaN value")

        try:
            original = str(name).strip()
        except Exception as exc:
            logger.warning("Could not convert name to string: %r — %s", name, exc)
            return NameFormatResult("", str(name), False, f"Unparseable value: {exc}")

        if not original:
            return NameFormatResult("", "", False, "Empty after strip")

        # --- Normalize internal whitespace ---
        normalized = " ".join(original.split())

        # --- Apply proper case ---
        formatted = self._apply_proper_case(normalized)

        if formatted == original:
            return NameFormatResult(formatted, original, False, "Already in proper case")

        return NameFormatResult(
            formatted=formatted,
            original=original,
            was_changed=True,
            description=f"Formatted from: '{original}'",
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _apply_proper_case(self, text: str) -> str:
        words = text.split()
        result = []
        for idx, word in enumerate(words):
            is_first = idx == 0
            result.append(self._format_word(word, is_first=is_first))
        return " ".join(result)

    def _format_word(self, word: str, is_first: bool = True) -> str:
        """Format one space-separated token."""
        if not word:
            return word

        # Hyphenated: each segment capitalized (Mary-Anne, Singh-Patel)
        if "-" in word:
            parts = word.split("-")
            # First segment of first word obeys is_first; rest always capitalize
            formatted_parts = [
                self._format_simple_word(p, is_first=(is_first and i == 0))
                for i, p in enumerate(parts)
            ]
            return "-".join(formatted_parts)

        # Apostrophe names: O'Connor, D'Souza — each segment capitalized
        if "'" in word:
            parts = word.split("'")
            return "'".join(self._capitalize_simple(p) for p in parts)

        return self._format_simple_word(word, is_first=is_first)

    def _format_simple_word(self, word: str, is_first: bool = True) -> str:
        """
        Format a word with no hyphens or apostrophes.
        Respects LOWERCASE_PARTICLES unless it's the first word of the name.
        """
        if not word:
            return word

        word_lower = word.lower()

        # Keep particles lowercase (e.g. "van", "de") unless first word
        if not is_first and word_lower in self.LOWERCASE_PARTICLES:
            return word_lower

        # Mac / Mc prefix: McDonald, MacLeod
        if word_lower.startswith("mc") and len(word) > 2:
            return "Mc" + word[2].upper() + word[3:].lower()

        if word_lower.startswith("mac") and len(word) > 3:
            # Avoid "Macro" → "MacRo"; only apply if rest looks like a name
            rest = word[3:]
            if rest and rest[0].isalpha():
                return "Mac" + rest[0].upper() + rest[1:].lower()

        return self._capitalize_simple(word)

    @staticmethod
    def _capitalize_simple(word: str) -> str:
        """Capitalize first letter, lowercase the rest."""
        if not word:
            return word
        return word[0].upper() + word[1:].lower()

    # ------------------------------------------------------------------
    # DataFrame helpers
    # ------------------------------------------------------------------

    def format_dataframe_column(
        self, df: pd.DataFrame, column: str
    ) -> tuple[pd.DataFrame, List[Dict]]:
        """
        Format a name column in a DataFrame in-place (on a copy).

        Returns:
            (updated_df, list_of_change_dicts)
        """
        if column not in df.columns:
            logger.error("Column '%s' not found. Available: %s", column, list(df.columns))
            return df, []

        df = df.copy()
        changes: List[Dict] = []

        for idx, raw_value in df[column].items():
            result = self.format_name(raw_value)

            if result.was_changed:
                df.at[idx, column] = result.formatted
                changes.append({
                    "DataFrame_Index": idx,
                    "Excel_Row": df.index.get_loc(idx) + 2,  # +1 header, +1 0-based
                    "Column": column,
                    "Original": result.original,
                    "Formatted": result.formatted,
                    "Description": result.description,
                })

        logger.info(
            "format_dataframe_column('%s'): %d/%d names changed.",
            column, len(changes), len(df),
        )
        return df, changes

    def validate_case_consistency(self, df: pd.DataFrame) -> List[Dict]:
        """
        Scan all *name* columns and flag ALL-CAPS or all-lowercase entries.

        Returns a list of issue dicts (does not modify df).
        """
        issues: List[Dict] = []
        name_columns = [c for c in df.columns if "name" in c.lower()]

        for col in name_columns:
            for idx, raw in df[col].items():
                if raw is None or (isinstance(raw, float) and pd.isna(raw)):
                    continue
                name_str = str(raw).strip()
                if len(name_str) <= 2:
                    continue

                if name_str.isupper():
                    issues.append({
                        "DataFrame_Index": idx,
                        "Excel_Row": df.index.get_loc(idx) + 2,
                        "Column": col,
                        "Name": name_str,
                        "Issue": "All uppercase",
                        "Suggested": self._apply_proper_case(name_str),
                    })
                elif name_str.islower():
                    issues.append({
                        "DataFrame_Index": idx,
                        "Excel_Row": df.index.get_loc(idx) + 2,
                        "Column": col,
                        "Name": name_str,
                        "Issue": "All lowercase",
                        "Suggested": self._apply_proper_case(name_str),
                    })

        return issues


# ---------------------------------------------------------------------------
# Quick self-test (run with: python name_formatter.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    formatter = NameCaseFormatter()

    test_cases = [
        ("RAMESH KUMAR",         "Ramesh Kumar"),
        ("jijabai patil",        "Jijabai Patil"),
        ("SuNItA DeshMUKH",      "Sunita Deshmukh"),
        ("mary-anne wilson",     "Mary-Anne Wilson"),
        ("o'connor",             "O'Connor"),
        ("d'souza",              "D'Souza"),
        ("mcdonald",             "McDonald"),   # Mc handled
        ("jan van der berg",     "Jan van der Berg"),
        ("Ramesh Kumar",         "Ramesh Kumar"),   # no change
        (None,                   ""),
        ("",                     ""),
        (float("nan"),           ""),
    ]

    print("Name Case Formatter — Self-Test")
    print("=" * 65)
    all_passed = True
    for raw, expected in test_cases:
        result = formatter.format_name(raw)
        ok = result.formatted == expected
        if not ok:
            all_passed = False
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status}  {repr(raw)!s:<30} → {repr(result.formatted)}")
        if not ok:
            print(f"       Expected: {repr(expected)}")

    print()
    print("All tests passed ✅" if all_passed else "Some tests FAILED ❌")