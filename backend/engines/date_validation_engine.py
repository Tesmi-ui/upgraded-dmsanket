"""
Date Validation Engine v4.0
============================
Better than manual date checking.

Excel limitations:
- Manual date validation ❌
- No age range checking ❌
- No future date detection ❌

This engine:
- Auto-validates date formats ✅
- Age range validation (18-100) ✅
- Future date detection ✅
- Handles 100K+ rows instantly ✅
"""

import pandas as pd
import logging
from datetime import datetime
from typing import Tuple, Dict, List

log = logging.getLogger("brlf.date_validation_engine")


class DateValidationEngine:
    """
    Specialized engine for date and age validation.
    Does ONE thing: Validate dates and ages.
    """
    
    def __init__(self, min_age: int = 18, max_age: int = 100):
        self.min_age = min_age
        self.max_age = max_age
        
        self.stats = {
            "total_processed": 0,
            "valid": 0,
            "invalid": 0,
            "future_dates": 0,
            "below_min_age": 0,
            "above_max_age": 0,
            "invalid_format": 0,
        }
    
    def process_dataframe(
        self,
        df: pd.DataFrame,
        date_columns: List[str] = None,
        age_columns: List[str] = None,
        in_place: bool = False
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Process DataFrame - validate all date and age fields.
        
        Args:
            df: Input DataFrame
            date_columns: List of date columns to validate
            age_columns: List of age columns to validate
            in_place: If True, modifies df directly
        
        Returns:
            (dataframe, results_dict)
        
        Example:
            engine = DateValidationEngine(min_age=18, max_age=100)
            df, results = engine.process_dataframe(
                df,
                date_columns=['date_of_survey', 'SubmissionDate'],
                age_columns=['age']
            )
            print(f"Invalid: {results['stats']['invalid']}")
        """
        if not in_place:
            df = df.copy()
        
        self._reset_stats()
        issues = []
        
        # Validate date columns
        if date_columns:
            for col in date_columns:
                if col not in df.columns:
                    log.warning(f"Date column '{col}' not found - skipping")
                    continue
                
                log.info(f"Validating date column: {col}")
                col_issues = self._validate_date_column(df, col)
                issues.extend(col_issues)
        
        # Validate age columns
        if age_columns:
            for col in age_columns:
                if col not in df.columns:
                    log.warning(f"Age column '{col}' not found - skipping")
                    continue
                
                log.info(f"Validating age column: {col}")
                col_issues = self._validate_age_column(df, col)
                issues.extend(col_issues)
        
        log.info(
            f"Date Validation Complete: "
            f"{self.stats['valid']:,} valid, "
            f"{self.stats['invalid']:,} invalid"
        )
        
        return df, {
            "stats": self.stats,
            "issues": issues,
            "summary": self._generate_summary()
        }
    
    def _validate_date_column(self, df: pd.DataFrame, column: str) -> List[Dict]:
        """Validate a date column."""
        issues = []
        
        for idx in df.index:
            date_val = df.at[idx, column]
            self.stats["total_processed"] += 1
            
            is_valid, reason, issue_type = self._validate_date(date_val)
            
            if is_valid:
                self.stats["valid"] += 1
            else:
                self.stats["invalid"] += 1
                
                if issue_type == "future_date":
                    self.stats["future_dates"] += 1
                elif issue_type == "invalid_format":
                    self.stats["invalid_format"] += 1
                
                issues.append({
                    "row": idx + 2,
                    "column": column,
                    "value": date_val,
                    "issue": reason,
                    "issue_type": issue_type
                })
        
        return issues
    
    def _validate_age_column(self, df: pd.DataFrame, column: str) -> List[Dict]:
        """Validate an age column."""
        issues = []
        
        for idx in df.index:
            age_val = df.at[idx, column]
            self.stats["total_processed"] += 1
            
            is_valid, reason, issue_type = self._validate_age(age_val)
            
            if is_valid:
                self.stats["valid"] += 1
            else:
                self.stats["invalid"] += 1
                
                if issue_type == "below_min":
                    self.stats["below_min_age"] += 1
                elif issue_type == "above_max":
                    self.stats["above_max_age"] += 1
                elif issue_type == "invalid_format":
                    self.stats["invalid_format"] += 1
                
                issues.append({
                    "row": idx + 2,
                    "column": column,
                    "value": age_val,
                    "issue": reason,
                    "issue_type": issue_type
                })
        
        return issues
    
    def _validate_date(self, date_val) -> Tuple[bool, str, str]:
        """Validate a single date."""
        if pd.isna(date_val):
            return (True, "", None)
        
        try:
            date = pd.to_datetime(date_val, errors='coerce')
            
            if pd.isna(date):
                return (False, "Invalid date format", "invalid_format")
            
            # Check if future date
            if date > pd.Timestamp.now():
                return (False, "Date is in the future", "future_date")
            
            return (True, "Valid date", None)
        
        except Exception as e:
            return (False, f"Invalid date: {str(e)}", "invalid_format")
    
    def _validate_age(self, age_val) -> Tuple[bool, str, str]:
        """Validate a single age."""
        if pd.isna(age_val):
            return (True, "", None)
        
        try:
            age = float(age_val)
            
            if age < self.min_age:
                return (False, f"Below minimum age {self.min_age}", "below_min")
            
            if age > self.max_age:
                return (False, f"Above maximum age {self.max_age}", "above_max")
            
            return (True, "Valid age", None)
        
        except (ValueError, TypeError):
            return (False, "Non-numeric age value", "invalid_format")
    
    def _reset_stats(self):
        """Reset statistics."""
        for key in self.stats:
            self.stats[key] = 0
    
    def _generate_summary(self) -> str:
        """Generate human-readable summary."""
        total = self.stats["total_processed"]
        valid = self.stats["valid"]
        invalid = self.stats["invalid"]
        
        valid_rate = (valid / total * 100) if total > 0 else 0
        
        summary = [
            f"Date/Age Validation Summary:",
            f"",
            f"Total fields processed: {total:,}",
            f"Valid: {valid:,} ({valid_rate:.1f}%)",
            f"Invalid: {invalid:,}",
            f"",
            f"Issue Breakdown:",
            f"  Future dates: {self.stats['future_dates']:,}",
            f"  Below min age ({self.min_age}): {self.stats['below_min_age']:,}",
            f"  Above max age ({self.max_age}): {self.stats['above_max_age']:,}",
            f"  Invalid format: {self.stats['invalid_format']:,}",
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
        print("DATE VALIDATION ENGINE - Standalone Mode")
        print("=" * 70)
        print(f"\nInput: {input_file}")
        
        # Load
        df = pd.read_excel(input_file)
        print(f"Loaded {len(df):,} records")
        
        # Create engine
        engine = DateValidationEngine(min_age=18, max_age=100)
        
        # Process
        df, results = engine.process_dataframe(
            df,
            date_columns=['date_of_survey', 'SubmissionDate'],
            age_columns=['age']
        )
        
        # Show results
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(results["summary"])
        
        # Show sample issues
        if results["issues"]:
            print("\n" + "=" * 70)
            print("SAMPLE ISSUES (first 10)")
            print("=" * 70)
            for issue in results["issues"][:10]:
                print(f"Row {issue['row']}, Col '{issue['column']}':")
                print(f"  Value: {issue['value']}")
                print(f"  Issue: {issue['issue']}\n")
        
        print(f"\n✅ Validation complete")
    
    else:
        # Demo mode
        print("=" * 70)
        print("DATE VALIDATION ENGINE - Demo Mode")
        print("=" * 70)
        
        # Sample data
        data = {
            "date": [
                "2024-01-15",     # Valid
                "2030-01-15",     # Future
                "invalid",        # Invalid format
                None,             # Null
            ],
            "age": [
                25,               # Valid
                15,               # Below min
                105,              # Above max
                "abc",            # Invalid
            ]
        }
        df = pd.DataFrame(data)
        
        print("\nSample data:")
        print(df)
        
        # Create engine
        engine = DateValidationEngine(min_age=18, max_age=100)
        
        # Process
        df, results = engine.process_dataframe(
            df,
            date_columns=['date'],
            age_columns=['age']
        )
        
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(results["summary"])
        
        if results["issues"]:
            print("\nIssues found:")
            for issue in results["issues"]:
                print(f"  {issue['column']}: {issue['value']} - {issue['issue']}")
        
        print("\n✅ Engine ready for production use!")


if __name__ == "__main__":
    main()