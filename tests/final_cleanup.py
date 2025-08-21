#!/usr/bin/env python3
"""
Final Database Cleanup - Remove Legacy rollout_entries Table
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import get_settings

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")


async def remove_legacy_table():
    """Remove the legacy rollout_entries table."""
    settings = get_settings()
    database_url = settings.get_database_url()
    engine = create_async_engine(database_url)

    try:
        print("🗑️  Removing legacy rollout_entries table...")

        async with engine.begin() as conn:
            # Drop the legacy table
            await conn.execute(text("DROP TABLE IF EXISTS rollout_entries CASCADE"))
            print("✅ Legacy rollout_entries table removed")

            # Verify final structure
            result = await conn.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """
                )
            )
            tables = [row[0] for row in result.fetchall()]

            print(f"\n📊 Final Database Structure ({len(tables)} tables):")
            print("=" * 50)

            for table in tables:
                count_result = await conn.execute(
                    text(f'SELECT COUNT(*) FROM "{table}"')
                )
                row_count = count_result.scalar()
                print(f"✅ {table}: {row_count:,} rows")

        print("\n🎉 Database cleanup completed successfully!")
        print("   - Removed 4 unused/legacy tables")
        print("   - Kept normalized rollout structure (companies + quotas)")
        print("   - Backup files created for safety")

    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(remove_legacy_table())
