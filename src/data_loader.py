"""Data loaders for VNBdigitaler matching system."""

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

try:
    from .config import get_settings
    from .matching_models import BDEWCompany, BNetzACompany
    from .models import Company
except ImportError:
    # When run as script, use absolute imports
    from src.config import get_settings
    from src.matching_models import BDEWCompany, BNetzACompany
    from src.models import Company

logger = logging.getLogger(__name__)


class DataLoader:
    """Load data from various sources into matching models."""

    def __init__(self) -> None:
        """Initialize data loader."""
        self.settings = get_settings()
        self.engine = create_async_engine(self.settings.database_url)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession)

    async def load_bdew_companies_from_db(self) -> list[BDEWCompany]:
        """Load BDEW companies from database."""
        logger.info("Loading BDEW companies from database...")

        async with self.session_factory() as session:
            result = await session.execute(
                select(
                    Company.bdew_code,
                    Company.bdew_name,
                    Company.bdew_city,
                    Company.bdew_name_normalized,
                )
            )
            rows = result.fetchall()

        companies = []
        for row in rows:
            company = BDEWCompany(
                bdew_code=row.bdew_code,
                name=row.bdew_name,
                city=row.bdew_city,
                normalized_name=row.bdew_name_normalized,
            )
            companies.append(company)

        logger.info(f"Loaded {len(companies)} BDEW companies from database")
        return companies

    def load_bnetza_companies_from_csv(self, csv_path: Path) -> list[BNetzACompany]:
        """Load BNetzA companies from CSV file."""
        logger.info(f"Loading BNetzA companies from CSV: {csv_path}")

        df = pd.read_csv(csv_path)
        companies = []

        for idx, (_, row) in enumerate(df.iterrows()):
            # Handle different possible column names
            original_name = ""
            rollout_quote = None

            # Try different column name variations
            if "original_name" in row:
                original_name = row["original_name"]
            elif "company_name" in row:
                original_name = row["company_name"]
            elif "name" in row:
                original_name = row["name"]
            else:
                # Use the first string column as name
                for col in df.columns:
                    if df[col].dtype == "object" and pd.notna(row[col]):
                        original_name = str(row[col])
                        break

            # Try to get rollout quote
            if "ausstattungsquote" in row:
                quote_val = row["ausstattungsquote"]
                if pd.notna(quote_val) and quote_val != "":
                    try:
                        rollout_quote = float(quote_val)
                    except (ValueError, TypeError):
                        rollout_quote = None
            elif "rollout_quote" in row:
                quote_val = row["rollout_quote"]
                if pd.notna(quote_val) and quote_val != "":
                    try:
                        rollout_quote = float(quote_val)
                    except (ValueError, TypeError):
                        rollout_quote = None

            if original_name.strip():
                company = BNetzACompany(
                    index=idx,
                    original_name=original_name.strip(),
                    rollout_quote=rollout_quote,
                )
                companies.append(company)

        logger.info(f"Loaded {len(companies)} BNetzA companies from CSV")
        return companies

    def load_bdew_companies_from_csv(self, csv_path: Path) -> list[BDEWCompany]:
        """Load BDEW companies from CSV file."""
        logger.info(f"Loading BDEW companies from CSV: {csv_path}")

        df = pd.read_csv(csv_path)
        companies = []

        for _index, row in df.iterrows():
            # Handle different possible column names
            bdew_code = ""
            name = ""
            city = None

            # Try to get BDEW code
            if "bdew_code" in row:
                bdew_code = str(row["bdew_code"])
            elif "code" in row:
                bdew_code = str(row["code"])
            elif "id" in row:
                bdew_code = str(row["id"])

            # Try to get company name
            if "original_name" in row:
                name = row["original_name"]
            elif "name" in row:
                name = row["name"]
            elif "company_name" in row:
                name = row["company_name"]
            elif "bdew_name" in row:
                name = row["bdew_name"]

            # Try to get city
            if "city" in row and pd.notna(row["city"]):
                city = row["city"]
            elif "bdew_city" in row and pd.notna(row["bdew_city"]):
                city = row["bdew_city"]

            if bdew_code and name:
                company = BDEWCompany(
                    bdew_code=bdew_code,
                    name=name.strip(),
                    city=city.strip() if city else None,
                )
                companies.append(company)

        logger.info(f"Loaded {len(companies)} BDEW companies from CSV")
        return companies

    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()


