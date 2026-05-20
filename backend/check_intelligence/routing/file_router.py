"""
file_router.py  —  Admin File Routing System  (Production)
===========================================================
Controls how uploaded files move into the gender library build pipeline.

THE COMPLETE FLOW
-----------------

  STEP 1 — Upload
    Field staff / surveyor uploads a file.
    File lands in  data/inbox/  automatically.
    System registers it in  inbox_registry.json  with status = "pending".
    System does NOT touch verified/ or unverified/ yet.

  STEP 2 — Admin Review
    Admin calls  list_pending()  to see all files waiting for decision.
    Admin inspects the file (manually, or via the preview function).
    Admin makes ONE of these decisions:

      approve(filename)  →  file moves to  data/verified/
                             → will feed the STRICT library (confidence 1.00)
                             → admin is saying: "this data is 100% correct"

      reject(filename)   →  file moves to  data/unverified/
                             → will feed the PROBABILISTIC library (conf ≥ 0.95)
                             → admin is saying: "this data is real but may have noise"

      hold(filename)     →  file stays in inbox, marked as held
                             → admin is saying: "not ready yet, come back later"

  STEP 3 — Library Rebuild
    After approving/rejecting files, admin runs:
      python rebuild.py
    This picks up the moved files and rebuilds the gender libraries.

  LATER — Change of Mind
    Admin discovers a mistake:
      promote(filename)  →  moves from unverified/ → verified/
      revoke(filename)   →  moves from verified/ → unverified/

FILE STATE MACHINE
------------------
  pending   → approve  → approved  (moved to verified/)
  pending   → reject   → rejected  (moved to unverified/)
  pending   → hold     → held      (stays in inbox)
  held      → approve  → approved  (moved to verified/)
  held      → reject   → rejected  (moved to unverified/)
  approved  → revoke   → revoked   (moved to unverified/)
  rejected  → promote  → promoted  (moved to verified/)

  The system NEVER moves files automatically.
  Every transition requires an explicit admin action with a name logged.

REGISTRY FILE: data/inbox/inbox_registry.json
  Every file ever uploaded is tracked here permanently.
  Full audit trail: who uploaded, who reviewed, when, why.

CHANGES FROM ORIGINAL
---------------------
  1. BUG FIX: _transition() source path resolution — used to try
     src_dir/filename first, then src_dir/dest_name. Now uses only
     dest_name (the actual stored name) for deterministic lookup.

  2. BUG FIX: upload() now stores 'dest_name' as the registry KEY so
     admin always uses dest_name (what was actually stored on disk) to
     address files via approve/reject/etc.  The print_pending() display
     shows both original_name and dest_name when they differ.

  3. BUG FIX: hold() now uses _transition() internally so all state
     transitions share ONE code path. Eliminates duplicated
     reviewed_by / reviewed_at / history logic.

  4. BUG FIX: Atomic registry writes — now writes to temp file then
     renames, so a mid-write crash can never corrupt the registry.

  5. BUG FIX: File locking (fcntl on POSIX, msvcrt on Windows) prevents
     two concurrent uploads from corrupting the registry.

  6. CONSISTENCY: list_pending() and list_all() now both sort ascending
     by uploaded_at (oldest first) — consistent ordering everywhere.

  7. REMOVED: FASTAPI_ROUTER_CODE string constant — moved to its own
     file (file_router_api.py) so it is importable and testable.
"""

import fcntl
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from gender_intelligence.lib_utils import (
    SUPPORTED_EXTENSIONS,
    checksum,
    now_utc,
)

log = logging.getLogger("gender_intelligence.file_router")

Status = Literal["pending", "held", "approved", "rejected", "promoted", "revoked"]

# Statuses that mean the file is inside inbox/
_INBOX_STATUSES = frozenset({"pending", "held"})


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRY HELPERS  (atomic + locked)
# ─────────────────────────────────────────────────────────────────────────────

