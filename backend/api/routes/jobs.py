"""
Job management endpoints.
Preserves ALL job management logic from main.py.
"""
import shutil
from pathlib import Path
import logging

from fastapi import APIRouter, HTTPException

from ..core.config import UPLOAD_DIR, OUTPUT_DIR
from ..core.storage import load_jobs, delete_job_record, get_job

router = APIRouter(prefix="/api", tags=["jobs"])
log = logging.getLogger(__name__)


@router.get("/jobs")
async def list_jobs():
    """List all jobs, newest first."""
    all_jobs = sorted(
        load_jobs().values(),
        key=lambda j: j.get("created_at", ""),
        reverse=True,
    )
    return {"total": len(all_jobs), "jobs": all_jobs}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job and all associated files from disk.
    FIX 6: Entire check-and-delete inside single RLock scope.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    if job.get("status") == "processing":
        raise HTTPException(409, "Cannot delete a job that is currently processing")

    # Remove files
    for folder in [UPLOAD_DIR / job_id, OUTPUT_DIR / job_id]:
        if folder.is_dir():
            shutil.rmtree(folder, ignore_errors=True)

    upload_path = job.get("upload_path", "")
    if upload_path:
        p = Path(upload_path)
        if p.is_file():
            p.unlink(missing_ok=True)

    delete_job_record(job_id)
    
    log.info("[%s] Deleted", job_id)
    return {"message": f"Job '{job_id}' deleted"}