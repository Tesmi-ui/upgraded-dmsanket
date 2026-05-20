"""
Admin endpoints (gender library & file routing).
Preserves ALL admin functionality from main.py.
"""
import tempfile
from pathlib import Path
from typing import Optional
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from ..core.config import VERIFIED_DIR, UNVERIFIED_DIR, GENDER_LIB_DIR, INBOX_DIR
from ..core.dependencies import get_file_router, reload_gender_library
from check_intelligence.library.rebuild import run_rebuild, library_status
from models.schema import ReviewRequest, RebuildRequest

router = APIRouter(prefix="/api/admin", tags=["admin"])
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# GENDER LIBRARY
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/gender-library/status")
async def gender_library_status_endpoint():
    """
    Current library sizes and files waiting to be ingested. Read-only.
    """
    return library_status(
        verified_dir=str(VERIFIED_DIR),
        unverified_dir=str(UNVERIFIED_DIR),
        strict_path=str(GENDER_LIB_DIR / "brlf_gender_strict.json"),
        prob_path=str(GENDER_LIB_DIR / "brlf_gender_prob.json"),
        manifest_path=str(GENDER_LIB_DIR / "file_manifest.json"),
    )


@router.post("/gender-library/rebuild")
async def gender_library_rebuild(body: RebuildRequest):
    """
    Rebuild gender libraries from verified/ and unverified/ folders.
    Call after the admin approves/rejects files via the file routing endpoints.
    After rebuild, the next pipeline run uses the updated libraries.
    """
    try:
        result = run_rebuild(
            verified_dir=str(VERIFIED_DIR),
            unverified_dir=str(UNVERIFIED_DIR),
            strict_out=str(GENDER_LIB_DIR / "brlf_gender_strict.json"),
            prob_out=str(GENDER_LIB_DIR / "brlf_gender_prob.json"),
            manifest_path=str(GENDER_LIB_DIR / "file_manifest.json"),
            confirmed=True,
            full_rebuild=body.full,
            dry_run=body.dry_run,
        )
        
        if result.get("status") == "success":
            reload_gender_library()
            log.info("Gender library reloaded after rebuild")
        
        return result
    
    except FileNotFoundError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        log.error("Library rebuild failed: %s", e, exc_info=True)
        raise HTTPException(500, f"Rebuild failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# FILE ROUTING
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/files/upload")
async def admin_upload_file(
    file: UploadFile = File(...),
    uploaded_by: str = Form(default="unknown"),
):
    """
    Upload a dataset file to the admin inbox for review.
    File stays in inbox until admin approves or rejects it.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xls", ".csv"}:
        raise HTTPException(400, f"Unsupported type '{suffix}'")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        import shutil as _shutil
        _shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        router_obj = get_file_router()
        entry = router_obj.upload(tmp_path, uploaded_by=uploaded_by)
        
        # Rename to original filename if possible
        stored = Path(entry["current_path"])
        target = stored.parent / (file.filename or stored.name)
        if not target.exists():
            stored.rename(target)
            entry["dest_name"] = target.name
            entry["current_path"] = str(target)
        
        return {"status": "uploaded", "file": entry}
    
    except (ValueError, FileExistsError) as e:
        raise HTTPException(400, str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.get("/files/pending")
async def get_pending_files(include_held: bool = False):
    """List files in inbox awaiting admin decision."""
    return get_file_router().list_pending(include_held=include_held)


@router.get("/files/all")
async def get_all_files(status: Optional[str] = None):
    """Full file history. Filter with ?status=pending|held|approved|rejected|..."""
    return get_file_router().list_all(status_filter=status)


@router.get("/files/summary")
async def get_files_summary():
    """Dashboard counts — files by status."""
    return get_file_router().summary()


@router.post("/files/{filename}/approve")
async def approve_file(filename: str, body: ReviewRequest):
    """Approve → verified/. Feeds STRICT library."""
    try:
        entry = get_file_router().approve(filename, admin=body.admin, note=body.note)
        return {
            "status": "approved",
            "file": entry,
            "message": f"'{filename}' moved to verified/. Run rebuild to update library."
        }
    except (KeyError, ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e))


@router.post("/files/{filename}/reject")
async def reject_file(filename: str, body: ReviewRequest):
    """Reject → unverified/. Feeds PROBABILISTIC library."""
    try:
        entry = get_file_router().reject(filename, admin=body.admin, note=body.note)
        return {
            "status": "rejected",
            "file": entry,
            "message": f"'{filename}' moved to unverified/. Run rebuild to update library."
        }
    except (KeyError, ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e))


@router.post("/files/{filename}/hold")
async def hold_file(filename: str, body: ReviewRequest):
    """Hold in inbox. Hidden from pending list unless include_held=True."""
    try:
        return {
            "status": "held",
            "file": get_file_router().hold(filename, admin=body.admin, note=body.note)
        }
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))


@router.post("/files/{filename}/promote")
async def promote_file(filename: str, body: ReviewRequest):
    """Promote unverified/ → verified/. Use when rejected file turns out clean."""
    try:
        entry = get_file_router().promote(filename, admin=body.admin, note=body.note)
        return {
            "status": "promoted",
            "file": entry,
            "message": f"'{filename}' moved to verified/. Run full rebuild."
        }
    except (KeyError, ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e))


@router.post("/files/{filename}/revoke")
async def revoke_file(filename: str, body: ReviewRequest):
    """Revoke verified/ → unverified/. Use when approved file has errors."""
    try:
        entry = get_file_router().revoke(filename, admin=body.admin, note=body.note)
        return {
            "status": "revoked",
            "file": entry,
            "message": f"'{filename}' moved to unverified/. Run full rebuild."
        }
    except (KeyError, ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e))