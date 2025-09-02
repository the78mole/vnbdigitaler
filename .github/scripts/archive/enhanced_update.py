#!/usr/bin/env python3
"""
GitHub Actions Enhanced Update Script

This script runs the rollout updater with enhanced output parsing and JSON summary creation.
"""

import json
import re
import subprocess
import sys
from pathlib import Path


def run_update(force_update: bool = False) -> bool:
    """
    Run the rollout updater with enhanced output parsing.

    Args:
        force_update: Whether to force update even if no changes detected

    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        # Build command arguments
        cmd = [
            "uv",
            "run",
            "python",
            "src/bnetza/rollout_report_updater.py",
            "--verbose",
        ]

        if force_update:
            cmd.append("--force-update")

        # Run the updater with verbose output
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=".", check=False
        )

        output = result.stdout + result.stderr
        print(output)  # Show full output

        # Parse detailed summary information
        summary_data = extract_summary_from_output(output)

        # Save summary as JSON for GitHub Actions
        with Path("update_summary.json").open("w") as f:
            json.dump(summary_data, f, indent=2)

        # Also save to log
        with Path("update_output.log").open("w") as f:
            f.write(output)

        return result.returncode == 0

    except Exception as e:
        print(f"Error running update: {e}")
        return False


def extract_summary_from_output(output: str) -> dict:
    """Extract structured data from the detailed summary output."""
    summary = {
        "companies": {
            "total_processed": 0,
            "up_to_date": [],
            "updated": [],
            "new": [],
            "not_in_current": [],
        },
        "quotas": {
            "total_quotas": 0,
            "current_date": 0,
            "outdated_date": 0,
            "error_count": 0,
            "most_recent_date": "",
            "errors": [],
        },
    }

    lines = output.split("\n")

    # Parse the detailed summary section
    in_summary = False
    current_section = None

    for line in lines:
        stripped = line.strip()

        # Detect summary start
        if "DETAILED UPDATE SUMMARY" in stripped:
            in_summary = True
            continue

        if not in_summary:
            continue

        # End of summary
        if stripped.startswith("===") and in_summary and current_section:
            break

        # Parse company statistics
        if "Companies Processed:" in stripped:
            match = re.search(r"Companies Processed: (\d+)", stripped)
            if match:
                summary["companies"]["total_processed"] = int(match.group(1))

        elif "Up-to-date:" in stripped:
            match = re.search(r"Up-to-date: (\d+)", stripped)
            if match:
                summary["companies"]["up_to_date_count"] = int(match.group(1))

        elif "Updated:" in stripped:
            match = re.search(r"Updated: (\d+)", stripped)
            if match:
                summary["companies"]["updated_count"] = int(match.group(1))

        elif "New:" in stripped:
            match = re.search(r"New: (\d+)", stripped)
            if match:
                summary["companies"]["new_count"] = int(match.group(1))

        elif "Not in current report (not in update):" in stripped:
            match = re.search(
                r"Not in current report \(not in update\): (\d+)", stripped
            )
            if match:
                summary["companies"]["not_in_current_count"] = int(match.group(1))

        # Parse quota statistics
        elif "Quota Records:" in stripped:
            match = re.search(r"Quota Records: (\d+)", stripped)
            if match:
                summary["quotas"]["total_quotas"] = int(match.group(1))

        elif "Current Date" in stripped:
            match = re.search(r"Current Date \(([^)]+)\): (\d+)", stripped)
            if match:
                summary["quotas"]["most_recent_date"] = match.group(1)
                summary["quotas"]["current_date"] = int(match.group(2))

        elif "Outdated Date:" in stripped:
            match = re.search(r"Outdated Date: (\d+)", stripped)
            if match:
                summary["quotas"]["outdated_date"] = int(match.group(1))

        elif "Errors:" in stripped:
            match = re.search(r"Errors: (\d+)", stripped)
            if match:
                summary["quotas"]["error_count"] = int(match.group(1))

        # Track section changes for detailed lists
        elif "Updated Companies" in stripped:
            current_section = "updated_companies"
        elif "New Companies" in stripped:
            current_section = "new_companies"
        elif "Not in Current Report Companies" in stripped:
            current_section = "not_in_current_companies"
        elif "Quota Errors" in stripped:
            current_section = "quota_errors"

        # Parse company lists
        elif current_section and re.match(r"\s*\d+\.\s+(.+)", stripped):
            company_match = re.match(r"\s*\d+\.\s+(.+)", stripped)
            if company_match:
                company_name = company_match.group(1)
                if current_section == "updated_companies":
                    summary["companies"]["updated"].append(company_name)
                elif current_section == "new_companies":
                    summary["companies"]["new"].append(company_name)
                elif current_section == "not_in_current_companies":
                    summary["companies"]["not_in_current"].append(company_name)
                elif current_section == "quota_errors":
                    summary["quotas"]["errors"].append(company_name)

    return summary


def main():
    """Main entry point."""
    # Check for force update argument
    force_update = "--force-update" in sys.argv

    success = run_update(force_update)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
