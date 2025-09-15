#!/usr/bin/env python3
"""
Set up normalized market functions table and update bdew_code_registry schema.
"""

import os

import psycopg2
from psycopg2.extras import RealDictCursor


def setup_market_functions_table():
    """Create market_functions lookup table and update bdew_code_registry."""

    # Database connection
    connection = psycopg2.connect(
        host=os.getenv("DATABASE_HOST", "localhost"),
        database=os.getenv("DATABASE_NAME", "vnb_digitaler"),
        user=os.getenv("DATABASE_USER", "postgres"),
        password=os.getenv("DATABASE_PASSWORD", ""),
        port=os.getenv("DATABASE_PORT", "5432"),
    )

    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            print("🔧 Setting up normalized market functions...")

            # 1. Create market_functions lookup table
            print("📋 Creating market_functions table...")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS vnb_digitaler.market_functions (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """
            )

            # 2. Insert the 6 market functions we found
            market_functions = [
                (1, "Lieferant"),
                (2, "Bilanzkreisverantwortlicher"),
                (3, "Betreiber einer technischen Ressource"),
                (4, "Einsatzverantwortlicher"),
                (5, "Messstellenbetreiber"),
                (6, "Netzbetreiber"),
            ]

            print("📝 Inserting market functions...")
            for func_id, func_name in market_functions:
                cursor.execute(
                    """
                    INSERT INTO vnb_digitaler.market_functions (id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;
                """,
                    (func_id, func_name),
                )

            # 3. Add market_function_id column to bdew_code_registry
            print("🔗 Adding market_function_id column to bdew_code_registry...")
            cursor.execute(
                """
                ALTER TABLE vnb_digitaler.bdew_code_registry
                ADD COLUMN IF NOT EXISTS market_function_id INTEGER
                REFERENCES vnb_digitaler.market_functions(id);
            """
            )

            # 4. Check if we should remove the old role_code column
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'vnb_digitaler'
                AND table_name = 'bdew_code_registry'
                AND column_name = 'role_code';
            """
            )

            if cursor.fetchone():
                print("🗑️  Removing old role_code column...")
                cursor.execute(
                    """
                    ALTER TABLE vnb_digitaler.bdew_code_registry
                    DROP COLUMN IF EXISTS role_code;
                """
                )

            connection.commit()
            print("✅ Schema update completed successfully!")

            # 5. Show updated schema
            cursor.execute(
                """
                SELECT column_name, data_type, character_maximum_length, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'vnb_digitaler'
                AND table_name = 'bdew_code_registry'
                ORDER BY ordinal_position;
            """
            )

            print("\n📊 Updated bdew_code_registry schema:")
            print("-" * 60)
            for row in cursor.fetchall():
                max_len = (
                    f"({row['character_maximum_length']})"
                    if row["character_maximum_length"]
                    else ""
                )
                nullable = "NULL" if row["is_nullable"] == "YES" else "NOT NULL"
                print(
                    f"  {row['column_name']:20s} {row['data_type']}{max_len:15s} {nullable}"
                )

            # 6. Show market functions
            cursor.execute("SELECT * FROM vnb_digitaler.market_functions ORDER BY id;")
            print("\n📋 Market functions lookup table:")
            print("-" * 60)
            for row in cursor.fetchall():
                print(f"  {row['id']:2d}. {row['name']}")

    except Exception as e:
        connection.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    setup_market_functions_table()
