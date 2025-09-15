#!/usr/bin/env python3
"""
Setup PostgreSQL database schema for BDEW workflow with normalized market functions.
"""

import logging
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_postgres_schema():
    """Create tables and insert market functions in PostgreSQL."""

    # Database connection configuration (matching docker-compose.yml)
    config = {
        "host": "localhost",
        "port": "5432",
        "database": "vnb_digitaler",
        "user": "vnb_admin",
        "password": "vnb_secure_password_2024",  # pragma: allowlist secret
    }

    try:
        connection = psycopg2.connect(**config)
        cursor = connection.cursor(cursor_factory=RealDictCursor)

        print("🔗 Connected to PostgreSQL database")

        # 1. Create schema if not exists
        print("🔧 Creating vnb_digitaler schema...")
        cursor.execute("CREATE SCHEMA IF NOT EXISTS vnb_digitaler;")

        # 2. Create market_functions lookup table
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

        # 3. Insert the 11 market functions
        print("📝 Inserting market functions...")
        market_functions = [
            (1, "Einsatzverantwortlicher"),
            (2, "Betreiber einer technischen Ressource"),
            (3, "Bilanzkreisverantwortlicher"),
            (4, "Lieferant"),
            (5, "Messstellenbetreiber"),
            (6, "Netzbetreiber"),
            (7, "Energieserviceanbieter des Anschlussnutzers"),
            (8, "Netznutzer ohne All-Inklusiv-Vertrag"),
            (9, "Bilanzkoordinator"),
            (10, "Übertragungsnetzbetreiber"),
            (11, "Data Provider"),
        ]

        for func_id, func_name in market_functions:
            cursor.execute(
                """
                INSERT INTO vnb_digitaler.market_functions (id, name)
                VALUES (%s, %s)
                ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;
            """,
                (func_id, func_name),
            )

        # 4. Drop old bdew_code_registry if exists (for clean slate)
        print("🗑️  Dropping old bdew_code_registry table if exists...")
        cursor.execute("DROP TABLE IF EXISTS vnb_digitaler.bdew_code_registry;")

        # 5. Create new bdew_code_registry table with normalized structure
        print("🔧 Creating bdew_code_registry table...")
        cursor.execute(
            """
            CREATE TABLE vnb_digitaler.bdew_code_registry (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                bdew_code VARCHAR(20) NOT NULL,
                company_name VARCHAR(255) NOT NULL,
                market_function_id INTEGER NOT NULL,
                registration_date VARCHAR(50),
                status VARCHAR(20) DEFAULT 'ACTIVE',
                last_sync_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_hash VARCHAR(64),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (market_function_id) REFERENCES vnb_digitaler.market_functions(id),
                UNIQUE(bdew_code, market_function_id)
            );
        """
        )

        # 6. Create indexes for performance
        print("📊 Creating indexes...")
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_bdew_code_registry_bdew_code
            ON vnb_digitaler.bdew_code_registry(bdew_code);
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_bdew_code_registry_market_function
            ON vnb_digitaler.bdew_code_registry(market_function_id);
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_bdew_code_registry_status
            ON vnb_digitaler.bdew_code_registry(status);
        """
        )

        connection.commit()
        print("✅ Schema setup completed successfully!")

        # 7. Show what we created
        cursor.execute(
            """
            SELECT column_name, data_type, character_maximum_length, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'vnb_digitaler'
            AND table_name = 'bdew_code_registry'
            ORDER BY ordinal_position;
        """
        )

        print("\n📊 bdew_code_registry schema:")
        print("-" * 70)
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

        # 8. Show market functions
        cursor.execute(
            "SELECT id, name FROM vnb_digitaler.market_functions ORDER BY id;"
        )
        print("\n📋 Market functions in database:")
        print("-" * 70)
        for row in cursor.fetchall():
            print(f"  {row['id']:2d}. {row['name']}")

        return True

    except Exception as e:
        logger.error(f"❌ Error setting up schema: {e}")
        if "connection" in locals():
            connection.rollback()
        return False
    finally:
        if "connection" in locals():
            connection.close()


if __name__ == "__main__":
    success = setup_postgres_schema()
    if success:
        print("\n🎯 PostgreSQL schema ready for BDEW workflow!")
        print("Database: vnb_digitaler")
        print("Schema: vnb_digitaler")
        print("Tables: market_functions, bdew_code_registry")
    else:
        print("\n❌ Schema setup failed!")
        sys.exit(1)
