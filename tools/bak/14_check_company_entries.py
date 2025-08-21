#!/usr/bin/env python3
"""
VNBdigitaler - Company Entry Consistency Checker

This script analyzes database entries and identifies companies where the BDEW name
and rollout_report_name don't match exactly. This helps identify potential data
quality issues or inconsistent naming.

Author: VNBdigitaler Project
Date: 2025-08-22
"""

import asyncio
import logging
import os
import re
import sys
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

try:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file if it exists
except ImportError:
    pass  # dotenv is optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

# Constants
MIN_SIMILARITY_THRESHOLD = 0.8  # Minimum similarity to consider as "close match"
EXACT_MATCH_SCORE = 1.0  # Score for exact matches


class CompanyConsistencyChecker:
    """Analyzes company entries for naming consistency."""

    def __init__(self):
        self.companies = []
        self.mismatches = []
        self.engine = None

    async def connect_to_database(self) -> bool:
        """Connect to the database."""
        try:
            # Get database URL from environment variables
            database_url = (
                os.getenv("NEON_DATABASE_URL")
                or os.getenv("DATABASE_URL")
                or os.getenv("DB_URL")
            )

            if not database_url:
                logger.error("❌ No database URL configured")
                logger.error(
                    "   Please set NEON_DATABASE_URL, DATABASE_URL, or DB_URL environment variable"
                )
                return False

            # Convert to async URL if needed
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace(
                    "postgresql://", "postgresql+asyncpg://", 1
                )

            # Remove SSL mode parameters that are not supported by asyncpg
            if "?" in database_url:
                base_url, params = database_url.split("?", 1)
                # Filter out all potentially problematic parameters
                excluded_params = {"ssl", "sslmode", "channel_binding", "gssencmode"}
                param_pairs = []
                for param in params.split("&"):
                    param_name = param.split("=")[0].lower()
                    if param_name not in excluded_params:
                        param_pairs.append(param)

                if param_pairs:
                    database_url = f"{base_url}?{'&'.join(param_pairs)}"
                else:
                    database_url = base_url

            logger.info(f"🔗 Connecting to database: {database_url.split('@')[0]}@***")
            self.engine = create_async_engine(database_url)

            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

            logger.info("✅ Database connection successful")
            return True

        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False

    async def load_companies(self) -> bool:
        """Load all companies from database."""
        try:
            logger.info("📖 Loading companies from database...")

            async with AsyncSession(self.engine) as session:
                result = await session.execute(
                    text(
                        """
                    SELECT
                        id,
                        bdew_name,
                        bdew_code,
                        rollout_report_name,
                        rollout_name_variations,
                        name_matching_confidence
                    FROM companies
                    WHERE rollout_report_name IS NOT NULL
                    AND rollout_report_name != ''
                    ORDER BY bdew_name
                    """
                    )
                )
                rows = result.fetchall()

            self.companies = [
                {
                    "id": row.id,
                    "bdew_name": row.bdew_name,
                    "bdew_code": row.bdew_code,
                    "rollout_report_name": row.rollout_report_name,
                    "rollout_name_variations": row.rollout_name_variations,
                    "name_matching_confidence": row.name_matching_confidence,
                }
                for row in rows
            ]

            logger.info(
                f"✅ Loaded {len(self.companies)} companies with rollout_report_name"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load companies: {e}")
            return False

    def _normalize_name(self, name: str) -> str:
        """Normalize company name for comparison."""
        if not name:
            return ""

        # Convert to lowercase and strip whitespace
        normalized = name.lower().strip()

        # Remove common punctuation and special characters
        normalized = re.sub(r"[^\w\s]", " ", normalized)

        # Replace multiple spaces with single space
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized.strip()

    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names using simple word overlap."""
        norm1 = self._normalize_name(name1)
        norm2 = self._normalize_name(name2)

        if not norm1 or not norm2:
            return 0.0

        # Exact match
        if norm1 == norm2:
            return 1.0

        # Word-based similarity
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def analyze_mismatches(self) -> None:
        """Analyze companies for name mismatches."""
        logger.info("🔍 Analyzing company name consistency...")

        exact_matches = 0
        close_matches = 0
        mismatches = 0

        for company in self.companies:
            bdew_name = company["bdew_name"]
            rollout_name = company["rollout_report_name"]

            similarity = self._calculate_similarity(bdew_name, rollout_name)

            mismatch_info = {
                "id": company["id"],
                "bdew_code": company["bdew_code"],
                "bdew_name": bdew_name,
                "rollout_report_name": rollout_name,
                "rollout_name_variations": company["rollout_name_variations"],
                "name_matching_confidence": company["name_matching_confidence"],
                "similarity": similarity,
                "normalized_bdew": self._normalize_name(bdew_name),
                "normalized_rollout": self._normalize_name(rollout_name),
            }

            if similarity == EXACT_MATCH_SCORE:
                exact_matches += 1
            elif similarity >= MIN_SIMILARITY_THRESHOLD:
                close_matches += 1
                mismatch_info["category"] = "close_match"
                self.mismatches.append(mismatch_info)
            else:
                mismatches += 1
                mismatch_info["category"] = "mismatch"
                self.mismatches.append(mismatch_info)

        logger.info("=" * 60)
        logger.info("📊 COMPANY NAME CONSISTENCY ANALYSIS")
        logger.info("=" * 60)
        logger.info(f"✅ Exact matches: {exact_matches}")
        logger.info(
            f"🟡 Close matches (≥{MIN_SIMILARITY_THRESHOLD*100:.0f}% similarity): {close_matches}"
        )
        logger.info(
            f"❌ Mismatches (<{MIN_SIMILARITY_THRESHOLD*100:.0f}% similarity): {mismatches}"
        )
        logger.info(f"📊 Total companies analyzed: {len(self.companies)}")
        logger.info(f"📈 Exact match rate: {exact_matches/len(self.companies)*100:.1f}%")

    def print_detailed_mismatches(
        self, show_close_matches: bool = True, limit: int | None = None
    ) -> None:
        """Print detailed information about mismatches."""
        if not self.mismatches:
            logger.info("🎉 No mismatches found!")
            return

        # Sort by category first (close matches first), then by similarity
        sorted_mismatches = sorted(
            self.mismatches,
            key=lambda x: (x["category"] == "mismatch", x["similarity"]),
        )

        if limit:
            sorted_mismatches = sorted_mismatches[:limit]

        logger.info("\n" + "=" * 80)
        logger.info("📋 DETAILED MISMATCH ANALYSIS")
        logger.info("=" * 80)

        for i, mismatch in enumerate(sorted_mismatches, 1):
            if not show_close_matches and mismatch["category"] == "close_match":
                continue

            category_icon = "🟡" if mismatch["category"] == "close_match" else "❌"
            category_text = (
                "Close Match" if mismatch["category"] == "close_match" else "Mismatch"
            )

            logger.info(
                f"\n{category_icon} {category_text} #{i} (Similarity: {mismatch['similarity']:.2f})"
            )
            logger.info(f"   BDEW Code: {mismatch['bdew_code']}")
            logger.info(f"   BDEW Name: '{mismatch['bdew_name']}'")
            logger.info(f"   Rollout Name: '{mismatch['rollout_report_name']}'")

    def export_mismatches_to_csv(
        self, filename: str = "data/company_name_mismatches.csv"
    ) -> None:
        """Export mismatches to CSV file."""
        if not self.mismatches:
            logger.info("🎉 No mismatches to export!")
            return

        try:
            df = pd.DataFrame(self.mismatches)
            df.to_csv(filename, index=False)
            logger.info(f"📁 Exported {len(self.mismatches)} mismatches to: {filename}")
        except Exception as e:
            logger.error(f"❌ Failed to export CSV: {e}")

    async def cleanup(self) -> None:
        """Cleanup database connection."""
        if self.engine:
            await self.engine.dispose()


async def main() -> int:
    """Main entry point."""
    # Environment variables already loaded at startup
    logger.info("✅ Environment variables loaded from .env file")

    parser = ArgumentParser(description="Company Entry Consistency Checker")

    parser.add_argument(
        "--hide-close-matches",
        action="store_true",
        help="Hide close matches (≥80% similarity) from detailed output",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of mismatches shown in detailed output",
    )
    parser.add_argument(
        "--export-csv",
        type=str,
        default="data/company_name_mismatches.csv",
        help="Export mismatches to CSV file",
    )
    parser.add_argument(
        "--no-export",
        action="store_true",
        help="Don't export CSV file",
    )

    args = parser.parse_args()

    logger.info("🚀 VNBdigitaler - Company Entry Consistency Checker")
    logger.info("=" * 60)

    checker = CompanyConsistencyChecker()

    try:
        # Connect to database
        if not await checker.connect_to_database():
            return 1

        # Load companies
        if not await checker.load_companies():
            return 2

        # Analyze mismatches
        checker.analyze_mismatches()

        # Print detailed results
        checker.print_detailed_mismatches(
            show_close_matches=not args.hide_close_matches, limit=args.limit
        )

        # Export to CSV if requested
        if not args.no_export:
            checker.export_mismatches_to_csv(args.export_csv)

        logger.info("\n" + "=" * 60)
        logger.info("🎉 Company consistency check completed successfully!")

        return 0

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 99
    finally:
        await checker.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
