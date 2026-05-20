"""
backend/execution_context.py
=============================
Execution control layer for the BRLF intelligence pipeline.

Three modes:

  GLOBAL    — default, backward-compatible.
              Every rule and every column is allowed.
              Behaves exactly like v4.0 with no context supplied.

  SELECTIVE — reduced-risk mode.
              Only the columns listed in `selected_columns` may be mutated.
              Only the rules listed in `selected_rules` may run.
              Any attempt to modify a non-selected column raises RuntimeError
              (enforced by the column-integrity check in DataMigrationEngine.process()).

  ADVISORY  — zero-mutation mode.
              All inference and correction logic runs (so audit logs are produced)
              but no values are ever written back to the DataFrame.
              dry_run is forced True automatically.

Usage
-----
# Run everything as before:
ctx = ExecutionContext(mode=ExecutionMode.GLOBAL)

# Only fix gender and run dedup:
ctx = ExecutionContext(
    mode=ExecutionMode.SELECTIVE,
    selected_columns=["gender"],
    selected_rules=["deduplicate", "auto_correct", "auto_correct_gender"],
)

# See what would change without touching anything:
ctx = ExecutionContext(mode=ExecutionMode.ADVISORY)

API contract
------------
allow_rule(name)   → True  if the named rule is permitted to run
allow_column(name) → True  if the named column is permitted to be mutated
dry_run            → True  means log but never assign DataFrame values

Rule name registry (used by intelligence_engine.py)
-----------------------------------------------------
  "format_name"          — NameCaseFormatter in run_pipeline()
  "validate_contact"     — ContactValidator in run_pipeline()
  "validate_mgnrega"     — MGNREGAValidator in run_pipeline()
  "infer_gender"         — gender inference in run_pipeline()
  "infer_category"       — category inference in run_pipeline()
  "deduplicate"          — _remove_duplicates() in DataMigrationEngine
  "auto_correct"         — _auto_correct() top-level gate
  "auto_correct_gender"  — gender block inside _auto_correct()
  "auto_correct_category"— category block inside _auto_correct()
  "spell_check"          — _spell_check_names() in DataMigrationEngine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Set


class ExecutionMode(str, Enum):
    """Operating mode for the intelligence pipeline."""
    GLOBAL    = "GLOBAL"
    SELECTIVE = "SELECTIVE"
    ADVISORY  = "ADVISORY"


@dataclass
class ExecutionContext:
    """
    Controls which rules and columns the pipeline is allowed to touch.

    Parameters
    ----------
    mode : ExecutionMode
        GLOBAL    — all rules and columns allowed (default, backward-compatible).
        SELECTIVE — only rules/columns in the selected_* sets are allowed.
        ADVISORY  — all rules run in read-only / log-only mode (dry_run=True).

    selected_columns : set[str] | None
        Column names that may be mutated.
        None (default) means "all columns" when mode is GLOBAL or ADVISORY.
        In SELECTIVE mode None is treated as an empty set (nothing allowed).

    selected_rules : set[str] | None
        Rule names that may execute.
        None (default) means "all rules".
        In SELECTIVE mode None is treated as an empty set (nothing allowed).

    dry_run : bool
        If True: inference / correction logic runs for logging purposes, but
        DataFrame values are never modified.
        Automatically set to True when mode == ADVISORY.
    """

    mode:             ExecutionMode       = ExecutionMode.GLOBAL
    selected_columns: Optional[Set[str]] = None
    selected_rules:   Optional[Set[str]] = None
    dry_run:          bool               = False

    def __post_init__(self) -> None:
        # Normalise: ADVISORY always implies dry_run regardless of what the
        # caller passed, so there is no accidental data mutation in audit mode.
        if self.mode == ExecutionMode.ADVISORY:
            self.dry_run = True

    # ── Permission checks ─────────────────────────────────────────────────────

    def allow_rule(self, name: str) -> bool:
        """
        Return True if the named rule is permitted to execute.

        GLOBAL    → always True (all rules run).
        ADVISORY  → True if no rules specified, OR if name is in selected_rules.
        SELECTIVE → True only if name is in selected_rules.
                    If selected_rules was not provided, returns False
                    (caller must explicitly list every rule they want).
        """
        if self.mode == ExecutionMode.GLOBAL:
            return True
        if self.mode == ExecutionMode.ADVISORY and self.selected_rules is None:
            return True
        # SELECTIVE or restricted ADVISORY
        if self.selected_rules is None:
            return False
        return name in self.selected_rules

    def allow_column(self, name: str) -> bool:
        """
        Return True if the named column is permitted to be mutated.

        GLOBAL    → always True.
        ADVISORY  → True if no columns specified, OR if name is in selected_columns.
        SELECTIVE → True only if name is in selected_columns.
                    If selected_columns was not provided, returns False.
        """
        if self.mode == ExecutionMode.GLOBAL:
            return True
        if self.mode == ExecutionMode.ADVISORY and self.selected_columns is None:
            return True
        # SELECTIVE or restricted ADVISORY
        if self.selected_columns is None:
            return False
        return name in self.selected_columns

    # ── Convenience constructors ──────────────────────────────────────────────

    @classmethod
    def global_mode(cls) -> ExecutionContext:
        """Factory: full pipeline, all columns, all rules (v4.0 default)."""
        return cls(mode=ExecutionMode.GLOBAL)

    @classmethod
    def advisory_mode(
        cls,
        columns: Optional[Set[str]] = None,
        rules: Optional[Set[str]] = None,
    ) -> ExecutionContext:
        """Factory: full audit run, zero data mutation (with optional restrictions)."""
        return cls(
            mode=ExecutionMode.ADVISORY,
            selected_columns=columns,
            selected_rules=rules,
        )

    @classmethod
    def selective_mode(
        cls,
        columns: Set[str],
        rules:   Set[str],
    ) -> ExecutionContext:
        """
        Factory: only the listed columns and rules may run.

        Example — fix gender only:
            ExecutionContext.selective_mode(
                columns={"gender"},
                rules={"deduplicate", "auto_correct", "auto_correct_gender"},
            )
        """
        return cls(
            mode=ExecutionMode.SELECTIVE,
            selected_columns=columns,
            selected_rules=rules,
        )

    # ── Repr ─────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        cols  = sorted(self.selected_columns) if self.selected_columns else "ALL"
        rules = sorted(self.selected_rules)   if self.selected_rules   else "ALL"
        return (
            f"ExecutionContext(mode={self.mode.value}, "
            f"dry_run={self.dry_run}, "
            f"columns={cols}, "
            f"rules={rules})"
        )