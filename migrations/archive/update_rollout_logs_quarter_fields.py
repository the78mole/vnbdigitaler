#!/usr/bin/env python3
"""
Update rollout_update_logs table to split quarter into separate quarter and year fields.

This migration replaces the report_quarter VARCHAR field with a proper quarter INTEGER field (1-4).
The year information is already in the separate report_year field.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text

from src.database_config import get_database_url


def update_rollout_logs_quarter_fields():
    """Update the rollout_update_logs table to use proper quarter field."""

    # Get database engine with sync driver
    database_url = get_database_url()

    # Convert asyncpg URL to psycopg2 for sync operations
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://", 1
        )
        # Convert ssl parameter for psycopg2
        database_url = database_url.replace("ssl=require", "sslmode=require")

    engine = create_engine(database_url)

    # SQL for updating the table structure
    update_sql = """
    -- First, check if we need to update the table
    DO $$
    BEGIN
        -- Add new quarter column if it doesn't exist
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'rollout_update_logs' AND column_name = 'quarter') THEN
            ALTER TABLE rollout_update_logs ADD COLUMN quarter INTEGER;
        END IF;

        -- Update existing data to extract quarter from report_quarter
        UPDATE rollout_update_logs
        SET quarter = CASE
            WHEN report_quarter LIKE '%Q1%' OR report_quarter LIKE '%q1%' THEN 1
            WHEN report_quarter LIKE '%Q2%' OR report_quarter LIKE '%q2%' THEN 2
            WHEN report_quarter LIKE '%Q3%' OR report_quarter LIKE '%q3%' THEN 3
            WHEN report_quarter LIKE '%Q4%' OR report_quarter LIKE '%q4%' THEN 4
            ELSE 1  -- Default fallback
        END
        WHERE quarter IS NULL;

        -- Add constraint to ensure quarter is between 1 and 4
        BEGIN
            ALTER TABLE rollout_update_logs
            ADD CONSTRAINT chk_quarter_valid CHECK (quarter >= 1 AND quarter <= 4);
        EXCEPTION
            WHEN duplicate_object THEN NULL;  -- Constraint already exists
        END;

        -- Make quarter NOT NULL after updating existing data
        ALTER TABLE rollout_update_logs ALTER COLUMN quarter SET NOT NULL;

        -- Add comment to the new quarter column
        COMMENT ON COLUMN rollout_update_logs.quarter IS 'Quarter number (1-4)';

        -- Update comment on report_quarter to indicate it's deprecated
        COMMENT ON COLUMN rollout_update_logs.report_quarter IS 'Original quarter string (deprecated, use quarter field instead)';
    END $$;

    -- Create index for better query performance
    CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_quarter
        ON rollout_update_logs (quarter);
    CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_quarter_year
        ON rollout_update_logs (quarter, report_year);
    """

    try:
        print("Updating rollout_update_logs table quarter fields...")

        # Execute the SQL
        with engine.connect() as connection:
            connection.execute(text(update_sql))
            connection.commit()
            print("✅ rollout_update_logs table updated successfully!")

        print("\nChanges made:")
        print("- Added quarter INTEGER column (1-4)")
        print("- Migrated existing report_quarter data to new quarter field")
        print("- Added constraint to ensure quarter is between 1 and 4")
        print("- report_quarter field kept for backward compatibility (deprecated)")
        print("- Added indexes for better query performance")

    except Exception as e:
        print(f"❌ Error updating rollout_update_logs table: {e}")
        return False

    return True


if __name__ == "__main__":
    success = update_rollout_logs_quarter_fields()
    if success:
        print("\n🎉 Migration completed successfully!")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)
