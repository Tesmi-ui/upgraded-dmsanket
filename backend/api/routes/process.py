"""
Processing endpoints (unified multi-system).
Preserves ALL routing logic from main.py.
"""
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException

from ..core.storage import get_job, update_job
from ..models.schemas import UnifiedProcessRequest, ProcessingSystem, MigrationRequest, ApplyEditsRequest
from ..workers.production import process_production_system
from ..workers.check_intelligence import process_check_intelligence
from core.execution_context import ExecutionMode
from models.schema import ProcessingOptions
import asyncio

router = APIRouter(prefix="/api", tags=["processing"])
log = logging.getLogger(__name__)


@router.post("/process")
async def process_unified(
    request: UnifiedProcessRequest,
    background_tasks: BackgroundTasks,
):
    """
    Unified processing endpoint for all systems.
    
    Systems:
    - PRODUCTION: intelligence_engine.py (full pipeline)
    - GLOBAL: check_intelligence GLOBAL mode
    - ADVISORY: check_intelligence ADVISORY mode  
    - SELECTIVE: check_intelligence SELECTIVE mode
    """
    job_id = request.job_id
    job = get_job(job_id)
    
    if not job:
        raise HTTPException(404, "Job not found")
    
    if job["status"] not in ("uploaded", "error") and request.stage == 1:
        raise HTTPException(400, f"Job is already '{job['status']}'")

    if request.stage > 1:
        # Mock Stage 2/3 delay to simulate UI progress
        async def mock_stage(j_id, stg):
            await asyncio.sleep(2)
            update_job(j_id, {"status": "complete", "progress": 100, "message": f"Stage {stg} complete"})
            
        update_job(job_id, {
            "status": "processing",
            "progress": 50,
            "message": f"Running Stage {request.stage}...",
            "system_used": request.system.value,
        })
        background_tasks.add_task(mock_stage, job_id, request.stage)
        return {"job_id": job_id, "status": "processing", "system": request.system.value}

    update_job(job_id, {
        "status": "processing",
        "progress": 20,
        "message": f"Starting {request.system.value} system...",
        "system_used": request.system.value,
    })
    
    options = request.options or ProcessingOptions()
    
    # Route to appropriate system
    if request.system == ProcessingSystem.PRODUCTION:
        background_tasks.add_task(process_production_system, job_id, options)
    
    elif request.system in [ProcessingSystem.GLOBAL, ProcessingSystem.ADVISORY, ProcessingSystem.SELECTIVE]:
        mode_map = {
            ProcessingSystem.GLOBAL: ExecutionMode.GLOBAL,
            ProcessingSystem.ADVISORY: ExecutionMode.ADVISORY,
            ProcessingSystem.SELECTIVE: ExecutionMode.SELECTIVE,
        }
        mode = mode_map[request.system]
        background_tasks.add_task(process_check_intelligence, job_id, mode, options)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "system": request.system.value
    }


@router.post("/process/{job_id}")
async def process_file_legacy(
    job_id: str,
    options: ProcessingOptions,
    background_tasks: BackgroundTasks,
):
    """
    Legacy endpoint - defaults to PRODUCTION system.
    Preserves backward compatibility with old API.
    """
    return await process_unified(
        UnifiedProcessRequest(
            job_id=job_id,
            system=ProcessingSystem.PRODUCTION,
            options=options,
            stage=1
        ),
        background_tasks
    )

@router.post("/migrate/{job_id}")
async def migrate_data(job_id: str, request: MigrationRequest, background_tasks: BackgroundTasks):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
        
    async def mock_migration(j_id):
        await asyncio.sleep(2)
        update_job(j_id, {"status": "complete", "progress": 100, "message": "Migration complete"})
        
    update_job(job_id, {
        "status": "processing", 
        "progress": 10, 
        "message": "Starting migration upload..."
    })
    background_tasks.add_task(mock_migration, job_id)
    return {"job_id": job_id, "status": "migrating"}

@router.get("/jobs/{job_id}/suggestions")
def get_job_suggestions(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
        
    import os, json
    from ..core.config import OUTPUT_DIR
    suggestions_path = OUTPUT_DIR / job_id / "suggestions.json"
    
    if not suggestions_path.exists():
        return {"changes": [], "spell_changes": []}
        
    with open(suggestions_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data

@router.post("/jobs/{job_id}/apply-edits")
def apply_job_edits(job_id: str, request: ApplyEditsRequest):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
        
    cleaned_path = job.get("output_paths", {}).get("cleaned")
    if not cleaned_path:
        raise HTTPException(400, "Cleaned dataset not found for this job")
        
    import pandas as pd
    try:
        df_clean = pd.read_excel(cleaned_path)
        
        applied_count = 0
        for edit in request.edits:
            # Edit request uses Excel row index (1-based header) -> Excel_Row - 2 = df row index
            df_idx = edit.row_index
            if df_idx < 0 or df_idx >= len(df_clean):
                continue
            if edit.field in df_clean.columns:
                df_clean.at[df_idx, edit.field] = edit.value
                applied_count += 1
                
        # Save back the explicitly modified file
        df_clean.to_excel(cleaned_path, index=False)
        return {"status": "success", "applied": applied_count}
    except Exception as e:
        log.error("Failed to apply edits: %s", e)
        raise HTTPException(500, f"Error applying edits: {e}")