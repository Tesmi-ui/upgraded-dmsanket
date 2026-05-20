#!/usr/bin/env python3
"""
Compare Outputs
===============
Compare results from intelligence_engine.py vs engines/
"""

import sys
from pathlib import Path
import pandas as pd


def compare_files(file1, file2):
    """Compare two Excel files."""
    print("\n" + "=" * 70)
    print("COMPARING FILES")
    print("=" * 70)
    
    df1 = pd.read_excel(file1)
    df2 = pd.read_excel(file2)
    
    print(f"\nFile 1: {Path(file1).name}")
    print(f"  Records: {len(df1):,}")
    print(f"  Columns: {len(df1.columns)}")
    
    print(f"\nFile 2: {Path(file2).name}")
    print(f"  Records: {len(df2):,}")
    print(f"  Columns: {len(df2.columns)}")
    
    print(f"\n📊 Difference:")
    print(f"  Records: {abs(len(df1) - len(df2)):,}")
    
    # Compare columns
    cols1 = set(df1.columns)
    cols2 = set(df2.columns)
    
    if cols1 == cols2:
        print(f"  Columns: ✅ Same")
    else:
        print(f"  Columns: ⚠️  Different")
        only_1 = cols1 - cols2
        only_2 = cols2 - cols1
        if only_1:
            print(f"    Only in File 1: {only_1}")
        if only_2:
            print(f"    Only in File 2: {only_2}")


def main():
    """Main function."""
    if len(sys.argv) < 3:
        print("Usage: python compare_outputs.py <file1> <file2>")
        print("\nExample:")
        print("  python scripts/compare_outputs.py old_output.xlsx new_output.xlsx")
        return
    
    compare_files(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()