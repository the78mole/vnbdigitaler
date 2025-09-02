#!/usr/bin/env python3
"""
Format company matching results for GitHub Actions summary.

This script reads company_results.json and formats the results
for display in GitHub Actions workflow summaries.
"""

import json
import sys
from pathlib import Path

# Constants for display limits
MAX_MATCHED_DISPLAY = 5
MAX_UNMATCHED_DISPLAY = 3


def format_company_results(results_file: str = "company_results.json") -> None:
    """Format company results for workflow summary."""
    try:
        results_path = Path(results_file)
        if not results_path.exists():
            print("#### [i] No company results file found")
            return

        with results_path.open() as f:
            data = json.load(f)

        # Show some matched companies
        matched_companies = data.get("matched_companies", [])
        if matched_companies:
            print("#### ✅ Recently Matched Companies")
            for match in matched_companies[:MAX_MATCHED_DISPLAY]:
                bnetza_name = match.get("bnetza_name", "Unknown")
                bdew_name = match.get("bdew_name", "Unknown")
                match_score = match.get("match_score", "N/A")
                print(f"- **{bnetza_name}** → {bdew_name} (Score: {match_score})")

            if len(matched_companies) > MAX_MATCHED_DISPLAY:
                remaining = len(matched_companies) - MAX_MATCHED_DISPLAY
                print(f"- *... and {remaining} more matches*")
        else:
            print("#### [i] No new matches found in this run")

        # Show some unmatched companies
        unmatched_companies = data.get("unmatched_companies", [])
        if unmatched_companies:
            print("\n#### ❓ Sample Unmatched Companies")
            for company in unmatched_companies[:MAX_UNMATCHED_DISPLAY]:
                print(f"- {company}")

            if len(unmatched_companies) > MAX_UNMATCHED_DISPLAY:
                remaining = len(unmatched_companies) - MAX_UNMATCHED_DISPLAY
                print(f"- *... and {remaining} more unmatched*")

    except Exception as e:
        print(f"Could not load detailed results: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Allow optional command line argument for results file
    results_file = sys.argv[1] if len(sys.argv) > 1 else "company_results.json"
    format_company_results(results_file)
