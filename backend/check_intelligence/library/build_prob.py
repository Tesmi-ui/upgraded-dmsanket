"""
build_prob.py  —  Probabilistic Gender Library Builder  (Production)
=====================================================================
Builds  brlf_gender_prob.json  from the  unverified/  folder.

WHO CALLS THIS
--------------
Only  rebuild.py  calls this.  The pipeline reads the JSON.

WHY UNVERIFIED → PROBABILISTIC
--------------------------------
Unverified contains real field data with some noise.  The prob library
captures high-confidence patterns (≥ 95%) that survive that noise.
Worst case of a false positive: an unnecessary suggestion a human ignores.

PROBABILISTIC QUALIFICATION RULES
----------------------------------
  • Total occurrences ≥ min_occurrences (default 3).
  • Dominant-gender ratio ≥ min_confidence (default 0.95).
  • NOT already in the strict library (strict always wins).
  • First token ≥ 3 purely alphabetic characters.

CHANGES FROM ORIGINAL
---------------------
  1. BUG FIX (merge overwrite): The original used `existing.update(new_prob)`
     which REPLACES old entries with new ones, potentially discarding more
     evidence. Now merges counts additively and recalculates confidence.

  2. BUG FIX (stale strict_names): strict_names was loaded once at the start.
     If rebuild.py just ran build_strict before this, the strict JSON on disk
     is now updated. We re-read strict from disk just before the exclusion
     check so the set is always current.

  3. BUG FIX (confidence floor on merge): After additive merge, confidence
     is recalculated. If the merged ratio drops below min_confidence, the
     entry is removed from the library rather than silently staying.

  4. DEDUPLICATION: All shared helpers imported from lib_utils.

  5. PERFORMANCE: read_pairs() now uses vectorised pandas, not iterrows().
"""

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, Set

from gender_intelligence.lib_utils import (
    SUPPORTED_EXTENSIONS,
    checksum,
    load_manifest,
    now_utc,
    read_pairs,
    save_manifest,
)

