"""
Data Cleaning Engine v4.0
==========================
Better than Excel TRIM().

Excel TRIM() limitations:
- Only removes some spaces ❌
- Doesn't handle NaN/None ❌
- Doesn't normalize case ❌
- Can't clean multiple columns ❌

This engine:
- Removes ALL whitespace issues ✅
- Handles NaN/None/empty ✅
- Normalizes case ✅
- Cleans multiple columns instantly ✅
- Standardizes values ✅
"""

import pandas as pd
import numpy as np
import logging
import math
from typing import List, Dict, Tuple

log = logging.getLogger("brlf.data_cleaning_engine")


class DataCleaningEngine:
    """
    Specialized engine for data cleaning.
    Does ONE thing: Clean and normalize data (better than TRIM).
    """
    
    def __init__(self):
        self.stats = {
            "total_cells_processed": 0,
            "cells_cleaned": 0,
            "null_values_found": 0,
            "whitespace_fixed": 0,
            "case_normalized": 0,
        }
    
    def process_dataframe(
        self,
        df: pd.DataFrame,
        columns: List[str] = None,
        operations: List[str] = None,
        in_place: bool = False
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Process DataFrame - clean all specified columns.
        
        Args:
            df: Input DataFrame
            columns: List of columns to clean (None = all text columns)
            operations: List of operations: ['trim', 'normalize_case', 'remove_nulls']
                       (None = all operations)
            in_place: If True, modifies df directly
        
        Returns:
            (cleaned_dataframe, results_dict)
        
        Example:
            engine = DataCleaningEngine()
            df_clean, results = engine.process_dataframe(
                df,
                columns=['farmer_name', 'village'],
                operations=['trim', 'normalize_case']
            )
            print(f"Cleaned {results['stats']['cells_cleaned']} cells")
        """
        if not in_place:
            df = df.copy()
        
        # Default: clean all text columns
        if columns is None:
            columns = [col for col in df.columns if df[col].dtype == 'object']
        
        # Default: all operations
        if operations is None:
            operations = ['trim', 'normalize_case', 'handle_nulls']
        
        self._reset_stats()
        changes = []
        
        log.info(f"Cleaning {len(columns)} columns with operations: {operations}")
        
        for col in columns:
            if col not in df.columns:
                log.warning(f"Column '{col}' not found - skipping")
                continue
            
            col_changes = self._clean_column(df, col, operations)
            changes.extend(col_changes)
        
        log.info(
            f"Data Cleaning Complete: "
            f"{self.stats['cells_cleaned']:,} cells cleaned "
            f"out of {self.stats['total_cells_processed']:,} processed"
        )
        
        return df, {
            "stats": self.stats,
            "changes": changes,
            "summary": self._generate_summary()
        }
    
    def _clean_column(self, df: pd.DataFrame, column: str, operations: List[str]) -> List[Dict]:
        """Clean a single column."""
        changes = []
        
        for idx in df.index:
            original = df.at[idx, column]
            self.stats["total_cells_processed"] += 1
            
            cleaned = original
            change_types = []
            
            # Apply operations
            if 'handle_nulls' in operations:
                cleaned, is_null = self._handle_null(cleaned)
                if is_null:
                    self.stats["null_values_found"] += 1
                    change_types.append("null_handled")
            
            if 'trim' in operations and cleaned:
                cleaned, was_trimmed = self._trim(cleaned)
                if was_trimmed:
                    self.stats["whitespace_fixed"] += 1
                    change_types.append("trimmed")
            
            if 'normalize_case' in operations and cleaned:
                cleaned, was_normalized = self._normalize_case(cleaned)
                if was_normalized:
                    self.stats["case_normalized"] += 1
                    change_types.append("case_normalized")
            
            # If changed, update and log
            if str(cleaned) != str(original):
                df.at[idx, column] = cleaned
                self.stats["cells_cleaned"] += 1
                
                changes.append({
                    "row": idx + 2,
                    "column": column,
                    "original": original,
                    "cleaned": cleaned,
                    "operations": change_types
                })
        
        return changes
    
    def _handle_null(self, value) -> Tuple[str, bool]:
        """Handle None/NaN/empty values."""
        if value is None:
            return ("", True)
        if isinstance(value, float) and math.isnan(value):
            return ("", True)
        if isinstance(value, str) and value.strip() == "":
            return ("", True)
        return (value, False)
    
    def _trim(self, value) -> Tuple[str, bool]:
        """
        Better than Excel TRIM - removes ALL whitespace issues.
        Excel TRIM only removes leading/trailing spaces.
        This removes multiple spaces, tabs, newlines, etc.
        """
        if not isinstance(value, str):
            return (value, False)
        
        original = value
        
        # Remove leading/trailing whitespace
        cleaned = value.strip()
        
        # Replace multiple spaces with single space
        cleaned = " ".join(cleaned.split())
        
        # Remove tabs, newlines, etc.
        cleaned = cleaned.replace("\t", " ").replace("\n", " ").replace("\r", " ")
        cleaned = " ".join(cleaned.split())
        
        was_changed = (cleaned != original)
        
        return (cleaned, was_changed)
    
    def _normalize_case(self, value) -> Tuple[str, bool]:
        """Normalize to lowercase (for comparison/matching)."""
        if not isinstance(value, str):
            return (value, False)
        
        original = value
        normalized = value.lower()
        
        was_changed = (normalized != original)
        
        return (normalized, was_changed)
    
    def _reset_stats(self):
        """Reset statistics."""
        for key in self.stats:
            self.stats[key] = 0
    
    def _generate_summary(self) -> str:
        """Generate human-readable summary."""
        total = self.stats["total_cells_processed"]
        cleaned = self.stats["cells_cleaned"]
        
        clean_rate = (cleaned / total * 100) if total > 0 else 0
        
        summary = [
            f"Data Cleaning Summary:",
            f"",
            f"Total cells processed: {total:,}",
            f"Cells cleaned: {cleaned:,} ({clean_rate:.1f}%)",
            f"",
            f"Operations Applied:",
            f"  Null values handled: {self.stats['null_values_found']:,}",
            f"  Whitespace fixed: {self.stats['whitespace_fixed']:,}",
            f"  Case normalized: {self.stats['case_normalized']:,}",
        ]
        
        return "\n".join(summary)


# ============================================================================
# STANDALONE USAGE
# ============================================================================

def main():
    """Standalone usage example."""
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        
        print("=" * 70)
        print("DATA CLEANING ENGINE - Standalone Mode")
        print("=" * 70)
        print(f"\nInput: {input_file}")
        
        # Load
        df = pd.read_excel(input_file)
        print(f"Loaded {len(df):,} records")
        
        # Create engine
        engine = DataCleaningEngine()
        
        # Process (clean all text columns)
        df_clean, results = engine.process_dataframe(
            df,
            operations=['trim', 'handle_nulls']
        )
        
        # Show results
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(results["summary"])
        
        # Show sample changes
        if results["changes"]:
            print("\n" + "=" * 70)
            print("SAMPLE CHANGES (first 10)")
            print("=" * 70)
            for change in results["changes"][:10]:
                print(f"Row {change['row']}, Col '{change['column']}':")
                print(f"  Before: '{change['original']}'")
                print(f"  After:  '{change['cleaned']}'")
                print(f"  Ops: {', '.join(change['operations'])}\n")
        
        # Save
        output_file = input_file.replace(".xlsx", "_CLEANED.xlsx")
        df_clean.to_excel(output_file, index=False)
        print(f"✅ Saved: {output_file}")
    
    else:
        # Demo mode
        print("=" * 70)
        print("DATA CLEANING ENGINE - Demo Mode")
        print("=" * 70)
        
        # Sample data with various issues
        data = {
            "name": [
                "  Ramesh Kumar  ",      # Extra spaces
                "SUNITA DESHMUKH",       # All caps
                "vijay    patil",        # Multiple spaces + lowercase
                "  ",                     # Empty
                None,                     # Null
            ]
        }
        df = pd.DataFrame(data)
        
        print("\nOriginal data:")
        print(df)
        
        # Create engine
        engine = DataCleaningEngine()
        
        # Process
        df_clean, results = engine.process_dataframe(
            df,
            columns=['name'],
            operations=['trim', 'handle_nulls']
        )
        
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(results["summary"])
        
        print("\nCleaned data:")
        print(df_clean)
        
        print("\n✅ Engine ready for production use!")


if __name__ == "__main__":
    main()