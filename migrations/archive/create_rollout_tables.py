#!/usr/bin/env python3
"""
Migration: Create new rollout tables (rollout_companies and rollout_quotas)

This migration creates the new normalized table structure for rollout data
and provides functions to migrate existing data from rollout_entries.
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import insert, select, text

from src.database import get_db_manager
from src.models import Company, RolloutCompany, RolloutEntry, RolloutQuota

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


async def create_tables():
    """Create the new rollout tables."""
    print("🏗️  Creating new rollout tables...")

    db_manager = get_db_manager()

    async for session in db_manager.get_async_session():
        # Create tables using raw SQL
        await session.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS rollout_companies (
                id SERIAL PRIMARY KEY,
                bnetza_name VARCHAR(500) UNIQUE NOT NULL,
                normalized_name VARCHAR(500) NOT NULL,
                bdew_company_id INTEGER REFERENCES companies(id),
                is_manually_verified BOOLEAN DEFAULT FALSE NOT NULL,
                verification_notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
            );
        """
            )
        )

        # Create rollout_quotas table
        await session.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS rollout_quotas (
                id SERIAL PRIMARY KEY,
                rollout_company_id INTEGER REFERENCES rollout_companies(id) NOT NULL,
                rollout_quota DECIMAL(10,6) NOT NULL,
                reference_date DATE NOT NULL,
                report_quarter VARCHAR(10),
                source_file VARCHAR(200) NOT NULL,
                csv_line_number INTEGER,
                import_date TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                import_metadata JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

                CONSTRAINT chk_quota_range CHECK (rollout_quota >= 0.0 AND rollout_quota <= 1.0),
                CONSTRAINT uq_rollout_quota_company_date_quarter UNIQUE (rollout_company_id, reference_date, report_quarter)
            );
        """
            )
        )

        # Create indexes
        await session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rollout_companies_bnetza_name ON rollout_companies(bnetza_name);"
            )
        )
        await session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rollout_companies_normalized_name ON rollout_companies(normalized_name);"
            )
        )
        await session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rollout_companies_bdew_company_id ON rollout_companies(bdew_company_id);"
            )
        )

        await session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rollout_quotas_company_id ON rollout_quotas(rollout_company_id);"
            )
        )
        await session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rollout_quotas_reference_date ON rollout_quotas(reference_date);"
            )
        )
        await session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_rollout_quotas_report_quarter ON rollout_quotas(report_quarter);"
            )
        )

        await session.commit()

        print("✅ Tables created successfully")
        break


async def migrate_existing_data():
    """Migrate data from rollout_entries to the new table structure."""
    print("🔄 Migrating existing rollout data...")

    db_manager = get_db_manager()

    async for session in db_manager.get_async_session():
        # Get all existing rollout entries
        rollout_query = select(RolloutEntry)
        result = await session.execute(rollout_query)
        rollout_entries = result.scalars().all()

        print(f"📊 Found {len(rollout_entries)} rollout entries to migrate")

        # Get all BDEW companies for matching
        company_query = select(Company).where(Company.rollout_report_name.is_not(None))
        company_result = await session.execute(company_query)
        companies = company_result.scalars().all()

        # Create lookup for BDEW companies by rollout_report_name
        bdew_lookup = {
            company.rollout_report_name: company.id
            for company in companies
            if company.rollout_report_name
        }
        print(f"📊 Found {len(bdew_lookup)} BDEW companies for matching")

        # Step 1: Create unique companies
        unique_companies = {}  # bnetza_name -> company_data

        for entry in rollout_entries:
            if entry.company_name not in unique_companies:
                # Check if this company matches a BDEW company
                bdew_company_id = bdew_lookup.get(entry.company_name)

                unique_companies[entry.company_name] = {
                    "bnetza_name": entry.company_name,
                    "normalized_name": entry.name_normalized,
                    "bdew_company_id": bdew_company_id,
                    "is_manually_verified": False,
                }

        print(f"📊 Found {len(unique_companies)} unique companies")

        # Insert companies
        company_id_mapping = {}  # bnetza_name -> new_id

        for company_data in unique_companies.values():
            insert_stmt = (
                insert(RolloutCompany)
                .values(**company_data)
                .returning(RolloutCompany.id, RolloutCompany.bnetza_name)
            )
            result = await session.execute(insert_stmt)
            row = result.fetchone()
            if row:
                company_id_mapping[row[1]] = row[0]  # row[1] = bnetza_name, row[0] = id

        print(f"✅ Inserted {len(company_id_mapping)} companies")

        # Step 2: Create quota entries
        quota_data = []

        for entry in rollout_entries:
            # Determine report quarter from source file or reference date
            report_quarter = None
            if "Q1_2025" in entry.source_file:
                report_quarter = "2025Q1"
            elif entry.reference_date:
                year = entry.reference_date.year
                month = entry.reference_date.month
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

            quota_data.append(
                {
                    "rollout_company_id": company_id_mapping[entry.company_name],
                    "rollout_quota": entry.rollout_quota,
                    "reference_date": entry.reference_date,
                    "report_quarter": report_quarter,
                    "source_file": entry.source_file,
                    "csv_line_number": entry.csv_line_number,
                    "import_metadata": entry.import_metadata,
                }
            )

        # Insert quotas in batches
        batch_size = 100
        for i in range(0, len(quota_data), batch_size):
            batch = quota_data[i : i + batch_size]
            await session.execute(insert(RolloutQuota), batch)
            print(
                f"✅ Inserted quota batch {i//batch_size + 1}/{(len(quota_data) + batch_size - 1)//batch_size}"
            )

        await session.commit()
        print(f"✅ Migrated {len(quota_data)} quota entries")
        break


async def verify_migration():
    """Verify that the migration was successful."""
    print("🔍 Verifying migration...")

    db_manager = get_db_manager()

    async for session in db_manager.get_async_session():
        # Count records in old table
        old_count_result = await session.execute(
            select(func.count()).select_from(RolloutEntry)
        )
        old_count = old_count_result.scalar()

        # Count records in new tables
        company_count_result = await session.execute(
            select(func.count()).select_from(RolloutCompany)
        )
        company_count = company_count_result.scalar() or 0

        quota_count_result = await session.execute(
            select(func.count()).select_from(RolloutQuota)
        )
        quota_count = quota_count_result.scalar() or 0

        # Count matched companies
        matched_count_result = await session.execute(
            select(func.count())
            .select_from(RolloutCompany)
            .where(RolloutCompany.bdew_company_id.is_not(None))
        )
        matched_count = matched_count_result.scalar() or 0

        print("\n📊 Migration Results:")
        print(f"   Old rollout_entries: {old_count}")
        print(f"   New rollout_companies: {company_count}")
        print(f"   New rollout_quotas: {quota_count}")
        print(f"   Companies with BDEW link: {matched_count}")
        print(
            f"   Match rate: {(matched_count / company_count * 100):.1f}%"
            if company_count > 0
            else "   Match rate: 0%"
        )

        if quota_count == old_count:
            print("✅ Migration successful - quota count matches")
        else:
            print(
                f"⚠️  Warning: quota count mismatch (old: {old_count}, new: {quota_count})"
            )

        break


async def main():
    """Run the complete migration."""
    print("🚀 Starting rollout table migration...")

    try:
        await create_tables()
        await migrate_existing_data()
        await verify_migration()

        print("\n✅ Migration completed successfully!")
        print("\n📝 Next steps:")
        print("   1. Update the router to use the new tables")
        print("   2. Test the new API endpoints")
        print("   3. Consider backing up and dropping the old rollout_entries table")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    # Import func here to avoid circular imports
    from sqlalchemy import func

    asyncio.run(main())
