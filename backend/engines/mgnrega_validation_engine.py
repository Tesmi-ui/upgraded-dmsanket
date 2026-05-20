"""
MGNREGA Validation Engine v4.0
===============================
Better than manual validation.

Excel limitations:
- Manual checking (slow, error-prone) ❌
- No format validation ❌
- No pattern matching ❌

This engine:
- Auto-validates MGNREGA card format ✅
- Pattern: MH-DD-BBB-GGG-NNN/NNNNNN ✅
- Flags invalid formats instantly ✅
- Handles 100K+ rows ✅
"""

import re
import pandas as pd
import logging
from typing import Tuple, Dict, List

log = logging.getLogger("brlf.mgnrega_validation_engine")


class MGNREGAValidationEngine:
    """
    Specialized engine for MGNREGA card validation.
    Does ONE thing: Validate MGNREGA card format.
    """
    
    def __init__(self):
        # MGNREGA format: MH-DD-BBB-GGG-NNN/NNNNNN
        # MH = Maharashtra
        # DD = District code (2 digits)
        # BBB = Block code (3 digits)
        # GGG = GP code (3 digits)
        # NNN/NNNNNN = Registration number
        self.pattern = r'^MH-\d{2}-\d{3}-\d{3}-\d{3}/\d{6}$'
        
        self.stats = {
            "total_processed": 0,
            "valid": 0,
            "invalid": 0,
            "blank": 0,
            "wrong_state": 0,
            "wrong_format": 0,
        }
    
    def process_dataframe(
        self,
        df: pd.DataFrame,
        column: str = "mgnrega",
        in_place: bool = False
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Process DataFrame - validate all MGNREGA cards.
        
        Args:
            df: Input DataFrame
            column: Column containing MGNREGA card numbers
            in_place: If True, modifies df directly
        
        Returns:
            (dataframe, results_dict)
        
        Example:
            engine = MGNREGAValidationEngine()
            df, results = engine.process_dataframe(df, "mgnrega")
            print(f"Valid: {results['stats']['valid']}")
            print(f"Invalid: {results['stats']['invalid']}")
        """
        if not in_place:
            df = df.copy()
        
        if column not in df.columns:
            log.error(f"Column '{column}' not found")
            return df, {"error": f"Column '{column}' not found"}
        
        self._reset_stats()
        issues = []
        
        log.info(f"Validating MGNREGA cards in column: {column}")
        
        for idx in df.index:
            card = df.at[idx, column]
            self.stats["total_processed"] += 1
            
            is_valid, reason, issue_type = self._validate_single(card)
            
            if not card or pd.isna(card) or str(card).strip() == "":
                self.stats["blank"] += 1
            elif is_valid:
                self.stats["valid"] += 1
            else:
                self.stats["invalid"] += 1
                
                # Track specific issue types
                if issue_type == "wrong_state":
                    self.stats["wrong_state"] += 1
                elif issue_type == "wrong_format":
                    self.stats["wrong_format"] += 1
                
                issues.append({
                    "row": idx + 2,
                    "card": card,
                    "issue": reason,
                    "expected_format": "MH-DD-BBB-GGG-NNN/NNNNNN"
                })
        
        log.info(
            f"MGNREGA Validation Complete: "
            f"{self.stats['valid']:,} valid, "
            f"{self.stats['invalid']:,} invalid"
        )
        
        return df, {
            "stats": self.stats,
            "issues": issues,
            "summary": self._generate_summary()
        }
    
    def _validate_single(self, card) -> Tuple[bool, str, str]:
        """
        Validate a single MGNREGA card.
        
        Returns:
            (is_valid, reason, issue_type)
        """
        if not card or pd.isna(card):
            return (True, "Blank (optional field)", None)
        
        card_str = str(card).strip().upper()
        
        # Check pattern
        if re.match(self.pattern, card_str):
            return (True, "Valid MGNREGA format", None)
        
        # Specific validations
        if not card_str.startswith("MH"):
            return (False, "Should start with 'MH' (Maharashtra)", "wrong_state")
        
        parts = card_str.split("-")
        if len(parts) != 5:
            return (False, f"Expected 5 parts separated by '-', got {len(parts)}", "wrong_format")
        
        # Check part lengths
        if len(parts) >= 2 and len(parts[1]) != 2:
            return (False, f"District code should be 2 digits, got {len(parts[1])}", "wrong_format")
        
        if len(parts) >= 3 and len(parts[2]) != 3:
            return (False, f"Block code should be 3 digits, got {len(parts[2])}", "wrong_format")
        
        return (False, "Invalid MGNREGA card format", "wrong_format")
    
    def _reset_stats(self):
        """Reset statistics."""
        for key in self.stats:
            self.stats[key] = 0
    
    def _generate_summary(self) -> str:
        """Generate human-readable summary."""
        total = self.stats["total_processed"]
        valid = self.stats["valid"]
        invalid = self.stats["invalid"]
        blank = self.stats["blank"]
        
        filled = total - blank
        valid_rate = (valid / filled * 100) if filled > 0 else 0
        
        summary = [
            f"MGNREGA Validation Summary:",
            f"",
            f"Total records: {total:,}",
            f"Blank: {blank:,}",
            f"Filled: {filled:,}",
            f"",
            f"Validation Results:",
            f"  Valid: {valid:,} ({valid_rate:.1f}%)",
            f"  Invalid: {invalid:,}",
            f"",
            f"Issue Breakdown:",
            f"  Wrong state code: {self.stats['wrong_state']:,}",
            f"  Wrong format: {self.stats['wrong_format']:,}",
            f"",
            f"Expected format: MH-DD-BBB-GGG-NNN/NNNNNN",
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
        print("MGNREGA VALIDATION ENGINE - Standalone Mode")
        print("=" * 70)
        print(f"\nInput: {input_file}")
        
        # Load
        df = pd.read_excel(input_file)
        print(f"Loaded {len(df):,} records")
        
        # Create engine
        engine = MGNREGAValidationEngine()
        
        # Process
        df, results = engine.process_dataframe(df, "mgnrega")
        
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
                print(f"Row {issue['row']}: '{issue['card']}'")
                print(f"  Issue: {issue['issue']}")
                print(f"  Expected: {issue['expected_format']}\n")
        
        print(f"\n✅ Validation complete")
    
    else:
        # Demo mode
        print("=" * 70)
        print("MGNREGA VALIDATION ENGINE - Demo Mode")
        print("=" * 70)
        
        test_cases = [
            "MH-12-345-678-901/234567",  # Valid
            "MH-12-345-678-901234567",   # Missing /
            "GJ-12-345-678-901/234567",  # Wrong state
            "MH-1-345-678-901/234567",   # District code wrong length
            "MH-12-34-678-901/234567",   # Block code wrong length
            "",                           # Blank
        ]
        
        engine = MGNREGAValidationEngine()
        
        print("\nTest Results:")
        print("-" * 70)
        for card in test_cases:
            is_valid, reason, issue_type = engine._validate_single(card)
            status = "✅ VALID" if is_valid else "❌ INVALID"
            print(f"{status}: '{card}'")
            print(f"         {reason}\n")
        
        print("✅ Engine ready for production use!")


if __name__ == "__main__":
    main()