#!/usr/bin/env python3
"""
Import BNetzA Roll-Out CSV data into the database using the new table structure.
"""

import asyncio
import csv
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select, text

from src.data_loader import DataLoader
from src.models import Base, RolloutCompany, RolloutQuota


def normalize_company_name(name: str) -> str:
    """Normalize company name for matching."""
    if not name:
        return ""

    # Basic normalization
    normalized = name.strip()
    normalized = normalized.replace("  ", " ")  # Multiple spaces to single space
    normalized = normalized.lower()

    # Remove common legal suffixes for better matching
    suffixes = [
        " gmbh",
        " gmbh & co. kg",
        " gmbh & co kg",
        " gmbh&co.kg",
        " ag",
        " kg",
        " e.g.",
        " eg",
        " ohg",
        " mbh",
        " se",
        " co. kg",
        " co kg",
        " ug",
        " ltd",
        " gesellschaft mit beschränkter haftung",
        " aktiengesellschaft",
        " kommanditgesellschaft",
    ]

    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
            break

    return normalized


async def create_tables_if_not_exist():
    """Create tables if they don't exist."""
    data_loader = DataLoader()

    async with data_loader.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Tables created/verified")


async def import_rollout_csv(csv_file_path: str):
    """Import Roll-Out CSV data into the database using the new table structure."""

    if not Path(csv_file_path).exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

    print(f"📂 Importing Roll-Out data from: {csv_file_path}")

    # Create tables first
    await create_tables_if_not_exist()

    data_loader = DataLoader()
    source_filename = Path(csv_file_path).name

    # Read and parse CSV data first
    companies_data = {}  # bnetza_name -> normalized_name
    quota_entries = []
    line_number = 0

    try:
        with Path(csv_file_path).open(encoding="utf-8") as csvfile:
            # Detect delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter

            reader = csv.DictReader(csvfile, delimiter=delimiter)

            # Show available columns for debugging
            if reader.fieldnames:
                print(f"📋 Available CSV columns: {', '.join(reader.fieldnames)}")

            for row in reader:
                line_number += 1

                # Extract data from CSV columns
                company_name = row.get("Unternehmen", "").strip()

                # Try different column names for quota (header changes with each report)
                quota_str = ""
                possible_quota_columns = [
                    "Ausstattungsquote",
                    "Ausstattungsquote zum 31. März 2025",
                    "Ausstattungsquote zum 31.03.2025",
                    "Ausstattungsquote zum 31. Dezember 2024",
                    "Ausstattungsquote zum 31.12.2024",
                ]

                for col_name in possible_quota_columns:
                    if col_name in row and row[col_name].strip():
                        quota_str = row[col_name].strip()
                        break

                date_str = row.get("Stichtag", "").strip()

                if not company_name:
                    print(f"⚠️  Skipping line {line_number}: No company name")
                    continue

                # Parse quota
                try:
                    rollout_quota = (
                        float(quota_str.replace(",", ".")) if quota_str else 0.0
                    )
                except ValueError:
                    print(
                        f"⚠️  Line {line_number}: Invalid quota '{quota_str}', defaulting to 0.0"
                    )
                    rollout_quota = 0.0

                # Parse date
                try:
                    if date_str:
                        reference_date = datetime.strptime(date_str, "%d.%m.%Y").date()
                    else:
                        reference_date = datetime.strptime(
                            "31.03.2025", "%d.%m.%Y"
                        ).date()
                except ValueError:
                    print(
                        f"⚠️  Line {line_number}: Invalid date '{date_str}', using default"
                    )
                    reference_date = datetime.strptime("31.03.2025", "%d.%m.%Y").date()

                # Store company data
                normalized_name = normalize_company_name(company_name)
                companies_data[company_name] = normalized_name

                # Determine report quarter from source file or reference date
                report_quarter = None
                if "Q1_2025" in source_filename:
                    report_quarter = "2025Q1"
                elif reference_date:
                    year = reference_date.year
                    month = reference_date.month
                    # Quarter calculation constants
                    Q1_MAX_MONTH = 3
                    Q2_MAX_MONTH = 6
                    Q3_MAX_MONTH = 9
                    if month <= Q1_MAX_MONTH:
                        report_quarter = f"{year}Q1"
                    elif month <= Q2_MAX_MONTH:
                        report_quarter = f"{year}Q2"
                    elif month <= Q3_MAX_MONTH:
                        report_quarter = f"{year}Q3"
                    else:
                        report_quarter = f"{year}Q4"

                # Store quota data (will link to company later)
                quota_entries.append(
                    {
                        "bnetza_name": company_name,
                        "rollout_quota": rollout_quota,
                        "reference_date": reference_date,
                        "report_quarter": report_quarter,
                        "source_file": source_filename,
                        "csv_line_number": line_number,
                        "import_metadata": {
                            "import_date": datetime.now().isoformat(),
                            "original_quota_string": quota_str,
                            "original_date_string": date_str,
                        },
                    }
                )

                if line_number % 100 == 0:
                    print(f"📊 Processed {line_number} lines...")

    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return

    print(f"📊 Parsed {len(quota_entries)} quota entries from CSV")
    print(f"📊 Found {len(companies_data)} unique companies")

    # Import into database
    async with data_loader.session_factory() as session:
        # Step 1: Insert/update companies
        company_id_mapping = {}  # bnetza_name -> rollout_company_id

        for bnetza_name, normalized_name in companies_data.items():
            # Check if company already exists
            existing_query = select(RolloutCompany).where(
                RolloutCompany.bnetza_name == bnetza_name
            )
            result = await session.execute(existing_query)
            existing_company = result.scalar_one_or_none()

            if existing_company:
                company_id_mapping[bnetza_name] = existing_company.id
            else:
                # Create new company
                new_company = RolloutCompany(
                    bnetza_name=bnetza_name,
                    normalized_name=normalized_name,
                )
                session.add(new_company)
                await session.flush()  # Get the ID
                company_id_mapping[bnetza_name] = new_company.id

        print(f"✅ Processed {len(company_id_mapping)} companies")

        # Step 2: Clear existing quota data for this source file
        await session.execute(
            text("DELETE FROM rollout_quotas WHERE source_file = :source_file"),
            {"source_file": source_filename},
        )
        print(f"🗑️  Deleted existing quota entries from {source_filename}")

        # Step 3: Insert quota entries
        quota_objects = []
        for quota_data in quota_entries:
            rollout_company_id = company_id_mapping[quota_data["bnetza_name"]]

            quota_entry = RolloutQuota(
                rollout_company_id=rollout_company_id,
                rollout_quota=quota_data["rollout_quota"],
                reference_date=quota_data["reference_date"],
                report_quarter=quota_data["report_quarter"],
                source_file=quota_data["source_file"],
                csv_line_number=quota_data["csv_line_number"],
                import_metadata=quota_data["import_metadata"],
            )
            quota_objects.append(quota_entry)

        session.add_all(quota_objects)
        await session.commit()
        print(f"✅ Imported {len(quota_objects)} quota entries into database")

    # Show summary statistics
    await show_import_statistics(source_filename)


