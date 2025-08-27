#!/usr/bin/env python3
"""
BNetzA Company Update Script for GitHub Actions

This script processes BNetzA rollout companies and matches them with existing BDEW companies
in the database. It provides comprehensive statistics for GitHub Actions workflows.

Usage:
    python company_updater.py [--dry-run] [--force-update]

Arguments:
    --dry-run       Show what would be updated without making changes
    --force-update  Force update even if no changes detected

Author: GitHub Copilot
Date: 2025-01-28
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import after adding to path
from src.company_matcher import CompanyMatcher  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.matching_models import BDEWCompany, BNetzACompany  # noqa: E402
from src.models import Company, RolloutCompany  # noqa: E402

# Constants
HIGH_CONFIDENCE_THRESHOLD = 85

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class CompanyUpdateStats:
    """Statistics tracking for company updates."""

    def __init__(self):
        self.companies_processed = 0
        self.companies_updated = 0
        self.companies_new = 0
        self.companies_matched = 0
        self.companies_unmatched = 0
        self.new_companies = []
        self.updated_companies = []
        self.matched_companies = []
        self.unmatched_companies = []


class CompanyUpdater:
    """Handles company matching and database updates."""

    def __init__(self, session: AsyncSession, dry_run: bool = False):
        self.session = session
        self.dry_run = dry_run
        self.stats = CompanyUpdateStats()

    async def load_bdew_companies(self) -> list[BDEWCompany]:
        """Load BDEW companies from database."""
        query = select(Company)
        result = await self.session.execute(query)
        companies = result.scalars().all()

        bdew_companies = []
        for company in companies:
            bdew_company = BDEWCompany(
                bdew_code=company.bdew_code,
                name=company.bdew_name,
                normalized_name=company.bdew_name_normalized,
                city=company.bdew_city or "",
            )
            bdew_companies.append(bdew_company)

        logger.info(f"Loaded {len(bdew_companies)} BDEW companies")
        return bdew_companies

    async def load_rollout_companies(self) -> list[BNetzACompany]:
        """Load BNetzA rollout companies from database."""
        query = select(RolloutCompany)
        result = await self.session.execute(query)
        rollout_companies = result.scalars().all()

        bnetza_companies = []
        for idx, company in enumerate(rollout_companies):
            bnetza_company = BNetzACompany(
                index=idx,
                original_name=company.bnetza_name,
                normalized_name=company.normalized_name,
            )
            bnetza_companies.append(bnetza_company)

        logger.info(f"Loaded {len(bnetza_companies)} BNetzA rollout companies")
        return bnetza_companies

    async def find_unmatched_companies(self) -> list[RolloutCompany]:
        """Find rollout companies that don't have BDEW matches yet."""
        query = select(RolloutCompany).where(RolloutCompany.bdew_code.is_(None))
        result = await self.session.execute(query)
        unmatched = list(result.scalars().all())

        logger.info(f"Found {len(unmatched)} unmatched rollout companies")
        return unmatched

    async def process_companies(self) -> CompanyUpdateStats:
        """Process company matching and updates."""
        logger.info("🏢 Starting company processing...")

        # Load data
        bdew_companies = await self.load_bdew_companies()
        unmatched_companies = await self.find_unmatched_companies()

        if not bdew_companies:
            logger.warning("No BDEW companies found in database")
            return self.stats

        if not unmatched_companies:
            logger.info("All rollout companies are already matched")
            return self.stats

        # Initialize matcher
        matcher = CompanyMatcher(bdew_companies)

        # Process each unmatched company
        for rollout_company in unmatched_companies:
            await self._process_single_company(rollout_company, matcher)

        logger.info("📊 Processing complete:")
        logger.info(f"   Processed: {self.stats.companies_processed}")
        logger.info(f"   Updated: {self.stats.companies_updated}")
        logger.info(f"   New matches: {self.stats.companies_matched}")
        logger.info(f"   Still unmatched: {self.stats.companies_unmatched}")

        return self.stats

    async def _process_single_company(
        self, rollout_company: RolloutCompany, matcher: CompanyMatcher
    ):
        """Process a single rollout company for matching."""
        self.stats.companies_processed += 1

        # Convert to BNetzA company for matching
        bnetza_company = BNetzACompany(
            index=0,  # Index not relevant for matching
            original_name=rollout_company.bnetza_name,
            normalized_name=rollout_company.normalized_name,
        )

        # Try exact matches first
        exact_matches = matcher.find_exact_matches(bnetza_company)

        if exact_matches:
            # Use the first exact match
            best_match = exact_matches[0]
            await self._apply_match(rollout_company, best_match)
            return

        # Try fuzzy matches
        fuzzy_matches = matcher.find_fuzzy_matches(bnetza_company)

        if fuzzy_matches:
            # Use the best fuzzy match if confidence is high enough
            best_match = fuzzy_matches[0]
            if (
                best_match.match_score >= HIGH_CONFIDENCE_THRESHOLD
            ):  # High confidence threshold
                await self._apply_match(rollout_company, best_match)
                return

        # No good match found
        self.stats.companies_unmatched += 1
        self.stats.unmatched_companies.append(rollout_company.bnetza_name)
        logger.debug(f"No match found for: {rollout_company.bnetza_name}")

    async def _apply_match(self, rollout_company: RolloutCompany, match):
        """Apply a match between rollout and BDEW company."""
        if self.dry_run:
            logger.info(
                f"DRY RUN: Would match '{rollout_company.bnetza_name}' -> '{match.bdew_company.name}'"
            )
        else:
            # Update the rollout company with BDEW match
            rollout_company.bdew_code = match.bdew_company.bdew_code
            rollout_company.verification_notes = (
                f"Auto-matched via {match.match_type} (score: {match.match_score})"
            )

            await self.session.commit()
            logger.info(
                f"Matched '{rollout_company.bnetza_name}' -> '{match.bdew_company.name}' (score: {match.match_score})"
            )

        self.stats.companies_matched += 1
        self.stats.companies_updated += 1
        self.stats.matched_companies.append(
            {
                "bnetza_name": rollout_company.bnetza_name,
                "bdew_name": match.bdew_company.name,
                "bdew_code": match.bdew_company.bdew_code,
                "match_score": match.match_score,
                "match_type": match.match_type,
            }
        )


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Update BNetzA company matches")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Force update even if no changes detected",
    )
    args = parser.parse_args()

    try:
        # Get database settings
        settings = get_settings()

        # Create async engine
        engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
        )

        # Create session
        async_session = async_sessionmaker(engine, expire_on_commit=False)

        async with async_session() as session:
            # Create updater
            updater = CompanyUpdater(session, dry_run=args.dry_run)

            # Process companies
            stats = await updater.process_companies()

            # Save results to JSON
            results = {
                "companies_processed": stats.companies_processed,
                "companies_updated": stats.companies_updated,
                "companies_new": stats.companies_new,
                "companies_matched": stats.companies_matched,
                "companies_unmatched": stats.companies_unmatched,
                "new_companies": stats.new_companies,
                "updated_companies": stats.updated_companies,
                "matched_companies": stats.matched_companies,
                "unmatched_companies": stats.unmatched_companies,
                "dry_run": args.dry_run,
                "force_update": args.force_update,
                "timestamp": datetime.now().isoformat(),
            }

            with Path("company_results.json").open("w") as f:
                json.dump(results, f, indent=2)

            # Set GitHub Actions outputs
            set_github_outputs(stats)

            return True

    except Exception as e:
        logger.error(f"Error processing companies: {e}")
        return False
    finally:
        if "engine" in locals():
            await engine.dispose()


def set_github_outputs(stats: CompanyUpdateStats):
    """Set GitHub Actions outputs."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with Path(output_file).open("a") as f:
            f.write(f"companies_processed={stats.companies_processed}\n")
            f.write(f"companies_updated={stats.companies_updated}\n")
            f.write(f"companies_new={stats.companies_new}\n")
            f.write(f"companies_matched={stats.companies_matched}\n")
            f.write(f"companies_unmatched={stats.companies_unmatched}\n")


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
