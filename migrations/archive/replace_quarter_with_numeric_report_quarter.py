#!/usr/bin/env python3
"""
Replace quarter column with numeric report_quarter column.

This migration:
1. Updates report_quarter from VARCHAR to INTEGER (1-4)
2. Migrates data from quarter column to report_quarter
3. Drops the separate quarter column
4. Updates constraints and indexes
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text

from src.database_config import get_database_url


def replace_quarter_with_numeric_report_quarter():
    """Replace quarter column with numeric report_quarter column."""

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

    # SQL for updating both tables
    update_sql = """
    -- Fix rollout_update_logs table
    DO $$
    BEGIN
        -- Step 1: Copy data from quarter to report_quarter where report_quarter is not already numeric
        UPDATE rollout_update_logs
        SET report_quarter = quarter::text
        WHERE quarter IS NOT NULL
        AND (report_quarter IS NULL OR report_quarter !~ '^[1-4]$');

        -- Step 2: Add temporary column for numeric values
        ALTER TABLE rollout_update_logs ADD COLUMN report_quarter_new INTEGER;

        -- Step 3: Convert report_quarter data to numeric
        UPDATE rollout_update_logs
        SET report_quarter_new = CASE
            WHEN report_quarter ~ '^[1-4]$' THEN report_quarter::integer
            WHEN report_quarter LIKE '%Q1%' OR report_quarter LIKE '%q1%' OR report_quarter LIKE '%1%' THEN 1
            WHEN report_quarter LIKE '%Q2%' OR report_quarter LIKE '%q2%' OR report_quarter LIKE '%2%' THEN 2
            WHEN report_quarter LIKE '%Q3%' OR report_quarter LIKE '%q3%' OR report_quarter LIKE '%3%' THEN 3
            WHEN report_quarter LIKE '%Q4%' OR report_quarter LIKE '%q4%' OR report_quarter LIKE '%4%' THEN 4
            WHEN quarter IS NOT NULL THEN quarter
            ELSE 1  -- Default fallback
        END;

        -- Step 4: Drop old columns and constraints
        BEGIN
            ALTER TABLE rollout_update_logs DROP CONSTRAINT IF EXISTS chk_quarter_valid;
        EXCEPTION
            WHEN OTHERS THEN NULL;
        END;

        BEGIN
            ALTER TABLE rollout_update_logs DROP CONSTRAINT IF EXISTS chk_rollout_logs_quarter_valid;
        EXCEPTION
            WHEN OTHERS THEN NULL;
        END;

        ALTER TABLE rollout_update_logs DROP COLUMN IF EXISTS quarter;
        ALTER TABLE rollout_update_logs DROP COLUMN IF EXISTS report_quarter;

        -- Step 5: Rename new column and add constraints
        ALTER TABLE rollout_update_logs RENAME COLUMN report_quarter_new TO report_quarter;
        ALTER TABLE rollout_update_logs ALTER COLUMN report_quarter SET NOT NULL;

        -- Add constraint for valid quarters
        ALTER TABLE rollout_update_logs
        ADD CONSTRAINT chk_report_quarter_valid CHECK (report_quarter >= 1 AND report_quarter <= 4);

        -- Add comment
        COMMENT ON COLUMN rollout_update_logs.report_quarter IS 'Quarter number (1-4)';
    END $$;

    -- Fix rollout_quotas table
    DO $$
    BEGIN
        -- Step 1: Copy data from quarter to report_quarter where needed
        UPDATE rollout_quotas
        SET report_quarter = quarter::text
        WHERE quarter IS NOT NULL
        AND (report_quarter IS NULL OR report_quarter !~ '^[1-4]$');

        -- Step 2: Add temporary column for numeric values
        ALTER TABLE rollout_quotas ADD COLUMN report_quarter_new INTEGER;

        -- Step 3: Convert report_quarter data to numeric
        UPDATE rollout_quotas
        SET report_quarter_new = CASE
            WHEN report_quarter ~ '^[1-4]$' THEN report_quarter::integer
            WHEN report_quarter LIKE '%Q1%' OR report_quarter LIKE '%q1%' OR report_quarter LIKE '%1%' THEN 1
            WHEN report_quarter LIKE '%Q2%' OR report_quarter LIKE '%q2%' OR report_quarter LIKE '%2%' THEN 2
            WHEN report_quarter LIKE '%Q3%' OR report_quarter LIKE '%q3%' OR report_quarter LIKE '%3%' THEN 3
            WHEN report_quarter LIKE '%Q4%' OR report_quarter LIKE '%q4%' OR report_quarter LIKE '%4%' THEN 4
            WHEN quarter IS NOT NULL THEN quarter
            ELSE NULL  -- Allow NULL for rollout_quotas
        END;

        -- Step 4: Drop old columns and constraints
        BEGIN
            ALTER TABLE rollout_quotas DROP CONSTRAINT IF EXISTS chk_rollout_quotas_quarter_valid;
        EXCEPTION
            WHEN OTHERS THEN NULL;
        END;

        -- Drop the unique constraint temporarily
        BEGIN
            ALTER TABLE rollout_quotas DROP CONSTRAINT IF EXISTS uq_rollout_quota_company_date_quarter;
        EXCEPTION
            WHEN OTHERS THEN NULL;
        END;

        ALTER TABLE rollout_quotas DROP COLUMN IF EXISTS quarter;
        ALTER TABLE rollout_quotas DROP COLUMN IF EXISTS report_quarter;

        -- Step 5: Rename new column and add constraints
        ALTER TABLE rollout_quotas RENAME COLUMN report_quarter_new TO report_quarter;

        -- Add constraint for valid quarters (allow NULL)
        ALTER TABLE rollout_quotas
        ADD CONSTRAINT chk_report_quarter_valid CHECK (report_quarter IS NULL OR (report_quarter >= 1 AND report_quarter <= 4));

        -- Recreate the unique constraint with new column name
        ALTER TABLE rollout_quotas
        ADD CONSTRAINT uq_rollout_quota_company_date_quarter
        UNIQUE (rollout_company_id, reference_date, report_quarter);

        -- Add comment
        COMMENT ON COLUMN rollout_quotas.report_quarter IS 'Quarter number (1-4)';
    END $$;

    -- Update indexes
    DROP INDEX IF EXISTS idx_rollout_update_logs_quarter;
    DROP INDEX IF EXISTS idx_rollout_update_logs_quarter_year;
    DROP INDEX IF EXISTS idx_rollout_quotas_quarter;

    CREATE INDEX idx_rollout_update_logs_report_quarter ON rollout_update_logs (report_quarter);
    CREATE INDEX idx_rollout_update_logs_report_quarter_year ON rollout_update_logs (report_quarter, report_year);
    CREATE INDEX idx_rollout_quotas_report_quarter ON rollout_quotas (report_quarter);
    """

    try:
        print("Replacing quarter column with numeric report_quarter...")

        # Execute the SQL
        with engine.connect() as connection:
            connection.execute(text(update_sql))
            connection.commit()
            print("✅ Columns updated successfully!")

        # Verify the changes
        with engine.connect() as connection:
            print("\nVerifying rollout_update_logs report_quarter field:")
            result = connection.execute(
                text(
                    """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'rollout_update_logs' AND column_name = 'report_quarter'
                ORDER BY column_name;
            """
                )
            )
            for row in result:
                print(
                    f"  {row.column_name}: {row.data_type} ({'NULL' if row.is_nullable == 'YES' else 'NOT NULL'})"
                )

            print("\nVerifying rollout_quotas report_quarter field:")
            result = connection.execute(
                text(
                    """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'rollout_quotas' AND column_name = 'report_quarter'
                ORDER BY column_name;
            """
                )
            )
            for row in result:
                print(
                    f"  {row.column_name}: {row.data_type} ({'NULL' if row.is_nullable == 'YES' else 'NOT NULL'})"
                )

            # Check constraints
            print("\nChecking constraints:")
            result = connection.execute(
                text(
                    """
                SELECT table_name, constraint_name
                FROM information_schema.table_constraints
                WHERE table_name IN ('rollout_update_logs', 'rollout_quotas')
                AND constraint_name LIKE '%report_quarter%'
                ORDER BY table_name, constraint_name;
            """
                )
            )
            for row in result:
                print(f"  {row.table_name}: {row.constraint_name}")

        print("\nChanges made:")
        print("- rollout_update_logs.report_quarter: INTEGER NOT NULL (1-4)")
        print("- rollout_quotas.report_quarter: INTEGER NULL (1-4)")
        print("- Removed separate quarter columns")
        print("- Updated constraints and indexes")
        print("- Preserved data integrity during migration")

    except Exception as e:
        print(f"❌ Error updating columns: {e}")
        return False

    return True


if __name__ == "__main__":
    success = replace_quarter_with_numeric_report_quarter()
    if success:
        print("\n🎉 Migration completed successfully!")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)
