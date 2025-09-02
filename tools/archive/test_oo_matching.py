#!/usr/bin/env python3
"""
Quick test script for the new object-oriented matching system.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
_src_path = str(Path(__file__).parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from src.company_matcher import CompanyMatcher  # noqa: E402
from src.data_loader import DataLoader  # noqa: E402
from src.matching_models import BDEWCompany, BNetzACompany  # noqa: E402

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def test_swe_problem():
    """Test the SWE Netz disambiguation problem specifically."""
    logger.info("🧪 Testing SWE Netz disambiguation...")

    # Create sample BDEW companies
    bdew_companies = [
        BDEWCompany(bdew_code="744", name="SWE Netz GmbH", city="Erfurt"),
        BDEWCompany(bdew_code="7637", name="SWE Netz GmbH", city="Ettlingen"),
        # Add some other companies to make it realistic
        BDEWCompany(bdew_code="123", name="Stadtwerke München GmbH", city="München"),
        BDEWCompany(bdew_code="456", name="Energie Berlin AG", city="Berlin"),
    ]

    # Create sample BNetzA companies
    bnetza_companies = [
        BNetzACompany(index=717, original_name="SWE Netz GmbH", rollout_quote=0.15941),
        BNetzACompany(index=718, original_name="SWE Netz GmbH", rollout_quote=0.01229),
    ]

    # Initialize matcher
    matcher = CompanyMatcher(bdew_companies)

    logger.info("📋 Test data:")
    logger.info("BDEW companies:")
    for company in bdew_companies:
        logger.info(f"  - {company}")
    logger.info("BNetzA companies:")
    for company in bnetza_companies:
        logger.info(f"  - {company}")

    # Test individual matching
    logger.info("\n🔍 Testing individual matches...")
    for bnetza_comp in bnetza_companies:
        logger.info(f"\nTesting: {bnetza_comp}")

        # Find exact matches
        exact_matches = matcher.find_exact_matches(bnetza_comp)
        logger.info(f"  Exact matches found: {len(exact_matches)}")
        for match in exact_matches:
            logger.info(f"    -> {match.bdew_company} (score: {match.match_score})")

        # Find best match
        best_match = matcher.find_best_match(bnetza_comp)
        if best_match:
            logger.info(
                f"  Best match: {best_match.bdew_company} (type: {best_match.match_type})"
            )
        else:
            logger.info("  No best match found")

    # Test batch matching
    logger.info("\n📦 Testing batch matching...")
    results = matcher.batch_match(bnetza_companies)

    logger.info("Results:")
    logger.info(f"  Total matches: {len(results['matches'])}")
    logger.info(f"  No matches: {len(results['no_matches'])}")
    logger.info(f"  Multiple matches: {len(results['multiple_matches'])}")

    for match in results["matches"]:
        logger.info(
            f"  ✅ {match.bnetza_company.original_name} -> {match.bdew_company.name} "
            f"({match.bdew_company.city}) [code: {match.bdew_company.bdew_code}]"
        )

    logger.info("\n🎉 Test completed!")


async def test_with_real_data():
    """Test with real data from CSV files."""
    logger.info("🔧 Testing with real data...")

    # Check if files exist
    bnetza_csv = Path("data/rollout_companies.csv")
    if not bnetza_csv.exists():
        logger.warning(f"❌ Real data test skipped - file not found: {bnetza_csv}")
        return

    # Load data
    data_loader = DataLoader()

    try:
        # Load small sample of BNetzA companies
        bnetza_companies = data_loader.load_bnetza_companies_from_csv(bnetza_csv)
        logger.info(f"Loaded {len(bnetza_companies)} BNetzA companies")

        # Take only first 10 for testing
        bnetza_sample = bnetza_companies[:10]
        logger.info(f"Testing with sample of {len(bnetza_sample)} companies")

        # Load BDEW companies from database
        bdew_companies = await data_loader.load_bdew_companies_from_db()
        logger.info(f"Loaded {len(bdew_companies)} BDEW companies")

        # Initialize matcher and test
        matcher = CompanyMatcher(bdew_companies)
        results = matcher.batch_match(bnetza_sample)

        logger.info("Sample results:")
        for match in results["matches"][:5]:  # Show first 5
            logger.info(
                f"  ✅ {match.bnetza_company.original_name} -> "
                f"{match.bdew_company.name} ({match.match_score}%)"
            )

    except Exception as e:
        logger.error(f"Error in real data test: {e}")
    finally:
        await data_loader.close()


async def main():
    """Run all tests."""
    logger.info("🚀 Starting Object-Oriented Matching System Tests")
    logger.info("=" * 60)

    # Test 1: SWE disambiguation
    await test_swe_problem()

    logger.info("\n" + "=" * 60)

    # Test 2: Real data (if available)
    await test_with_real_data()

    logger.info("\n✅ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
