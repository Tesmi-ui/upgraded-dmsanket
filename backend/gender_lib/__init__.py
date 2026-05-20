"""
gender_lib
==========
Standalone gender-inference library for Marathi / Vidarbha personal names.

Public API
----------
    from gender_lib import infer_gender, GenderResult

    result = infer_gender("Sunita Deshmukh", spouse_or_father="Ramesh")
    result.gender      # "female"
    result.confidence  # 95
    result.reason      # "First name 'sunita' is a well-known female name..."
    result.tier        # 1
    result.label       # "High"
    result.is_determined  # True

The library has NO dependencies outside Python stdlib + pandas.
It can be installed/imported independently of the BRLF system.
"""

from .gender import GenderResult, infer_gender, UNDETERMINED
from .knowledge_base import (
    FEMALE_NAMES,
    MALE_NAMES,
    FEMALE_SUFFIXES,
    MALE_SUFFIXES,
    SURNAME_CATEGORY,
    GenderLibrary,
)

__all__ = [
    # Core inference
    "infer_gender",
    "GenderResult",
    "UNDETERMINED",
    # Knowledge-base access (for callers that want to inspect / extend)
    "FEMALE_NAMES",
    "MALE_NAMES",
    "FEMALE_SUFFIXES",
    "MALE_SUFFIXES",
    "SURNAME_CATEGORY",
    # Dynamic library loader (loaded from build-output JSON files)
    "GenderLibrary",
]

__version__ = "1.0.0"