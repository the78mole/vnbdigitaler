#!/usr/bin/env python3
"""
Neon PostgreSQL Integration Test

This script tests the complete Neon database integration including:
- Connection testing
- Table creation and management
- CRUD operations for Roll-Out reports
- Session tracking
- Repository layer functionality
"""

import argparse
import asyncio
import sys
import traceback
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import get_db_manager  # noqa: E402
from repository import get_repository  # noqa: E402


async def test_connection():
    """Test basic database connection."""
    print("🔗 Testing Neon database connection...")

    try:
        db_manager = get_db_manager()

        if await db_manager.test_connection():
            print("✅ Database connection successful!")
            return True
        else:
            print("❌ Database connection failed!")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


async def create_tables():
    """Create database tables."""
    print("📋 Creating database tables...")

    try:
        db_manager = get_db_manager()
        await db_manager.create_tables()
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False


async def test_repository_operations():
    """Test repository operations with sample data."""
    print("🧪 Testing repository operations...")

    try:
        async for repo in get_repository():
            # Test saving a download session
            print("  📦 Saving download session...")
            download_session = await repo.save_download_session(
                session_id="test_session_001",
                temp_directory="/tmp/test_download",  # nosec B108
                total_urls_found=10,
                excel_urls_found=4,
                user_agent="test-agent/1.0",
                script_version="1.0.0",
                metadata={"test": True, "source": "integration_test"},
                status="completed",
            )
            print(f"    ✅ Download session saved with ID: {download_session.id}")

            # Test saving a Roll-Out report
            print("  📊 Saving Roll-Out report...")
            report = await repo.save_roll_out_report(
                filename="Roll-out-Quoten_Q1_2025.xlsx",
                url="https://www.bundesnetzagentur.de/DE/test/Roll-out-Quoten_Q1_2025.xlsx",
                quarter="Q1",
                year=2025,
                confidence="high",
                method="ai_analysis",
                reasoning="Test report for integration testing",
                ai_model_used="NousResearch/Hermes-2-Pro-Llama-3-8B",
                ai_tokens_used=637,
                ai_response='{"selected_index": 3, "quarter": "Q1", "year": 2025}',
                download_session_id=download_session.session_id,
                source_metadata={"test_mode": True},
            )
            print(f"    ✅ Roll-Out report saved with ID: {report.id}")

            # Test saving an analysis session
            print("  🤖 Saving analysis session...")
            analysis = await repo.save_analysis_session(
                download_session_id=download_session.session_id,
                model_used="NousResearch/Hermes-2-Pro-Llama-3-8B",
                dry_run=False,
                selected_report_id=report.id,
                total_tokens_used=637,
                analysis_metadata={"confidence": "high", "method": "ai_analysis"},
                status="completed",
            )
            print(f"    ✅ Analysis session saved with ID: {analysis.id}")

            # Test retrieving data
            print("  🔍 Testing data retrieval...")

            # Get latest report
            latest_report = await repo.get_latest_report(quarter="Q1", year=2025)
            if latest_report:
                print(f"    ✅ Found latest Q1 2025 report: {latest_report.filename}")
            else:
                print("    ⚠️  No latest report found")

            # Get report by ID
            retrieved_report = await repo.get_report_by_id(report.id)
            if retrieved_report:
                print(f"    ✅ Retrieved report by ID: {retrieved_report.filename}")
            else:
                print("    ⚠️  Could not retrieve report by ID")

            # Get reports by session
            session_reports = await repo.get_reports_by_session(
                download_session.session_id
            )
            print(f"    ✅ Found {len(session_reports)} reports for session")

            # Get recent reports
            recent_reports = await repo.get_recent_reports(limit=5)
            print(f"    ✅ Found {len(recent_reports)} recent reports")

            print("✅ All repository operations completed successfully!")
            return True

    except Exception as e:
        print(f"❌ Repository operation failed: {e}")
        traceback.print_exc()
        return False


