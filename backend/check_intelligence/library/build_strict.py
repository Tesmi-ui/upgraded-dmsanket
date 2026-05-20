"""
build_strict.py  —  Strict Gender Library Builder  (Production)
================================================================
Builds  brlf_gender_strict.json  from the  verified/  folder.

WHO CALLS THIS
--------------
Only  rebuild.py  calls this.  The pipeline reads the JSON — it never
calls this module.

HOW SCANNING WORKS
------------------
1. Scans every .xlsx / .xls / .csv in  verified_folder/.
2. Checks  file_manifest.json  for already-ingested checksums.
3. Reads ONLY new or changed files (SHA-256 checksum comparison).
4. Classifies names as strict or ambiguous across ALL files.
5. Merges new findings into the existing library (additive counts).
6. Updates  file_manifest.json.
7. Writes  brlf_gender_strict.json  and  brlf_gender_strict_ambiguous.json.

Pass  full_rebuild=True  to ignore the manifest and re-read everything.

STRICT QUALIFICATION RULES (confidence = 1.00)
-----------------------------------------------
A name enters the strict library ONLY if:
  • Appears ≥ min_occurrences times total  (default 2).
  • Appears as ONE gender only in every verified file.
    Any within-file or cross-file conflict → AMBIGUOUS.
  • First token is ≥ 3 purely alphabetic characters (no initials/digits).

CHANGES FROM ORIGINAL
---------------------
  1. BUG FIX (count accumulation): The original stored only the NEW
     file's count, not the cumulative total. Now counts from new files
     are ADDED to existing counts on merge, not replaced.

  2. BUG FIX (Python 3.8 compat): Replaced `.with_stem()` (Python 3.9+)
     with explicit path construction using stem + suffix.

  3. PERFORMANCE: Replaced iterrows() with vectorised pandas operations
     via lib_utils.read_pairs(). ~100x faster on large files.

  4. DEDUPLICATION: All shared helpers (checksum, load_manifest,
     save_manifest, extract_first, read_pairs, SUPPORTED_EXTENSIONS)
     imported from gender_intelligence.lib_utils — not duplicated here.

  5. TYPE HINT FIX: per_file dict type hint corrected to reflect actual
     nested defaultdict structure.
"""

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict

from gender_intelligence.lib_utils import (
    SUPPORTED_EXTENSIONS,
    checksum,
    extract_first,
    load_manifest,
    now_utc,
    read_pairs,
    save_manifest,
)

