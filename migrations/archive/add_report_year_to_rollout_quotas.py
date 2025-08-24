#!/usr/bin/env python3
"""
Migration: Add report_year column to rollout_quotas table

This migration adds the missing report_year column to the rollout_quotas table
to complement the existing report_quarter column.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from sqlalchemy import create_engine, text

from src.database_config import get_database_url


def add_report_year_column():
    """Add report_year column to rollout_quotas table"""

    database_url = get_database_url()
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://", 1
        )
        database_url = database_url.replace("ssl=require", "sslmode=require")

    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()

        try:
            print("🔄 Adding report_year column to rollout_quotas table...")

            # Add report_year column
            conn.execute(
                text(
                    """
                ALTER TABLE rollout_quotas
                ADD COLUMN IF NOT EXISTS report_year INTEGER NULL;
            """
                )
            )

            print("✅ Added report_year column")

            # Add constraint to ensure valid year values (2024-2030)
            print("🔄 Adding constraint for valid report_year values...")

            # Check if constraint already exists
            constraint_exists = conn.execute(
                text(
                    """
                SELECT COUNT(*) FROM information_schema.table_constraints
                WHERE table_name = 'rollout_quotas'
                AND constraint_name = 'chk_report_year_valid';
            """
                )
            ).scalar()

            if not constraint_exists:
                conn.execute(
                    text(
                        """
                    ALTER TABLE rollout_quotas
                    ADD CONSTRAINT chk_report_year_valid
                    CHECK (report_year IS NULL OR (report_year >= 2024 AND report_year <= 2030));
                """
                    )
                )
                print("✅ Added constraint for report_year")
            else:
                print("✅ Constraint for report_year already exists")

            # Create index for better performance
            print("🔄 Creating index for report_year...")
            conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_rollout_quotas_report_year
                ON rollout_quotas(report_year);
            """
                )
            )

            print("✅ Created index for report_year")

            # Create composite index for quarter + year
            print("🔄 Creating composite index for report_quarter and report_year...")
            conn.execute(
                text(
                    """
                CREATE INDEX IF NOT EXISTS idx_rollout_quotas_quarter_year
                ON rollout_quotas(report_quarter, report_year);
            """
                )
            )

            print("✅ Created composite index for quarter + year")

            # Commit transaction
            trans.commit()
            print("✅ Migration completed successfully!")

        except Exception as e:
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    add_report_year_column()
