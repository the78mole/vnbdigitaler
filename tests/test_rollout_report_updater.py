#!/usr/bin/env python3
"""Test script for RolloutReportUpdater class.

This script demonstrates the usage of the RolloutReportUpdater class.
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bnetza.rollout_report_updater import RolloutReportUpdater

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Test the RolloutReportUpdater functionality."""
    try:
        print("RolloutReportUpdater Test")
        print("=" * 50)

        # Initialize the updater
        print("\n1. Initializing RolloutReportUpdater...")
        updater = RolloutReportUpdater(download_dir="tmp")
        print(f"   ✅ Updater initialized: {updater}")

        # Check for new reports
        print("\n2. Checking for new reports...")
        has_new = updater.has_new_reports()
        print(f"   📊 New reports available: {has_new}")

        # Show current state
        print("\n3. Current state:")
        print(f"   Current report: {updater.current_report}")
        print(f"   ETag: {updater.etag}")
        print(f"   Local file: {updater.local_file_path}")
        print(f"   Report ID: {updater.report_id}")

        if has_new:
            # Discover and download workflow
            print("\n4. Running discover and download workflow...")
            success = updater.discover_and_download()

            if success:
                print("   ✅ Workflow completed successfully!")
                print(f"   📊 Final state: {updater}")
                print(f"   🏷️  ETag: {updater.etag}")
                print(f"   📁 Local file: {updater.local_file_path}")
                print(f"   🔄 File changed: {updater.file_changed}")
            else:
                print("   ❌ Workflow failed!")
        else:
            print("\n4. No new reports to process")

            # Show latest report info
            latest = updater.get_latest_report_info()
            if latest:
                print(
                    f"   📊 Latest report: {latest['filename']} (Q{latest['quarter']} {latest['year']})"
                )
                print(f"   📅 Discovery date: {latest['discovery_date']}")
            else:
                print("   No reports stored yet")

        print("\n🎉 Test completed!")

    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
