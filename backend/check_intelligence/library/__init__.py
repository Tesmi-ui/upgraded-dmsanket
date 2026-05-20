"""
check_intelligence.library
==========================
Admin-only tools that build the gender JSON libraries from disk files.

  build_strict_library()  — reads verified/,   writes brlf_gender_strict.json
  build_prob_library()    — reads unverified/, writes brlf_gender_prob.json
  run_rebuild()           — orchestrates both, used by main.py admin endpoints
  library_status()        — read-only status summary, used by main.py
"""
from check_intelligence.library.build_strict import build_strict_library
from check_intelligence.library.build_prob   import build_prob_library
from check_intelligence.library.rebuild      import run_rebuild, library_status

__all__ = [
    "build_strict_library",
    "build_prob_library",
    "run_rebuild",
    "library_status",
]