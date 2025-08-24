#!/usr/bin/env python3
"""
Migration: Add 'discovered' status to rollout_update_logs table

This migration updates the check constraint to allow 'discovered' as a valid status.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from sqlalchemy import create_engine, text

from src.database_config import get_database_url


def add_discovered_status():
    """Add 'discovered' status to the valid status constraint."""

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

    # SQL for updating the constraint
    update_sql = """
    -- Drop the old constraint
    ALTER TABLE rollout_update_logs DROP CONSTRAINT IF EXISTS chk_status_valid;

    -- Add new constraint with 'discovered' status
    ALTER TABLE rollout_update_logs
    ADD CONSTRAINT chk_status_valid
    CHECK (status IN ('discovered', 'downloaded', 'processing', 'completed', 'failed'));

    -- Update comment to reflect new status options
    COMMENT ON COLUMN rollout_update_logs.status IS 'Processing status: discovered, downloaded, processing, completed, failed';
    """

    try:
        print("🔄 Updating status constraint for rollout_update_logs table...")

        # Execute the SQL
        with engine.connect() as connection:
            connection.execute(text(update_sql))
            connection.commit()
            print("✅ Status constraint updated successfully!")

        print("\nStatus values now allowed:")
        print("- discovered: Report found but not yet processed")
        print("- downloaded: Excel file downloaded")
        print("- processing: Data processing in progress")
        print("- completed: All processing finished successfully")
        print("- failed: Processing failed with errors")

    except Exception as e:
        print(f"❌ Error updating status constraint: {e}")
        return False

    return True


if __name__ == "__main__":
    success = add_discovered_status()
    if success:
        print("\n🎉 Migration completed successfully!")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)
