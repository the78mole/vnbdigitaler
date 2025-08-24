#!/usr/bin/env python3
"""
Consolidated Migration: Create Complete VNBdigitaler Database Schema

This migration creates the complete database schema for VNBdigitaler from scratch,
incorporating all previous migrations into a single, comprehensive setup.

This includes:
- Companies table with BDEW data and vnbdigital.de integration
- Rollout companies and quotas tables for BNetzA rollout tracking
- Rollout update logs for automated report processing
- All necessary indexes, constraints, and relationships

Author: VNBdigitaler Project
Date: 2025-08-25
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

# ruff: noqa: E402
from sqlalchemy import create_engine, text

from src.database_config import get_database_url


def create_complete_database_schema():
    """Create the complete VNBdigitaler database schema"""

    database_url = get_database_url()
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://", 1
        )
        database_url = database_url.replace("ssl=require", "sslmode=require")

    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Check if tables already exist
        result = conn.execute(
            text(
                """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('companies', 'rollout_companies', 'rollout_quotas', 'rollout_update_logs');
        """
            )
        )
        existing_tables = [row.table_name for row in result]

        if existing_tables:
            print("⚠️  WARNING: Database already contains VNBdigitaler tables:")
            for table in existing_tables:
                print(f"  - {table}")
            print("\nThis script is designed for fresh database installations.")
            print(
                "Continuing will add missing tables and indexes but won't modify existing data.\n"
            )

        # Start transaction
        trans = conn.begin()

        try:
            print("🏗️  Creating complete VNBdigitaler database schema...")

            # 1. Companies table (main BDEW companies with vnbdigital.de integration)
            print("📋 Creating companies table...")
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS companies (
                    id SERIAL PRIMARY KEY,

                    -- BDEW data (Single Source of Truth)
                    bdew_code VARCHAR(20) UNIQUE NOT NULL,
                    bdew_name VARCHAR(255) NOT NULL,
                    bdew_name_normalized VARCHAR(255) UNIQUE NOT NULL,
                    bdew_city VARCHAR(100),

                    -- vnbdigital.de Stammdaten
                    vnbdigital_name VARCHAR(255),
                    vnbdigital_address VARCHAR(255),
                    vnbdigital_postcode VARCHAR(10),
                    vnbdigital_city VARCHAR(100),
                    vnbdigital_phone VARCHAR(50),
                    vnbdigital_email VARCHAR(255),
                    vnbdigital_website VARCHAR(255),
                    vnbdigital_grid_types TEXT[],

                    -- Geographic data
                    network_territory_geojson JSONB,
                    latitude DOUBLE PRECISION,
                    longitude DOUBLE PRECISION,
                    geocoding_address TEXT,
                    geocoding_source VARCHAR(50),
                    geocoding_confidence DOUBLE PRECISION,
                    geocoding_timestamp TIMESTAMP WITH TIME ZONE,

                    -- Metadata
                    source_metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                );
            """
                )
            )

            # 2. Rollout companies table (BNetzA company names)
            print("🏢 Creating rollout_companies table...")
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS rollout_companies (
                    id SERIAL PRIMARY KEY,
                    bnetza_name VARCHAR(500) UNIQUE NOT NULL,
                    normalized_name VARCHAR(500) NOT NULL,
                    bdew_company_id INTEGER REFERENCES companies(id),
                    is_manually_verified BOOLEAN DEFAULT FALSE NOT NULL,
                    verification_notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
                );
            """
                )
            )

            # 3. Rollout quotas table (time-series quota data)
            print("📊 Creating rollout_quotas table...")
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS rollout_quotas (
                    id SERIAL PRIMARY KEY,
                    rollout_company_id INTEGER REFERENCES rollout_companies(id) NOT NULL,
                    rollout_quota DECIMAL(10,6) NOT NULL,
                    reference_date DATE NOT NULL,
                    report_quarter INTEGER,
                    report_year INTEGER,
                    source_file VARCHAR(200) NOT NULL,
                    csv_line_number INTEGER,
                    import_date TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    import_metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

                    CONSTRAINT chk_quota_range CHECK (rollout_quota >= 0.0 AND rollout_quota <= 1.0),
                    CONSTRAINT chk_report_quarter_valid CHECK (report_quarter IS NULL OR (report_quarter >= 1 AND report_quarter <= 4)),
                    CONSTRAINT chk_report_year_valid CHECK (report_year IS NULL OR (report_year >= 2024 AND report_year <= 2030)),
                    CONSTRAINT uq_rollout_quota_company_date_quarter_year UNIQUE (rollout_company_id, reference_date, report_quarter, report_year)
                );
            """
                )
            )

            # 4. Rollout update logs table (tracking automated report processing)
            print("📝 Creating rollout_update_logs table...")
            conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS rollout_update_logs (
                    id SERIAL PRIMARY KEY,

                    -- Report identification
                    article_url VARCHAR(500) NOT NULL,
                    excel_filename VARCHAR(255) NOT NULL,
                    excel_file_hash VARCHAR(64) NOT NULL,
                    report_reference_date DATE NOT NULL,
                    report_quarter INTEGER NOT NULL,
                    report_year INTEGER NOT NULL,

                    -- Processing status
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',

                    -- Statistics
                    total_entries_in_report INTEGER NOT NULL DEFAULT 0,
                    entries_matched INTEGER NOT NULL DEFAULT 0,
                    entries_updated INTEGER NOT NULL DEFAULT 0,
                    entries_added INTEGER NOT NULL DEFAULT 0,
                    entries_with_wrong_reference_date INTEGER NOT NULL DEFAULT 0,

                    -- Timing
                    download_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    processing_timestamp TIMESTAMP WITH TIME ZONE,
                    processing_duration_seconds DOUBLE PRECISION,

                    -- Additional information
                    notes TEXT,
                    error_message TEXT,

                    -- Metadata
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

                    CONSTRAINT chk_status_valid CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
                    CONSTRAINT chk_report_quarter_valid CHECK (report_quarter >= 1 AND report_quarter <= 4),
                    CONSTRAINT chk_report_year_valid CHECK (report_year >= 2020 AND report_year <= 2050),
                    CONSTRAINT chk_total_entries_positive CHECK (total_entries_in_report >= 0),
                    CONSTRAINT chk_entries_matched_positive CHECK (entries_matched >= 0),
                    CONSTRAINT chk_entries_updated_positive CHECK (entries_updated >= 0),
                    CONSTRAINT chk_entries_added_positive CHECK (entries_added >= 0),
                    CONSTRAINT chk_wrong_date_entries_positive CHECK (entries_with_wrong_reference_date >= 0),
                    CONSTRAINT chk_processing_duration_positive CHECK (processing_duration_seconds IS NULL OR processing_duration_seconds >= 0),
                    CONSTRAINT uq_rollout_update_logs_file_hash UNIQUE (excel_file_hash)
                );
            """
                )
            )

            print("✅ Created all tables")

            # Create indexes for companies table
            print("🔍 Creating indexes for companies table...")
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_companies_bdew_code ON companies(bdew_code);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_companies_bdew_name ON companies(bdew_name);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_companies_bdew_name_normalized ON companies(bdew_name_normalized);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_companies_bdew_city ON companies(bdew_city);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_companies_vnbdigital_name ON companies(vnbdigital_name);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_companies_vnbdigital_city ON companies(vnbdigital_city);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_companies_location ON companies(latitude, longitude);"
                )
            )

            # Create indexes for rollout_companies table
            print("🔍 Creating indexes for rollout_companies table...")
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_companies_bnetza_name ON rollout_companies(bnetza_name);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_companies_normalized_name ON rollout_companies(normalized_name);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_companies_bdew_company_id ON rollout_companies(bdew_company_id);"
                )
            )

            # Create indexes for rollout_quotas table
            print("🔍 Creating indexes for rollout_quotas table...")
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_quotas_company_id ON rollout_quotas(rollout_company_id);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_quotas_reference_date ON rollout_quotas(reference_date);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_quotas_report_quarter ON rollout_quotas(report_quarter);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_quotas_report_year ON rollout_quotas(report_year);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_quotas_quarter_year ON rollout_quotas(report_quarter, report_year);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_quotas_source_file ON rollout_quotas(source_file);"
                )
            )

            # Create indexes for rollout_update_logs table
            print("🔍 Creating indexes for rollout_update_logs table...")
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_article_url ON rollout_update_logs(article_url);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_excel_filename ON rollout_update_logs(excel_filename);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_status ON rollout_update_logs(status);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_report_quarter ON rollout_update_logs(report_quarter);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_report_year ON rollout_update_logs(report_year);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_report_quarter_year ON rollout_update_logs(report_quarter, report_year);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_download_timestamp ON rollout_update_logs(download_timestamp);"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_update_logs_processing_timestamp ON rollout_update_logs(processing_timestamp);"
                )
            )

            print("✅ Created all indexes")

            # Commit transaction
            trans.commit()
            print("🎉 Complete VNBdigitaler database schema created successfully!")

            # Print summary
            print("\n" + "=" * 60)
            print("DATABASE SCHEMA SUMMARY")
            print("=" * 60)
            print(
                "📋 companies: BDEW companies with vnbdigital.de integration and geocoding"
            )
            print("🏢 rollout_companies: BNetzA company names for rollout tracking")
            print(
                "📊 rollout_quotas: Time-series rollout quota data with quarter/year tracking"
            )
            print("📝 rollout_update_logs: Automated report processing logs")
            print("\n✅ Ready for data import and automated rollout quota updates!")

        except Exception as e:
            trans.rollback()
            print(f"❌ Database schema creation failed: {e}")
            raise


if __name__ == "__main__":
    create_complete_database_schema()
