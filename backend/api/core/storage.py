"""
Persistent job storage with thread-safe operations (RLock).
FIX 1+2 from main.py: RLock + atomic load-mutate-save.
"""
import json
import threading
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from .config import LOGS_DIR

JOBS_FILE = LOGS_DIR / "jobs.json"
_lock = threading.RLock()  # FIX 1: RLock allows re-entrant calls


def load_jobs() -> Dict[str, Any]:
    """Load all jobs from disk (thread-safe)."""
    with _lock:
        if not JOBS_FILE.exists():
            return {}
        try:
            return json.loads(JOBS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}


def save_jobs(jobs: Dict[str, Any]) -> None:
    """Save all jobs to disk (thread-safe)."""
    with _lock:
        JOBS_FILE.write_text(json.dumps(jobs, indent=2, default=str))


def update_job(job_id: str, updates: Dict[str, Any]) -> None:
    """
    Update a specific job atomically.
    FIX 2: Entire load-mutate-save inside ONE RLock scope.
    """
    with _lock:
        try:
            jobs = json.loads(JOBS_FILE.read_text()) if JOBS_FILE.exists() else {}
        except (json.JSONDecodeError, OSError):
            jobs = {}
        
        if job_id in jobs:
            jobs[job_id].update(updates)
            JOBS_FILE.write_text(json.dumps(jobs, indent=2, default=str))


def get_job(job_id: str) -> Dict[str, Any]:
    """Get a specific job."""
    jobs = load_jobs()
    return jobs.get(job_id, {})


def create_job(job_id: str, job_data: Dict[str, Any]) -> None:
    """Create a new job."""
    with _lock:
        jobs = load_jobs()
        jobs[job_id] = job_data
        save_jobs(jobs)


def delete_job_record(job_id: str) -> None:
    """Delete a job record (thread-safe)."""
    with _lock:
        try:
            jobs = json.loads(JOBS_FILE.read_text()) if JOBS_FILE.exists() else {}
        except (json.JSONDecodeError, OSError):
            jobs = {}
        
        jobs.pop(job_id, None)
        JOBS_FILE.write_text(json.dumps(jobs, indent=2, default=str))