async def simulate_real_workflow():
    """Simulate the real workflow of processing BNetzA data."""
    print("🔄 Simulating real workflow...")

    # Simulate processing the actual data from our last run
    sample_metadata = {  # pragma: allowlist secret
        "download_session": {
            "timestamp": "2025-08-15T19:32:53.151185",
            "temp_directory": "/home/daniel/GIT/APPS/vnbdigitaler/tmp/bnetza_download_20250815_193252",  # pragma: allowlist secret
            "script_version": "1.0",
        },
        "excel_files": {
            "count": 4,
            "found_urls": [
                "https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/NetzzugangMesswesen/Mess-undZaehlwesen/iMSys/_DL/Fragebogen_StandardQ2_.xlsx?__blob=publicationFile&amp;v=3",
                "https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/NetzzugangMesswesen/Mess-undZaehlwesen/iMSys/_DL/Fragebogen_SonderQ2_.xlsx?__blob=publicationFile&amp;v=3",
                "https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/NetzzugangMesswesen/Mess-undZaehlwesen/iMSys/_DL/Fragebogen_StandardQ1.xlsx?__blob=publicationFile&amp;v=3",
                "https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/NetzzugangMesswesen/Mess-undZaehlwesen/iMSys/_DL/Roll-out-Quoten_Q1_2025.xlsx?__blob=publicationFile&amp;v=3",
            ],
        },
    }

    # Analysis result from our Hermes-2-Pro run
    analysis_result = {
        "selected_index": 3,
        "selected_url": "https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/NetzzugangMesswesen/Mess-undZaehlwesen/iMSys/_DL/Roll-out-Quoten_Q1_2025.xlsx?__blob=publicationFile&amp;v=3",
        "confidence": "high",
        "reasoning": "The URL contains 'Roll-out-Quoten' in the filename, indicates the quarter as Q1, and specifies the year as 2025. It is the most recent quarter available based on the current date.",
        "quarter": "Q1",
        "year": 2025,
        "ai_response": '{"selected_index": 3, "quarter": "Q1", "year": 2025, "confidence": "high"}',
        "model_used": "NousResearch/Hermes-2-Pro-Llama-3-8B",
        "tokens_used": 637,
    }

    try:
        async for repo in get_repository():
            # Step 1: Save download session
            print("  1️⃣ Saving download session...")
            download_session = await repo.save_download_session(
                session_id="bnetza_download_20250815_193252",
                temp_directory=sample_metadata["download_session"]["temp_directory"],
                total_urls_found=len(sample_metadata["excel_files"]["found_urls"]),
                excel_urls_found=sample_metadata["excel_files"]["count"],
                user_agent="vnbdigitaler/1.0 (BNetzA Downloader)",
                script_version=sample_metadata["download_session"]["script_version"],
                metadata=sample_metadata,
                status="completed",
            )
            print(f"    ✅ Download session: {download_session.session_id}")

            # Step 2: Save the selected Roll-Out report
            print("  2️⃣ Saving selected Roll-Out report...")
            selected_url = analysis_result["selected_url"]
            filename = Path(selected_url.split("/")[-1].split("?")[0]).name

            report = await repo.save_roll_out_report(
                filename=filename,
                url=selected_url,
                quarter=analysis_result["quarter"],
                year=analysis_result["year"],
                confidence=analysis_result["confidence"],
                method="ai_analysis",
                reasoning=analysis_result["reasoning"],
                ai_model_used=analysis_result["model_used"],
                ai_tokens_used=analysis_result["tokens_used"],
                ai_response=analysis_result["ai_response"],
                download_session_id=download_session.session_id,
                source_metadata={"analysis_timestamp": "2025-08-15T19:52:59.255897"},
            )
            print(f"    ✅ Roll-Out report: {report.filename} (ID: {report.id})")

            # Step 3: Save analysis session
            print("  3️⃣ Saving analysis session...")
            analysis_session = await repo.save_analysis_session(
                download_session_id=download_session.session_id,
                model_used=analysis_result["model_used"],
                dry_run=False,
                selected_report_id=report.id,
                total_tokens_used=analysis_result["tokens_used"],
                analysis_metadata=analysis_result,
                status="completed",
            )
            print(f"    ✅ Analysis session: {analysis_session.id}")

            # Step 4: Verify the data
            print("  4️⃣ Verifying stored data...")
            latest = await repo.get_latest_report()
            if latest and latest.id == report.id:
                print(f"    ✅ Latest report correctly identified: {latest.filename}")
                print(f"    📊 Quarter: {latest.quarter}, Year: {latest.year}")
                print(f"    🎯 Confidence: {latest.confidence}")
                print(f"    🤖 AI Model: {latest.ai_model_used}")
                print(f"    🔢 Tokens used: {latest.ai_tokens_used}")
            else:
                print("    ⚠️  Latest report verification failed")

            print("✅ Real workflow simulation completed successfully!")
            return True

    except Exception as e:
        print(f"❌ Workflow simulation failed: {e}")
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test Neon database integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--create-tables", action="store_true", help="Create database tables"
    )

    parser.add_argument(
        "--test-data", action="store_true", help="Insert and test with sample data"
    )

    parser.add_argument(
        "--real-workflow",
        action="store_true",
        help="Simulate real workflow with actual data",
    )

    args = parser.parse_args()

    print("🧪 Neon Database Integration Test")
    print("=" * 40)

    # Test connection first
    if not await test_connection():
        print(
            "\n❌ Database connection failed. Check your NEON_DATABASE_URL configuration."
        )
        sys.exit(1)

    # Create tables if requested
    if args.create_tables and not await create_tables():
        print("\n❌ Failed to create tables.")
        sys.exit(1)

    # Test with sample data if requested
    if args.test_data and not await test_repository_operations():
        print("\n❌ Repository tests failed.")
        sys.exit(1)

    # Simulate real workflow if requested
    if args.real_workflow and not await simulate_real_workflow():
        print("\n❌ Real workflow simulation failed.")
        sys.exit(1)

    # If no specific options, just test connection
    if not any([args.create_tables, args.test_data, args.real_workflow]):
        print("\n✅ Basic connection test completed.")
        print("\nTo run more tests, use:")
        print("  --create-tables   Create database tables")
        print("  --test-data       Test with sample data")
        print("  --real-workflow   Simulate real workflow")

    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