log = logging.getLogger("gender_intelligence.build_prob")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_prob_library(
    unverified_folder:  str   = "data/unverified",
    strict_path:        str   = "gender_intelligence/brlf_gender_strict.json",
    farmer_col:         str   = "farmer_name",
    gender_col:         str   = "gender",
    min_confidence:     float = 0.95,
    min_occurrences:    int   = 3,
    output_path:        str   = "gender_intelligence/brlf_gender_prob.json",
    manifest_path:      str   = "gender_intelligence/file_manifest.json",
    full_rebuild:       bool  = False,
    dry_run:            bool  = False,
) -> dict:
    """
    Scan unverified_folder, read new/changed files, update prob library.

    Parameters
    ----------
    unverified_folder : Incoming field files (may contain noise).
    strict_path       : Path to strict library — names there are excluded.
                        Read AFTER strict build runs so the set is current.
    farmer_col        : Column name for full farmer name.
    gender_col        : Column name for gender.
    min_confidence    : Minimum dominant-gender ratio (default 0.95).
    min_occurrences   : Minimum total appearances (default 3).
    output_path       : Where to write brlf_gender_prob.json.
    manifest_path     : Path to file_manifest.json.
    full_rebuild      : Ignore manifest, re-read everything.
    dry_run           : Preview only — write nothing.

    Returns
    -------
    Complete probabilistic library dict, or {} on dry_run / empty folder.
    """
    uf_path  = Path(unverified_folder)
    out_path = Path(output_path)
    mf_path  = Path(manifest_path)

    if not uf_path.exists():
        raise FileNotFoundError(
            f"Unverified folder not found: '{uf_path.resolve()}'\n"
            f"Create it and place incoming field files inside it."
        )

    # ── Load strict names NOW (after any preceding build_strict call) ─────────
    # FIX: read from disk at this point, not earlier, so we get the latest set.
    strict_names: Set[str] = set()
    sp = Path(strict_path)
    if sp.exists():
        try:
            strict_names = set(json.loads(sp.read_text(encoding="utf-8")).keys())
            log.info("Strict library: %d names will be excluded from prob", len(strict_names))
        except json.JSONDecodeError:
            log.warning("Could not read strict library at '%s'", strict_path)
    else:
        log.warning(
            "Strict library not found at '%s' — all names eligible for prob",
            strict_path,
        )

    # ── Scan folder ───────────────────────────────────────────────────────────
    all_files = sorted(
        p for p in uf_path.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not all_files:
        log.warning("No supported files in '%s' — nothing to build", uf_path)
        return {}

    log.info("Scanning '%s'  →  %d file(s) found", uf_path, len(all_files))

    manifest = load_manifest(mf_path)
    ingested = manifest.setdefault("unverified_files", {})

    to_read: list[Path] = []
    to_skip: list[Path] = []

    for f in all_files:
        chk  = checksum(f)
        prev = ingested.get(f.name, {})
        if not full_rebuild and prev.get("checksum") == chk:
            to_skip.append(f)
        else:
            to_read.append(f)

    for f in to_skip:
        log.info("  SKIP  (unchanged): %s", f.name)
    for f in to_read:
        log.info("  READ  (%s): %s", "new" if f.name not in ingested else "modified", f.name)

    if not to_read:
        log.info("All files already ingested — prob library is up to date")
        if out_path.exists():
            return json.loads(out_path.read_text(encoding="utf-8"))
        return {}

    if dry_run:
        log.info("DRY RUN — %d file(s) would be read, nothing written", len(to_read))
        return {}

    # ── Read new/changed files ────────────────────────────────────────────────
    # Accumulate counts across all new files before qualifying
    new_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"male": 0, "female": 0})
    new_file_sets: Dict[str, set] = defaultdict(set)
    now = now_utc()

    for f in to_read:
        try:
            pairs, total_rows = read_pairs(f, farmer_col, gender_col)
        except ValueError as exc:
            log.error("  SKIP '%s' — %s", f.name, exc)
            continue
        except Exception as exc:
            log.error("  SKIP '%s' — unexpected error: %s", f.name, exc)
            continue

        for first, gender in pairs:
            new_counts[first][gender] += 1
            new_file_sets[first].add(f.name)

        ingested[f.name] = {
            "path":        str(f.resolve()),
            "ingested_at": now,
            "total_rows":  total_rows,
            "pair_count":  len(pairs),
            "checksum":    checksum(f),
        }
        log.info("  Read '%s': %d pairs / %d rows", f.name, len(pairs), total_rows)

    # ── Load existing prob library ────────────────────────────────────────────
    existing: dict = {}
    if out_path.exists() and not full_rebuild:
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            log.info("Loaded existing prob library: %d entries", len(existing))
        except json.JSONDecodeError:
            log.warning("Existing prob library corrupt — rebuilding from new files only")

    # ── Merge new counts into existing (ADDITIVE, then re-qualify) ───────────
    # FIX: merge counts first, THEN re-qualify — never blindly overwrite.
    for name, c in new_counts.items():
        if name in strict_names:
            continue  # strict always wins

        if name in existing:
            # Accumulate evidence from both old and new observations
            existing[name]["male_count"]   += c["male"]
            existing[name]["female_count"] += c["female"]
            existing[name]["total"]         = (
                existing[name]["male_count"] + existing[name]["female_count"]
            )
            existing[name]["source_files"]  = sorted(
                set(existing[name].get("source_files", [])) | new_file_sets[name]
            )
            existing[name]["built_at"] = now
        else:
            m, f   = c["male"], c["female"]
            total  = m + f
            existing[name] = {
                "gender":       "",    # will be set during re-qualification below
                "confidence":   0.0,
                "male_count":   m,
                "female_count": f,
                "total":        total,
                "source_files": sorted(new_file_sets[name]),
                "built_at":     now,
            }

    # ── Re-qualify every entry (confidence may have changed after merge) ──────
    to_remove = []
    for name, entry in existing.items():
        # FIX: also re-check against strict_names (may have grown since last prob build)
        if name in strict_names:
            to_remove.append(name)
            log.info("  PROMOTED '%s' — prob → strict (now in strict library)", name)
            continue

        m     = entry["male_count"]
        f     = entry["female_count"]
        total = entry["total"]

        if total < min_occurrences:
            to_remove.append(name)
            continue

        ratio_m = m / total
        ratio_f = f / total

        if ratio_m >= min_confidence:
            entry["gender"]     = "male"
            entry["confidence"] = round(ratio_m, 4)
        elif ratio_f >= min_confidence:
            entry["gender"]     = "female"
            entry["confidence"] = round(ratio_f, 4)
        else:
            # FIX: confidence dropped below threshold after merging more data — remove
            log.info(
                "  REMOVED '%s' — confidence dropped to %.3f after merge "
                "(below threshold %.2f)",
                name, max(ratio_m, ratio_f), min_confidence,
            )
            to_remove.append(name)

    for name in to_remove:
        existing.pop(name, None)

    final = dict(sorted(existing.items()))
    log.info("Final prob library: %d entries", len(final))

    # ── Write prob library ────────────────────────────────────────────────────
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Written: '%s'  (%d KB)", out_path, out_path.stat().st_size // 1024)

    # ── Update manifest ───────────────────────────────────────────────────────
    manifest["last_prob_build"] = now
    save_manifest(manifest, mf_path)
    log.info("Manifest updated: '%s'", mf_path)

    m_c = sum(1 for v in final.values() if v["gender"] == "male")
    f_c = sum(1 for v in final.values() if v["gender"] == "female")
    log.info("Stats → male=%d  female=%d  total=%d", m_c, f_c, len(final))

    return final


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import logging

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")

    p = argparse.ArgumentParser(description="Build BRLF Probabilistic Gender Library")
    p.add_argument("--unverified-dir", default="data/unverified")
    p.add_argument("--strict",         default="gender_intelligence/brlf_gender_strict.json")
    p.add_argument("--output",         default="gender_intelligence/brlf_gender_prob.json")
    p.add_argument("--manifest",       default="gender_intelligence/file_manifest.json")
    p.add_argument("--farmer-col",     default="farmer_name")
    p.add_argument("--gender-col",     default="gender")
    p.add_argument("--min-conf",       default=0.95, type=float)
    p.add_argument("--min-occ",        default=3,    type=int)
    p.add_argument("--full",           action="store_true")
    p.add_argument("--dry-run",        action="store_true")

    args   = p.parse_args()
    result = build_prob_library(
        unverified_folder = args.unverified_dir,
        strict_path       = args.strict,
        farmer_col        = args.farmer_col,
        gender_col        = args.gender_col,
        min_confidence    = args.min_conf,
        min_occurrences   = args.min_occ,
        output_path       = args.output,
        manifest_path     = args.manifest,
        full_rebuild      = args.full,
        dry_run           = args.dry_run,
    )
    if not args.dry_run and result:
        m = sum(1 for v in result.values() if v["gender"] == "male")
        f = sum(1 for v in result.values() if v["gender"] == "female")
        print(f"\n✓  Prob library: {len(result)} names  (male={m}  female={f})")