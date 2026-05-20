#!/usr/bin/env python3
"""
Quick Engine Runner
===================
Easy way to run any single engine or combination.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")


def show_menu():
    """Show engine selection menu."""
    print("\n" + "=" * 70)
    print("  BRLF SPECIALIZED ENGINES - Quick Runner")
    print("=" * 70)
    print("\n  Available Engines:")
    print("  [1] Name Formatting        (Fix: RAMESH KUMAR → Ramesh Kumar)")
    print("  [2] Contact Validation     (Validate Indian mobile numbers)")
    print("  [3] Duplicate Removal      (Remove duplicates, keep recent)")
    print("  [4] Gender Inference       (Predict gender from name)")
    print("  [5] Data Cleaning          (Better than Excel TRIM)")
    print("  [6] MGNREGA Validation     (Validate card format)")
    print("  [7] Date/Age Validation    (Check age ranges, future dates)")
    print("  [8] Land Validation        (Validate land areas)")
    print("  [9] ALL Engines            (Run complete pipeline)")
    print("\n" + "=" * 70)


def run_single_engine(engine_num, input_file):
    """Run a single engine."""
    from engines import (
        NameFormattingEngine,
        ContactValidationEngine,
        DuplicateRemovalEngine,
        GenderInferenceEngine,
        DataCleaningEngine,
        MGNREGAValidationEngine,
        DateValidationEngine,
        LandValidationEngine,
        MasterOrchestrator
    )
    
    df = pd.read_excel(input_file)
    output = input_file.replace('.xlsx', '')
    
    if engine_num == 1:
        print("\n🚀 Running Name Formatting Engine...")
        engine = NameFormattingEngine()
        df, results = engine.process_dataframe(df, ['farmer_name', 'father_spouse_name'])
        output_file = f"{output}_FORMATTED.xlsx"
        print(results['summary'])
    
    elif engine_num == 2:
        print("\n🚀 Running Contact Validation Engine...")
        engine = ContactValidationEngine()
        df, results = engine.process_dataframe(df)
        output_file = f"{output}_CONTACTS.xlsx"
        print(results['summary'])
    
    elif engine_num == 3:
        print("\n🚀 Running Duplicate Removal Engine...")
        engine = DuplicateRemovalEngine()
        df, results = engine.process_dataframe(df)
        output_file = f"{output}_DEDUPED.xlsx"
        print(results['summary'])
    
    elif engine_num == 4:
        print("\n🚀 Running Gender Inference Engine...")
        engine = GenderInferenceEngine()
        df, results = engine.process_dataframe(df)
        output_file = f"{output}_GENDER.xlsx"
        print(results['summary'])
    
    elif engine_num == 5:
        print("\n🚀 Running Data Cleaning Engine...")
        engine = DataCleaningEngine()
        df, results = engine.process_dataframe(df)
        output_file = f"{output}_CLEANED.xlsx"
        print(results['summary'])
    
    elif engine_num == 6:
        print("\n🚀 Running MGNREGA Validation Engine...")
        engine = MGNREGAValidationEngine()
        df, results = engine.process_dataframe(df)
        output_file = f"{output}_MGNREGA.xlsx"
        print(results['summary'])
    
    elif engine_num == 7:
        print("\n🚀 Running Date Validation Engine...")
        engine = DateValidationEngine()
        df, results = engine.process_dataframe(df, date_columns=['date_of_survey'], age_columns=['age'])
        output_file = f"{output}_DATES.xlsx"
        print(results['summary'])
    
    elif engine_num == 8:
        print("\n🚀 Running Land Validation Engine...")
        engine = LandValidationEngine()
        df, results = engine.process_dataframe(df)
        output_file = f"{output}_LAND.xlsx"
        print(results['summary'])
    
    elif engine_num == 9:
        print("\n🚀 Running ALL Engines...")
        orchestrator = MasterOrchestrator()
        results = orchestrator.process_file(input_file)
        print(f"\n✅ Complete! Output: {results['output_file']}")
        return
    
    # Save
    df.to_excel(output_file, index=False)
    print(f"\n✅ Saved: {output_file}")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        show_menu()
        print("\nUsage: python run_engine.py <input_file> [engine_number]")
        print("\nExamples:")
        print("  python scripts/run_engine.py data.xlsx 1     # Name formatting")
        print("  python scripts/run_engine.py data.xlsx 9     # All engines")
        return
    
    input_file = sys.argv[1]
    
    if not Path(input_file).exists():
        print(f"\n❌ Error: File not found: {input_file}")
        return
    
    if len(sys.argv) > 2:
        engine_num = int(sys.argv[2])
    else:
        show_menu()
        engine_num = int(input("\n👉 Select engine (1-9): "))
    
    run_single_engine(engine_num, input_file)


if __name__ == "__main__":
    main()