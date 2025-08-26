#!/usr/bin/env python3
"""
Migration: Remove is_manually_verified column from rollout_companies table

This migration removes the is_manually_verified column from the rollout_companies
table as manual verification is no longer needed in the simplified data model.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text

from src.database import get_db_manager


async def remove_manual_verification_column():
    """Remove is_manually_verified column from rollout_companies table."""
    db_manager = get_db_manager()

    print("🗑️  Removing is_manually_verified column from rollout_companies table...")

    async with db_manager.async_engine.begin() as conn:
        # Check if column exists before trying to drop it
        check_column_sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'rollout_companies'
        AND column_name = 'is_manually_verified';
        """

        result = await conn.execute(text(check_column_sql))
        existing_column = result.fetchone()

        if existing_column:
            print("  - Dropping is_manually_verified column...")
            await conn.execute(
                text("ALTER TABLE rollout_companies DROP COLUMN is_manually_verified;")
            )
            print("  ✅ is_manually_verified column removed")
        else:
            print("  - is_manually_verified column already removed")

    print("✅ Manual verification column removed from rollout_companies table")


async def main():
    """Run the migration."""
    print(
        "📋 Migration: Remove is_manually_verified column from rollout_companies table"
    )
    print("=" * 75)

    try:
        await remove_manual_verification_column()
        print("\n🎉 Migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