async def show_import_statistics(source_filename: str):
    """Show import summary statistics."""
    data_loader = DataLoader()

    async with data_loader.session_factory() as session:
        # Total companies
        company_count_query = select(func.count()).select_from(RolloutCompany)
        company_result = await session.execute(company_count_query)
        total_companies = company_result.scalar()

        # Total quota entries
        quota_count_query = select(func.count()).select_from(RolloutQuota)
        quota_result = await session.execute(quota_count_query)
        total_quotas = quota_result.scalar()

        # Quota entries with quota > 0
        quota_gt_zero_query = (
            select(func.count())
            .select_from(RolloutQuota)
            .where(RolloutQuota.rollout_quota > 0)
        )
        quota_gt_zero_result = await session.execute(quota_gt_zero_query)
        quotas_with_value = quota_gt_zero_result.scalar()

        # Quota entries from this file
        file_quota_query = (
            select(func.count())
            .select_from(RolloutQuota)
            .where(RolloutQuota.source_file == source_filename)
        )
        file_quota_result = await session.execute(file_quota_query)
        file_quotas = file_quota_result.scalar()

        print("\n📈 Import Summary:")
        print(f"   Total companies: {total_companies}")
        print(f"   Total quota entries: {total_quotas}")
        print(f"   Quota entries from this file: {file_quotas}")
        print(f"   Quota entries with value > 0: {quotas_with_value}")
        print(f"   Source file: {source_filename}")


async def main():
    """Main import function."""
    csv_file = "data/Roll-out-Quoten_Q1_2025.csv"

    print("🚀 Starting BNetzA Roll-Out CSV import...")
    print(f"📁 CSV file: {csv_file}")

    try:
        await import_rollout_csv(csv_file)
        print("\n✅ Import completed successfully!")
    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
