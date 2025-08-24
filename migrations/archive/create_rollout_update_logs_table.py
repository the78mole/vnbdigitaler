#!/usr/bin/env python3
"""
Create rollout_update_logs table for tracking report updates.

This table tracks the download and processing of BNetzA rollout quota reports,
including the source URL, file hash, processing statistics, and metadata.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


from sqlalchemy import create_engine

from src.database_config import get_database_url


def create_rollout_update_logs_table():
    """Create the rollout_update_logs table."""

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

    # SQL for creating the rollout_update_logs table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS rollout_update_logs (
        id SERIAL PRIMARY KEY,

        -- Report source information
        article_url TEXT NOT NULL,
        excel_filename VARCHAR(255) NOT NULL,
        excel_file_hash VARCHAR(64) NOT NULL UNIQUE,

        -- Report metadata
        report_reference_date DATE NOT NULL,
        report_quarter VARCHAR(10) NOT NULL,
        report_year INTEGER NOT NULL,

        -- Processing statistics
        total_entries_in_report INTEGER NOT NULL DEFAULT 0,
        entries_updated INTEGER NOT NULL DEFAULT 0,
        entries_added INTEGER NOT NULL DEFAULT 0,
        entries_with_wrong_reference_date INTEGER NOT NULL DEFAULT 0,

        -- Processing metadata
        download_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        processing_timestamp TIMESTAMP WITH TIME ZONE,
        processing_duration_seconds NUMERIC(10,3),

        -- Additional information
        notes TEXT,
        error_message TEXT,

        -- Status tracking
        status VARCHAR(20) NOT NULL DEFAULT 'downloaded',

        -- Timestamps
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

        CONSTRAINT chk_report_year_valid CHECK (report_year >= 2020 AND report_year <= 2050),
        CONSTRAINT chk_status_valid CHECK (status IN ('downloaded', 'processing', 'completed', 'failed')),
        CONSTRAINT chk_entries_positive CHECK (
            total_entries_in_report >= 0 AND
            entries_updated >= 0 AND
            entries_added >= 0 AND
            entries_with_wrong_reference_date >= 0
        )
    );

    -- Create indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_report_quarter
        ON rollout_update_logs (report_quarter);
    CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_report_year
        ON rollout_update_logs (report_year);
    CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_reference_date
        ON rollout_update_logs (report_reference_date);
    CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_status
        ON rollout_update_logs (status);
    CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_download_timestamp
        ON rollout_update_logs (download_timestamp);

    -- Create trigger for automatic updated_at timestamp
    CREATE OR REPLACE FUNCTION update_rollout_update_logs_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_rollout_update_logs_updated_at
        BEFORE UPDATE ON rollout_update_logs
        FOR EACH ROW
        EXECUTE FUNCTION update_rollout_update_logs_updated_at();

    -- Add comment to the table
    COMMENT ON TABLE rollout_update_logs IS 'Logs for tracking BNetzA rollout quota report downloads and updates';
    COMMENT ON COLUMN rollout_update_logs.article_url IS 'URL of the BNetzA article page containing the report';
    COMMENT ON COLUMN rollout_update_logs.excel_filename IS 'Original filename of the downloaded Excel file';
    COMMENT ON COLUMN rollout_update_logs.excel_file_hash IS 'SHA-256 hash of the Excel file content for change detection';
    COMMENT ON COLUMN rollout_update_logs.report_reference_date IS 'The official reference date (Stichtag) of the report data';
    COMMENT ON COLUMN rollout_update_logs.report_quarter IS 'Quarter of the report (e.g. Q1_2025)';
    COMMENT ON COLUMN rollout_update_logs.entries_with_wrong_reference_date IS 'Number of entries with different reference dates than expected';
    COMMENT ON COLUMN rollout_update_logs.status IS 'Processing status: downloaded, processing, completed, failed';
    """

    try:
        print("Creating rollout_update_logs table...")

        # Execute the SQL
        with engine.connect() as connection:
            connection.execute(text(create_table_sql))
            connection.commit()
            print("✅ rollout_update_logs table created successfully!")

        print("\nTable structure:")
        print("- article_url: URL der BNetzA-Artikelseite")
        print("- excel_filename: Name der Excel-Datei")
        print("- excel_file_hash: SHA-256 Hash der Datei für Änderungserkennung")
        print("- report_reference_date: Offizieller Stichtag des Reports")
        print("- report_quarter: Quartal (z.B. Q1_2025)")
        print("- total_entries_in_report: Gesamtanzahl Einträge im Report")
        print("- entries_updated: Anzahl aktualisierte Einträge")
        print("- entries_added: Anzahl neue Einträge")
        print("- entries_with_wrong_reference_date: Einträge mit abweichendem Stichtag")
        print("- download_timestamp: Zeitpunkt des Downloads")
        print("- processing_timestamp: Zeitpunkt der Verarbeitung")
        print("- status: downloaded, processing, completed, failed")

    except Exception as e:
        print(f"❌ Error creating rollout_update_logs table: {e}")
        return False

    return True


if __name__ == "__main__":
    # Import text function for SQL execution
    from sqlalchemy import text

    success = create_rollout_update_logs_table()
    if success:
        print("\n🎉 Migration completed successfully!")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)
