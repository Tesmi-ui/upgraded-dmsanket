"""
check_intelligence.routing
===========================
File lifecycle management — upload, approve, reject, hold, promote, revoke.

  FileRouter  — class that manages the full pending→verified/unverified flow,
                atomic registry writes, and file locking.
"""
from check_intelligence.routing.file_router import FileRouter

__all__ = ["FileRouter"]