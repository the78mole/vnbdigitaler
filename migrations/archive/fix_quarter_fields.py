#!/usr/bin/env python3
"""
Fix quarter fields in rollout_update_logs and rollout_quotas tables.

This migration properly converts quarter fields from VARCHAR to INTEGER (1-4)
and fixes any inconsistencies in both tables.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text

from src.database_config import get_database_url


def fix_quarter_fields():
    """Fix quarter fields in both rollout_update_logs and rollout_quotas tables."""

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

    # SQL for fixing both tables
    fix_sql = """
    -- Fix rollout_update_logs table
    DO $$
    BEGIN
        -- First make report_quarter nullable if it isn't already
        BEGIN
            ALTER TABLE rollout_update_logs ALTER COLUMN report_quarter DROP NOT NULL;
        EXCEPTION
            WHEN OTHERS THEN NULL;  -- Ignore if already nullable
        END;

        -- Ensure quarter column exists and is properly typed
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'rollout_update_logs' AND column_name = 'quarter') THEN
            ALTER TABLE rollout_update_logs ADD COLUMN quarter INTEGER;
        END IF;

        -- Update existing data to extract quarter from report_quarter
        UPDATE rollout_update_logs
        SET quarter = CASE
            WHEN report_quarter LIKE '%Q1%' OR report_quarter LIKE '%q1%' OR report_quarter LIKE '%1%' THEN 1
            WHEN report_quarter LIKE '%Q2%' OR report_quarter LIKE '%q2%' OR report_quarter LIKE '%2%' THEN 2
            WHEN report_quarter LIKE '%Q3%' OR report_quarter LIKE '%q3%' OR report_quarter LIKE '%3%' THEN 3
            WHEN report_quarter LIKE '%Q4%' OR report_quarter LIKE '%q4%' OR report_quarter LIKE '%4%' THEN 4
            ELSE 1  -- Default fallback
        END
        WHERE quarter IS NULL OR quarter NOT BETWEEN 1 AND 4;

        -- Make quarter NOT NULL and add constraint
        ALTER TABLE rollout_update_logs ALTER COLUMN quarter SET NOT NULL;

        -- Add constraint if it doesn't exist
        BEGIN
            ALTER TABLE rollout_update_logs
            ADD CONSTRAINT chk_rollout_logs_quarter_valid CHECK (quarter >= 1 AND quarter <= 4);
        EXCEPTION
            WHEN duplicate_object THEN NULL;  -- Constraint already exists
        END;

        -- Add comment
        COMMENT ON COLUMN rollout_update_logs.quarter IS 'Quarter number (1-4)';
        COMMENT ON COLUMN rollout_update_logs.report_quarter IS 'Original quarter string (deprecated)';
    END $$;

    -- Fix rollout_quotas table
    DO $$
    BEGIN
        -- Add quarter column if it doesn't exist
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                      WHERE table_name = 'rollout_quotas' AND column_name = 'quarter') THEN
            ALTER TABLE rollout_quotas ADD COLUMN quarter INTEGER;
        END IF;

        -- Update existing data to extract quarter from report_quarter
        UPDATE rollout_quotas
        SET quarter = CASE
            WHEN report_quarter LIKE '%Q1%' OR report_quarter LIKE '%q1%' OR report_quarter LIKE '%1%' THEN 1
            WHEN report_quarter LIKE '%Q2%' OR report_quarter LIKE '%q2%' OR report_quarter LIKE '%2%' THEN 2
            WHEN report_quarter LIKE '%Q3%' OR report_quarter LIKE '%q3%' OR report_quarter LIKE '%3%' THEN 3
            WHEN report_quarter LIKE '%Q4%' OR report_quarter LIKE '%q4%' OR report_quarter LIKE '%4%' THEN 4
            ELSE 1  -- Default fallback
        END
        WHERE quarter IS NULL OR quarter NOT BETWEEN 1 AND 4;

        -- Add constraint if it doesn't exist
        BEGIN
            ALTER TABLE rollout_quotas
            ADD CONSTRAINT chk_rollout_quotas_quarter_valid CHECK (quarter >= 1 AND quarter <= 4);
        EXCEPTION
            WHEN duplicate_object THEN NULL;  -- Constraint already exists
        END;

        -- Add comment
        COMMENT ON COLUMN rollout_quotas.quarter IS 'Quarter number (1-4)';
        COMMENT ON COLUMN rollout_quotas.report_quarter IS 'Original quarter string (deprecated)';
    END $$;

    -- Create indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_quarter
        ON rollout_update_logs (quarter);
    CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_quarter_year
        ON rollout_update_logs (quarter, report_year);
    CREATE INDEX IF NOT EXISTS idx_rollout_quotas_quarter
        ON rollout_quotas (quarter);
    """

    try:
        print(
            "Fixing quarter fields in rollout_update_logs and rollout_quotas tables..."
        )

        # Execute the SQL
        with engine.connect() as connection:
            connection.execute(text(fix_sql))
            connection.commit()
            print("✅ Quarter fields fixed successfully!")

        # Verify the changes
        with engine.connect() as connection:
            print("\nVerifying rollout_update_logs quarter field:")
            result = connection.execute(
                text(
                    """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'rollout_update_logs' AND column_name IN ('quarter', 'report_quarter')
                ORDER BY column_name;
            """
                )
            )
            for row in result:
                print(
                    f"  {row.column_name}: {row.data_type} ({'NULL' if row.is_nullable == 'YES' else 'NOT NULL'})"
                )

            print("\nVerifying rollout_quotas quarter field:")
            result = connection.execute(
                text(
                    """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'rollout_quotas' AND column_name IN ('quarter', 'report_quarter')
                ORDER BY column_name;
            """
                )
            )
            for row in result:
                print(
                    f"  {row.column_name}: {row.data_type} ({'NULL' if row.is_nullable == 'YES' else 'NOT NULL'})"
                )

        print("\nChanges made:")
        print("- rollout_update_logs.quarter: INTEGER NOT NULL (1-4)")
        print("- rollout_update_logs.report_quarter: VARCHAR NULL (deprecated)")
        print("- rollout_quotas.quarter: INTEGER (1-4)")
        print("- rollout_quotas.report_quarter: VARCHAR NULL (deprecated)")
        print("- Added constraints to ensure quarter is between 1 and 4")
        print("- Added indexes for better query performance")

    except Exception as e:
        print(f"❌ Error fixing quarter fields: {e}")
        return False

    return True


if __name__ == "__main__":
    success = fix_quarter_fields()
    if success:
        print("\n🎉 Migration completed successfully!")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)