def export_matches_to_csv(matches: list[Any], output_path: Path) -> None:
    """Export matches to CSV file."""
    logger.info(f"Exporting {len(matches)} matches to: {output_path}")

    # Convert matches to dictionaries
    data = []
    for match in matches:
        if hasattr(match, "to_dict"):
            data.append(match.to_dict())
        else:
            # Handle other match types if needed
            data.append(match)

    # Create DataFrame and save
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)

    logger.info(f"Successfully exported matches to {output_path}")


def export_companies_to_csv(companies: list[Any], output_path: Path) -> None:
    """Export companies to CSV file."""
    logger.info(f"Exporting {len(companies)} companies to: {output_path}")

    # Convert companies to dictionaries
    data = []
    for company in companies:
        if isinstance(company, BNetzACompany):
            data.append(
                {
                    "bnetza_index": company.index,
                    "original_name": company.original_name,
                    "normalized_name": company.normalized_name,
                    "rollout_quote": company.rollout_quote or "",
                }
            )
        elif isinstance(company, BDEWCompany):
            data.append(
                {
                    "bdew_code": company.bdew_code,
                    "original_name": company.name,
                    "city": company.city or "",
                    "normalized_name": company.normalized_name,
                }
            )
        else:
            # Handle other company types - ensure dict format
            company_data = (
                company.__dict__
                if hasattr(company, "__dict__")
                else {"name": str(company)}
            )
            data.append(company_data)

    # Create DataFrame and save
    df = pd.DataFrame(data)
    df.to_csv(output_path, index=False)

    logger.info(f"Successfully exported companies to {output_path}")


if __name__ == "__main__":
    import argparse
    import subprocess
    import sys

    def main() -> None:
        """Main function with CLI argument support."""
        parser = argparse.ArgumentParser(description="Data loader for VNBdigitaler")
        parser.add_argument(
            "--rollout-quota-update",
            action="store_true",
            help="Download and convert BNetzA rollout quota reports",
        )

        args = parser.parse_args()

        if args.rollout_quota_update:
            print("📥 Starting BNetzA rollout quota reports download and conversion...")
            print("🔍 Step 1: Discovering available reports...")

            # Use the existing BNetzA rollout report updater
            try:
                print(
                    "⏳ Step 2: Downloading and processing reports (this may take a few minutes)..."
                )

                # Run with timeout (10 minutes) and real-time output
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "src.bnetza.rollout_report_updater",
                        "--download-dir=data",
                        "--force-update",
                        "--verbose",
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )

                print("✅ Step 3: Processing completed successfully!")

                # Parse and display relevant output
                output_lines = result.stdout.split("\n")
                for line in output_lines:
                    # Show important progress messages
                    if any(
                        keyword in line.lower()
                        for keyword in [
                            "downloading",
                            "processing",
                            "imported",
                            "final state",
                            "report:",
                            "records",
                            "completed",
                        ]
                    ):
                        print(f"  📊 {line.strip()}")

                print("🎯 Rollout quota data successfully updated!")

            except subprocess.TimeoutExpired:
                print(
                    "⏰ Download timed out after 10 minutes - BNetzA server may be slow"
                )
                print(
                    "💡 Try running the command again or check your internet connection"
                )
                sys.exit(1)
            except subprocess.CalledProcessError as e:
                print(
                    f"❌ Failed to download rollout reports (exit code: {e.returncode})"
                )
                if e.stdout:
                    print("📋 Output:")
                    print(e.stdout)
                if e.stderr:
                    print("🚨 Error details:")
                    print(e.stderr)
                sys.exit(1)
        else:
            print(
                "No action specified. Use --rollout-quota-update to download reports."
            )

    main()
