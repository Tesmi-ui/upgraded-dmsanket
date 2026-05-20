"""
Quick Engine endpoint — run individual specialised engines on uploaded files.
"""
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Literal, Optional

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from ..core.config import UPLOAD_DIR, OUTPUT_DIR
from ..core.storage import get_job, update_job, load_jobs

router = APIRouter(prefix="/api", tags=["engines"])
log = logging.getLogger(__name__)

# ── Quick Engine availability ─────────────────────────────────────────────
try:
    from engines import (
        NameFormattingEngine,
        ContactValidationEngine,
        DuplicateRemovalEngine,
        GenderInferenceEngine,
    )
    ENGINES_AVAILABLE = True
except ImportError:
    ENGINES_AVAILABLE = False


class QuickEngineRequest(BaseModel):
    """Body for POST /api/engine/run/{job_id}."""
    engine_name: Literal[
        "name_formatting",
        "contact_validation",
        "duplicate_removal",
        "gender_inference",
    ]
    columns: Optional[List[str]] = None


def _run_quick_engine_job(job_id: str, body: QuickEngineRequest) -> None:
    """Background worker: run individual specialised engine."""
    try:
        log.info("[%s] Quick engine: %s", job_id, body.engine_name)
        job = get_job(job_id)
        upload_path = job.get("upload_path", "")

        if not upload_path or not os.path.exists(upload_path):
            found = list(UPLOAD_DIR.glob(f"{job_id}.*"))
            if not found:
                raise FileNotFoundError(f"Upload file not found for job {job_id}")
            upload_path = str(found[0])

        update_job(job_id, {
            "progress": 30,
            "message": f"Loading data for {body.engine_name}…",
        })

        # Load file
        p = Path(upload_path)
        if p.suffix.lower() in (".xlsx", ".xls"):
            df = pd.read_excel(upload_path)
        else:
            df = pd.read_csv(upload_path)

        update_job(job_id, {
            "progress": 50,
            "message": f"Running {body.engine_name}…",
        })

        # Run selected engine
        results = {}
        if body.engine_name == "name_formatting":
            engine = NameFormattingEngine()
            df, results = engine.process_dataframe(df, body.columns or ["farmer_name"])
        elif body.engine_name == "contact_validation":
            engine = ContactValidationEngine()
            df, results = engine.process_dataframe(df)
        elif body.engine_name == "duplicate_removal":
            engine = DuplicateRemovalEngine()
            df, results = engine.process_dataframe(df)
        elif body.engine_name == "gender_inference":
            engine = GenderInferenceEngine()
            df, results = engine.process_dataframe(df)

        update_job(job_id, {"progress": 80, "message": "Saving results…"})

        # Save output
        job_output_dir = OUTPUT_DIR / job_id
        job_output_dir.mkdir(parents=True, exist_ok=True)
        output_path = job_output_dir / f"{job_id}_{body.engine_name}.xlsx"
        df.to_excel(str(output_path), index=False)

        stats = results.get("stats", {}) if isinstance(results, dict) else {}

        update_job(job_id, {
            "status": "complete",
            "progress": 100,
            "message": f"Engine {body.engine_name} complete",
            "finished_at": datetime.now().isoformat(),
            "stats": stats,
            "output_paths": {"result": str(output_path)},
        })
        log.info("[%s] Quick engine complete", job_id)

    except Exception as exc:
        log.error("[%s] Quick engine failed: %s", job_id, exc, exc_info=True)
        update_job(job_id, {
            "status": "error",
            "message": str(exc),
            "progress": 0,
        })


@router.post("/engine/run/{job_id}")
async def run_engine(
    job_id: str,
    body: QuickEngineRequest,
    background_tasks: BackgroundTasks,
):
    """
    Run an individual specialised engine on a previously uploaded file.

    Available engines:
      - name_formatting     — proper case, trimming, Unicode normalisation
      - contact_validation  — mobile number format validation
      - duplicate_removal   — deduplication by unique key
      - gender_inference    — AI gender inference from names
    """
    if not ENGINES_AVAILABLE:
        raise HTTPException(
            503,
            "Quick engines are not loaded. "
            "Ensure the 'engines' package is installed.",
        )

    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["status"] not in ("uploaded", "complete", "error"):
        raise HTTPException(
            400,
            f"Job is '{job['status']}' — cannot run engine now",
        )

    update_job(job_id, {
        "status": "processing",
        "progress": 20,
        "message": f"Running {body.engine_name} engine…",
        "system_used": f"quick_engine:{body.engine_name}",
    })
    background_tasks.add_task(_run_quick_engine_job, job_id, body)

    return {
        "job_id": job_id,
        "status": "processing",
        "engine": body.engine_name,
    }
