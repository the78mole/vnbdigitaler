#!/usr/bin/env python3
"""
Migration: Remove verification and matching columns from companies table

This migration removes the manual_verification, verification_notes, and
name_matching_confidence columns from the companies table since this
information is now managed in the rollout_companies table.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text

from src.database import get_db_manager


async def remove_verification_columns():
    """Remove manual_verification, verification_notes, and name_matching_confidence columns from companies table."""
    db_manager = get_db_manager()

    print("🗑️  Removing verification and matching columns from companies table...")

    columns_to_remove = [
        "manual_verification",
        "verification_notes",
        "name_matching_confidence",
    ]

    async with db_manager.async_engine.begin() as conn:
        for column_name in columns_to_remove:
            # Check if column exists before trying to drop it
            check_column_sql = f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'companies'
            AND column_name = '{column_name}';
            """

            result = await conn.execute(text(check_column_sql))
            existing_column = result.fetchone()

            if existing_column:
                print(f"  - Dropping {column_name} column...")
                await conn.execute(
                    text(f"ALTER TABLE companies DROP COLUMN {column_name};")
                )
            else:
                print(f"  - {column_name} column already removed")

    print("✅ Verification and matching columns removed from companies table")


async def main():
    """Run the migration."""
    print("📋 Migration: Remove verification and matching columns from companies table")
    print("=" * 75)

    try:
        await remove_verification_columns()
        print("\n🎉 Migration completed successfully!")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
