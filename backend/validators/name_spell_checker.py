"""
backend/validators/name_spell_checker.py
=========================================
Token-by-token spelling correction for Indian farmer names.

Extracted from core_engine.py and all bugs fixed:

FIXES vs core_engine.py
------------------------
  1. PERF FIX: check_series() stores token_results directly from check_name()
     — no second check_name() call per name (core_engine called it twice).

  2. BUG FIX: _PHONETIC_RULES 'v'→'w' now has \\b word-boundary anchor so it
     only fires at word start, not mid-word (was corrupting "avanthi" etc.).

  3. BUG FIX: Phonetic rules applied in order to working copy; vowel-strip
     runs last so it doesn't clobber previous substitutions.

  4. DEDUPLICATION: FEMALE_NAMES, MALE_NAMES, SURNAME_CATEGORY imported from
     gender_lib.knowledge_base — not redefined here.

  5. Python 3.8 compat: from __future__ import annotations added.
"""

from __future__ import annotations

import difflib
import re
from typing import Dict, List, Tuple

import pandas as pd

from gender_lib.knowledge_base import (
    FEMALE_NAMES,
    MALE_NAMES,
    SURNAME_CATEGORY,
)

# ---------------------------------------------------------------------------
# Protected names — valid regional Indian name variants that must never be
# "corrected" even if they are close to another known name in the dictionary.
# Govinda ≠ Govind, Chandar ≠ Chandra, Bhimraj ≠ Bhimrao — these are distinct.
# ---------------------------------------------------------------------------
PROTECTED_NAMES: frozenset = frozenset({
    # Male names — Sanskrit / Marathi variants
    "govinda", "govind",
    "chandar", "chandra", "chandram",
    "bhimraj", "bhimrao",
    "shankar", "shankara",
    "omkar", "omkara",
    "vitthal", "vithal",
    "kailas", "kailash",
    "sudam", "sudama",
    "ramdas", "ramadas",
    "devidas", "devdas",
    "tukaram", "tukarama",
    "namdev", "namdeo",
    "dnyandev", "dnyandeo", "dnyaneshwar",
    "eknath", "eknath",
    "brahmananda", "brahmanand",
    "sacchidananda", "sachchidanand",
    "vijayananda", "vijayanand",
    "shivananda", "shivanand",
    "ananda", "anand",
    "premlal", "premchand",
    "tarachand", "tarachan",
    "chunnilal", "chunilal",
    "mayalal", "maialal",
    "hemraj", "himraj",
    "youraj", "yuraj",
    "uddal", "udal",
    "ramu", "rama",
    "kalu", "kala",
    "bhura", "bhuraji",
    # Female names — regional variants
    "anjanabai", "anjnabai",
    "kamlabai", "kamaladevi",
    "shantabai", "shantidevi",
    "subhadrabai", "subhadra",
    "parvatibai", "parvatabai",
    "vimalbai", "vimaladevi",
    "shobhabai", "shobhadevi",
    # Common surnames in Vidarbha that look like other names
    "pandhare", "pandhari",
    "mandhare", "mandhari",
    "nagoshe", "nagose",
    "nehare", "nehara",
    "dhanre", "dhanra",
    "borkar", "borker",
    "gharat", "ghrad",
    "madavi", "madawi",
    "markulwar", "markulvar",
})

# Extended surname vocabulary
KNOWN_SURNAMES: set = set(SURNAME_CATEGORY.keys()) | {
    "balbudhe", "mohapure", "mohanpure", "nagoshe", "nikude", "pendor",
    "bhoyar", "bobade", "ijpade", "shende", "darane", "pote", "more",
    "vagh", "zamre", "bagath", "nehare", "dhanre", "ruparail", "madavagade",
    "kothekar", "aaglave", "borkute", "mandhare", "uike", "dhvas",
    "kamble", "kambale", "bele", "kawade",
}


