#!/usr/bin/env python3
"""
Database Analysis Script

Analyzes the current database structure to identify tables and their usage.
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import get_settings

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")


async def analyze_database():
    """Analyze the current database structure."""
    settings = get_settings()
    database_url = settings.get_database_url()

    if not database_url:
        print("❌ No database URL configured")
        return

    print(
        f"🔍 Analyzing database: {database_url.split('@')[1] if '@' in database_url else 'localhost'}"
    )

    # Create async engine
    engine = create_async_engine(database_url)

    try:
        async with engine.begin() as conn:
            # Get all table names
            result = await conn.execute(
                text(
                    """
                SELECT table_name, table_schema
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """
                )
            )
            tables = result.fetchall()

            print(f"\n📊 Found {len(tables)} tables in public schema:")
            print("=" * 60)

            for table_name, _schema in tables:
                print(f"📋 {table_name}")

                # Get row count
                try:
                    count_result = await conn.execute(
                        text(f'SELECT COUNT(*) FROM "{table_name}"')
                    )
                    row_count = count_result.scalar()
                    print(f"   📈 Rows: {row_count:,}")
                except Exception as e:
                    print(f"   ❌ Error getting count: {e}")

                # Get column info
                try:
                    columns_result = await conn.execute(
                        text(
                            f"""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_name = '{table_name}' AND table_schema = 'public'
                        ORDER BY ordinal_position;
                    """
                        )
                    )
                    columns = columns_result.fetchall()
                    print(f"   📝 Columns ({len(columns)}):")
                    for col_name, data_type, nullable in columns[
                        :5
                    ]:  # Show first 5 columns
                        null_str = "NULL" if nullable == "YES" else "NOT NULL"
                        print(f"      - {col_name}: {data_type} {null_str}")
                    if len(columns) > 5:
                        print(f"      ... and {len(columns) - 5} more columns")
                except Exception as e:
                    print(f"   ❌ Error getting columns: {e}")

                print()

    except Exception as e:
        print(f"❌ Database analysis failed: {e}")
    finally:
        await engine.dispose()


async def check_table_dependencies():
    """Check foreign key relationships between tables."""
    settings = get_settings()
    database_url = settings.get_database_url()

    engine = create_async_engine(database_url)

    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text(
                    """
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = 'public'
                ORDER BY tc.table_name, kcu.column_name;
            """
                )
            )

            relationships = result.fetchall()

            print("\n🔗 Foreign Key Relationships:")
            print("=" * 60)

            if relationships:
                for table, column, foreign_table, foreign_column in relationships:
                    print(f"📋 {table}.{column} → {foreign_table}.{foreign_column}")
            else:
                print("No foreign key relationships found.")

    except Exception as e:
        print(f"❌ Error checking dependencies: {e}")
    finally:
        await engine.dispose()


async def main():
    """Main analysis function."""
    print("🔍 VNBdigitaler Database Analysis")
    print("=" * 50)

    await analyze_database()
    await check_table_dependencies()

    print("\n💡 Cleanup Recommendations:")
    print("=" * 50)
    print("1. Check tables with 0 rows - might be safe to drop")
    print("2. Look for duplicate/similar table structures")
    print("3. Verify foreign key constraints before dropping tables")
    print("4. Consider backing up data before cleanup")


if __name__ == "__main__":
    asyncio.run(main())
