#!/usr/bin/env python3
"""Test script for BNetzAReportDiscovery class."""

import logging
import re
import sys
import traceback
from pathlib import Path

from src.bnetza.rollout_report_discovery import BNetzAConfig, BNetzAReportDiscovery

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Constants
MAX_DISPLAY_FILES = 5

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_config():
    """Test BNetzAConfig constants."""
    print("=" * 60)
    print("TESTING BNETZA CONFIG")
    print("=" * 60)

    print(f"Base URL: {BNetzAConfig.BASE_URL}")
    print(f"Rollout URL: {BNetzAConfig.ROLLOUT_URL}")
    print(f"User Agent: {BNetzAConfig.USER_AGENT}")
    print(f"Request Timeout: {BNetzAConfig.REQUEST_TIMEOUT}s")
    print(f"Excel Pattern: {BNetzAConfig.EXCEL_FILE_PATTERN}")
    print(f"Quarter Pattern: {BNetzAConfig.QUARTER_PATTERN}")
    print(f"Year Pattern: {BNetzAConfig.YEAR_PATTERN}")
    print(f"Number of Keywords: {len(BNetzAConfig.ROLLOUT_KEYWORDS)}")
    print(f"Keywords: {', '.join(BNetzAConfig.ROLLOUT_KEYWORDS)}")
    print(f"Scoring Weights: {BNetzAConfig.SCORING_WEIGHTS}")
    print()


def test_quarter_year_extraction():
    """Test quarter and year extraction functionality."""
    print("=" * 60)
    print("TESTING QUARTER/YEAR EXTRACTION")
    print("=" * 60)

    # Initialize discovery service (this might fail if DB not available)
    try:
        discovery = BNetzAReportDiscovery()

        # Test cases for quarter/year extraction
        test_cases = [
            {
                "filename": "Roll-out-Quoten_Q1_2025.xlsx",
                "text": "Smart Meter Rollout Q1 2025",
            },
            {"filename": "rollout_data_2024_Q4.xlsx", "text": "Quarterly report"},
            {
                "filename": "smart_meter_Q2_2025.xlsx",
                "text": "BNetzA rollout statistics",
            },
            {"filename": "no_quarter_info.xlsx", "text": "Some other report"},
            {"filename": "Roll-out-Quoten_Q3_2024.xlsx", "text": ""},
        ]

        for i, test_case in enumerate(test_cases, 1):
            quarter, year = discovery.extract_quarter_year(dict(test_case))
            print(f"Test {i}: {test_case['filename']}")
            print(f"  Result: Q{quarter} {year}")
            print()

    except Exception as e:
        print(f"Could not initialize BNetzAReportDiscovery: {e}")
        # Test regex patterns directly
        test_strings = [
            "Roll-out-Quoten_Q1_2025.xlsx Smart Meter Rollout Q1 2025",
            "rollout_data_2024_Q4.xlsx Quarterly report",
            "smart_meter_Q2_2025.xlsx BNetzA rollout statistics",
            "no_quarter_info.xlsx Some other report",
            "Roll-out-Quoten_Q3_2024.xlsx",
        ]

        for i, test_string in enumerate(test_strings, 1):
            quarter_match = re.search(
                BNetzAConfig.QUARTER_PATTERN, test_string, re.IGNORECASE
            )
            year_match = re.search(BNetzAConfig.YEAR_PATTERN, test_string)

            quarter = int(quarter_match.group(1)) if quarter_match else None
            year = int(f"20{year_match.group(1)}") if year_match else None

            print(f"Test {i}: {test_string}")
            print(f"  Result: Q{quarter} {year}")
            print()


def test_rollout_filtering():
    """Test rollout report filtering."""
    print("=" * 60)
    print("TESTING ROLLOUT REPORT FILTERING")
    print("=" * 60)

    # Mock Excel files data
    mock_excel_files = [
        {
            "filename": "Roll-out-Quoten_Q1_2025.xlsx",
            "text": "Smart Meter Rollout Q1 2025",
            "url": "https://example.com/rollout.xlsx",
        },
        {
            "filename": "energy_statistics_2025.xlsx",
            "text": "Annual energy statistics",
            "url": "https://example.com/energy.xlsx",
        },
        {
            "filename": "messstellenbetrieb_data.xlsx",
            "text": "MSB operator data",
            "url": "https://example.com/msb.xlsx",
        },
        {
            "filename": "unrelated_report.xlsx",
            "text": "Some unrelated report",
            "url": "https://example.com/other.xlsx",
        },
        {
            "filename": "smart_meter_installations.xlsx",
            "text": "Installation statistics",
            "url": "https://example.com/smart.xlsx",
        },
    ]

    try:
        discovery = BNetzAReportDiscovery()

        print("Input files:")
        for i, file_info in enumerate(mock_excel_files, 1):
            print(f"  {i}. {file_info['filename']} - {file_info['text']}")
        print()

        filtered_reports = discovery.filter_rollout_reports(mock_excel_files)

        print("Filtered rollout reports:")
        for i, report in enumerate(filtered_reports, 1):
            print(f"  {i}. {report['filename']} - {report['text']}")
        print()

        print(
            f"Found {len(filtered_reports)} out of {len(mock_excel_files)} potential rollout reports"
        )

    except Exception as e:
        print(f"Could not initialize BNetzAReportDiscovery: {e}")
        print("Manual keyword matching test...")

        for file_info in mock_excel_files:
            filename = file_info["filename"].lower()
            text = file_info["text"].lower()

            contains_keywords = any(
                keyword in filename or keyword in text
                for keyword in BNetzAConfig.ROLLOUT_KEYWORDS
            )

            status = "✓ MATCH" if contains_keywords else "✗ NO MATCH"
            print(f"  {status}: {file_info['filename']}")


