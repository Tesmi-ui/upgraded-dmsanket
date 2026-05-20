"""
Check Intelligence system background worker.
Supports GLOBAL/ADVISORY/SELECTIVE modes.
"""
import os
import logging
from pathlib import Path
from datetime import datetime

from services.pipeline_orchestrator import DataMigrationEngine
from core.execution_context import ExecutionContext, ExecutionMode
from models.schema import ProcessingOptions
from ..core.config import UPLOAD_DIR, OUTPUT_DIR
from ..core.storage import update_job, get_job

log = logging.getLogger(__name__)


def _build_config(options: ProcessingOptions) -> dict:
    """Build engine config from options."""
    return options.to_engine_config()


def process_check_intelligence(
    job_id: str,
    mode: ExecutionMode,
    options: ProcessingOptions
) -> None:
    """
    Background worker: CHECK INTELLIGENCE system.
    Supports GLOBAL/ADVISORY/SELECTIVE modes.
    """
    try:
        log.info("[%s] Starting CHECK INTELLIGENCE (%s)", job_id, mode.value)
        
        job = get_job(job_id)
        upload_path = job.get("upload_path", "")
        
        if not upload_path or not os.path.exists(upload_path):
            raise FileNotFoundError(f"Upload file not found for job {job_id}")
        
        update_job(job_id, {
            "progress": 20,
            "message": f"Loading file for {mode.value} mode..."
        })
        
        # Create execution context
        options.execution_mode = mode.value
        context = options.to_execution_context()
        
        # Use intelligence_engine with check_intelligence mode
        job_out = str(OUTPUT_DIR / job_id)
        os.makedirs(job_out, exist_ok=True)
        
        update_job(job_id, {"progress": 40, "message": "Running intelligence checks..."})
        
        engine = DataMigrationEngine(_build_config(options))
        result = engine.process(upload_path, job_out, context=context)
        
        update_job(job_id, {"progress": 70, "message": "Generating output..."})
        
        stats = {
            "total_records": result["final_records"],
            "corrections_made": result["auto_corrections"],
            "mode_used": mode.value
        }
        
        update_job(job_id, {
            "status": "complete",
            "progress": 100,
            "message": f"Check intelligence ({mode.value}) complete",
            "finished_at": datetime.now().isoformat(),
            "stats": stats,
            "output_paths": {
                "cleaned": result.get("output_file", ""),
                "review": result.get("review_file", ""),
                "report": result.get("report_file", ""),
            },
        })
        
        log.info("[%s] CHECK INTELLIGENCE complete", job_id)
    
    except Exception as exc:
        log.error("[%s] CHECK INTELLIGENCE failed: %s", job_id, exc, exc_info=True)
        update_job(job_id, {"status": "error", "message": str(exc), "progress": 0})