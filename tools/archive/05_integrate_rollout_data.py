#!/usr/bin/env python3
"""
VNBdigitaler - Script 05: Roll-Out Quoten Integration

This script integrates BNetzA Roll-Out Quoten data into the existing database
by matching companies and storing quota values with proper metadata.

Author: VNBdigitaler Project
Date: 2025-08-21
"""

import argparse
import asyncio
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from fuzzywuzzy import fuzz
from sqlalchemy import select, update
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
from src.models import Company, RollOutReport

# Constants
MIN_FUZZY_MATCH_SCORE = 70  # Minimum score for fuzzy matching (0-100)
HIGH_CONFIDENCE_THRESHOLD = 90  # High confidence threshold for auto-matching
MAX_NAME_DISPLAY_LENGTH = 50
DEFAULT_STICHTAG = "31.03.2025"
MAX_NO_MATCH_DISPLAY = 10
MAX_LOW_CONFIDENCE_DISPLAY = 5

# Roll-Out data schema
EXPECTED_COLUMNS = ["Unternehmen", "Ausstattungsquote", "Stichtag"]


class RollOutDataIntegrator:
    """Integrates Roll-Out Quoten data with the companies database."""

    def __init__(self, database_url: str, dry_run: bool = False):
        """Initialize the integrator."""
        self.database_url = database_url
        self.dry_run = dry_run
        self.engine = create_async_engine(database_url, echo=False)
        self.session_factory = async_sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def load_csv_data(self, csv_file: Path) -> pd.DataFrame:
        """Load and validate CSV data from the roll-out report."""
        logger.info(f"Loading CSV data from: {csv_file}")

        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        # Load CSV with pandas
        try:
            df = pd.read_csv(csv_file, encoding="utf-8")
        except UnicodeDecodeError:
            # Fallback to different encodings
            try:
                df = pd.read_csv(csv_file, encoding="latin1")
                logger.warning("Used latin1 encoding as fallback")
            except Exception:
                df = pd.read_csv(csv_file, encoding="cp1252")
                logger.warning("Used cp1252 encoding as fallback")

        logger.info(f"Loaded {len(df)} rows with columns: {list(df.columns)}")

        # Check for expected columns
        missing_columns = []
        for col in EXPECTED_COLUMNS:
            # Check if exact column exists, or find similar column names
            if col not in df.columns:
                # Try to find similar column names (case-insensitive, partial match)
                similar_cols = [c for c in df.columns if col.lower() in c.lower()]
                if similar_cols:
                    logger.info(
                        f"Column '{col}' not found exactly, using '{similar_cols[0]}'"
                    )
                    df = df.rename(columns={similar_cols[0]: col})
                else:
                    missing_columns.append(col)

        if missing_columns:
            logger.warning(f"Missing columns in CSV: {missing_columns}")
            logger.info(f"Available columns: {list(df.columns)}")

        # Clean up data
        df = df.dropna(subset=["Unternehmen"])  # Remove rows without company names
        df["Unternehmen"] = df["Unternehmen"].astype(str).str.strip()

        # Remove empty company names
        df = df[df["Unternehmen"] != ""]

        logger.info(f"After cleanup: {len(df)} rows with valid company names")
        return df

    def normalize_company_name(self, name: str) -> str:
        """Normalize company name for better matching."""
        if not name:
            return ""

        # Basic normalization
        normalized = name.strip()

        # Remove common suffixes and standardize
        suffixes_to_remove = [
            " GmbH",
            " GmbH & Co. KG",
            " AG",
            " KG",
            " eG",
            " mbH",
            " Gesellschaft mit beschränkter Haftung",
            " Aktiengesellschaft",
            " eingetragene Genossenschaft",
        ]

        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)].strip()
                break  # Only remove one suffix

        # Standardize common terms
        replacements = {
            "Stadtwerke": "SW",
            "Energieversorgung": "EV",
            "Elektrizitätswerk": "EW",
            "Gemeindewerke": "GW",
            "Überlandwerk": "ÜW",
        }

        for old, new in replacements.items():
            normalized = normalized.replace(old, new)

        return normalized.lower()

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

            logger.info(f"Fetched {len(companies)} companies from database")
            return companies

    def match_company_names(self, rollout_name: str, db_companies: list[dict]) -> dict:
        """Match a rollout report company name with database companies."""
        rollout_normalized = self.normalize_company_name(rollout_name)

        best_match = {
            "company_id": None,
            "matched_name": None,
            "match_type": None,
            "confidence": 0,
            "match_details": None,
        }

        for company in db_companies:
            # Try exact matches first
            for name_type, name_value in [
                ("bdew_name", company["bdew_name"]),
                ("vnbdigital_name", company["vnbdigital_name"]),
                ("rollout_report_name", company["rollout_report_name"]),
            ]:
                if name_value and name_value.lower() == rollout_name.lower():
                    return {
                        "company_id": company["id"],
                        "matched_name": name_value,
                        "match_type": f"exact_{name_type}",
                        "confidence": 100,
                        "match_details": f"Exact match on {name_type}",
                    }

            # Try fuzzy matching on normalized names
            for name_type, normalized_name in [
                ("bdew_normalized", company["normalized_bdew"]),
                ("vnbdigital_normalized", company["normalized_vnb"]),
                ("rollout_normalized", company["normalized_rollout"]),
            ]:
                if normalized_name:
                    score = fuzz.ratio(rollout_normalized, normalized_name)
                    if score > best_match["confidence"]:
                        best_match = {
                            "company_id": company["id"],
                            "matched_name": company[
                                "bdew_name"
                            ],  # Always return BDEW name as primary
                            "match_type": f"fuzzy_{name_type}",
                            "confidence": score,
                            "match_details": f"Fuzzy match ({score}%) on {name_type}",
                        }

        return best_match

    async def create_rollout_report_entry(self, metadata_file: Path) -> int:
        """Create a RollOutReport entry from metadata and return its ID."""
        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")

        with metadata_file.open("r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Extract report information
        input_analysis = metadata.get("input_analysis", {})

        report_data = {
            "filename": input_analysis.get("filename", "unknown.xlsx"),
            "url": input_analysis.get("selected_url", ""),
            "quarter": 1,  # Default, will be updated if found in metadata
            "year": datetime.now().year,  # Default
            "confidence": input_analysis.get("ai_confidence", "unknown"),
            "method": self._convert_method_to_int(
                input_analysis.get("ai_method", "unknown")
            ),
            "reasoning": "Imported from CSV conversion process",
            "ai_model_used": None,
            "ai_tokens_used": None,
            "source_metadata": metadata,
            "is_latest": True,
            "is_processed": False,
        }

        # Try to extract quarter and year from filename or metadata
        filename = report_data["filename"].lower()
        for q in range(1, 5):
            if f"q{q}" in filename or f"_{q}_" in filename:
                report_data["quarter"] = q
                break

        # Extract year from filename
        year_match = re.search(r"20\d{2}", filename)
        if year_match:
            report_data["year"] = int(year_match.group())

        if not self.dry_run:
            async with self.session_factory() as session:
                # Set all other reports as not latest for this quarter/year
                await session.execute(
                    update(RollOutReport)
                    .where(
                        (RollOutReport.quarter == report_data["quarter"])
                        & (RollOutReport.year == report_data["year"])
                    )
                    .values(is_latest=False)
                )

                # Create new report entry
                new_report = RollOutReport(**report_data)
                session.add(new_report)
                await session.commit()
                await session.refresh(new_report)

                logger.info(f"Created RollOutReport entry with ID {new_report.id}")
                return new_report.id
        else:
            logger.info("DRY RUN: Would create RollOutReport entry")
            return -1  # Dummy ID for dry run

    def _convert_method_to_int(self, method_str: str) -> int:
        """Convert method string to integer code."""
        method_map = {"ai_analysis": 1, "fallback_pattern": 2, "unknown": 0}
        return method_map.get(method_str.lower(), 0)

    async def update_company_rollout_data(
        self, company_id: int, rollout_data: dict
    ) -> None:
        """Update company with roll-out quota data."""
        if self.dry_run:
            logger.info(f"DRY RUN: Would update company {company_id} with rollout data")
            return

        # Add rollout quota fields to the company record
        update_data = {}

        # Store the roll-out report name if not already set
        if rollout_data.get("rollout_name"):
            update_data["rollout_report_name"] = rollout_data["rollout_name"]

        # For now, we'll store the quota data in source_metadata
        # In a future version, we might add dedicated quota columns
        quota_info = {
            "ausstattungsquote": rollout_data.get("ausstattungsquote"),
            "stichtag": rollout_data.get("stichtag", DEFAULT_STICHTAG),
            "last_updated": datetime.now().isoformat(),
            "match_confidence": rollout_data.get("match_confidence", 0),
            "match_type": rollout_data.get("match_type", "unknown"),
        }

        async with self.session_factory() as session:
            # Get current source_metadata
            result = await session.execute(
                select(Company.source_metadata).where(Company.id == company_id)
            )
            current_metadata = result.scalar_one_or_none() or {}

            # Add rollout data to metadata
            if "rollout_quotas" not in current_metadata:
                current_metadata["rollout_quotas"] = []

            current_metadata["rollout_quotas"].append(quota_info)
            update_data["source_metadata"] = current_metadata

            # Update the company
            await session.execute(
                update(Company).where(Company.id == company_id).values(**update_data)
            )
            await session.commit()

    async def process_rollout_data(
        self, csv_file: Path, metadata_file: Path
    ) -> dict[str, Any]:
        """Main processing function to integrate rollout data."""
        logger.info("🔢 VNBdigitaler - Roll-Out Quoten Integration")
        logger.info("=" * 60)

        stats = {
            "total_rollout_companies": 0,
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "no_matches": 0,
            "low_confidence_matches": 0,
            "companies_updated": 0,
            "processing_errors": 0,
        }

        try:
            # Create RollOutReport entry
            report_id = await self.create_rollout_report_entry(metadata_file)

            # Load CSV data
            df = await self.load_csv_data(csv_file)
            stats["total_rollout_companies"] = len(df)

            # Get companies from database
            db_companies = await self.get_companies_from_db()

            # Process each company in the rollout data
            logger.info(f"Processing {len(df)} companies from roll-out report...")

            no_match_companies = []
            low_confidence_companies = []

            for i, row in df.iterrows():
                company_name = row["Unternehmen"]
                ausstattungsquote = row.get("Ausstattungsquote", None)
                stichtag = row.get("Stichtag", DEFAULT_STICHTAG)

                # Truncate name for display
                display_name = (
                    company_name[:MAX_NAME_DISPLAY_LENGTH] + "..."
                    if len(company_name) > MAX_NAME_DISPLAY_LENGTH
                    else company_name
                )

                try:
                    # Match with database companies
                    match_result = self.match_company_names(company_name, db_companies)

                    if match_result["company_id"] is None:
                        stats["no_matches"] += 1
                        no_match_companies.append(company_name)
                        logger.warning(f"❌ No match [{i+1}/{len(df)}] {display_name}")
                    elif match_result["confidence"] < MIN_FUZZY_MATCH_SCORE:
                        stats["low_confidence_matches"] += 1
                        low_confidence_companies.append(
                            {"name": company_name, "match": match_result}
                        )
                        logger.warning(
                            f"⚠️  Low confidence [{i+1}/{len(df)}] {display_name} -> {match_result['matched_name']} ({match_result['confidence']}%)"
                        )
                    else:
                        # Good match - update company
                        if match_result["match_type"].startswith("exact"):
                            stats["exact_matches"] += 1
                            logger.info(
                                f"✅ Exact match [{i+1}/{len(df)}] {display_name} -> {match_result['matched_name']}"
                            )
                        else:
                            stats["fuzzy_matches"] += 1
                            logger.info(
                                f"🔄 Fuzzy match [{i+1}/{len(df)}] {display_name} -> {match_result['matched_name']} ({match_result['confidence']}%)"
                            )

                        # Update company with rollout data
                        rollout_data = {
                            "rollout_name": company_name,
                            "ausstattungsquote": ausstattungsquote,
                            "stichtag": stichtag,
                            "match_confidence": match_result["confidence"],
                            "match_type": match_result["match_type"],
                        }

                        await self.update_company_rollout_data(
                            match_result["company_id"], rollout_data
                        )
                        stats["companies_updated"] += 1

                except Exception as e:
                    stats["processing_errors"] += 1
                    logger.error(
                        f"❌ Error processing [{i+1}/{len(df)}] {display_name}: {e}"
                    )

                # Small delay to avoid overwhelming the database
                await asyncio.sleep(0.01)

            # Mark report as processed
            if not self.dry_run and report_id > 0:
                async with self.session_factory() as session:
                    await session.execute(
                        update(RollOutReport)
                        .where(RollOutReport.id == report_id)
                        .values(is_processed=True)
                    )
                    await session.commit()

            # Report final statistics
            logger.info("\n" + "=" * 50)
            logger.info("ROLL-OUT QUOTEN INTEGRATION COMPLETED")
            logger.info("=" * 50)
            logger.info(
                f"Total companies in roll-out report: {stats['total_rollout_companies']}"
            )
            logger.info(f"Exact matches: {stats['exact_matches']}")
            logger.info(f"Fuzzy matches: {stats['fuzzy_matches']}")
            logger.info(f"No matches: {stats['no_matches']}")
            logger.info(f"Low confidence matches: {stats['low_confidence_matches']}")
            logger.info(f"Companies updated: {stats['companies_updated']}")

            if stats["total_rollout_companies"] > 0:
                match_rate = (
                    (stats["exact_matches"] + stats["fuzzy_matches"])
                    / stats["total_rollout_companies"]
                ) * 100
                logger.info(f"Overall match rate: {match_rate:.1f}%")

            logger.info("=" * 50)

            # Log unmatched companies
            if no_match_companies:
                logger.warning(
                    f"\n❌ Companies without matches ({len(no_match_companies)}):"
                )
                for name in no_match_companies[:MAX_NO_MATCH_DISPLAY]:  # Show first 10
                    logger.warning(f"  - {name}")
                if len(no_match_companies) > MAX_NO_MATCH_DISPLAY:
                    logger.warning(
                        f"  ... and {len(no_match_companies) - MAX_NO_MATCH_DISPLAY} more"
                    )

            # Log low confidence matches
            if low_confidence_companies:
                logger.warning(
                    f"\n⚠️  Low confidence matches ({len(low_confidence_companies)}):"
                )
                for item in low_confidence_companies[
                    :MAX_LOW_CONFIDENCE_DISPLAY
                ]:  # Show first 5
                    logger.warning(
                        f"  - {item['name']} -> {item['match']['matched_name']} ({item['match']['confidence']}%)"
                    )
                if len(low_confidence_companies) > MAX_LOW_CONFIDENCE_DISPLAY:
                    logger.warning(
                        f"  ... and {len(low_confidence_companies) - MAX_LOW_CONFIDENCE_DISPLAY} more"
                    )

            if stats["companies_updated"] > 0:
                logger.info("✅ Roll-out quota integration completed successfully!")
            else:
                logger.warning("⚠️  No companies were updated with roll-out data")

            return stats

        except Exception as e:
            logger.error(f"❌ Roll-out integration failed: {e}")
            raise

    async def cleanup(self):
        """Clean up resources."""
        await self.engine.dispose()


def find_latest_csv_and_metadata() -> tuple[Path | None, Path | None]:
    """Find the most recent CSV and metadata files from the download process."""
    workspace_root = Path(__file__).parent.parent
    temp_dir = workspace_root / "tmp"

    if not temp_dir.exists():
        return None, None

    # Look for BNetzA download directories
    csv_files = []
    metadata_files = []

    for dir_path in temp_dir.glob("bnetza_download_*"):
        # Look for CSV files
        csv_candidates = list(dir_path.glob("*.csv"))
        for csv_file in csv_candidates:
            csv_files.append(csv_file)

        # Look for metadata
        metadata_file = dir_path / "download_conversion_metadata.json"
        if metadata_file.exists():
            metadata_files.append(metadata_file)

    if not csv_files:
        return None, None

    # Return the most recent files
    latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
    latest_metadata = (
        max(metadata_files, key=lambda f: f.stat().st_mtime) if metadata_files else None
    )

    return latest_csv, latest_metadata


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Integrate Roll-Out Quoten data into the companies database"
    )
    parser.add_argument(
        "--csv-file",
        type=Path,
        help="Path to CSV file with roll-out data (default: auto-detect latest)",
    )
    parser.add_argument(
        "--metadata-file",
        type=Path,
        help="Path to metadata JSON file from download process (default: auto-detect latest)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform dry run without updating database",
    )
    return parser.parse_args()


