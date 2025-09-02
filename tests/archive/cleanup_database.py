#!/usr/bin/env python3
"""
Database Cleanup Script

Safely removes unused tables and consolidates the database structure.
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import get_settings

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")


async def backup_table_data(engine, table_name):
    """Create a backup of table data before deletion."""
    print(f"📦 Creating backup of {table_name}...")

    async with engine.begin() as conn:
        # Get table structure
        result = await conn.execute(
            text(
                f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}' AND table_schema = 'public'
            ORDER BY ordinal_position;
        """
            )
        )
        columns = result.fetchall()

        # Get row count
        count_result = await conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
        row_count = count_result.scalar()

        print(f"   📊 Table {table_name}: {row_count} rows, {len(columns)} columns")

        if row_count > 0:
            # Export data as JSON for backup
            data_result = await conn.execute(text(f'SELECT * FROM "{table_name}"'))
            rows = data_result.fetchall()

            backup_file = Path(__file__).parent / f"backup_{table_name}.json"
            import json

            # Convert to list of dicts
            backup_data = []
            column_names = [col[0] for col in columns]

            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    if hasattr(value, "isoformat"):  # datetime objects
                        row_dict[column_names[i]] = value.isoformat()
                    else:
                        row_dict[column_names[i]] = value
                backup_data.append(row_dict)

            with Path(backup_file).open("w") as f:
                json.dump(
                    {
                        "table_name": table_name,
                        "backup_date": str(asyncio.get_event_loop().time()),
                        "row_count": row_count,
                        "columns": [
                            {"name": col[0], "type": col[1], "nullable": col[2]}
                            for col in columns
                        ],
                        "data": backup_data,
                    },
                    f,
                    indent=2,
                )

            print(f"   💾 Backup saved to {backup_file}")
        else:
            print(f"   ⚡ Table {table_name} is empty, no backup needed")


async def cleanup_database(dry_run=True):
    """Clean up unused tables from the database."""
    settings = get_settings()
    database_url = settings.get_database_url()

    if not database_url:
        print("❌ No database URL configured")
        return

    # Tables to remove (empty tables)
    tables_to_remove = ["analysis_sessions", "download_sessions", "rollout_reports"]

    # Legacy table to consider removing (has data but replaced by new structure)
    legacy_tables = [
        "rollout_entries"  # Replaced by rollout_companies + rollout_quotas
    ]

    engine = create_async_engine(database_url)

    try:
        print(f"🧹 Database Cleanup {'(DRY RUN)' if dry_run else '(LIVE)'}")
        print("=" * 60)

        # Backup and remove empty tables
        for table in tables_to_remove:
            await backup_table_data(engine, table)

            if not dry_run:
                async with engine.begin() as conn:
                    await conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                    print(f"   🗑️  Dropped table {table}")
            else:
                print(f"   🔄 Would drop table {table}")

        print("\n" + "=" * 60)
        print("📋 Legacy Tables Analysis:")
        print("=" * 60)

        # Analyze legacy tables
        for table in legacy_tables:
            await backup_table_data(engine, table)
            print(
                f"   ⚠️  Table {table} has data but might be replaced by new structure"
            )
            print("   💭 Consider manual verification before removal")

        if not dry_run:
            print("\n✅ Database cleanup completed!")
        else:
            print("\n🔄 Dry run completed. Run with dry_run=False to apply changes.")

    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
    finally:
        await engine.dispose()


async def verify_current_structure():
    """Verify the current database structure after cleanup."""
    settings = get_settings()
    database_url = settings.get_database_url()
    engine = create_async_engine(database_url)

    try:
        async with engine.begin() as conn:
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

            print("\n📊 Current Database Structure:")
            print("=" * 60)

            for table in tables:
                count_result = await conn.execute(
                    text(f'SELECT COUNT(*) FROM "{table}"')
                )
                row_count = count_result.scalar()
                status = "✅ Active" if row_count > 0 else "⚪ Empty"
                print(f"{status} {table}: {row_count:,} rows")

    except Exception as e:
        print(f"❌ Verification failed: {e}")
    finally:
        await engine.dispose()


async def main():
    """Main cleanup function."""
    print("🧹 VNBdigitaler Database Cleanup")
    print("=" * 50)

    # First, run dry-run to see what would happen
    await cleanup_database(dry_run=True)

    print("\n" + "=" * 60)
    choice = input("Do you want to proceed with the cleanup? (y/N): ").strip().lower()

    if choice == "y":
        await cleanup_database(dry_run=False)
        await verify_current_structure()
    else:
        print("❌ Cleanup cancelled")


if __name__ == "__main__":
    asyncio.run(main())
