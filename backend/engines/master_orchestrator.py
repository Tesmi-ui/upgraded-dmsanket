"""
Master Orchestrator - Works Alongside intelligence_engine.py
============================================================
Alternative pipeline using specialized engines.

DIFFERENCE from intelligence_engine.py:
- Modular (can run individual engines)
- Uses specialized engines (each does one thing)
- Simpler reports (not 9-sheet comprehensive)

USE CASE:
- Quick tasks
- Testing new approaches
- When you don't need full production pipeline

PRODUCTION USE:
- Still use intelligence_engine.py for main workflows
- Use this for quick one-off tasks
"""

import sys
from pathlib import Path
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List

# Import specialized engines from same folder
from .name_formatting_engine import NameFormattingEngine
from .contact_validation_engine import ContactValidationEngine
from .duplicate_removal_engine import DuplicateRemovalEngine
from .gender_inference_engine import GenderInferenceEngine
from .data_cleaning_engine import DataCleaningEngine
from .date_validation_engine import DateValidationEngine
from .land_validation_engine import LandValidationEngine
from .mgnrega_validation_engine import MGNREGAValidationEngine

log = logging.getLogger("brlf.master_orchestrator")


class MasterOrchestrator:
    """
    Coordinates specialized engines.
    Alternative to intelligence_engine.py for quick tasks.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Initialize all engines
        self.cleaning_engine = DataCleaningEngine()
        self.name_engine = NameFormattingEngine()
        self.contact_engine = ContactValidationEngine()
        self.dedup_engine = DuplicateRemovalEngine()
        self.gender_engine = GenderInferenceEngine()
        self.mgnrega_engine = MGNREGAValidationEngine()
        self.date_engine = DateValidationEngine(
            min_age=self.config.get("min_age", 18),
            max_age=self.config.get("max_age", 100)
        )
        self.land_engine = LandValidationEngine(
            min_area=self.config.get("min_land_area", 0.01),
            max_area=self.config.get("max_land_area", 1000)
        )
        
        self.results = {}
    
    def process_file(
        self,
        input_file: str,
        output_dir: str = None,
        engines_to_run: List[str] = None
    ) -> Dict:
        """
        Process file through selected engines.
        
        NOTE: This is DIFFERENT from intelligence_engine.py:
        - No file merging
        - Simpler reports
        - Can run individual engines
        
        For full production pipeline, use intelligence_engine.py
        """
        input_path = Path(input_file)
        if output_dir is None:
            output_dir = input_path.parent / f"{input_path.stem}_engines_output"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if engines_to_run is None:
            engines_to_run = [
                'cleaning', 'name_formatting', 'contact_validation',
                'duplicate_removal', 'gender_inference', 'mgnrega_validation',
                'date_validation', 'land_validation'
            ]
        
        log.info("=" * 70)
        log.info("MASTER ORCHESTRATOR (Specialized Engines)")
        log.info("=" * 70)
        log.info(f"Input: {input_file}")
        log.info(f"Engines: {', '.join(engines_to_run)}")
        log.info("=" * 70)
        
        # Load
        log.info("\n📂 Loading file...")
        df_original = pd.read_excel(input_file)
        n_original = len(df_original)
        log.info(f"✅ Loaded {n_original:,} records")
        
        df = df_original.copy()
        
        # Run selected engines
        if 'cleaning' in engines_to_run:
            log.info("\n🧹 Data Cleaning...")
            df, result = self.cleaning_engine.process_dataframe(df, operations=['trim', 'handle_nulls'])
            self.results['cleaning'] = result
            log.info(f"✅ Cleaned {result['stats']['cells_cleaned']:,} cells")
        
        if 'name_formatting' in engines_to_run:
            log.info("\n✏️  Name Formatting...")
            df, result = self.name_engine.process_dataframe(df, ['farmer_name', 'father_spouse_name'])
            self.results['name_formatting'] = result
            log.info(f"✅ Formatted {result['stats']['total_changed']:,} names")
        
        if 'contact_validation' in engines_to_run:
            log.info("\n📞 Contact Validation...")
            df, result = self.contact_engine.process_dataframe(df, "contact_number")
            self.results['contact_validation'] = result
            log.info(f"✅ Validated: {result['stats']['valid']:,} valid, {result['stats']['invalid']:,} invalid")
        
        if 'duplicate_removal' in engines_to_run:
            log.info("\n🗂️  Duplicate Removal...")
            df, result = self.dedup_engine.process_dataframe(
                df,
                unique_key=self.config.get("unique_key", "Unique Key"),
                date_column=self.config.get("date_column", "SubmissionDate")
            )
            self.results['duplicate_removal'] = result
            log.info(f"✅ Removed {result['stats']['duplicates_removed']:,} duplicates")
        
        if 'gender_inference' in engines_to_run:
            log.info("\n⚤  Gender Inference...")
            df, result = self.gender_engine.process_dataframe(df, min_confidence=self.config.get("min_confidence", 75))
            self.results['gender_inference'] = result
            log.info(f"✅ Inferred {result['stats']['inferred']:,} genders")
        
        if 'mgnrega_validation' in engines_to_run:
            log.info("\n🆔 MGNREGA Validation...")
            df, result = self.mgnrega_engine.process_dataframe(df, "mgnrega")
            self.results['mgnrega_validation'] = result
            log.info(f"✅ Validated: {result['stats']['valid']:,} valid, {result['stats']['invalid']:,} invalid")
        
        if 'date_validation' in engines_to_run:
            log.info("\n📅 Date/Age Validation...")
            df, result = self.date_engine.process_dataframe(
                df,
                date_columns=['date_of_survey', 'SubmissionDate'],
                age_columns=['age']
            )
            self.results['date_validation'] = result
            log.info(f"✅ Found {result['stats']['invalid']:,} date/age issues")
        
        if 'land_validation' in engines_to_run:
            log.info("\n🌾 Land Validation...")
            df, result = self.land_engine.process_dataframe(df)
            self.results['land_validation'] = result
            log.info(f"✅ Found {result['stats']['invalid']:,} land issues")
        
        # Save
        output_file = output_path / f"{input_path.stem}_PROCESSED_{timestamp}.xlsx"
        df.to_excel(output_file, index=False)
        log.info(f"\n💾 Saved: {output_file}")
        
        # Summary
        total_changes = sum(
            result.get('stats', {}).get('total_changed', 0) +
            result.get('stats', {}).get('cells_cleaned', 0) +
            result.get('stats', {}).get('inferred', 0) +
            result.get('stats', {}).get('corrected', 0)
            for result in self.results.values()
        )
        
        log.info("\n" + "=" * 70)
        log.info("COMPLETE")
        log.info("=" * 70)
        log.info(f"Original: {n_original:,} → Final: {len(df):,} records")
        log.info(f"Total changes: {total_changes:,}")
        log.info("=" * 70)
        
        return {
            "input_file": input_file,
            "output_file": str(output_file),
            "original_records": n_original,
            "final_records": len(df),
            "total_changes": total_changes,
            "engine_results": self.results
        }


def main():
    """Standalone usage."""
    import sys
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    
    if len(sys.argv) > 1:
        orchestrator = MasterOrchestrator({
            "min_confidence": 75,
            "unique_key": "Unique Key",
            "date_column": "SubmissionDate"
        })
        
        results = orchestrator.process_file(sys.argv[1])
        print(f"\n✅ Output: {results['output_file']}")
    else:
        print("Usage: python master_orchestrator.py <input_file>")


if __name__ == "__main__":
    main()