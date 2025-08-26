#!/usr/bin/env python3
"""
Migration: Remove unused rollout_company_manually_checked column from companies table

This migration removes the unused rollout_company_manually_checked column
from the companies table.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text

from src.database import get_db_manager


async def remove_unused_rollout_column():
    """Remove rollout_company_manually_checked column from companies table."""
    db_manager = get_db_manager()

    print(
        "🗑️  Removing unused rollout_company_manually_checked column from companies table..."
    )

    async with db_manager.async_engine.begin() as conn:
        # Check if column exists before trying to drop it
        check_column_sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'companies'
        AND column_name = 'rollout_company_manually_checked';
        """

        result = await conn.execute(text(check_column_sql))
        existing_column = result.fetchone()

        if existing_column:
            print("  - Dropping rollout_company_manually_checked column...")
            await conn.execute(
                text(
                    "ALTER TABLE companies DROP COLUMN rollout_company_manually_checked;"
                )
            )
            print("  ✅ rollout_company_manually_checked column removed")
        else:
            print("  - rollout_company_manually_checked column already removed")

    print("✅ Unused rollout column removed from companies table")


async def main():
    """Run the migration."""
    print("📋 Migration: Remove unused rollout_company_manually_checked column")
    print("=" * 65)

    try:
        await remove_unused_rollout_column()
        print("\n🎉 Migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
