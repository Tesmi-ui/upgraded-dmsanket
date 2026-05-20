"""
Backend Engines Package
=======================
Specialized engines for specific tasks.

Each engine does ONE thing perfectly:
- NameFormattingEngine: Format names only
- ContactValidationEngine: Validate contacts only
- DuplicateRemovalEngine: Remove duplicates only
- GenderInferenceEngine: Infer gender only
- DataCleaningEngine: Clean data only
- DateValidationEngine: Validate dates only
- LandValidationEngine: Validate land only
- MGNREGAValidationEngine: Validate MGNREGA only
- MasterOrchestrator: Run all engines together

Use these for quick one-off tasks.
Use intelligence_engine.py for full production pipeline.
"""

from .name_formatting_engine import NameFormattingEngine
from .contact_validation_engine import ContactValidationEngine
from .duplicate_removal_engine import DuplicateRemovalEngine
from .gender_inference_engine import GenderInferenceEngine
from .data_cleaning_engine import DataCleaningEngine
from .date_validation_engine import DateValidationEngine
from .land_validation_engine import LandValidationEngine
from .mgnrega_validation_engine import MGNREGAValidationEngine
from .master_orchestrator import MasterOrchestrator

__version__ = "4.0.0"

__all__ = [
    "NameFormattingEngine",
    "ContactValidationEngine",
    "DuplicateRemovalEngine",
    "GenderInferenceEngine",
    "DataCleaningEngine",
    "DateValidationEngine",
    "LandValidationEngine",
    "MGNREGAValidationEngine",
    "MasterOrchestrator",
]