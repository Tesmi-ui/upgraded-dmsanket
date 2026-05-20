import os
import re

base_dir = r"d:\BRLF\brlf\brlfdmtosanket\dmsanket\backend"
intelligence_engine_path = os.path.join(base_dir, "intelligence_engine.py")

with open(intelligence_engine_path, "r", encoding="utf-8") as f:
    content = f.read()

# We need to split out the run_pipeline function (and its imports/helpers if possible, but they share a lot.
# To be perfectly safe, both files can just import all the shared dependencies.

header = """\"\"\"
Extracted from intelligence_engine.py
\"\"\"
from __future__ import annotations
import logging
import math
from typing import List, Optional
from core.execution_context import ExecutionContext, ExecutionMode
import pandas as pd
from gender_lib import infer_gender as _lib_infer_gender
from gender_lib.knowledge_base import FEMALE_NAMES, MALE_NAMES, FEMALE_SUFFIXES, MALE_SUFFIXES, SURNAME_CATEGORY
from check_intelligence.inference.engine import infer_gender as _brlf_infer_gender, infer_category as _brlf_infer_category
from validators.name_formatter import NameCaseFormatter
from validators.contact_validator import ContactValidator
from validators.mgnrega_validator import MGNREGAValidator
from validators.name_spell_checker import NameSpellChecker
from models.schema import FarmerRecord, ProcessedRecord, ProcessRequest, ProcessResponse, ValidationDetail, InferenceDetail

log = logging.getLogger("brlf.intelligence_engine")

def _clean_val(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v).strip().lower()

_name_fmt  = NameCaseFormatter()
_contact_v = ContactValidator()
_mgnrega_v = MGNREGAValidator()
"""

# Extract run_pipeline
run_pipeline_match = re.search(r'(def run_pipeline\(.*?return ProcessResponse\([^\)]+\)\n)', content, re.DOTALL)
run_pipeline_code = run_pipeline_match.group(1) if run_pipeline_match else ""

record_processor_path = os.path.join(base_dir, "services", "record_processor.py")
with open(record_processor_path, "w", encoding="utf-8") as f:
    f.write(header + "\n" + run_pipeline_code)

# Now for pipeline_orchestrator, we just remove run_pipeline from the content and save it
if run_pipeline_match:
    pipeline_orchestrator_content = content.replace(run_pipeline_match.group(1), "")
else:
    pipeline_orchestrator_content = content

pipeline_orchestrator_path = os.path.join(base_dir, "services", "pipeline_orchestrator.py")
with open(pipeline_orchestrator_path, "w", encoding="utf-8") as f:
    f.write(pipeline_orchestrator_content)

# Remove the original file
os.remove(intelligence_engine_path)

# Update imports in all files in the backend
# replacing `from schema import` -> `from models.schema import`
# replacing `import schema` -> `import models.schema as schema`
# replacing `from execution_context import` -> `from core.execution_context import`
# replacing `from intelligence_engine import run_pipeline` -> `from services.record_processor import run_pipeline`
# replacing `from intelligence_engine import DataMigrationEngine` -> `from services.pipeline_orchestrator import DataMigrationEngine`

for root, dirs, files in os.walk(base_dir):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                file_content = f.read()
                
            orig = file_content
            file_content = re.sub(r'^from schema import', 'from models.schema import', file_content, flags=re.MULTILINE)
            file_content = re.sub(r'^import schema', 'from models import schema', file_content, flags=re.MULTILINE)
            file_content = re.sub(r'^from execution_context import', 'from core.execution_context import', file_content, flags=re.MULTILINE)
            
            # fix cross-imports if files moved deeper
            file_content = file_content.replace('from intelligence_engine import run_pipeline', 'from services.record_processor import run_pipeline')
            file_content = file_content.replace('from intelligence_engine import DataMigrationEngine', 'from services.pipeline_orchestrator import DataMigrationEngine')
            file_content = file_content.replace('from intelligence_engine import', 'from services.pipeline_orchestrator import')
            file_content = file_content.replace('import intelligence_engine', 'from services import pipeline_orchestrator')

            # if in services/pipeline_orchestrator.py, models.schema is actually ..models.schema or just models.schema (fastapi root is backend usually, we will rely on absolute imports assuming root is backend)
            # Actually, the original files use 'from schema import ...' which relies on backend being in PYTHONPATH.
            
            if file_content != orig:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(file_content)

print("Extraction and import replacement complete.")
