"""
File validation utilities.
FIX 7 from main.py: Size limit with streaming.
"""
from pathlib import Path
from typing import List
import logging

from fastapi import HTTPException, UploadFile

from ..core.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES

log = logging.getLogger(__name__)


def validate_extension(filename: str) -> str:
    """Validate file extension."""
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Invalid file type '{ext}'. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return ext


async def read_with_size_limit(upload: UploadFile) -> bytes:
    """
    Read uploaded file with size limit (streaming).
    FIX 7: Prevents memory exhaustion from large files.
    """
    chunks: List[bytes] = []
    total = 0
    
    while True:
        chunk = await upload.read(64 * 1024)  # 64 KB at a time
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            log.warning(f"File upload rejected: {total} bytes exceeds limit")
            raise HTTPException(
                413,
                f"File exceeds maximum upload size ({MAX_UPLOAD_BYTES // (1024*1024)} MB).",
            )
        chunks.append(chunk)
    
    return b"".join(chunks)