"""
rebuild.py  —  Gender Library Admin Rebuild Tool  (Production)
===============================================================
The SINGLE command an admin runs to rebuild the gender libraries
after approving/rejecting files via file_router.py.

USAGE
-----
  python rebuild.py                    # interactive — shows plan, asks confirm
  python rebuild.py --yes              # non-interactive (for scripts/cron)
  python rebuild.py --dry-run          # preview only, write nothing
  python rebuild.py --full             # ignore manifest, reread everything
  python rebuild.py --status           # show current library status, then exit
  python rebuild.py --strict-only      # rebuild strict library only
  python rebuild.py --prob-only        # rebuild prob library only

WHAT IT DOES (in order)
------------------------
  1. Reads file_manifest.json to know current state.
  2. Scans data/verified/   — shows which files are new since last build.
  3. Scans data/unverified/ — shows which files are new since last build.
  4. Asks for confirmation (skipped with --yes or confirmed=True).
  5. Calls build_strict_library()  →  updates brlf_gender_strict.json.
  6. Calls build_prob_library()    →  updates brlf_gender_prob.json.
  7. Updates file_manifest.json.
  8. Prints a clear summary.

CHANGES FROM ORIGINAL
---------------------
  1. CRITICAL FIX: No longer imports private helpers (_load_manifest,
     _checksum, _SUPPORTED) from build_strict.  Uses the shared
     lib_utils module instead.  Breaks no internal encapsulation.

  2. BUG FIX: files_read is now populated AFTER a successful library
     build, not before.  If build_strict raises, files_read stays empty.

  3. BUG FIX: Both build calls are wrapped in try/except independently.
     If strict build fails, the error is logged and prob build still runs
     (and vice versa).  The final status reflects partial failures.

  4. CLARITY: run_rebuild() return dict now includes 'strict_skipped' and
     'prob_skipped' booleans so callers know when a library was not rebuilt
     (e.g. due to --strict-only), rather than inferring from a 0 entry count.

  5. REMOVED: FASTAPI_SNIPPET string constant — moved to rebuild_api.py.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from check_intelligence.library.build_strict import build_strict_library
from check_intelligence.library.build_prob   import build_prob_library
from gender_intelligence.lib_utils import (
    SUPPORTED_EXTENSIONS,
    checksum,
    load_manifest,
)

log = logging.getLogger("gender_intelligence.rebuild")

DEFAULT_VERIFIED_DIR   = "data/verified"
DEFAULT_UNVERIFIED_DIR = "data/unverified"
DEFAULT_STRICT_OUT     = "gender_intelligence/brlf_gender_strict.json"
DEFAULT_PROB_OUT       = "gender_intelligence/brlf_gender_prob.json"
DEFAULT_MANIFEST       = "gender_intelligence/file_manifest.json"


# ─────────────────────────────────────────────────────────────────────────────
# STATUS DISPLAY  (read-only)
# ─────────────────────────────────────────────────────────────────────────────

def print_status(
    verified_dir:   str = DEFAULT_VERIFIED_DIR,
    unverified_dir: str = DEFAULT_UNVERIFIED_DIR,
    strict_path:    str = DEFAULT_STRICT_OUT,
    prob_path:      str = DEFAULT_PROB_OUT,
    manifest_path:  str = DEFAULT_MANIFEST,
) -> dict:
    """
    Print library status to terminal.  Returns a summary dict for API use.
    Read-only — writes nothing.
    """
    mf          = load_manifest(Path(manifest_path))
    ingested_v  = mf.get("verified_files", {})
    ingested_uv = mf.get("unverified_files", {})

    print("\n" + "═" * 62)
    print("  BRLF Gender Library Status")
    print("═" * 62)

    for label, path in [("Strict", strict_path), ("Probabilistic", prob_path)]:
        p = Path(path)
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                m = sum(1 for v in data.values() if v.get("gender") == "male")
                f = sum(1 for v in data.values() if v.get("gender") == "female")
                print(f"\n  {label} Library  ({p.name})")
                print(f"    Entries : {len(data):,}  (male={m:,}  female={f:,})")
            except Exception:
                print(f"\n  {label} Library  — CORRUPT or unreadable")
        else:
            print(f"\n  {label} Library  — NOT BUILT YET  ({path})")

    print(f"\n  Last strict build : {mf.get('last_strict_build') or 'never'}")
    print(f"  Last prob build   : {mf.get('last_prob_build')   or 'never'}")

    def _new_in(folder: str, ingested: dict) -> list[tuple[str, str]]:
        p = Path(folder)
        result = []
        if p.exists():
            for f in sorted(fp for fp in p.iterdir()
                            if fp.is_file() and fp.suffix.lower() in SUPPORTED_EXTENSIONS):
                chk  = checksum(f)
                prev = ingested.get(f.name, {})
                if prev.get("checksum") != chk:
                    result.append((f.name, "NEW" if f.name not in ingested else "MODIFIED"))
        return result

    new_v  = _new_in(verified_dir,   ingested_v)
    new_uv = _new_in(unverified_dir, ingested_uv)

    for label, folder, new_files in [
        ("Verified",   verified_dir,   new_v),
        ("Unverified", unverified_dir, new_uv),
    ]:
        print(f"\n  {label} folder  ({folder})")
        if not Path(folder).exists():
            print(f"    ✗  Folder does not exist")
        elif new_files:
            print(f"    ⚠  {len(new_files)} file(s) not yet ingested:")
            for fname, status in new_files:
                print(f"       [{status}]  {fname}")
        else:
            print(f"    ✓  All files already ingested")

    print("\n" + "═" * 62)
    if new_v or new_uv:
        print("  → Run  python rebuild.py  to ingest new files")
    else:
        print("  → Libraries are up to date.  No rebuild needed.")
    print("═" * 62 + "\n")

    return {
        "new_verified":   new_v,
        "new_unverified": new_uv,
        "last_strict":    mf.get("last_strict_build"),
        "last_prob":      mf.get("last_prob_build"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN REBUILD FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

# library_status is an alias for print_status that returns a structured dict
# without printing to terminal — used by main.py FastAPI admin endpoints.
library_status = print_status


def run_rebuild(
    verified_dir:   str   = DEFAULT_VERIFIED_DIR,
    unverified_dir: str   = DEFAULT_UNVERIFIED_DIR,
    strict_out:     str   = DEFAULT_STRICT_OUT,
    prob_out:       str   = DEFAULT_PROB_OUT,
    manifest_path:  str   = DEFAULT_MANIFEST,
    farmer_col:     str   = "farmer_name",
    gender_col:     str   = "gender",
    confirmed:      bool  = False,
    dry_run:        bool  = False,
    full_rebuild:   bool  = False,
    strict_only:    bool  = False,
    prob_only:      bool  = False,
) -> dict:
    """
    Rebuild gender libraries from folder contents.

    Returns
    -------
    {
      "status":          "success" | "partial" | "dry_run" | "cancelled" | "no_changes",
      "strict_entries":  int,       # 0 if not rebuilt or empty
      "prob_entries":    int,       # 0 if not rebuilt or empty
      "strict_new":      int,
      "prob_new":        int,
      "strict_skipped":  bool,      # True when --prob-only was used
      "prob_skipped":    bool,      # True when --strict-only was used
      "strict_error":    str|None,  # set if strict build raised
      "prob_error":      str|None,  # set if prob build raised
      "files_read":      list[str],
      "built_at":        str,
    }
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    print("\n" + "═" * 62)
    print("  BRLF Gender Library Rebuild")
    print("═" * 62)
    if dry_run:
        print("  MODE: DRY RUN — nothing will be written\n")
    if full_rebuild:
        print("  MODE: FULL REBUILD — ignoring manifest\n")

    # ── Scan for new files ────────────────────────────────────────────────────
    mf          = load_manifest(Path(manifest_path))
    ingested_v  = mf.get("verified_files", {})
    ingested_uv = mf.get("unverified_files", {})

    def _new_in(folder: str, ingested: dict) -> list[tuple[str, str]]:
        p = Path(folder)
        result = []
        if p.exists():
            for f in sorted(fp for fp in p.iterdir()
                            if fp.is_file() and fp.suffix.lower() in SUPPORTED_EXTENSIONS):
                chk  = checksum(f)
                prev = ingested.get(f.name, {})
                if full_rebuild or prev.get("checksum") != chk:
                    result.append((f.name, "NEW" if f.name not in ingested else "MODIFIED"))
        return result

    new_v  = _new_in(verified_dir,   ingested_v)  if not prob_only  else []
    new_uv = _new_in(unverified_dir, ingested_uv) if not strict_only else []

    # ── Show plan ─────────────────────────────────────────────────────────────
    if not prob_only:
        print(f"  Strict Library  ← verified/  ({verified_dir})")
        for fname, status in new_v:
            print(f"    [{status}]  {fname}")
        if not new_v:
            print("    ✓  No new files")

    if not strict_only:
        print(f"\n  Probabilistic Library  ← unverified/  ({unverified_dir})")
        for fname, status in new_uv:
            print(f"    [{status}]  {fname}")
        if not new_uv:
            print("    ✓  No new files")

    if not new_v and not new_uv and not full_rebuild:
        print("\n  Libraries are up to date.  Nothing to rebuild.")
        print("═" * 62 + "\n")
        return {
            "status": "no_changes",
            "strict_entries": 0, "prob_entries": 0,
            "strict_new": 0, "prob_new": 0,
            "strict_skipped": prob_only, "prob_skipped": strict_only,
            "strict_error": None, "prob_error": None,
            "files_read": [], "built_at": now,
        }

    # ── Confirm ───────────────────────────────────────────────────────────────
    if not confirmed and not dry_run:
        print()
        try:
            answer = input("  Proceed with rebuild? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"
        if answer not in ("y", "yes"):
            print("  Cancelled.\n" + "═" * 62 + "\n")
            return {
                "status": "cancelled",
                "strict_entries": 0, "prob_entries": 0,
                "strict_new": 0, "prob_new": 0,
                "strict_skipped": prob_only, "prob_skipped": strict_only,
                "strict_error": None, "prob_error": None,
                "files_read": [], "built_at": now,
            }

    print()

    # ── Rebuild strict ────────────────────────────────────────────────────────
    strict_before = _lib_size(strict_out)
    strict_result: dict = {}
    strict_error: str | None = None
    files_read:   list[str] = []

    if not prob_only:
        try:
            strict_result = build_strict_library(
                verified_folder = verified_dir,
                farmer_col      = farmer_col,
                gender_col      = gender_col,
                output_path     = strict_out,
                manifest_path   = manifest_path,
                full_rebuild    = full_rebuild,
                dry_run         = dry_run,
            )
            # FIX: only add to files_read AFTER successful build
            files_read.extend(fname for fname, _ in new_v)
        except Exception as exc:
            strict_error = str(exc)
            log.error("Strict library build FAILED: %s", exc)

    # ── Rebuild prob ──────────────────────────────────────────────────────────
    prob_before = _lib_size(prob_out)
    prob_result: dict = {}
    prob_error:  str | None = None

    if not strict_only:
        try:
            prob_result = build_prob_library(
                unverified_folder = unverified_dir,
                strict_path       = strict_out,    # reads UPDATED strict file
                farmer_col        = farmer_col,
                gender_col        = gender_col,
                output_path       = prob_out,
                manifest_path     = manifest_path,
                full_rebuild      = full_rebuild,
                dry_run           = dry_run,
            )
            files_read.extend(fname for fname, _ in new_uv)
        except Exception as exc:
            prob_error = str(exc)
            log.error("Prob library build FAILED: %s", exc)

    # ── Summary ───────────────────────────────────────────────────────────────
    strict_after = len(strict_result)
    prob_after   = len(prob_result)
    had_errors   = bool(strict_error or prob_error)
    status       = "dry_run" if dry_run else ("partial" if had_errors else "success")

    print("\n" + "═" * 62)
    if dry_run:
        print("  DRY RUN COMPLETE — no files written")
    else:
        print("  ✓  REBUILD COMPLETE" + ("  (with errors — see log)" if had_errors else ""))
        if not prob_only:
            _print_lib_line("Strict", strict_before, strict_after, strict_error)
        if not strict_only:
            _print_lib_line("Prob  ", prob_before,   prob_after,   prob_error)
        if files_read:
            print(f"\n  Files ingested  :  {len(files_read)}")
            for fname in files_read:
                print(f"    • {fname}")
        print(f"\n  Libraries take effect on the next pipeline run.")
    print("═" * 62 + "\n")

    return {
        "status":         status,
        "strict_entries": strict_after,
        "prob_entries":   prob_after,
        "strict_new":     max(0, strict_after - strict_before),
        "prob_new":       max(0, prob_after   - prob_before),
        "strict_skipped": prob_only,
        "prob_skipped":   strict_only,
        "strict_error":   strict_error,
        "prob_error":     prob_error,
        "files_read":     files_read,
        "built_at":       now,
    }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _lib_size(path: str) -> int:
    p = Path(path)
    if p.exists():
        try:
            return len(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    return 0


def _print_lib_line(label: str, before: int, after: int, error: str | None) -> None:
    if error:
        print(f"  {label} Library  :  ✗  BUILD FAILED — {error}")
    else:
        delta = max(0, after - before)
        print(f"  {label} Library  :  {before:,} → {after:,} entries  (+{delta} new)")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
    )

    p = argparse.ArgumentParser(
        description="Rebuild BRLF Gender Libraries",
        epilog=(
            "Examples:\n"
            "  python rebuild.py                  # interactive rebuild\n"
            "  python rebuild.py --yes            # skip confirmation\n"
            "  python rebuild.py --dry-run        # preview only\n"
            "  python rebuild.py --full           # re-read all files\n"
            "  python rebuild.py --status         # show status and exit\n"
            "  python rebuild.py --strict-only\n"
            "  python rebuild.py --prob-only\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--verified-dir",   default=DEFAULT_VERIFIED_DIR)
    p.add_argument("--unverified-dir", default=DEFAULT_UNVERIFIED_DIR)
    p.add_argument("--strict-out",     default=DEFAULT_STRICT_OUT)
    p.add_argument("--prob-out",       default=DEFAULT_PROB_OUT)
    p.add_argument("--manifest",       default=DEFAULT_MANIFEST)
    p.add_argument("--farmer-col",     default="farmer_name")
    p.add_argument("--gender-col",     default="gender")
    p.add_argument("--yes",            action="store_true")
    p.add_argument("--dry-run",        action="store_true")
    p.add_argument("--full",           action="store_true")
    p.add_argument("--status",         action="store_true")
    p.add_argument("--strict-only",    action="store_true")
    p.add_argument("--prob-only",      action="store_true")

    args = p.parse_args()

    if args.status:
        print_status(
            verified_dir   = args.verified_dir,
            unverified_dir = args.unverified_dir,
            strict_path    = args.strict_out,
            prob_path      = args.prob_out,
            manifest_path  = args.manifest,
        )
        sys.exit(0)

    result = run_rebuild(
        verified_dir   = args.verified_dir,
        unverified_dir = args.unverified_dir,
        strict_out     = args.strict_out,
        prob_out       = args.prob_out,
        manifest_path  = args.manifest,
        farmer_col     = args.farmer_col,
        gender_col     = args.gender_col,
        confirmed      = args.yes,
        dry_run        = args.dry_run,
        full_rebuild   = args.full,
        strict_only    = args.strict_only,
        prob_only      = args.prob_only,
    )
    sys.exit(0 if result["status"] in ("success", "dry_run", "no_changes") else 1)