#!/usr/bin/env python3
"""
GitHub Actions Format Companies Script

This script formats company lists for GitHub Actions summaries.
"""

import json
from pathlib import Path

# Constants for company display limits
MAX_COMPANIES_SHOW_ALL = 10
PREVIEW_COMPANIES_COUNT = 8
PREVIEW_LAST_COUNT = 2


def format_company_section(
    companies: list, title: str, emoji: str, description: str
) -> str:
    """
    Format a company section for GitHub summary.

    Args:
        companies: List of company names
        title: Section title
        emoji: Emoji for the section
        description: Description text

    Returns:
        str: Formatted markdown section
    """
    if not companies:
        return ""

    result = f"\n### {emoji} {title} ({len(companies)})\n"
    result += f"*{description}*\n\n"

    if len(companies) <= MAX_COMPANIES_SHOW_ALL:
        # Show all companies for small lists
        for i, company in enumerate(companies, 1):
            result += f"{i}. `{company}`\n"
    else:
        # Show first 8 and last 2 for large lists
        for i, company in enumerate(companies[:PREVIEW_COMPANIES_COUNT], 1):
            result += f"{i}. `{company}`\n"
        result += (
            f"... ({len(companies) - MAX_COMPANIES_SHOW_ALL} more companies) ...\n"
        )
        for i, company in enumerate(
            companies[-PREVIEW_LAST_COUNT:], len(companies) - 1
        ):
            result += f"{i}. `{company}`\n"

    return result


def main() -> None:
    """Main entry point."""
    try:
        with Path("update_summary.json").open("r") as f:
            summary = json.load(f)

        companies = summary.get("companies", {})
        quotas = summary.get("quotas", {})

        # Format company sections
        sections = []

        if companies.get("updated"):
            sections.append(
                format_company_section(
                    companies["updated"],
                    "Updated Companies",
                    "🔄",
                    "Companies with refreshed data from the current update",
                )
            )

        if companies.get("new"):
            sections.append(
                format_company_section(
                    companies["new"],
                    "New Companies",
                    "🆕",
                    "Companies added to the database for the first time",
                )
            )

        if companies.get("outdated"):
            sections.append(
                format_company_section(
                    companies["outdated"],
                    "Outdated Companies",
                    "⚠️",
                    "Companies in database but missing from current update",
                )
            )

        if quotas.get("errors"):
            sections.append(
                format_company_section(
                    quotas["errors"],
                    "Quota Validation Errors",
                    "❌",
                    "Companies with quota validation issues",
                )
            )

        # Print all sections
        for section in sections:
            print(section)

    except Exception as e:
        print(f"\n*Could not load detailed company information: {e}*\n")


if __name__ == "__main__":
    main()
