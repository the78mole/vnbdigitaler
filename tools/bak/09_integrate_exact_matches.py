#!/usr/bin/env python3
"""
VNBdigitaler - Script 09: Integrate Exact Matches

This script analyzes the BNetzA Roll-Out debug CSV file and creates a new CSV
with exact matches found in the BDEW database, including:
- Index from BNetzA debug CSV
- BDEW Code
- BDEW Company Name
- Roll-Out Quote

Author: VNBdigitaler Project
Date: 2025-08-21
"""

import argparse
import asyncio
import csv
import logging
import sys
import traceback
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Constants
MAX_LOG_MATCHES = 10  # Maximum number of matches to log for verification

# ruff: noqa: E402
from src.database_config import get_database_url
from src.models import Company


class ExactMatchIntegrator:
    """Finds exact matches between BNetzA Roll-Out data and BDEW companies."""

    def __init__(self, database_url: str):
        """Initialize the exact match integrator."""
        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False)
        self.session_factory = async_sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

    def normalize_company_name(self, name: str) -> str:
        """Normalize company name for better matching."""
        if not name:
            return ""

        # Basic normalization
        normalized = name.strip().lower()

        # Remove common punctuation and standardize spaces first
        normalized = normalized.replace(".", "").replace(",", "").replace(";", "")
        normalized = normalized.replace("(", "").replace(")", "")
        normalized = normalized.replace("[", "").replace("]", "")
        normalized = normalized.replace('"', "").replace("'", "")
        normalized = normalized.replace("-", " ").replace("_", " ")
        normalized = " ".join(normalized.split())  # Normalize whitespace

        # Remove common legal forms and replace with standardized versions
        legal_replacements = {
            " gmbh & co kg": "",
            " gmbh & co. kg": "",
            " gmbh &co kg": "",
            " gmbh u co kg": "",
            " gmbh und co kg": "",
            " gmbh": "",
            " ag": "",
            " kg": "",
            " ohg": "",
            " eg": "",
            " ev": "",
            " e.v.": "",
            " e.v": "",
            " mbh": "",
            " co kg": "",
            " & co": "",
            " und co": "",
            " u co": "",
            " limited": "",
            " ltd": "",
            " se": "",
            " corp": "",
            " corporation": "",
            " inc": "",
            " incorporated": "",
        }

        for old, new in legal_replacements.items():
            normalized = normalized.replace(old, new)

        # Remove common words that don't help matching
        common_words = [
            "gesellschaft",
            "unternehmen",
            "betrieb",
            "betriebe",
            "werke",
            "werk",
            "stadtwerke",
            "gemeindewerke",
            "energie",
            "strom",
            "gas",
            "wasser",
            "versorgung",
            "versorgungs",
            "netze",
            "netz",
            "verteilnetz",
            "verteilung",
            "distribution",
            "regional",
            "local",
            "kommunal",
        ]

        words = normalized.split()
        filtered_words = []
        for word in words:
            if word not in common_words and len(word) > 1:
                filtered_words.append(word)

        return " ".join(filtered_words).strip()

    async def get_companies_from_db(self) -> list[dict]:
        """Fetch all companies from the database."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(
                    Company.id,
                    Company.bdew_code,
                    Company.bdew_name,
                    Company.vnbdigital_name,
                    Company.rollout_report_name,
                )
            )
            companies = []
            for row in result:
                companies.append(
                    {
                        "id": row.id,
                        "bdew_code": row.bdew_code,
                        "bdew_name": row.bdew_name,
                        "vnbdigital_name": row.vnbdigital_name,
                        "rollout_report_name": row.rollout_report_name,
                        "normalized_bdew": self.normalize_company_name(row.bdew_name),
                        "normalized_vnb": self.normalize_company_name(
                            row.vnbdigital_name or ""
                        ),
                        "normalized_rollout": self.normalize_company_name(
                            row.rollout_report_name or ""
                        ),
                    }
                )

            logger.info(f"📊 Loaded {len(companies)} companies from database")
            return companies

    def find_exact_match(
        self, bnetza_name: str, db_companies: list[dict]
    ) -> dict | None:
        """Find exact match for a BNetzA company name in the database."""
        bnetza_normalized = self.normalize_company_name(bnetza_name)

        if not bnetza_normalized:
            return None

        for company in db_companies:
            # Try exact matches on normalized names
            for name_type, normalized_name in [
                ("bdew_normalized", company["normalized_bdew"]),
                ("vnbdigital_normalized", company["normalized_vnb"]),
                ("rollout_normalized", company["normalized_rollout"]),
            ]:
                if normalized_name and normalized_name == bnetza_normalized:
                    return {
                        "company_id": company["id"],
                        "bdew_code": company["bdew_code"],
                        "bdew_name": company["bdew_name"],
                        "match_type": f"exact_{name_type}",
                        "matched_field": name_type,
                    }

            # Also try exact matches on original names (case-insensitive)
            for name_type, original_name in [
                ("bdew_name", company["bdew_name"]),
                ("vnbdigital_name", company["vnbdigital_name"]),
                ("rollout_report_name", company["rollout_report_name"]),
            ]:
                if original_name and original_name.lower() == bnetza_name.lower():
                    return {
                        "company_id": company["id"],
                        "bdew_code": company["bdew_code"],
                        "bdew_name": company["bdew_name"],
                        "match_type": f"exact_{name_type}_original",
                        "matched_field": name_type,
                    }

        return None

    async def process_exact_matches(
        self, bnetza_csv_path: Path, output_csv_path: Path
    ) -> dict[str, Any]:
        """Process BNetzA CSV and find exact matches with BDEW database."""
        logger.info("🔍 VNBdigitaler - Exact Match Integration")
        logger.info("=" * 60)

        # Load BNetzA data
        logger.info(f"📖 Reading BNetzA data from: {bnetza_csv_path}")
        df = pd.read_csv(bnetza_csv_path)
        logger.info(f"📊 Loaded {len(df)} BNetzA companies")

        # Load database companies
        db_companies = await self.get_companies_from_db()

        # Find exact matches
        exact_matches = []
        stats = {
            "total_bnetza_companies": len(df),
            "exact_matches_found": 0,
            "no_matches": 0,
        }

        logger.info("🔍 Finding exact matches...")

        for index, row in df.iterrows():
            bnetza_name = row["original_name"]
            ausstattungsquote = row.get("ausstattungsquote", "")

            # Convert empty string or NaN to empty string for CSV
            if pd.isna(ausstattungsquote) or ausstattungsquote == "":
                ausstattungsquote = ""

            match_result = self.find_exact_match(bnetza_name, db_companies)

            if match_result:
                exact_matches.append(
                    {
                        "bnetza_index": int(index),
                        "bdew_code": match_result["bdew_code"],
                        "bdew_name": match_result["bdew_name"],
                        "bnetza_name": bnetza_name,
                        "rollout_quote": ausstattungsquote,
                        "match_type": match_result["match_type"],
                        "matched_field": match_result["matched_field"],
                    }
                )
                stats["exact_matches_found"] += 1

                # Log first few matches for verification
                if stats["exact_matches_found"] <= MAX_LOG_MATCHES:
                    logger.info(
                        f"✅ Exact match [{stats['exact_matches_found']}]: "
                        f"{bnetza_name} -> {match_result['bdew_name']} "
                        f"({match_result['bdew_code']})"
                    )
            else:
                stats["no_matches"] += 1

        # Save exact matches to CSV
        logger.info(
            f"💾 Saving {len(exact_matches)} exact matches to: {output_csv_path}"
        )

        # Ensure output directory exists
        output_csv_path.parent.mkdir(parents=True, exist_ok=True)

        with output_csv_path.open("w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "bnetza_index",
                "bdew_code",
                "bdew_name",
                "bnetza_name",
                "rollout_quote",
                "match_type",
                "matched_field",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(exact_matches)

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("📈 EXACT MATCH INTEGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"📊 Total BNetzA companies: {stats['total_bnetza_companies']}")
        logger.info(f"✅ Exact matches found: {stats['exact_matches_found']}")
        logger.info(f"❌ No matches: {stats['no_matches']}")

        match_rate = (
            stats["exact_matches_found"] / stats["total_bnetza_companies"]
        ) * 100
        logger.info(f"📊 Exact match rate: {match_rate:.1f}%")
        logger.info(f"💾 Output saved to: {output_csv_path}")

        return stats

    async def close(self):
        """Close database connections."""
        await self.engine.dispose()


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Find exact matches between BNetzA Roll-Out data and BDEW database"
    )

    parser.add_argument(
        "--bnetza-csv",
        type=Path,
        default=Path("data/debug_bnetza_rollout_companies.csv"),
        help="Path to BNetzA debug CSV file (default: data/debug_bnetza_rollout_companies.csv)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/exact_matches_rollout.csv"),
        help="Output CSV file path (default: data/exact_matches_rollout.csv)",
    )

    parser.add_argument(
        "--database-url",
        type=str,
        help="Database URL (default: from environment)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    return parser.parse_args()


async def main():
    """Main function."""
    args = parse_arguments()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Get database URL
    database_url = args.database_url or get_database_url()
    if not database_url:
        logger.error("❌ No database URL provided")
        sys.exit(1)

    # Check input file
    if not args.bnetza_csv.exists():
        logger.error(f"❌ BNetzA CSV file not found: {args.bnetza_csv}")
        sys.exit(1)

    # Initialize integrator
    integrator = ExactMatchIntegrator(database_url)

    try:
        # Process exact matches
        await integrator.process_exact_matches(args.bnetza_csv, args.output)

        logger.info("\n🎉 Exact match integration completed successfully!")

    except KeyboardInterrupt:
        logger.warning("\n⚠️ Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        if args.verbose:
            logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        await integrator.close()


if __name__ == "__main__":
    asyncio.run(main())