async def main():
    """Main execution function."""
    args = parse_arguments()

    # Auto-detect files if not provided
    if not args.csv_file or not args.metadata_file:
        csv_file, metadata_file = find_latest_csv_and_metadata()

        if not args.csv_file:
            args.csv_file = csv_file
        if not args.metadata_file:
            args.metadata_file = metadata_file

        if not args.csv_file:
            logger.error(
                "❌ No CSV file found. Run scripts 10-12 first to download and convert data."
            )
            sys.exit(1)

        if not args.metadata_file:
            logger.error(
                "❌ No metadata file found. Run scripts 10-12 first to download and convert data."
            )
            sys.exit(1)

        logger.info(f"📁 Using CSV file: {args.csv_file}")
        logger.info(f"📁 Using metadata file: {args.metadata_file}")

    if args.dry_run:
        logger.info("🔄 Dry run mode enabled")

    # Get database configuration
    database_url = get_database_url()
    logger.info("Database connection configured")

    # Create integrator
    integrator = RollOutDataIntegrator(database_url, dry_run=args.dry_run)

    try:
        # Process the data
        stats = await integrator.process_rollout_data(args.csv_file, args.metadata_file)

        if not args.dry_run and stats["companies_updated"] > 0:
            print(
                f"\n✅ Integration completed! Updated {stats['companies_updated']} companies."
            )
        elif args.dry_run:
            print(
                f"\n✅ Dry run completed! Would update {stats['exact_matches'] + stats['fuzzy_matches']} companies."
            )
        else:
            print("\n⚠️  Integration completed but no companies were updated.")

    except KeyboardInterrupt:
        logger.info("\n❌ Integration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Integration failed: {e}")
        sys.exit(1)
    finally:
        await integrator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
