"""
Bulk processing background worker.
Preserves ALL bulk processing logic from main.py.
"""
import os
import logging
from pathlib import Path
from typing import List
from datetime import datetime

from bulk_processor import BulkProcessor, build_master_report
from models.schema import ProcessingOptions
from ..core.storage import update_job

log = logging.getLogger(__name__)


def _build_config(options: ProcessingOptions) -> dict:
    """Build engine config from options."""
    return options.to_engine_config()


def process_bulk_job(
    job_id: str,
    file_paths: List[str],
    output_dir: str,
    options: ProcessingOptions,
) -> None:
    """
    Background worker: multiple files → BulkProcessor.
    Preserves ALL logic from main.py _process_bulk_job().
    """
    try:
        log.info("[%s] Bulk processing %d file(s)", job_id, len(file_paths))
        
        update_job(job_id, {
            "progress": 20,
            "message": f"Processing {len(file_paths)} file(s)…",
        })

        context = options.to_execution_context()
        bp = BulkProcessor(_build_config(options))
        results = bp.process_files(file_paths, output_dir, context=context)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        master_path = os.path.join(output_dir, f"MASTER_SUMMARY_{ts}.xlsx")
        
        if results:
            build_master_report(results, master_path)

        success = [r for r in results if r["status"] == "success"]
        errors = [r for r in results if r["status"] == "error"]

        file_results = []
        for r in results:
            s = r.get("summary") or {}
            file_results.append({
                "file": Path(r["file"]).name,
                "status": r["status"],
                "error": r.get("error"),
                "stats": {
                    "original_records": s.get("original_records", 0),
                    "final_records": s.get("final_records", 0),
                    "duplicates_removed": s.get("duplicates_removed", 0),
                    "auto_corrections": s.get("auto_corrections", 0),
                    "spell_corrections": s.get("spell_corrections", 0),
                    "date_issues": s.get("date_issues", 0),
                    "placeholder_records": s.get("placeholder_records", 0),
                    "validation_warnings": s.get("validation_warnings", []),
                },
                "output_paths": {
                    "cleaned": s.get("output_file", ""),
                    "merged": s.get("merged_file", ""),
                    "review": s.get("review_file", ""),
                    "report": s.get("report_file", ""),
                    "backup": s.get("backup_file", ""),
                },
            })

        update_job(job_id, {
            "status": "complete" if not errors else "complete_with_errors",
            "progress": 100,
            "message": f"{len(success)}/{len(results)} files processed",
            "finished_at": datetime.now().isoformat(),
            "file_results": file_results,
            "master_report": master_path if results else "",
            "total_stats": {
                "original": sum((r.get("summary") or {}).get("original_records", 0) for r in success),
                "final": sum((r.get("summary") or {}).get("final_records", 0) for r in success),
                "dedup": sum((r.get("summary") or {}).get("duplicates_removed", 0) for r in success),
                "corrections": sum((r.get("summary") or {}).get("auto_corrections", 0) for r in success),
                "spelling": sum((r.get("summary") or {}).get("spell_corrections", 0) for r in success),
            },
        })
        
        log.info("[%s] Bulk done — %d/%d OK", job_id, len(success), len(results))

    except Exception as exc:
        log.error("[%s] Bulk failed: %s", job_id, exc, exc_info=True)
        update_job(job_id, {"status": "error", "message": str(exc), "progress": 0})