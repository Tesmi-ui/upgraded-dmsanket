"""
Singleton dependencies (gender library, file router).
Loaded at startup and held in memory.
"""
from typing import Optional
import logging

from gender_lib.knowledge_base import GenderLibrary
from check_intelligence.routing.file_router import FileRouter
from .config import GENDER_LIB_DIR, INBOX_DIR, VERIFIED_DIR, UNVERIFIED_DIR

log = logging.getLogger(__name__)

_gender_library: Optional[GenderLibrary] = None
_file_router: Optional[FileRouter] = None


def get_gender_library() -> GenderLibrary:
    """Get or create gender library singleton."""
    global _gender_library
    if _gender_library is None:
        strict = str(GENDER_LIB_DIR / "brlf_gender_strict.json")
        prob = str(GENDER_LIB_DIR / "brlf_gender_prob.json")
        _gender_library = GenderLibrary.load(strict, prob)
        log.info("Gender library loaded")
    return _gender_library


def get_file_router() -> FileRouter:
    """Get or create file router singleton."""
    global _file_router
    if _file_router is None:
        _file_router = FileRouter(
            inbox_dir=str(INBOX_DIR),
            verified_dir=str(VERIFIED_DIR),
            unverified_dir=str(UNVERIFIED_DIR),
            registry_path=str(INBOX_DIR / "inbox_registry.json"),
        )
        log.info("File router initialized")
    return _file_router


def reload_gender_library() -> None:
    """Reload gender library after rebuild."""
    global _gender_library
    if _gender_library:
        _gender_library = _gender_library.reload()
        log.info("Gender library reloaded")