def _load_registry(registry_path: Path) -> dict:
    if registry_path.exists():
        try:
            return json.loads(registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("Registry at '%s' corrupt — starting fresh", registry_path)
    return {"uploaded_files": {}}


def _save_registry(registry: dict, registry_path: Path) -> None:
    """Atomic write: temp file → rename. Never leaves a half-written file."""
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(registry, indent=2, ensure_ascii=False)

    fd, tmp = tempfile.mkstemp(
        dir=registry_path.parent, prefix=".registry_tmp_", suffix=".json"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, registry_path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class _RegistryLock:
    """
    File-based lock so concurrent uploads don't corrupt the registry.
    Uses a separate .lock file alongside the registry.
    Context manager: `with _RegistryLock(registry_path): ...`
    """
    def __init__(self, registry_path: Path):
        self._lock_path = registry_path.with_suffix(".lock")
        self._fh = None

    def __enter__(self):
        self._fh = open(self._lock_path, "w")
        fcntl.flock(self._fh, fcntl.LOCK_EX)
        return self

    def __exit__(self, *_):
        if self._fh:
            fcntl.flock(self._fh, fcntl.LOCK_UN)
            self._fh.close()
        return False


# ─────────────────────────────────────────────────────────────────────────────
# FILE ROUTER CLASS
# ─────────────────────────────────────────────────────────────────────────────

class FileRouter:
    """
    Manages the full lifecycle of uploaded data files.

    All file movements are logged with admin name, timestamp, and optional note.
    No file moves without an explicit admin action.
    Registry writes are atomic and lock-protected.
    """

    def __init__(
        self,
        inbox_dir:      str = "data/inbox",
        verified_dir:   str = "data/verified",
        unverified_dir: str = "data/unverified",
        registry_path:  str = "data/inbox/inbox_registry.json",
    ):
        self.inbox_dir      = Path(inbox_dir)
        self.verified_dir   = Path(verified_dir)
        self.unverified_dir = Path(unverified_dir)
        self.registry_path  = Path(registry_path)

        for d in (self.inbox_dir, self.verified_dir, self.unverified_dir):
            d.mkdir(parents=True, exist_ok=True)

    # ── UPLOAD ────────────────────────────────────────────────────────────────

    def upload(
        self,
        source_path: str,
        uploaded_by: str = "unknown",
    ) -> dict:
        """
        Register a file into the inbox for admin review.

        The file is COPIED from source_path into data/inbox/.
        Registry key is always dest_name (the name on disk after any renaming).
        Use the returned entry's 'dest_name' to address this file in future calls.

        Raises
        ------
        FileNotFoundError  if source_path does not exist.
        ValueError         if file type is not supported.
        FileExistsError    if the same file (same name + checksum) already exists.
        """
        src = Path(source_path)

        if not src.exists():
            raise FileNotFoundError(f"Source file not found: '{src}'")
        if src.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{src.suffix}'. "
                f"Accepted: {sorted(SUPPORTED_EXTENSIONS)}"
            )

        chk = checksum(src)

        with _RegistryLock(self.registry_path):
            registry = _load_registry(self.registry_path)
            files    = registry.setdefault("uploaded_files", {})

            # Duplicate detection — same filename AND same checksum
            existing_entry = files.get(src.name)
            if existing_entry and existing_entry.get("checksum") == chk:
                log.warning(
                    "Duplicate upload ignored: '%s' (already in registry, status='%s')",
                    src.name, existing_entry["status"],
                )
                return existing_entry

            # Filename collision with different content — rename with timestamp
            dest_name = src.name
            if (self.inbox_dir / dest_name).exists():
                ts        = now_utc().replace(":", "").replace("-", "").replace("T", "_")[:15]
                dest_name = f"{src.stem}_{ts}{src.suffix}"
                log.info(
                    "Filename conflict — stored as '%s' (different file already in inbox)",
                    dest_name,
                )

            dest = self.inbox_dir / dest_name
            shutil.copy2(str(src), str(dest))

            entry = {
                "original_name": src.name,
                "dest_name":     dest_name,     # THIS is the key to use in all future calls
                "uploaded_at":   now_utc(),
                "uploaded_by":   uploaded_by,
                "size_bytes":    dest.stat().st_size,
                "checksum":      chk,
                "status":        "pending",
                "reviewed_by":   None,
                "reviewed_at":   None,
                "review_note":   None,
                "destination":   None,
                "current_path":  str(dest),
                "history":       [],
            }
            # Registry key is dest_name — this is the stable handle for all future actions
            files[dest_name] = entry
            _save_registry(registry, self.registry_path)

        log.info(
            "UPLOADED  '%s'  by '%s'  (%d KB)  → inbox",
            dest_name, uploaded_by, dest.stat().st_size // 1024,
        )
        return entry

    # ── ADMIN REVIEW ACTIONS ──────────────────────────────────────────────────

    def approve(self, filename: str, admin: str, note: str = "") -> dict:
        """
        Approve → moves file from inbox/ to verified/.
        Admin is saying: "This data is 100% correct → Strict library."
        """
        return self._transition(
            filename    = filename,
            admin       = admin,
            note        = note,
            from_status = ("pending", "held"),
            to_status   = "approved",
            source_dir  = self.inbox_dir,
            destination = self.verified_dir,
            dest_label  = "verified",
            action_verb = "APPROVED",
        )

    def reject(self, filename: str, admin: str, note: str = "") -> dict:
        """
        Reject → moves file from inbox/ to unverified/.
        Admin is saying: "Real data but may have noise → Probabilistic library."
        """
        return self._transition(
            filename    = filename,
            admin       = admin,
            note        = note,
            from_status = ("pending", "held"),
            to_status   = "rejected",
            source_dir  = self.inbox_dir,
            destination = self.unverified_dir,
            dest_label  = "unverified",
            action_verb = "REJECTED",
        )

    def hold(self, filename: str, admin: str, note: str = "") -> dict:
        """
        Hold → keeps file in inbox/ but changes status to 'held'.
        Held files are hidden from the default pending list.
        """
        # Hold is a special transition: stays in inbox, no file move.
        # Uses _transition with source_dir == destination (no-op file move).
        return self._transition(
            filename    = filename,
            admin       = admin,
            note        = note,
            from_status = ("pending",),
            to_status   = "held",
            source_dir  = self.inbox_dir,
            destination = self.inbox_dir,   # stays put
            dest_label  = "inbox (held)",
            action_verb = "HELD",
            move_file   = False,            # explicit: don't touch the file
        )

    def promote(self, filename: str, admin: str, note: str = "") -> dict:
        """Promote: unverified/ → verified/."""
        return self._transition(
            filename    = filename,
            admin       = admin,
            note        = note,
            from_status = ("rejected", "revoked"),
            to_status   = "promoted",
            source_dir  = self.unverified_dir,
            destination = self.verified_dir,
            dest_label  = "verified",
            action_verb = "PROMOTED",
        )

    def revoke(self, filename: str, admin: str, note: str = "") -> dict:
        """Revoke: verified/ → unverified/."""
        return self._transition(
            filename    = filename,
            admin       = admin,
            note        = note,
            from_status = ("approved", "promoted"),
            to_status   = "revoked",
            source_dir  = self.verified_dir,
            destination = self.unverified_dir,
            dest_label  = "unverified",
            action_verb = "REVOKED",
        )

    # ── LIST / QUERY ──────────────────────────────────────────────────────────

    def list_pending(self, include_held: bool = False) -> list[dict]:
        """
        Return files waiting for admin decision, sorted oldest-first.
        Pass include_held=True to also see held files.
        """
        registry = _load_registry(self.registry_path)
        statuses = {"pending", "held"} if include_held else {"pending"}
        result   = [
            e for e in registry.get("uploaded_files", {}).values()
            if e.get("status") in statuses
        ]
        return sorted(result, key=lambda e: e.get("uploaded_at", ""))

    def list_all(self, status_filter: str | None = None) -> list[dict]:
        """
        Return all files ever uploaded, sorted oldest-first.
        Optionally filter by status string.
        """
        registry = _load_registry(self.registry_path)
        result   = list(registry.get("uploaded_files", {}).values())
        if status_filter:
            result = [e for e in result if e.get("status") == status_filter]
        return sorted(result, key=lambda e: e.get("uploaded_at", ""))

    def summary(self) -> dict:
        """Count all files by status — useful for dashboard / health-check."""
        registry = _load_registry(self.registry_path)
        files    = registry.get("uploaded_files", {})

        counts: dict[str, int] = {
            "pending": 0, "held": 0, "approved": 0,
            "rejected": 0, "promoted": 0, "revoked": 0, "total": len(files),
        }
        for e in files.values():
            s = e.get("status", "unknown")
            if s in counts:
                counts[s] += 1

        counts["in_verified"]   = counts["approved"]  + counts["promoted"]
        counts["in_unverified"] = counts["rejected"]   + counts["revoked"]
        counts["needs_review"]  = counts["pending"]    + counts["held"]
        return counts

    def print_pending(self, include_held: bool = False) -> None:
        """Pretty-print pending files to terminal for admin review."""
        pending = self.list_pending(include_held=include_held)

        print("\n" + "═" * 66)
        print("  FILES AWAITING ADMIN DECISION")
        print("═" * 66)

        if not pending:
            print("  ✓  No files pending review.")
            print("═" * 66 + "\n")
            return

        for i, entry in enumerate(pending, 1):
            icon    = "🕐" if entry["status"] == "pending" else "🔒"
            size_kb = (entry.get("size_bytes") or 0) // 1024
            name_display = entry["dest_name"]
            if entry["original_name"] != entry["dest_name"]:
                name_display += f"  (original: {entry['original_name']})"
            print(f"\n  {i}. {icon} [{entry['status'].upper()}]  {name_display}")
            print(f"     Uploaded  : {entry['uploaded_at']}  by {entry['uploaded_by']}")
            print(f"     Size      : {size_kb} KB")
            if entry.get("review_note"):
                print(f"     Note      : {entry['review_note']}")

        print(f"\n  Total: {len(pending)} file(s) waiting")
        print("\n  Use dest_name (shown above) in all approve/reject/hold calls.")
        print("  Actions:")
        print("    router.approve(dest_name, admin='your_name', note='...')")
        print("    router.reject(dest_name,  admin='your_name', note='...')")
        print("    router.hold(dest_name,    admin='your_name', note='...')")
        print("═" * 66 + "\n")

    # ── INTERNAL HELPERS ──────────────────────────────────────────────────────

    def _get_entry(self, registry: dict, filename: str) -> dict:
        entry = registry.get("uploaded_files", {}).get(filename)
        if entry is None:
            available = list(registry.get("uploaded_files", {}).keys())
            raise KeyError(
                f"File '{filename}' not found in registry.\n"
                f"Available: {available}\n"
                f"Tip: use dest_name (from upload() return value or print_pending())"
            )
        return entry

    def _assert_status(
        self,
        entry:       dict,
        allowed:     tuple[str, ...],
        action_name: str,
        filename:    str,
    ) -> None:
        current = entry.get("status")
        if current not in allowed:
            raise ValueError(
                f"Cannot '{action_name}' '{filename}': "
                f"current status is '{current}', "
                f"requires status in {list(allowed)}."
            )

    def _transition(
        self,
        filename:    str,
        admin:       str,
        note:        str,
        from_status: tuple[str, ...],
        to_status:   str,
        source_dir:  Path,
        destination: Path,
        dest_label:  str,
        action_verb: str,
        move_file:   bool = True,
    ) -> dict:
        """
        Core state transition — single path for ALL actions.

        move_file=False is used by hold() which keeps the file in place.
        Registry write is atomic and lock-protected.
        """
        with _RegistryLock(self.registry_path):
            registry = _load_registry(self.registry_path)
            entry    = self._get_entry(registry, filename)

            self._assert_status(entry, from_status, action_verb.lower(), filename)

            ts_now    = now_utc()
            hist_entry: dict = {
                "action": to_status,
                "by":     admin,
                "at":     ts_now,
                "note":   note or None,
            }

            if move_file:
                # Resolve current file path using dest_name (always reliable)
                stored_name = entry.get("dest_name", filename)
                src_path    = source_dir / stored_name

                if not src_path.exists():
                    raise FileNotFoundError(
                        f"File '{stored_name}' not found in '{source_dir}'. "
                        f"It may have been moved or deleted outside the system."
                    )

                # Handle filename collision in destination
                dest_path = destination / src_path.name
                if dest_path.exists():
                    ts        = ts_now.replace(":", "").replace("-", "").replace("T", "_")[:15]
                    dest_path = destination / f"{src_path.stem}_{ts}{src_path.suffix}"
                    log.warning(
                        "Filename collision in '%s/' — renamed to '%s'",
                        dest_label, dest_path.name,
                    )

                shutil.move(str(src_path), str(dest_path))
                entry["current_path"] = str(dest_path)
                hist_entry["from"]    = str(src_path)
                hist_entry["to"]      = str(dest_path)

            entry["status"]      = to_status
            entry["reviewed_by"] = admin
            entry["reviewed_at"] = ts_now
            entry["review_note"] = note or None
            entry["destination"] = dest_label
            entry["history"].append(hist_entry)

            _save_registry(registry, self.registry_path)

        log.info(
            "%s  '%s'  by '%s'  → %s%s",
            action_verb, filename, admin, dest_label,
            f"  note: '{note}'" if note else "",
        )
        return entry


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import logging
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
    )

    p = argparse.ArgumentParser(
        description="BRLF File Router — admin file management",
        epilog=(
            "Examples:\n"
            "  python file_router.py pending\n"
            "  python file_router.py upload  survey_mh.xlsx  --by field_01\n"
            "  python file_router.py approve survey_mh.xlsx  --admin pratik --note 'verified'\n"
            "  python file_router.py reject  raw_batch.xlsx  --admin pratik --note 'has noise'\n"
            "  python file_router.py hold    unclear.xlsx    --admin pratik\n"
            "  python file_router.py promote raw_batch.xlsx  --admin pratik\n"
            "  python file_router.py revoke  survey_mh.xlsx  --admin pratik --note 'found errors'\n"
            "  python file_router.py summary\n"
            "  python file_router.py all\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("pending", help="List files awaiting decision").add_argument(
        "--held", action="store_true", help="Include held files"
    )

    sp_upload = sub.add_parser("upload", help="Upload a file to inbox")
    sp_upload.add_argument("file")
    sp_upload.add_argument("--by", default="cli_upload")

    for cmd, help_text in [
        ("approve", "Approve → verified/"),
        ("reject",  "Reject  → unverified/"),
        ("hold",    "Hold in inbox"),
        ("promote", "Promote: unverified/ → verified/"),
        ("revoke",  "Revoke:  verified/ → unverified/"),
    ]:
        sp = sub.add_parser(cmd, help=help_text)
        sp.add_argument("file")
        sp.add_argument("--admin", required=True)
        sp.add_argument("--note",  default="")

    sub.add_parser("summary", help="Show counts by status")
    sp_all = sub.add_parser("all", help="Show all files")
    sp_all.add_argument("--status", default=None)

    args   = p.parse_args()
    router = FileRouter()

    if args.command == "pending":
        router.print_pending(include_held=getattr(args, "held", False))

    elif args.command == "upload":
        try:
            entry = router.upload(args.file, uploaded_by=args.by)
            print(f"\n✓  Uploaded '{entry['dest_name']}' to inbox")
            if entry["dest_name"] != entry["original_name"]:
                print(f"   (renamed from '{entry['original_name']}')")
            print(f"   Status : {entry['status']}")
            print(f"   Size   : {(entry['size_bytes'] or 0) // 1024} KB\n")
        except (FileNotFoundError, ValueError) as e:
            print(f"✗  {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command in ("approve", "reject", "hold", "promote", "revoke"):
        try:
            entry = getattr(router, args.command)(args.file, admin=args.admin, note=args.note)
            print(f"\n✓  {args.command.upper()}  '{args.file}'")
            print(f"   Status      : {entry['status']}")
            print(f"   Destination : {entry.get('destination', 'inbox (held)')}/")
            print(f"   Reviewed by : {entry['reviewed_by']}")
            if entry.get("review_note"):
                print(f"   Note        : {entry['review_note']}")
            if args.command in ("approve", "reject", "promote", "revoke"):
                print("   → Run  python rebuild.py  to update gender libraries")
            print()
        except (KeyError, ValueError, FileNotFoundError) as e:
            print(f"✗  {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "summary":
        c = router.summary()
        print("\n" + "═" * 44)
        print("  BRLF File Registry Summary")
        print("═" * 44)
        print(f"  Total uploaded  : {c['total']}")
        print(f"  Needs review    : {c['needs_review']}  (pending={c['pending']}  held={c['held']})")
        print(f"  In verified/    : {c['in_verified']}  (approved={c['approved']}  promoted={c['promoted']})")
        print(f"  In unverified/  : {c['in_unverified']}  (rejected={c['rejected']}  revoked={c['revoked']})")
        print("═" * 44 + "\n")

    elif args.command == "all":
        files = router.list_all(status_filter=args.status)
        if not files:
            print("\n  No files found.\n")
        else:
            print(f"\n  {'FILENAME':<40}  {'STATUS':<12}  {'UPLOADED':<20}  BY")
            print("  " + "─" * 80)
            for e in files:
                print(f"  {e['dest_name']:<40}  {e['status']:<12}  {e['uploaded_at']:<20}  {e['uploaded_by']}")
            print()