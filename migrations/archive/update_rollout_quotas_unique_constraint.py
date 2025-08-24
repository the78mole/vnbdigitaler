#!/usr/bin/env python3
"""
Migration: Update unique constraint for rollout_quotas to include report_year

This migration updates the unique constraint to include the new report_year column.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from sqlalchemy import create_engine, text

from src.database_config import get_database_url


def update_unique_constraint():
    """Update the unique constraint to include report_year"""

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
            print("🔄 Dropping old unique constraint...")

            # Drop the old constraint
            conn.execute(
                text(
                    """
                ALTER TABLE rollout_quotas
                DROP CONSTRAINT IF EXISTS uq_rollout_quota_company_date_quarter;
            """
                )
            )

            print("✅ Dropped old constraint")

            # Add new constraint including report_year
            print("🔄 Adding new unique constraint with report_year...")
            conn.execute(
                text(
                    """
                ALTER TABLE rollout_quotas
                ADD CONSTRAINT uq_rollout_quota_company_date_quarter_year
                UNIQUE (rollout_company_id, reference_date, report_quarter, report_year);
            """
                )
            )

            print("✅ Added new constraint with report_year")

            # Commit transaction
            trans.commit()
            print("✅ Constraint update completed successfully!")

        except Exception as e:
            trans.rollback()
            print(f"❌ Constraint update failed: {e}")
            raise


if __name__ == "__main__":
    update_unique_constraint()
