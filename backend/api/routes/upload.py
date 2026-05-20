"""
File upload endpoints (single + bulk).
Preserves ALL code from main.py upload functions.
"""
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

import aiofiles
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, BackgroundTasks

from ..core.config import UPLOAD_DIR, OUTPUT_DIR
from ..core.storage import create_job, update_job
from ..models.schemas import UploadResponse, BulkUploadResponse
from ..utils.validators import validate_extension, read_with_size_limit
from ..workers.bulk import process_bulk_job
from models.schema import ProcessingOptions

router = APIRouter(prefix="/api", tags=["upload"])
log = logging.getLogger(__name__)


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload one file. Returns job_id.
    
    Runs BRLFSchemaValidator immediately on upload to surface structural
    issues (missing required columns, PII fields, LGD code problems) before
    the user starts processing. Warnings are returned in the response but
    never block the upload — the file is always accepted and a job_id returned.
    
    Call POST /api/process to start processing.
    """
    ext = validate_extension(file.filename or "")
    content = await read_with_size_limit(file)

    job_id = str(uuid.uuid4())[:8]
    upload_path = UPLOAD_DIR / f"{job_id}{ext}"

    async with aiofiles.open(upload_path, "wb") as f:
        await f.write(content)

    # ── Schema validation (non-blocking) ──────────────────────────────────
    schema_warnings: List[dict] = []
    schema_errors: List[dict] = []
    
    try:
        import pandas as pd
        from check_intelligence.inference.schema_validator import (
            BRLFSchemaValidator,
            ValidationContext,
        )
        
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(str(upload_path), dtype=str, nrows=500)
        else:
            df = pd.read_csv(str(upload_path), dtype=str, nrows=500)

        validator = BRLFSchemaValidator()
        context = ValidationContext(
            encryption_enabled=False,
            user_id="upload_endpoint",
            purpose="upload",
        )
        issues = validator.validate_dataframe(df, context)

        for issue in issues:
            entry = {
                "type": issue.type,
                "severity": issue.severity,
                "field": issue.field,
                "message": issue.message,
            }
            if issue.count:
                entry["count"] = issue.count
            
            if issue.severity in ("CRITICAL", "HIGH"):
                schema_errors.append(entry)
            else:
                schema_warnings.append(entry)

        if schema_errors or schema_warnings:
            log.warning(
                "[%s] Schema check: %d error(s), %d warning(s)",
                job_id, len(schema_errors), len(schema_warnings),
            )
    
    except Exception as exc:
        log.warning("[%s] Schema validation skipped: %s", job_id, exc)

    # Create job record
    create_job(job_id, {
        "job_id": job_id,
        "filename": file.filename,
        "upload_path": str(upload_path),
        "type": "single",
        "status": "uploaded",
        "progress": 10,
        "message": "File uploaded successfully",
        "created_at": datetime.now().isoformat(),
        "schema_errors": schema_errors,
        "schema_warnings": schema_warnings,
    })

    log.info("[%s] Uploaded: %s (%dKB)", job_id, file.filename, len(content) // 1024)
    
    return UploadResponse(
        job_id=job_id,
        filename=file.filename,
        status="uploaded",
        schema_errors=schema_errors,
        schema_warnings=schema_warnings,
    )


@router.post("/upload/bulk", response_model=BulkUploadResponse)
async def upload_bulk(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    options: Optional[str] = Form(None),  # FIX 5: Form(None)
):
    """
    Upload multiple files. Processing starts immediately.
    Returns job_id. Poll GET /api/status/{job_id} for progress.
    options: optional JSON string matching ProcessingOptions fields.
    """
    for upload in files:
        validate_extension(upload.filename or "")

    # FIX 5: parse options safely, return 422 on bad JSON
    proc_opts = ProcessingOptions()
    if options:
        try:
            proc_opts = ProcessingOptions(**json.loads(options))
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(422, f"Invalid JSON in 'options': {exc}")

    job_id = str(uuid.uuid4())[:8]
    job_dir = UPLOAD_DIR / job_id
    output_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved: List[str] = []
    for upload in files:
        content = await read_with_size_limit(upload)
        safe_name = Path(upload.filename or "upload").name
        dest = job_dir / safe_name
        async with aiofiles.open(dest, "wb") as f:
            await f.write(content)
        saved.append(str(dest))
        log.info("[%s] Saved: %s (%dKB)", job_id, safe_name, len(content) // 1024)

    create_job(job_id, {
        "job_id": job_id,
        "type": "bulk",
        "filenames": [Path(p).name for p in saved],
        "status": "processing",
        "progress": 10,
        "message": f"{len(saved)} file(s) uploaded — processing started",
        "created_at": datetime.now().isoformat(),
        "output_dir": str(output_dir),
        "system_used": "production",
    })

    background_tasks.add_task(process_bulk_job, job_id, saved, str(output_dir), proc_opts)

    return BulkUploadResponse(
        job_id=job_id,
        files=[Path(p).name for p in saved],
        status="processing",
        poll_url=f"/api/status/{job_id}",
    )