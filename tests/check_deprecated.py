#!/usr/bin/env python3
"""
Test File Protection Script

This script prevents recreation of deprecated BDEW test files
that were removed during the test cleanup process.

Deprecated files:
- test_bdew_simple.py
- test_bdew_working.py
- test_bdew_integration_full.py
- test_bdew_repository_complete.py

All BDEW functionality is covered in test_bdew_integration.py
"""

import os
import sys
from pathlib import Path

DEPRECATED_FILES = [
    "test_bdew_simple.py",
    "test_bdew_working.py",
    "test_bdew_integration_full.py",
    "test_bdew_repository_complete.py",
]


def check_for_deprecated_files():
    """Check if any deprecated test files exist."""
    tests_dir = Path(__file__).parent
    found_deprecated = []

    for file_name in DEPRECATED_FILES:
        file_path = tests_dir / file_name
        if file_path.exists():
            found_deprecated.append(file_name)

    return found_deprecated


def main():
    """Main protection check."""
    deprecated_found = check_for_deprecated_files()

    if deprecated_found:
        print("⚠️  DEPRECATED TEST FILES DETECTED:")
        for file_name in deprecated_found:
            print(f"   - {file_name}")
        print()
        print(
            "These files should be removed. All BDEW tests are in test_bdew_integration.py"
        )
        print(
            "Run: rm tests/test_bdew_simple.py tests/test_bdew_working.py tests/test_bdew_integration_full.py tests/test_bdew_repository_complete.py"
        )
        return 1

    print("✅ Test directory is clean - no deprecated files found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
