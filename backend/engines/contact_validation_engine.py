"""
Contact Validation Engine v4.0
===============================
Better than Excel manual validation.

Excel limitations:
- Manual checking (slow, error-prone) ❌
- Can't auto-correct formats ❌
- Can't extract from messy input ❌
- No validation rules ❌

This engine:
- Auto-validates Indian mobile format (10 digits, starts 6/7/8/9) ✅
- Auto-corrects +91, 91, 0 prefixes ✅
- Extracts valid numbers from messy input ✅
- Handles 100K+ rows instantly ✅
- Flags invalid numbers for review ✅
"""

import re
import pandas as pd
import logging
from typing import List, Dict, Tuple

log = logging.getLogger("brlf.contact_validation_engine")


class ContactValidationEngine:
    """
    Specialized engine for contact number validation.
    Does ONE thing: Validate and correct Indian mobile numbers.
    """
    
    def __init__(self):
        self.valid_starts = {'6', '7', '8', '9'}
        self.stats = {
            "total_processed": 0,
            "valid": 0,
            "corrected": 0,
            "invalid": 0,
            "blank": 0,
        }
    
    def process_dataframe(
        self,
        df: pd.DataFrame,
        column: str = "contact_number",
        in_place: bool = False
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Process entire DataFrame - validate all contact numbers.
        
        Args:
            df: Input DataFrame
            column: Column name containing contact numbers
            in_place: If True, modifies df directly; if False, returns copy
        
        Returns:
            (validated_dataframe, results_dict)
        
        Example:
            engine = ContactValidationEngine()
            df_clean, results = engine.process_dataframe(df, "contact_number")
            print(f"Corrected {results['stats']['corrected']} contacts")
            print(f"Invalid: {results['stats']['invalid']}")
        """
        if not in_place:
            df = df.copy()
        
        if column not in df.columns:
            log.error(f"Column '{column}' not found")
            return df, {"error": f"Column '{column}' not found"}
        
        self._reset_stats()
        corrections = []
        issues = []
        
        log.info(f"Validating contact numbers in column: {column}")
        
        for idx in df.index:
            original = df.at[idx, column]
            self.stats["total_processed"] += 1
            
            corrected, is_valid, reason = self._validate_single(original)
            
            # Categorize
            if not original or pd.isna(original) or str(original).strip() == "":
                self.stats["blank"] += 1
            elif is_valid:
                self.stats["valid"] += 1
                
                # If corrected, apply and log
                if corrected != str(original).strip():
                    df.at[idx, column] = corrected
                    self.stats["corrected"] += 1
                    corrections.append({
                        "row": idx + 2,
                        "original": original,
                        "corrected": corrected,
                        "reason": reason
                    })
            else:
                self.stats["invalid"] += 1
                issues.append({
                    "row": idx + 2,
                    "original": original,
                    "extracted": corrected,
                    "issue": reason
                })
        
        log.info(
            f"Contact Validation Complete: "
            f"{self.stats['valid']:,} valid, "
            f"{self.stats['corrected']:,} corrected, "
            f"{self.stats['invalid']:,} invalid"
        )
        
        return df, {
            "stats": self.stats,
            "corrections": corrections,
            "issues": issues,
            "summary": self._generate_summary()
        }
    
    def _validate_single(self, number) -> Tuple[str, bool, str]:
        """
        Validate a single contact number.
        
        Returns:
            (corrected_number, is_valid, reason)
        """
        if not number or pd.isna(number):
            return ("", False, "Blank contact number")
        
        num_str = str(number).strip()
        
        if not num_str:
            return ("", False, "Empty after trim")
        
        # Step 1: Remove prefixes (+91, 91, 0)
        cleaned = self._remove_prefixes(num_str)
        
        # Step 2: Extract only digits
        digits_only = re.sub(r'\D', '', cleaned)
        
        # Step 3: Validate
        return self._validate_digits(digits_only, num_str)
    
    def _remove_prefixes(self, number: str) -> str:
        """Remove common Indian mobile prefixes."""
        # Remove +91
        number = re.sub(r'^\+91', '', number)
        # Remove 91
        number = re.sub(r'^91', '', number)
        # Remove leading zeros
        number = re.sub(r'^0+', '', number)
        return number.strip()
    
    def _validate_digits(self, digits: str, original: str) -> Tuple[str, bool, str]:
        """Validate digit count and starting digit."""
        # Exactly 10 digits
        if len(digits) == 10:
            if digits[0] in self.valid_starts:
                if digits == original:
                    return (digits, True, "Valid mobile number")
                else:
                    return (digits, True, f"Corrected from: {original}")
            else:
                return (digits, False, f"Must start with 6/7/8/9 (starts with {digits[0]})")
        
        # Too short
        elif len(digits) < 10:
            return (digits, False, f"Too short: {len(digits)} digits (need 10)")
        
        # Too long - try to extract valid 10 digits
        elif len(digits) > 10:
            # Try last 10 digits
            last_10 = digits[-10:]
            if last_10[0] in self.valid_starts:
                return (last_10, True, f"Extracted last 10 digits from {len(digits)}-digit number")
            
            # Try first 10 digits
            first_10 = digits[:10]
            if first_10[0] in self.valid_starts:
                return (first_10, True, f"Extracted first 10 digits from {len(digits)}-digit number")
            
            return (digits, False, f"Too long: {len(digits)} digits, couldn't extract valid 10-digit number")
        
        return (digits, False, "Invalid format")
    
    def _reset_stats(self):
        """Reset statistics."""
        for key in self.stats:
            self.stats[key] = 0
    
    def _generate_summary(self) -> str:
        """Generate human-readable summary."""
        total = self.stats["total_processed"]
        valid = self.stats["valid"]
        corrected = self.stats["corrected"]
        invalid = self.stats["invalid"]
        blank = self.stats["blank"]
        
        filled = total - blank
        valid_rate = (valid / filled * 100) if filled > 0 else 0
        
        summary = [
            f"Processed {total:,} contact numbers",
            f"  Blank: {blank:,}",
            f"  Filled: {filled:,}",
            f"",
            f"Validation Results:",
            f"  Valid: {valid:,} ({valid_rate:.1f}%)",
            f"  Corrected: {corrected:,}",
            f"  Invalid: {invalid:,}",
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
        print("CONTACT VALIDATION ENGINE - Standalone Mode")
        print("=" * 70)
        print(f"\nInput: {input_file}")
        
        # Load
        df = pd.read_excel(input_file)
        print(f"Loaded {len(df):,} records")
        
        # Create engine
        engine = ContactValidationEngine()
        
        # Process
        df_validated, results = engine.process_dataframe(df, "contact_number")
        
        # Show results
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(results["summary"])
        
        # Save
        output_file = input_file.replace(".xlsx", "_CONTACTS_VALIDATED.xlsx")
        df_validated.to_excel(output_file, index=False)
        print(f"\n✅ Saved: {output_file}")
        
        # Show sample corrections
        if results["corrections"]:
            print("\n" + "=" * 70)
            print("SAMPLE CORRECTIONS (first 10)")
            print("=" * 70)
            for corr in results["corrections"][:10]:
                print(f"Row {corr['row']}: '{corr['original']}' → '{corr['corrected']}'")
        
        # Show sample issues
        if results["issues"]:
            print("\n" + "=" * 70)
            print("SAMPLE ISSUES (first 10)")
            print("=" * 70)
            for issue in results["issues"][:10]:
                print(f"Row {issue['row']}: '{issue['original']}' - {issue['issue']}")
    
    else:
        # Demo mode
        print("=" * 70)
        print("CONTACT VALIDATION ENGINE - Demo Mode")
        print("=" * 70)
        
        test_cases = [
            "9876543210",           # Valid
            "+91 9876543210",       # With country code
            "91-9876543210",        # With prefix and dash
            "09876543210",          # With leading 0
            "98765 43210",          # With space
            "5876543210",           # Invalid start
            "987654321",            # Too short
            "98765432109",          # Too long
            "919876543210",         # 12 digits
            "",                     # Blank
        ]
        
        engine = ContactValidationEngine()
        
        print("\nTest Results:")
        print("-" * 70)
        for number in test_cases:
            corrected, is_valid, reason = engine._validate_single(number)
            status = "✅ VALID" if is_valid else "❌ INVALID"
            print(f"{status}: '{number}' → '{corrected}'")
            print(f"         {reason}\n")
        
        print("✅ Engine ready for production use!")


if __name__ == "__main__":
    main()