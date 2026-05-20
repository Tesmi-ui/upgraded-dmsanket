"""
All Pydantic models for requests/responses.
"""
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

from models.schema import ProcessingOptions  # Import from existing schema.py


class ProcessingSystem(str, Enum):
    """Available processing systems."""
    PRODUCTION = "production"    # intelligence_engine.py
    GLOBAL = "global"            # check_intelligence GLOBAL
    ADVISORY = "advisory"        # check_intelligence ADVISORY
    SELECTIVE = "selective"      # check_intelligence SELECTIVE


class UnifiedProcessRequest(BaseModel):
    """Unified processing request for all systems."""
    job_id: str
    system: ProcessingSystem = ProcessingSystem.PRODUCTION
    stage: int = 1
    options: Optional[ProcessingOptions] = None

class MigrationRequest(BaseModel):
    format: str = "nrm"
    validate_only: bool = False


class UploadResponse(BaseModel):
    """Response after file upload."""
    job_id: str
    filename: str
    status: str
    schema_errors: List[dict] = []
    schema_warnings: List[dict] = []


class BulkUploadResponse(BaseModel):
    """Response after bulk upload."""
    job_id: str
    files: List[str]
    status: str
    poll_url: str


class JobStatusResponse(BaseModel):
    """Job status response."""
    job_id: str
    status: str
    progress: int
    message: str
    system_used: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None
    output_paths: Optional[Dict[str, str]] = None

class EditField(BaseModel):
    row_index: int  # 0-based or 1-based depending on frontend (using Excel_Row - 2)
    field: str      # e.g., "gender", "category"
    value: str      # e.g., "Male", "SC"

class ApplyEditsRequest(BaseModel):
    edits: List[EditField]