class NameSpellChecker:
    """
    Token-by-token spelling correction for Indian farmer names.
    stdlib only — no pip install required.

    Token routing:
      • Position 0         → first name  → FEMALE_NAMES | MALE_NAMES
      • Positions 1..n-2   → middle      → FEMALE_NAMES | MALE_NAMES
      • Last position n-1  → surname     → KNOWN_SURNAMES
    """

    # FIX: \\b anchor on 'v'→'w' prevents mid-word corruption
    # FIX: vowel-strip last so it doesn't clobber earlier rules
    _PHONETIC_RULES: List[Tuple[str, str]] = [
        (r"ee",        "i"),
        (r"oo",        "u"),
        (r"ae$",       "ai"),
        (r"ey$",       "ay"),
        (r"er$",       "ar"),
        (r"or$",       "ar"),
        (r"kh",        "k"),
        (r"gh",        "g"),
        (r"aa",        "a"),
        (r"sh",        "s"),
        (r"\bv",       "w"),   # FIX: word-start only
        (r"[aeiou]+$", ""),    # FIX: last — trailing vowel strip for root
    ]

    _COMPILED: List[Tuple[re.Pattern, str]] = [
        (re.compile(p), r) for p, r in _PHONETIC_RULES
    ]

    def __init__(
        self,
        min_confidence:    int = 70,
        high_confidence:   int = 90,  # FIX: raised from 80 to avoid false positives
        max_edit_distance: int = 2,
    ):
        self.min_confidence  = min_confidence
        self.high_confidence = high_confidence
        self.max_edit_dist   = max_edit_distance

        self._first_vocab   = FEMALE_NAMES | MALE_NAMES
        self._surname_vocab = KNOWN_SURNAMES

        self._first_phonetic   = self._build_phonetic_index(self._first_vocab)
        self._surname_phonetic = self._build_phonetic_index(self._surname_vocab)

    # ── Public API ────────────────────────────────────────────────────────────

    def check_name(self, full_name: str) -> dict:
        """
        Check and correct spelling in one full farmer name.

        Returns dict with keys: original, corrected, changed, tokens.
        Each token dict: position, role, original, corrected,
                         confidence, method, status.
        """
        if not full_name or not str(full_name).strip():
            return {"original": full_name, "corrected": full_name,
                    "changed": False, "tokens": []}

        tokens = str(full_name).strip().split()
        n      = len(tokens)
        result_tokens   = []
        corrected_parts = []

        for pos, tok in enumerate(tokens):
            role = ("first"   if pos == 0
                    else "surname" if pos == n - 1 and n > 1
                    else "middle")

            if len(tok) <= 2 or tok.isdigit():
                result_tokens.append({
                    "position": pos, "role": role,
                    "original": tok, "corrected": tok,
                    "confidence": 0, "method": "skipped_short",
                    "status": "correct",
                })
                corrected_parts.append(tok)
                continue

            vocab    = self._surname_vocab if role == "surname" else self._first_vocab
            phonetic = self._surname_phonetic if role == "surname" else self._first_phonetic

            new_tok, conf, method = self._correct_token(tok.lower(), vocab, phonetic)

            if conf == 100:
                result_tokens.append({
                    "position": pos, "role": role,
                    "original": tok, "corrected": tok,
                    "confidence": 100, "method": method,
                    "status": "correct",
                })
                corrected_parts.append(tok)

            elif conf >= self.min_confidence and new_tok != tok.lower():
                cap    = new_tok.capitalize()
                status = "corrected" if conf >= self.high_confidence else "review"
                result_tokens.append({
                    "position": pos, "role": role,
                    "original": tok, "corrected": cap,
                    "confidence": conf, "method": method,
                    "status": status,
                })
                corrected_parts.append(cap)

            else:
                result_tokens.append({
                    "position": pos, "role": role,
                    "original": tok, "corrected": tok,
                    "confidence": conf, "method": method,
                    "status": "unknown" if conf == 0 else "review",
                })
                corrected_parts.append(tok)

        corrected_name = " ".join(corrected_parts)
        return {
            "original":  full_name,
            "corrected": corrected_name,
            "changed":   corrected_name != full_name,
            "tokens":    result_tokens,
        }

    def check_series(self, series: pd.Series) -> pd.DataFrame:
        """
        Apply check_name() across a pandas Series.

        FIX: token_results stored directly — no second check_name() call.
        Returns DataFrame with: original, corrected, changed,
                                n_corrections, detail, token_results
        """
        rows = []
        for name in series:
            r = self.check_name(str(name) if name is not None else "")
            changed_tokens = [
                t for t in r["tokens"]
                if t["status"] in ("corrected", "review")
                and t["original"].lower() != t["corrected"].lower()
            ]
            rows.append({
                "original":      r["original"],
                "corrected":     r["corrected"],
                "changed":       r["changed"],
                "n_corrections": len(changed_tokens),
                "detail": "; ".join(
                    f"{t['original']}→{t['corrected']}({t['confidence']}%,{t['method']})"
                    for t in changed_tokens
                ),
                "token_results": r["tokens"],   # FIX: stored, not recomputed
            })
        return pd.DataFrame(rows)

    # ── Internals ─────────────────────────────────────────────────────────────

    @staticmethod
    def _levenshtein(s1: str, s2: str) -> int:
        m, n = len(s1), len(s2)
        if s1 == s2:       return 0
        if m == 0:         return n
        if n == 0:         return m
        if abs(m - n) > 3: return abs(m - n)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[:]
            dp[0] = i
            for j in range(1, n + 1):
                dp[j] = (prev[j - 1] if s1[i - 1] == s2[j - 1]
                         else 1 + min(prev[j], dp[j - 1], prev[j - 1]))
        return dp[n]

    def _phonetic_key(self, s: str) -> str:
        s = s.lower()
        for pattern, repl in self._COMPILED:
            s = pattern.sub(repl, s)
        return s

    def _build_phonetic_index(self, vocab: set) -> Dict[str, List[str]]:
        idx: Dict[str, List[str]] = {}
        for name in vocab:
            key = self._phonetic_key(name)
            idx.setdefault(key, []).append(name)
        return idx

    def _correct_token(
        self,
        token:        str,
        vocab:        set,
        phonetic_idx: Dict[str, List[str]],
    ) -> Tuple[str, int, str]:
        if token in vocab:
            return (token, 100, "exact_match")

        # Never correct a protected name — it is a valid regional variant
        if token in PROTECTED_NAMES:
            return (token, 100, "protected_name")

        best_name, best_conf, best_method = token, 0, "no_match"

        ph_key     = self._phonetic_key(token)
        ph_matches = phonetic_idx.get(ph_key, [])
        if ph_matches:
            top  = min(ph_matches, key=lambda c: self._levenshtein(token, c))
            dist = self._levenshtein(token, top)
            if dist <= self.max_edit_dist:
                ratio = difflib.SequenceMatcher(None, token, top).ratio()
                conf  = int(ratio * 92) if dist <= 1 else max(70, int(ratio * 88))
                if conf > best_conf:
                    best_name, best_conf = top, conf
                    best_method = f"phonetic(edit={dist})"

        fuzzy = difflib.get_close_matches(token, vocab, n=3, cutoff=0.75)
        if fuzzy:
            top  = fuzzy[0]
            dist = self._levenshtein(token, top)
            if dist <= self.max_edit_dist:
                ratio = difflib.SequenceMatcher(None, token, top).ratio()
                conf  = int(ratio * 88) if dist <= 1 else int(ratio * 76)
                if conf > best_conf:
                    best_name, best_conf = top, conf
                    best_method = f"fuzzy(edit={dist})"

        if best_conf < self.min_confidence:
            return (token, 0, "no_match")
        return (best_name, best_conf, best_method)