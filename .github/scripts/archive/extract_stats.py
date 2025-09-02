#!/usr/bin/env python3
"""
GitHub Actions Extract Statistics Script

This script extracts statistics from the JSON summary and sets GitHub Actions outputs.
"""

import json
import os
import re
from pathlib import Path


def extract_statistics() -> None:
    """Extract statistics from JSON summary and set GitHub Actions outputs."""
    try:
        # Try to load from JSON summary first
        if Path("update_summary.json").exists():
            extract_from_json()
        else:
            print("❌ No summary JSON found, using fallback method...")
            extract_from_log()

    except Exception as e:
        print(f"Error extracting statistics: {e}")
        set_default_outputs()


def extract_from_json() -> None:
    """Extract statistics from the JSON summary."""
    print("📊 Extracting statistics from detailed summary...")

    with Path("update_summary.json").open("r") as f:
        summary = json.load(f)

    companies = summary.get("companies", {})
    quotas = summary.get("quotas", {})

    # Extract company statistics
    total_processed = companies.get("total_processed", 0)
    up_to_date_count = companies.get(
        "up_to_date_count", len(companies.get("up_to_date", []))
    )
    updated_count = companies.get("updated_count", len(companies.get("updated", [])))
    new_count = companies.get("new_count", len(companies.get("new", [])))
    not_in_current_count = companies.get(
        "not_in_current_count", len(companies.get("not_in_current", []))
    )

    # Extract quota statistics
    total_quotas = quotas.get("total_quotas", 0)
    current_date_count = quotas.get("current_date", 0)
    outdated_date_count = quotas.get("outdated_date", 0)
    error_count = quotas.get("error_count", 0)
    most_recent_date = quotas.get("most_recent_date", "Unknown")

    # Set GitHub Actions outputs
    set_github_outputs(
        companies_processed=total_processed,
        companies_up_to_date=up_to_date_count,
        companies_updated=updated_count,
        companies_new=new_count,
        companies_not_in_current=not_in_current_count,
        quotas_total=total_quotas,
        quotas_current_date=current_date_count,
        quotas_outdated_date=outdated_date_count,
        quotas_errors=error_count,
        quotas_reference_date=most_recent_date,
    )

    # Print summary for logs
    print("📊 Extracted Statistics:")
    print(
        f"   Companies: {total_processed} total ({up_to_date_count} up-to-date, {updated_count} updated, {new_count} new, {not_in_current_count} not in current report)"
    )
    print(
        f"   Quotas: {total_quotas} total ({current_date_count} current date, {outdated_date_count} outdated date, {error_count} errors)"
    )
    print(f"   Reference Date: {most_recent_date}")


def extract_from_log() -> None:
    """Fallback to parsing the log file if JSON is not available."""
    companies = 0
    try:
        if Path("update_output.log").exists():
            with Path("update_output.log").open("r") as f:
                content = f.read()

            # Try to extract from various log patterns
            # Look for import messages
            match = re.search(r"Imported (\d+) company quota records", content)
            if match:
                companies = int(match.group(1))

            # Look for processed messages
            if companies == 0:
                match = re.search(r"Companies Processed: (\d+)", content)
                if match:
                    companies = int(match.group(1))

        set_github_outputs(
            companies_processed=companies,
            companies_up_to_date=0,
            companies_updated=0,
            companies_new=0,
            companies_not_in_current=0,
            quotas_total=companies,
            quotas_current_date=0,
            quotas_outdated_date=0,
            quotas_errors=0,
            quotas_reference_date="Unknown",
        )

        print(f"📊 Fallback extraction: {companies} companies processed")

    except Exception as e:
        print(f"Error in fallback extraction: {e}")
        set_default_outputs()


def set_default_outputs() -> None:
    """Set default outputs when extraction fails."""
    set_github_outputs(
        companies_processed=0,
        companies_up_to_date=0,
        companies_updated=0,
        companies_new=0,
        companies_not_in_current=0,
        quotas_total=0,
        quotas_current_date=0,
        quotas_outdated_date=0,
        quotas_errors=0,
        quotas_reference_date="Unknown",
    )


def set_github_outputs(**kwargs) -> None:
    """Set GitHub Actions outputs."""
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with Path(github_output).open("a") as f:
            for key, value in kwargs.items():
                f.write(f"{key}={value}\n")


def main() -> None:
    """Main entry point."""
    extract_statistics()


if __name__ == "__main__":
    main()
