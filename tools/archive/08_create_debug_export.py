#!/usr/bin/env python3
"""
VNBdigitaler - Script 08: Create Debug Export for Company Name Matching

This script creates two CSV files for debugging and analyzing company name matching:
1. debug_bdew_companies.csv - BDEW companies with normalized names
2. debug_bnetza_rollout_companies.csv - BNetzA Roll-Out companies with normalized names

These debug files help analyze and improve the company matching algorithms
by providing a clear view of how company names are normalized.

Usage:
    python tools/08_create_debug_export.py [--bnetza-csv PATH]

Author: VNBdigitaler Project
Date: 2025-08-21
"""

import argparse
import asyncio
import csv
import logging
import re
import sys
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

# ruff: noqa: E402
from src.database_config import get_database_url
from src.models import Company


class DebugExporter:
    """Creates debug CSV files for company name matching analysis."""

    def __init__(self, database_url: str):
        """Initialize the debug exporter."""
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
        normalized = re.sub(r"[,\.\-\(\)\&]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)

        # Standardize common legal forms with reduced weight impact (more aggressive)
        legal_form_mappings = {
            " gmbh": "",
            " gmbh co kg": "",
            " gmbh co k": "",
            " gmbh & co kg": "",
            " gmbh & co k": "",
            " ag": "",
            " aktiengesellschaft": "",
            " kg": "",
            " eg": "",
            " mbh": "",
            " gesellschaft mit beschränkter haftung": "",
            " eingetragene genossenschaft": "",
            " adör": "",
            " anstalt des öffentlichen rechts": "",
            "gesellschaft": "ges",
            " co": "",
            " & ": " ",
        }

        # Apply legal form normalization (remove most legal forms completely)
        for old_form, new_form in legal_form_mappings.items():
            normalized = normalized.replace(old_form, new_form)

        # Standardize common business terms
        business_term_mappings = {
            "stadtwerke": "sw",
            "energieversorgung": "ev",
            "elektrizitätswerk": "ew",
            "gemeindewerke": "gw",
            "überlandwerk": "üw",
            "netzgesellschaft": "ng",
            "versorgungsbetriebe": "vb",
            "technische werke": "tw",
            "energie und wasserversorgungs": "ewv",
            "energie und wasserversorgung": "ewv",
            "stromnetz": "sn",
            "energienetze": "en",
            "verteilnetz": "vn",
            "netz": "",
            "netze": "",
            "service": "",
            "betrieb": "",
            "betriebe": "",
            "versorgung": "vers",
        }

        for old_term, new_term in business_term_mappings.items():
            normalized = normalized.replace(old_term, new_term)

        # Clean up multiple spaces and trim
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = normalized.strip()

        return normalized

    async def export_bdew_companies(self, output_file: Path) -> int:
        """Export BDEW companies with normalized names to CSV."""
        logger.info("📊 Exporting BDEW companies...")

        async with self.session_factory() as session:
            # Get all companies from database
            stmt = select(Company)
            result = await session.execute(stmt)
            companies = result.scalars().all()

        # Prepare data for CSV export
        csv_data = []
        for company in companies:
            csv_data.append(
                {
                    "id": company.id,
                    "bdew_code": company.bdew_code or "",
                    "original_name": company.bdew_name,
                    "city": company.bdew_city or "",
                    "normalized_name": self.normalize_company_name(company.bdew_name),
                }
            )

        # Write to CSV
        with output_file.open("w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["id", "bdew_code", "original_name", "city", "normalized_name"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)

        logger.info(f"✅ Exported {len(csv_data)} BDEW companies to {output_file}")
        return len(csv_data)

    def export_bnetza_companies(self, csv_file: Path, output_file: Path) -> int:
        """Export BNetzA companies with normalized names to CSV."""
        logger.info("📊 Exporting BNetzA Roll-Out companies...")

        if not csv_file.exists():
            raise FileNotFoundError(f"BNetzA CSV file not found: {csv_file}")

        # Load BNetzA data
        try:
            df = pd.read_csv(csv_file, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(csv_file, encoding="latin-1")

        # Clean up data
        df = df.dropna(subset=["Unternehmen"])
        df["Unternehmen"] = df["Unternehmen"].astype(str).str.strip()
        df = df[df["Unternehmen"] != ""]

        # Prepare data for CSV export
        csv_data = []
        for idx, row in df.iterrows():
            company_name = row["Unternehmen"]
            # Try different column names for the quota
            ausstattungsquote = (
                row.get("Ausstattungsquote", "")
                or row.get("Ausstattungsquote zum 31. März 2025", "")
                or row.get("Ausstattungsquote zum 31. Dezember 2024", "")
                or ""
            )
            csv_data.append(
                {
                    "index": idx,
                    "original_name": company_name,
                    "normalized_name": self.normalize_company_name(company_name),
                    "ausstattungsquote": ausstattungsquote,
                }
            )

        # Write to CSV
        with output_file.open("w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "index",
                "original_name",
                "normalized_name",
                "ausstattungsquote",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)

        logger.info(f"✅ Exported {len(csv_data)} BNetzA companies to {output_file}")
        return len(csv_data)

    async def create_debug_exports(
        self, bnetza_csv_file: Path | None = None
    ) -> dict[str, Any]:
        """Create both debug export files."""
        logger.info("🔍 Creating debug export files...")
        logger.info("=" * 50)

        results = {}
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(exist_ok=True)

        try:
            # Export BDEW companies
            bdew_output = data_dir / "debug_bdew_companies.csv"
            bdew_count = await self.export_bdew_companies(bdew_output)
            results["bdew_companies"] = {"count": bdew_count, "file": str(bdew_output)}

            # Find BNetzA CSV file if not provided
            if not bnetza_csv_file:
                csv_candidates = list(data_dir.glob("*rollout*.csv")) + list(
                    data_dir.glob("*Roll-out*.csv")
                )
                if csv_candidates:
                    bnetza_csv_file = sorted(
                        csv_candidates, key=lambda x: x.stat().st_mtime
                    )[-1]
                    logger.info(f"Using BNetzA file: {bnetza_csv_file}")
                else:
                    raise FileNotFoundError(
                        "No BNetzA Roll-Out CSV file found in data directory"
                    )

            # Export BNetzA companies
            bnetza_output = data_dir / "debug_bnetza_rollout_companies.csv"
            bnetza_count = self.export_bnetza_companies(bnetza_csv_file, bnetza_output)
            results["bnetza_companies"] = {
                "count": bnetza_count,
                "file": str(bnetza_output),
            }

            logger.info("=" * 50)
            logger.info("✅ DEBUG EXPORT COMPLETED SUCCESSFULLY")
            logger.info("=" * 50)
            logger.info(
                f"📊 BDEW companies: {bdew_count} exported to {bdew_output.name}"
            )
            logger.info(
                f"📊 BNetzA companies: {bnetza_count} exported to {bnetza_output.name}"
            )
            logger.info("=" * 50)

            return results

        except Exception as e:
            logger.error(f"❌ Error during debug export: {e}")
            raise

    async def cleanup(self):
        """Clean up resources."""
        await self.engine.dispose()


def find_latest_bnetza_csv() -> Path | None:
    """Find the most recent BNetzA CSV file."""
    data_dir = Path(__file__).parent.parent / "data"

    if not data_dir.exists():
        return None

    csv_candidates = list(data_dir.glob("*rollout*.csv")) + list(
        data_dir.glob("*Roll-out*.csv")
    )

    # Exclude debug files
    csv_candidates = [f for f in csv_candidates if not f.name.startswith("debug_")]

    if csv_candidates:
        return sorted(csv_candidates, key=lambda x: x.stat().st_mtime)[-1]

    return None


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create debug CSV files for company name matching analysis"
    )
    parser.add_argument(
        "--bnetza-csv",
        type=Path,
        help="Path to BNetzA Roll-Out CSV file (default: auto-detect latest)",
    )
    return parser.parse_args()


async def main():
    """Main execution function."""
    args = parse_arguments()

    # Auto-detect BNetzA CSV if not provided
    bnetza_csv_file = args.bnetza_csv
    if not bnetza_csv_file:
        bnetza_csv_file = find_latest_bnetza_csv()
        if not bnetza_csv_file:
            logger.error(
                "❌ No BNetzA Roll-Out CSV file found. Please specify with --bnetza-csv"
            )
            sys.exit(1)

    # Get database configuration
    database_url = get_database_url()
    logger.info("Database connection configured")

    # Create exporter
    exporter = DebugExporter(database_url)

    try:
        # Create debug exports
        results = await exporter.create_debug_exports(bnetza_csv_file)

        # Summary
        logger.info("\n🎯 Debug export completed successfully!")
        logger.info(
            "You can now analyze the normalized company names for matching improvements."
        )

        return results

    except KeyboardInterrupt:
        logger.info("❌ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        await exporter.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
