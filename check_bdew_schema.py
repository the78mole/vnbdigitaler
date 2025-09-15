#!/usr/bin/env python3
"""
Show database schema for BDEW code registry and suggest fixes.
"""

import psycopg2


def check_bdew_schema():
    """Check the current BDEW database schema."""
    print("🔍 Checking BDEW database schema...")

    db_config = {
        "host": "localhost",
        "port": "5432",
        "database": "vnb_digitaler",
        "user": "vnb_admin",
        "password": "vnb_secure_password_2024",  # pragma: allowlist secret
    }

    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Check bdew_code_registry table structure
        cursor.execute(
            """
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'vnb_digitaler'
            AND table_name = 'bdew_code_registry'
            ORDER BY ordinal_position;
        """
        )

        columns = cursor.fetchall()

        print("\n📋 Current vnb_digitaler.bdew_code_registry schema:")
        print("-" * 80)
        for col in columns:
            name, dtype, max_len, nullable = col
            length_info = f"({max_len})" if max_len else ""
            nullable_info = "NULL" if nullable == "YES" else "NOT NULL"
            print(f"  {name:20s} {dtype:15s}{length_info:8s} {nullable_info}")

        # Show sample BDEW codes from our test
        print("\n🎯 Sample BDEW codes from API (length analysis):")
        print("-" * 50)
        sample_codes = [
            "9983711000009",  # 13 characters
            "9983712000008",  # 13 characters
            "9983563000009",  # 13 characters
            "9980136000002",  # 13 characters
        ]

        for code in sample_codes:
            print(f"  {code} ({len(code)} chars)")

        print("\n💡 Recommended schema change:")
        print("-" * 40)
        print("ALTER TABLE vnb_digitaler.bdew_code_registry")
        print("ALTER COLUMN bdew_code TYPE VARCHAR(20);")
        print("\n-- Reason: BDEW codes are 13 characters, current limit is 10")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error checking schema: {e}")


if __name__ == "__main__":
    check_bdew_schema()
