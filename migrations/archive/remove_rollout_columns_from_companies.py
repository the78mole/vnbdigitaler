#!/usr/bin/env python3
"""
Migration: Remove rollout_report_name and rollout_name_variations from companies table

This migration removes the rollout_report_name and rollout_name_variations columns
from the companies table since this information is now managed in the rollout_companies table.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text

from src.database import get_db_manager


async def remove_rollout_columns():
    """Remove rollout_report_name and rollout_name_variations columns from companies table."""
    db_manager = get_db_manager()

    print("🗑️  Removing rollout columns from companies table...")

    async with db_manager.async_engine.begin() as conn:
        # Check if columns exist before trying to drop them
        check_columns_sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'companies'
        AND column_name IN ('rollout_report_name', 'rollout_name_variations');
        """

        result = await conn.execute(text(check_columns_sql))
        existing_columns = [row[0] for row in result.fetchall()]

        if "rollout_report_name" in existing_columns:
            print("  - Dropping rollout_report_name column...")
            await conn.execute(
                text("ALTER TABLE companies DROP COLUMN rollout_report_name;")
            )
        else:
            print("  - rollout_report_name column already removed")

        if "rollout_name_variations" in existing_columns:
            print("  - Dropping rollout_name_variations column...")
            await conn.execute(
                text("ALTER TABLE companies DROP COLUMN rollout_name_variations;")
            )
        else:
            print("  - rollout_name_variations column already removed")

    print("✅ Rollout columns removed from companies table")


async def main():
    """Run the migration."""
    print("📋 Migration: Remove rollout columns from companies table")
    print("=" * 60)

    try:
        await remove_rollout_columns()
        print("\n🎉 Migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