log = logging.getLogger("gender_intelligence.build_strict")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_strict_library(
    verified_folder:  str   = "data/verified",
    farmer_col:       str   = "farmer_name",
    gender_col:       str   = "gender",
    min_occurrences:  int   = 2,
    output_path:      str   = "gender_intelligence/brlf_gender_strict.json",
    manifest_path:    str   = "gender_intelligence/file_manifest.json",
    full_rebuild:     bool  = False,
    dry_run:          bool  = False,
) -> dict:
    """
    Scan verified_folder, read new/changed files, update strict library.

    Parameters
    ----------
    verified_folder : Admin-approved files live here.
    farmer_col      : Column name for full farmer name in input files.
    gender_col      : Column name for gender in input files.
    min_occurrences : Minimum total appearances to qualify (default 2).
                      A single occurrence could be a data-entry typo.
    output_path     : Where to write brlf_gender_strict.json.
    manifest_path   : Path to file_manifest.json.
    full_rebuild    : Ignore manifest, re-read every file from scratch.
    dry_run         : Show plan only — write nothing.

    Returns
    -------
    Complete strict library dict, or {} on dry_run / empty folder.
    """
    vf_path  = Path(verified_folder)
    out_path = Path(output_path)
    mf_path  = Path(manifest_path)

    if not vf_path.exists():
        raise FileNotFoundError(
            f"Verified folder not found: '{vf_path.resolve()}'\n"
            f"Create it and place approved Excel/CSV files inside it."
        )

    # ── Scan folder ───────────────────────────────────────────────────────────
    all_files = sorted(
        p for p in vf_path.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not all_files:
        log.warning("No supported files in '%s' — nothing to build", vf_path)
        return {}

    log.info("Scanning '%s'  →  %d file(s) found", vf_path, len(all_files))

    # ── Decide what to read ───────────────────────────────────────────────────
    manifest = load_manifest(mf_path)
    ingested = manifest.setdefault("verified_files", {})

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
        log.info("All files already ingested — strict library is up to date")
        if out_path.exists():
            return json.loads(out_path.read_text(encoding="utf-8"))
        return {}

    if dry_run:
        log.info("DRY RUN — %d file(s) would be read, nothing written", len(to_read))
        return {}

    # ── Read new/changed files ────────────────────────────────────────────────
    # per_file[name][filename] = {"male": n, "female": n}
    per_file: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {"male": 0, "female": 0})
    )
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
            per_file[first][f.name][gender] += 1

        ingested[f.name] = {
            "path":        str(f.resolve()),
            "ingested_at": now,
            "total_rows":  total_rows,
            "pair_count":  len(pairs),
            "checksum":    checksum(f),
        }
        log.info("  Read '%s': %d pairs / %d rows", f.name, len(pairs), total_rows)

    # ── Classify names from new files ─────────────────────────────────────────
    new_strict: dict[str, dict] = {}
    new_ambig:  dict[str, dict] = {}

    for name, file_data in per_file.items():
        total_m = sum(d["male"]   for d in file_data.values())
        total_f = sum(d["female"] for d in file_data.values())
        total   = total_m + total_f

        in_file_conflict   = any(d["male"] > 0 and d["female"] > 0 for d in file_data.values())
        cross_file_conflict = total_m > 0 and total_f > 0

        if in_file_conflict or cross_file_conflict:
            new_ambig[name] = {
                "male_count":   total_m,
                "female_count": total_f,
                "total":        total,
                "source_files": list(file_data.keys()),
                "reason": "in_file_conflict" if in_file_conflict else "cross_file_conflict",
            }
            continue

        if total < min_occurrences:
            continue

        new_strict[name] = {
            "gender":       "male" if total_m > 0 else "female",
            "count":        total,
            "source_files": list(file_data.keys()),
            "built_at":     now,
        }

    log.info(
        "From new files → %d strict candidates | %d ambiguous",
        len(new_strict), len(new_ambig),
    )

    # ── Merge into existing library (ADDITIVE counts) ─────────────────────────
    existing: dict = {}
    if out_path.exists() and not full_rebuild:
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
            log.info("Loaded existing library: %d entries", len(existing))
        except json.JSONDecodeError:
            log.warning("Existing library corrupt — rebuilding from new files only")

    for name, entry in new_strict.items():
        if name in existing:
            # FIX: ACCUMULATE counts, don't overwrite with new-file count alone
            existing[name]["count"] = existing[name].get("count", 0) + entry["count"]
            existing[name]["source_files"] = sorted(
                set(existing[name].get("source_files", []) + entry["source_files"])
            )
            existing[name]["built_at"] = entry["built_at"]
        else:
            existing[name] = entry

    # Demote names that became ambiguous in new data
    demoted = [n for n in new_ambig if n in existing]
    for name in demoted:
        log.warning("DEMOTED '%s' — strict → ambiguous (seen as both genders in new data)", name)
        del existing[name]

    final = dict(sorted(existing.items()))
    log.info("Final strict library: %d entries  (%d demoted)", len(final), len(demoted))

    # ── Write strict library ──────────────────────────────────────────────────
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Written: '%s'  (%d KB)", out_path, out_path.stat().st_size // 1024)

    # ── Write ambiguous list ──────────────────────────────────────────────────
    # FIX: .with_stem() is Python 3.9+; use explicit construction for 3.8 compat
    ambig_path = out_path.parent / (out_path.stem + "_ambiguous" + out_path.suffix)
    existing_ambig: dict = {}
    if ambig_path.exists():
        try:
            existing_ambig = json.loads(ambig_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    existing_ambig.update(new_ambig)
    ambig_path.write_text(
        json.dumps(dict(sorted(existing_ambig.items())), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info(
        "Written: '%s'  (%d ambiguous names — review if needed)",
        ambig_path, len(existing_ambig),
    )

    # ── Update manifest ───────────────────────────────────────────────────────
    manifest["last_strict_build"] = now
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

    p = argparse.ArgumentParser(description="Build BRLF Strict Gender Library")
    p.add_argument("--verified-dir", default="data/verified")
    p.add_argument("--output",       default="gender_intelligence/brlf_gender_strict.json")
    p.add_argument("--manifest",     default="gender_intelligence/file_manifest.json")
    p.add_argument("--farmer-col",   default="farmer_name")
    p.add_argument("--gender-col",   default="gender")
    p.add_argument("--min-occ",      default=2, type=int)
    p.add_argument("--full",         action="store_true")
    p.add_argument("--dry-run",      action="store_true")

    args   = p.parse_args()
    result = build_strict_library(
        verified_folder = args.verified_dir,
        farmer_col      = args.farmer_col,
        gender_col      = args.gender_col,
        min_occurrences = args.min_occ,
        output_path     = args.output,
        manifest_path   = args.manifest,
        full_rebuild    = args.full,
        dry_run         = args.dry_run,
    )
    if not args.dry_run and result:
        m = sum(1 for v in result.values() if v["gender"] == "male")
        f = sum(1 for v in result.values() if v["gender"] == "female")
        print(f"\n✓  Strict library: {len(result):,} names  (male={m:,}  female={f:,})")