#!/usr/bin/env python3
"""
VNBdigitaler - Add Manual Check Column Migration

This script adds a new column 'rollout_company_manually_checked' to the companies table
to track whether rollout company name assignments have been manually verified.

Usage:
    python tools/15_add_manual_check_column.py [--dry-run]

Author: GitHub Copilot
Date: 2025-08-22
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# isort: off
from src.config import get_settings  # noqa: E402

# isort: on

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class ManualCheckColumnMigration:
    """Migration to add rollout_company_manually_checked column to companies table."""

    def __init__(self, dry_run: bool = False):
        """Initialize the migration."""
        self.dry_run = dry_run
        self.settings = get_settings()

        # Create async engine
        db_url = self.settings.neon_database_url
        # Ensure we use asyncpg driver for async support
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql+psycopg2://"):
            db_url = db_url.replace(
                "postgresql+psycopg2://", "postgresql+asyncpg://", 1
            )

        # Remove all URL parameters to avoid asyncpg compatibility issues
        if "?" in db_url:
            db_url = db_url.split("?")[0]

        self.engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
        )

        # Create session factory
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def check_column_exists(self) -> bool:
        """Check if the rollout_company_manually_checked column already exists."""
        check_query = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'companies'
            AND column_name = 'rollout_company_manually_checked'
        );
        """

        async with self.session_factory() as session:
            result = await session.execute(text(check_query))
            exists = result.scalar()
            return bool(exists)

    async def add_column(self) -> None:
        """Add the rollout_company_manually_checked column to the companies table."""
        add_column_query = """
        ALTER TABLE companies
        ADD COLUMN rollout_company_manually_checked BOOLEAN DEFAULT FALSE;
        """

        # Add comment to the column for documentation
        add_comment_query = """
        COMMENT ON COLUMN companies.rollout_company_manually_checked
        IS 'Indicates whether the rollout company name assignment has been manually verified by a human operator';
        """

        # Create index for performance
        create_index_query = """
        CREATE INDEX idx_companies_manually_checked
        ON companies(rollout_company_manually_checked);
        """

        if self.dry_run:
            logger.info("🔍 DRY RUN - Would execute the following SQL:")
            logger.info(f"   1. {add_column_query.strip()}")
            logger.info(f"   2. {add_comment_query.strip()}")
            logger.info(f"   3. {create_index_query.strip()}")
            return

        async with self.session_factory() as session:
            try:
                # Add the column
                logger.info("📝 Adding rollout_company_manually_checked column...")
                await session.execute(text(add_column_query))

                # Add comment
                logger.info("📋 Adding column comment...")
                await session.execute(text(add_comment_query))

                # Create index
                logger.info("🗂️ Creating index for performance...")
                await session.execute(text(create_index_query))

                # Commit all changes
                await session.commit()
                logger.info("✅ Column and index created successfully!")

            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Error during migration: {e}")
                raise

    async def verify_migration(self) -> bool:
        """Verify that the migration was successful."""
        # Check column exists and has correct properties
        verify_query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = 'companies'
        AND column_name = 'rollout_company_manually_checked';
        """

        # Check index exists
        index_query = """
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'companies'
        AND indexname = 'idx_companies_manually_checked';
        """

        async with self.session_factory() as session:
            # Verify column
            result = await session.execute(text(verify_query))
            column_info = result.fetchone()

            if column_info:
                logger.info("✅ Column verification:")
                logger.info(f"   - Name: {column_info.column_name}")
                logger.info(f"   - Type: {column_info.data_type}")
                logger.info(f"   - Nullable: {column_info.is_nullable}")
                logger.info(f"   - Default: {column_info.column_default}")
            else:
                logger.error("❌ Column was not created properly!")
                return False

            # Verify index
            result = await session.execute(text(index_query))
            index_info = result.fetchone()

            if index_info:
                logger.info(f"✅ Index created: {index_info.indexname}")
            else:
                logger.error("❌ Index was not created properly!")
                return False

        return True

    async def get_companies_summary(self) -> dict:
        """Get summary statistics about companies table after migration."""
        summary_query = """
        SELECT
            COUNT(*) as total_companies,
            COUNT(CASE WHEN rollout_report_name IS NOT NULL THEN 1 END) as companies_with_rollout_name,
            COUNT(CASE WHEN rollout_company_manually_checked = TRUE THEN 1 END) as manually_checked_companies,
            COUNT(CASE WHEN manual_verification = TRUE THEN 1 END) as manually_verified_companies
        FROM companies;
        """

        async with self.session_factory() as session:
            result = await session.execute(text(summary_query))
            row = result.fetchone()

            if row is None:
                return {
                    "total_companies": 0,
                    "companies_with_rollout_name": 0,
                    "manually_checked_companies": 0,
                    "manually_verified_companies": 0,
                }

            return {
                "total_companies": row.total_companies,
                "companies_with_rollout_name": row.companies_with_rollout_name,
                "manually_checked_companies": row.manually_checked_companies,
                "manually_verified_companies": row.manually_verified_companies,
            }

    async def run_migration(self) -> bool:
        """Run the complete migration process."""
        try:
            logger.info("🚀 VNBdigitaler - Manual Check Column Migration")
            logger.info("=" * 60)

            # Check if column already exists
            logger.info("🔍 Checking if column already exists...")
            if await self.check_column_exists():
                logger.warning(
                    "⚠️ Column 'rollout_company_manually_checked' already exists!"
                )
                logger.info("📊 Current statistics:")
                stats = await self.get_companies_summary()
                for key, value in stats.items():
                    logger.info(f"   - {key.replace('_', ' ').title()}: {value}")
                return True

            # Add the column
            await self.add_column()

            if not self.dry_run:
                # Verify migration
                logger.info("🔍 Verifying migration...")
                if not await self.verify_migration():
                    return False

                # Show summary
                logger.info("📊 Post-migration statistics:")
                stats = await self.get_companies_summary()
                for key, value in stats.items():
                    logger.info(f"   - {key.replace('_', ' ').title()}: {value}")

            logger.info("🎉 Migration completed successfully!")
            return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
        finally:
            await self.engine.dispose()


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Add rollout_company_manually_checked column to companies table"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )

    args = parser.parse_args()

    migration = ManualCheckColumnMigration(dry_run=args.dry_run)
    success = await migration.run_migration()

    if success:
        logger.info("✅ Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
