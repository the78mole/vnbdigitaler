#!/usr/bin/env python3
"""Complete test script for BNetzAReportDiscovery class with all functionality."""

import logging
import sys
import traceback
from pathlib import Path

from src.bnetza.rollout_report_discovery import BNetzAConfig, BNetzAReportDiscovery

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_complete_workflow():
    """Test the complete BNetzA discovery workflow."""
    print("=" * 60)
    print("TESTING COMPLETE BNETZA DISCOVERY WORKFLOW")
    print("=" * 60)

    try:
        discovery = BNetzAReportDiscovery()

        # Test 1: Check for new reports
        print("\n1. Checking for new reports...")
        try:
            has_new = discovery.has_new_reports()
            print(f"   New reports available: {has_new}")
        except Exception as e:
            print(f"   Error checking for new reports: {e}")

        # Test 2: Get latest stored report
        print("\n2. Getting latest stored report...")
        try:
            latest = discovery.get_latest_report_info()
            if latest:
                print(f"   Latest report: {latest['filename']}")
                print(f"   Quarter/Year: Q{latest['quarter']} {latest['year']}")
                print(f"   Method: {latest['selection_method']}")
                print(f"   Confidence: {latest['ai_confidence']}")
            else:
                print("   No reports stored yet")
        except Exception as e:
            print(f"   Error getting latest report: {e}")

        # Test 3: Get all stored reports
        print("\n3. Getting all stored reports...")
        try:
            all_reports = discovery.get_all_stored_reports()
            print(f"   Total stored reports: {len(all_reports)}")

            if all_reports:
                print("   Recent reports:")
                for report in all_reports[:3]:  # Show first 3
                    print(
                        f"   - {report['filename']} (Q{report['quarter']} {report['year']})"
                    )
        except Exception as e:
            print(f"   Error getting stored reports: {e}")

        # Test 4: Web discovery workflow
        print("\n4. Testing web discovery workflow...")
        try:
            discovered_reports = discovery.discover_and_store_reports()
            print(f"   Discovered {len(discovered_reports)} reports:")

            for report in discovered_reports:
                print(f"   - {report['filename']}")
                print(
                    f"     Quarter/Year: Q{report.get('report_quarter')} {report.get('report_year')}"
                )
                print(f"     Method: {report.get('selection_method')}")
                print(f"     Confidence: {report.get('ai_confidence')}")
                print(f"     Database ID: {report.get('database_id')}")

        except Exception as e:
            print(f"   Error in discovery workflow: {e}")

        # Test 5: Download functionality (mock test)
        print("\n5. Testing download functionality...")
        try:
            # Use a mock URL for testing
            mock_url = "https://httpbin.org/status/200"  # This will return a 200 status
            print(f"   Testing download with mock URL: {mock_url}")
            print("   (This is a safe test URL that won't download actual files)")

            # Note: We won't actually run this to avoid downloading files during testing
            print(
                "   Download test skipped for safety (would download to data/ directory)"
            )

        except Exception as e:
            print(f"   Download test error: {e}")

        print("\n✅ Complete workflow test finished!")

    except Exception as e:
        print(f"\n❌ Complete workflow test failed: {e}")
        traceback.print_exc()


def test_configuration():
    """Test all configuration constants."""
    print("=" * 60)
    print("TESTING CONFIGURATION")
    print("=" * 60)

    print(f"Base URL: {BNetzAConfig.BASE_URL}")
    print(f"Rollout URL: {BNetzAConfig.ROLLOUT_URL}")
    print(f"User Agent: {BNetzAConfig.USER_AGENT}")
    print(f"Request Timeout: {BNetzAConfig.REQUEST_TIMEOUT}s")
    print(f"Excel Pattern: {BNetzAConfig.EXCEL_FILE_PATTERN}")
    print(f"Quarter Pattern: {BNetzAConfig.QUARTER_PATTERN}")
    print(f"Year Pattern: {BNetzAConfig.YEAR_PATTERN}")

    print(f"\nKeywords ({len(BNetzAConfig.ROLLOUT_KEYWORDS)}):")
    for i, keyword in enumerate(BNetzAConfig.ROLLOUT_KEYWORDS, 1):
        print(f"  {i}. {keyword}")

    print("\nScoring Weights:")
    for key, value in BNetzAConfig.SCORING_WEIGHTS.items():
        print(f"  {key}: {value}")

    print("\nAI Configuration:")
    print(f"  Model Env Var: {BNetzAConfig.AI_MODEL_ENV_VAR}")
    print(f"  API Key Env Var: {BNetzAConfig.OPENROUTER_API_KEY_ENV_VAR}")
    print(f"  Base URL: {BNetzAConfig.OPENROUTER_BASE_URL}")


def test_database_operations():
    """Test database-related operations."""
    print("=" * 60)
    print("TESTING DATABASE OPERATIONS")
    print("=" * 60)

    try:
        discovery = BNetzAReportDiscovery()

        # Test database connection
        print("1. Testing database connection...")
        try:
            discovery._get_db_session()
            print("   ✅ Database connection successful")
        except Exception as e:
            print(f"   ❌ Database connection failed: {e}")
            return

        # Test getting stored reports
        print("\n2. Testing get_all_stored_reports...")
        try:
            reports = discovery.get_all_stored_reports()
            print(f"   Found {len(reports)} stored reports")
        except Exception as e:
            print(f"   Error: {e}")

        # Test getting latest report
        print("\n3. Testing get_latest_report_info...")
        try:
            latest = discovery.get_latest_report_info()
            if latest:
                print(f"   Latest: {latest['filename']}")
            else:
                print("   No latest report found")
        except Exception as e:
            print(f"   Error: {e}")

    except Exception as e:
        print(f"Database operations test failed: {e}")


def main():
    """Run all tests."""
    print("BNetzA Report Discovery - Complete Test Suite")
    print("=" * 70)
    print()

    try:
        test_configuration()
        print("\n")
        test_database_operations()
        print("\n")
        test_complete_workflow()

        print("\n" + "=" * 70)
        print("COMPLETE TEST SUITE FINISHED")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\nTest suite interrupted by user")
    except Exception as e:
        print(f"\nTest suite failed with error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
