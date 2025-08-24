#!/usr/bin/env python3
"""
Migration: Add geolocation column to companies table

This migration adds a new column to store the company headquarters location
as latitude/longitude coordinates. The column allows NULL values initially.
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

from src.database import get_db_manager

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


async def add_geolocation_column():
    """Add geolocation columns to companies table."""
    print("🏢 Adding geolocation columns to companies table...")

    db_manager = get_db_manager()

    async for session in db_manager.get_async_session():
        try:
            # Add latitude column
            add_latitude_sql = """
            ALTER TABLE companies
            ADD COLUMN company_latitude NUMERIC(10, 7);
            """

            await session.execute(text(add_latitude_sql))

            # Add longitude column
            add_longitude_sql = """
            ALTER TABLE companies
            ADD COLUMN company_longitude NUMERIC(10, 7);
            """

            await session.execute(text(add_longitude_sql))

            # Add comments to the columns
            comment_lat_sql = """
            COMMENT ON COLUMN companies.company_latitude IS
            'Company headquarters latitude in WGS84 decimal degrees (-90 to 90)';
            """

            comment_lng_sql = """
            COMMENT ON COLUMN companies.company_longitude IS
            'Company headquarters longitude in WGS84 decimal degrees (-180 to 180)';
            """

            await session.execute(text(comment_lat_sql))
            await session.execute(text(comment_lng_sql))

            # Add constraints for valid coordinate ranges
            lat_constraint_sql = """
            ALTER TABLE companies
            ADD CONSTRAINT chk_company_latitude
            CHECK (company_latitude IS NULL OR (company_latitude >= -90 AND company_latitude <= 90));
            """

            lng_constraint_sql = """
            ALTER TABLE companies
            ADD CONSTRAINT chk_company_longitude
            CHECK (company_longitude IS NULL OR (company_longitude >= -180 AND company_longitude <= 180));
            """

            await session.execute(text(lat_constraint_sql))
            await session.execute(text(lng_constraint_sql))

            # Create index for geospatial queries (both columns together)
            index_sql = """
            CREATE INDEX IF NOT EXISTS idx_companies_geolocation
            ON companies (company_latitude, company_longitude)
            WHERE company_latitude IS NOT NULL AND company_longitude IS NOT NULL;
            """

            await session.execute(text(index_sql))

            await session.commit()
            print("✅ Successfully added geolocation columns to companies table")
            print("📍 Columns: company_latitude, company_longitude (NUMERIC(10,7))")
            print("🔒 Constraints: Valid coordinate ranges (-90/90, -180/180)")
            print("🔍 Partial index created for non-NULL coordinates")

        except Exception as e:
            await session.rollback()
            print(f"❌ Error adding geolocation columns: {e}")
            raise


async def remove_geolocation_column():
    """Remove geolocation columns from companies table (rollback)."""
    print("🗑️ Removing geolocation columns from companies table...")

    db_manager = get_db_manager()

    async for session in db_manager.get_async_session():
        try:
            # Drop the index first
            drop_index_sql = """
            DROP INDEX IF EXISTS idx_companies_geolocation;
            """

            await session.execute(text(drop_index_sql))

            # Drop constraints
            drop_lat_constraint_sql = """
            ALTER TABLE companies DROP CONSTRAINT IF EXISTS chk_company_latitude;
            """

            drop_lng_constraint_sql = """
            ALTER TABLE companies DROP CONSTRAINT IF EXISTS chk_company_longitude;
            """

            await session.execute(text(drop_lat_constraint_sql))
            await session.execute(text(drop_lng_constraint_sql))

            # Drop the columns
            drop_latitude_sql = """
            ALTER TABLE companies DROP COLUMN IF EXISTS company_latitude;
            """

            drop_longitude_sql = """
            ALTER TABLE companies DROP COLUMN IF EXISTS company_longitude;
            """

            await session.execute(text(drop_latitude_sql))
            await session.execute(text(drop_longitude_sql))

            await session.commit()
            print("✅ Successfully removed geolocation columns from companies table")

        except Exception as e:
            await session.rollback()
            print(f"❌ Error removing geolocation columns: {e}")
            raise


async def verify_migration():
    """Verify that the migration was applied correctly."""
    print("🔍 Verifying geolocation columns...")

    db_manager = get_db_manager()

    async for session in db_manager.get_async_session():
        try:
            # Check if columns exist
            check_columns_sql = """
            SELECT
                column_name,
                data_type,
                numeric_precision,
                numeric_scale,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'companies'
            AND column_name IN ('company_latitude', 'company_longitude')
            ORDER BY column_name;
            """

            result = await session.execute(text(check_columns_sql))
            columns = result.fetchall()

            expected_columns = 2  # company_latitude and company_longitude
            if len(columns) == expected_columns:
                for col in columns:
                    print(f"✅ Column exists: {col.column_name}")
                    print(
                        f"   Data type: {col.data_type}({col.numeric_precision},{col.numeric_scale})"
                    )
                    print(f"   Nullable: {col.is_nullable}")
                    print(f"   Default: {col.column_default}")
            else:
                print(f"❌ Expected 2 columns, found {len(columns)}!")
                return False

            # Check if constraints exist
            check_constraints_sql = """
            SELECT constraint_name, check_clause
            FROM information_schema.check_constraints
            WHERE constraint_name IN ('chk_company_latitude', 'chk_company_longitude');
            """

            result = await session.execute(text(check_constraints_sql))
            constraints = result.fetchall()

            for constraint in constraints:
                print(f"✅ Constraint exists: {constraint.constraint_name}")
                print(f"   Check: {constraint.check_clause}")

            # Check if index exists
            check_index_sql = """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'companies'
            AND indexname = 'idx_companies_geolocation';
            """

            result = await session.execute(text(check_index_sql))
            index_info = result.fetchone()

            if index_info:
                print(f"✅ Index exists: {index_info.indexname}")
                print(f"   Definition: {index_info.indexdef}")
            else:
                print("⚠️ Geolocation index not found!")

            # Test coordinate validation
            test_sql = """
            SELECT
                CASE
                    WHEN 52.5200 BETWEEN -90 AND 90 THEN 'Valid latitude'
                    ELSE 'Invalid latitude'
                END as lat_test,
                CASE
                    WHEN 13.4050 BETWEEN -180 AND 180 THEN 'Valid longitude'
                    ELSE 'Invalid longitude'
                END as lng_test;
            """

            result = await session.execute(text(test_sql))
            test_result = result.fetchone()

            if test_result:
                print(
                    f"✅ Coordinate validation: {test_result.lat_test}, {test_result.lng_test}"
                )

            return True

        except Exception as e:
            print(f"❌ Error verifying migration: {e}")
            return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        asyncio.run(remove_geolocation_column())
    elif len(sys.argv) > 1 and sys.argv[1] == "verify":
        asyncio.run(verify_migration())
    else:
        asyncio.run(add_geolocation_column())
        print("\n🔍 Running verification...")
        asyncio.run(verify_migration())
