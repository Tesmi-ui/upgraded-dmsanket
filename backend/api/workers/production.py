"""
Production system background worker.
Preserves ALL production processing logic from main.py.
"""
import os
import logging
from pathlib import Path
from datetime import datetime

from services.pipeline_orchestrator import DataMigrationEngine
from models.schema import ProcessingOptions
from ..core.config import UPLOAD_DIR, OUTPUT_DIR
from ..core.storage import update_job, get_job

log = logging.getLogger(__name__)


def _build_config(options: ProcessingOptions) -> dict:
    """Build engine config from options."""
    return options.to_engine_config()


def process_production_system(job_id: str, options: ProcessingOptions) -> None:
    """
    Background worker: PRODUCTION system (intelligence_engine.py).
    Full pipeline with 3 files + 9-sheet report.
    
    Preserves ALL logic from main.py _process_single_job().
    """
    try:
        log.info("[%s] Starting PRODUCTION system", job_id)
        
        job = get_job(job_id)
        upload_path = job.get("upload_path", "")

        if not upload_path or not os.path.exists(upload_path):
            found = list(UPLOAD_DIR.glob(f"{job_id}.*"))
            if not found:
                raise FileNotFoundError(f"Upload file not found for job {job_id}")
            upload_path = str(found[0])

        job_out = str(OUTPUT_DIR / job_id)
        os.makedirs(job_out, exist_ok=True)

        update_job(job_id, {"progress": 30, "message": "Loading data…"})

        context = options.to_execution_context()
        engine = DataMigrationEngine(_build_config(options))
        
        update_job(job_id, {
            "progress": 50,
            "message": f"Running analysis [{context.mode.value}]…"
        })

        result = engine.process(upload_path, job_out, context=context)
        
        update_job(job_id, {"progress": 90, "message": "Generating report…"})

        update_job(job_id, {
            "status": "complete",
            "progress": 100,
            "message": "Complete!",
            "finished_at": datetime.now().isoformat(),
            "stats": {
                "original_records": result["original_records"],
                "duplicates_removed": result["duplicates_removed"],
                "auto_corrections": result["auto_corrections"],
                "spell_corrections": result.get("spell_corrections", 0),
                "date_issues": result.get("date_issues", 0),
                "placeholder_records": result.get("placeholder_records", 0),
                "final_records": result["final_records"],
                "validation_warnings": result["validation_warnings"],
            },
            "output_paths": {
                "cleaned": result.get("output_file", ""),
                "merged": result.get("merged_file", ""),
                "review": result.get("review_file", ""),
                "report": result.get("report_file", ""),
                "backup": result.get("backup_file", ""),
            },
        })
        
        log.info("[%s] PRODUCTION complete — %d records", job_id, result["final_records"])

    except Exception as exc:
        log.error("[%s] PRODUCTION failed: %s", job_id, exc, exc_info=True)
        update_job(job_id, {"status": "error", "message": str(exc), "progress": 0})