def test_web_fetch():
    """Test web page fetching (if network available)."""
    print("=" * 60)
    print("TESTING WEB PAGE FETCHING")
    print("=" * 60)

    try:
        discovery = BNetzAReportDiscovery()

        print(f"Attempting to fetch: {BNetzAConfig.ROLLOUT_URL}")
        html_content = discovery.fetch_article_page()

        print(f"Successfully fetched {len(html_content)} characters")
        print(f"First 200 characters: {html_content[:200]}...")
        print()

        # Test Excel URL extraction
        excel_files = discovery.extract_excel_urls(html_content)
        print(f"Found {len(excel_files)} Excel files:")

        for i, excel_file in enumerate(
            excel_files[:MAX_DISPLAY_FILES], 1
        ):  # Show first 5
            print(f"  {i}. {excel_file['filename']} - {excel_file['text'][:50]}...")

        if len(excel_files) > MAX_DISPLAY_FILES:
            print(f"  ... and {len(excel_files) - MAX_DISPLAY_FILES} more")

    except Exception as e:
        print(f"Web fetch test failed: {e}")
        print(
            "This is expected if no internet connection or database is not configured"
        )


def test_ai_classification():
    """Test AI classification functionality."""
    print("=" * 60)
    print("TESTING AI CLASSIFICATION")
    print("=" * 60)

    # Mock Excel files data with multiple potential rollout reports
    mock_excel_files = [
        {
            "filename": "Roll-out-Quoten_Q4_2024.xlsx",
            "text": "Q4 2024 Smart Meter Rollout",
            "url": "https://example.com/q4_2024.xlsx",
        },
        {
            "filename": "Roll-out-Quoten_Q1_2025.xlsx",
            "text": "Q1 2025 Smart Meter Rollout",
            "url": "https://example.com/q1_2025.xlsx",
        },
        {
            "filename": "energy_statistics_2025.xlsx",
            "text": "Annual energy statistics",
            "url": "https://example.com/energy.xlsx",
        },
        {
            "filename": "messstellenbetrieb_Q3_2024.xlsx",
            "text": "Q3 2024 MSB operator data",
            "url": "https://example.com/msb.xlsx",
        },
    ]

    try:
        discovery = BNetzAReportDiscovery()

        print("Input files for AI classification:")
        for i, file_info in enumerate(mock_excel_files, 1):
            print(f"  {i}. {file_info['filename']} - {file_info['text']}")
        print()

        # Test AI classification
        print("Testing AI classification...")
        try:
            ai_result = discovery.classify_reports_with_ai(mock_excel_files)

            print("AI Classification Result:")
            print(f"  Selected Index: {ai_result['selected_index']}")
            selected_idx = ai_result["selected_index"]
            if isinstance(selected_idx, int):
                print(f"  Selected File: {mock_excel_files[selected_idx]['filename']}")
            else:
                print(f"  Selected Index: {selected_idx} (invalid)")
            print(f"  Quarter: {ai_result['quarter']}")
            print(f"  Year: {ai_result['year']}")
            print(f"  Confidence: {ai_result['confidence']}")
            print(f"  Reasoning: {ai_result['reasoning']}")
            print(f"  Model: {ai_result['ai_model']}")
            print()

        except Exception as e:
            print(
                f"AI classification failed (this is OK if no API key configured): {e}"
            )
            print("Testing fallback to heuristics...")

            # Test the combined method with fallback
            selected_report = discovery.classify_reports_with_ai_or_heuristics(
                mock_excel_files
            )

            if selected_report:
                print("Heuristic Classification Result:")
                print(f"  Selected File: {selected_report['filename']}")
                print(f"  Quarter: {selected_report.get('report_quarter', 'N/A')}")
                print(f"  Year: {selected_report.get('report_year', 'N/A')}")
                print(f"  Method: {selected_report.get('selection_method', 'N/A')}")
                print(f"  Confidence: {selected_report.get('ai_confidence', 'N/A')}")
            else:
                print("No report selected by heuristics")

    except Exception as e:
        print(f"Could not initialize BNetzAReportDiscovery: {e}")
        print("This is expected if database is not configured")


def main():
    """Run all tests."""
    print("BNetzA Report Discovery - Test Suite")
    print("====================================")
    print()

    try:
        test_config()
        test_quarter_year_extraction()
        test_rollout_filtering()
        test_ai_classification()  # Add AI classification test
        test_web_fetch()

        print("=" * 60)
        print("TEST SUITE COMPLETED")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\nTest suite interrupted by user")
    except Exception as e:
        print(f"\nTest suite failed with error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
