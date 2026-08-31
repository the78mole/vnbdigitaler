#!/usr/bin/env python3
"""
VNBdigitaler Database Initialization Script

This script completely initializes the VNBdigitaler database schema from scratch.
It replaces all previous migration scripts and creates the complete, normalized
database structure based on the current SQLAlchemy models.

Features:
- Creates all tables with proper relationships
- Sets up all indexes and constraints
- Includes proper data types and checks
- Ready for immediate use with the application

Usage:
    python migrations/init_database.py

Author: VNBdigitaler Project
Date: 2025-08-26
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

# ruff: noqa: E402
from sqlalchemy import create_engine, text

from src.database_config import get_database_url


def drop_all_vnbdigitaler_tables():
    """Drop all VNBdigitaler tables to ensure clean state."""

    database_url = get_database_url()
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://", 1
        )
        database_url = database_url.replace("ssl=require", "sslmode=require")

    engine = create_engine(database_url)

    with engine.connect() as conn:
        print("🗑️  Dropping existing VNBdigitaler tables if they exist...")

        # Drop tables in correct order (respecting foreign keys)
        tables_to_drop = [
            "rollout_quotas",
            "rollout_companies",
            "rollout_update_logs",
            "rollout_reports",
            "download_sessions",
            "companies",
        ]

        for table in tables_to_drop:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
                print(f"  ✅ Dropped table: {table}")
            except Exception as e:
                print(f"  ⚠️  Could not drop table {table}: {e}")

        conn.commit()


def create_complete_database_schema():
    """Create the complete VNBdigitaler database schema from scratch."""

    database_url = get_database_url()
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://", 1
        )
        database_url = database_url.replace("ssl=require", "sslmode=require")

    engine = create_engine(database_url)

    with engine.connect() as conn:
        trans = conn.begin()

        try:
            print("🏗️  Creating complete VNBdigitaler database schema...")

            # 1. Companies table (BDEW companies with vnbdigital.de integration)
            print("📋 Creating companies table...")
            conn.execute(text("""
                CREATE TABLE companies (
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
                    vnbdigital_grid_types VARCHAR(50)[],

                    -- Geographic data (network territory)
                    network_territory_geojson JSONB,
                    network_territory_layer_url VARCHAR(1000),

                    -- Company headquarters location (WGS84 decimal degrees)
                    company_latitude DOUBLE PRECISION,
                    company_longitude DOUBLE PRECISION,

                    -- vnbdigital.de Zusatzdaten (flexible JSONB structure)
                    vnbdigital_raw_data JSONB,
                    vnbdigital_last_updated TIMESTAMP WITH TIME ZONE,

                    -- Metadata
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

                    -- Constraints
                    CONSTRAINT chk_company_latitude CHECK (company_latitude IS NULL OR (company_latitude >= -90 AND company_latitude <= 90)),
                    CONSTRAINT chk_company_longitude CHECK (company_longitude IS NULL OR (company_longitude >= -180 AND company_longitude <= 180)),
                    CONSTRAINT chk_bdew_code_not_empty CHECK (length(trim(bdew_code)) > 0),
                    CONSTRAINT chk_bdew_name_not_empty CHECK (length(trim(bdew_name)) > 0),
                    CONSTRAINT chk_normalized_name_not_empty CHECK (length(trim(bdew_name_normalized)) > 0)
                );
            """))

            # 2. Rollout companies table (BNetzA company names linked to BDEW)
            print("🏢 Creating rollout_companies table...")
            conn.execute(text("""
                CREATE TABLE rollout_companies (
                    id SERIAL PRIMARY KEY,
                    bnetza_name VARCHAR(500) UNIQUE NOT NULL,
                    bnetza_name_normalized VARCHAR(500) NOT NULL,
                    bdew_code VARCHAR(20) REFERENCES companies(bdew_code),
                    verification_notes TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

                    -- Constraints
                    CONSTRAINT chk_bnetza_name_not_empty CHECK (length(trim(bnetza_name)) > 0),
                    CONSTRAINT chk_bnetza_name_normalized_not_empty CHECK (length(trim(bnetza_name_normalized)) > 0)
                );
            """))

            # 3. Rollout quotas table (time-series quota data)
            print("📊 Creating rollout_quotas table...")
            conn.execute(text("""
                CREATE TABLE rollout_quotas (
                    id SERIAL PRIMARY KEY,
                    rollout_company_id INTEGER REFERENCES rollout_companies(id) NOT NULL,
                    rollout_quota DECIMAL(8,4) NOT NULL,
                    reference_date DATE NOT NULL,
                    report_quarter INTEGER,
                    report_year INTEGER,
                    quarter_year VARCHAR(10),
                    source_file VARCHAR(200) NOT NULL,
                    csv_line_number INTEGER,
                    excel_file_hash VARCHAR(64),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

                    -- Constraints
                    CONSTRAINT chk_quota_range CHECK (rollout_quota >= 0.0 AND rollout_quota <= 100.0),
                    CONSTRAINT chk_report_quarter_valid CHECK (report_quarter IS NULL OR (report_quarter >= 1 AND report_quarter <= 4)),
                    CONSTRAINT chk_report_year_valid CHECK (report_year IS NULL OR (report_year >= 2020 AND report_year <= 2050)),
                    CONSTRAINT uq_rollout_quota_unique UNIQUE (rollout_company_id, reference_date, report_quarter, report_year)
                );
            """))

            # 4. Rollout update logs table (tracking automated report processing)
            print("📝 Creating rollout_update_logs table...")
            conn.execute(text("""
                CREATE TABLE rollout_update_logs (
                    id SERIAL PRIMARY KEY,

                    -- Report identification
                    article_url VARCHAR(500) NOT NULL,
                    excel_filename VARCHAR(255) NOT NULL,
                    excel_file_hash VARCHAR(64),
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

                    -- Constraints
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
            """))

            # 5. Rollout reports table (BNetzA report metadata)
            print("📄 Creating rollout_reports table...")
            conn.execute(text("""
                CREATE TABLE rollout_reports (
                    id SERIAL PRIMARY KEY,

                    -- Report identification
                    filename VARCHAR(255) NOT NULL,
                    url TEXT NOT NULL,
                    quarter INTEGER NOT NULL,
                    year INTEGER NOT NULL,

                    -- Analysis metadata
                    confidence VARCHAR(20) NOT NULL,
                    method INTEGER NOT NULL DEFAULT 0,
                    reasoning TEXT,

                    -- AI analysis details
                    ai_model_used VARCHAR(100),
                    ai_tokens_used INTEGER,
                    ai_response TEXT,

                    -- Download session information
                    download_session_id VARCHAR(100),
                    source_metadata JSONB,

                    -- Timestamps
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

                    -- Status tracking
                    is_latest BOOLEAN DEFAULT FALSE NOT NULL,
                    is_processed BOOLEAN DEFAULT FALSE NOT NULL,

                    -- Constraints
                    CONSTRAINT quarter_range_check CHECK (quarter >= 1 AND quarter <= 4),
                    CONSTRAINT method_range_check CHECK (method >= 0 AND method <= 2)
                );
            """))

            # 6. Download sessions table (tracking download sessions)
            print("💾 Creating download_sessions table...")
            conn.execute(text("""
                CREATE TABLE download_sessions (
                    id SERIAL PRIMARY KEY,

                    -- Session identification
                    session_id VARCHAR(100) UNIQUE NOT NULL,
                    temp_directory VARCHAR(255) NOT NULL,

                    -- Download statistics
                    total_urls_found INTEGER NOT NULL DEFAULT 0,
                    excel_urls_found INTEGER NOT NULL DEFAULT 0,

                    -- Session metadata
                    user_agent VARCHAR(255) NOT NULL,
                    script_version VARCHAR(50) NOT NULL,

                    -- Status tracking
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    error_message TEXT,

                    -- Timestamps
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,

                    -- Constraints
                    CONSTRAINT chk_download_status_valid CHECK (status IN ('active', 'completed', 'failed', 'cancelled'))
                );
            """))

            print("✅ Created all tables")

            # Create indexes for companies table
            print("🔍 Creating indexes for companies table...")
            indexes_companies = [
                "CREATE INDEX idx_companies_bdew_code ON companies(bdew_code);",
                "CREATE INDEX idx_companies_bdew_name ON companies(bdew_name);",
                "CREATE INDEX idx_companies_bdew_name_normalized ON companies(bdew_name_normalized);",
                "CREATE INDEX idx_companies_bdew_city ON companies(bdew_city);",
                "CREATE INDEX idx_companies_vnbdigital_name ON companies(vnbdigital_name);",
                "CREATE INDEX idx_companies_vnbdigital_city ON companies(vnbdigital_city);",
                "CREATE INDEX idx_companies_location ON companies(company_latitude, company_longitude);",
                "CREATE INDEX idx_companies_created_at ON companies(created_at);",
                "CREATE INDEX idx_companies_updated_at ON companies(updated_at);",
            ]
            for index in indexes_companies:
                conn.execute(text(index))

            # Create indexes for rollout_companies table
            print("🔍 Creating indexes for rollout_companies table...")
            indexes_rollout_companies = [
                "CREATE INDEX idx_rollout_companies_bnetza_name ON rollout_companies(bnetza_name);",
                "CREATE INDEX idx_rollout_companies_bnetza_name_normalized ON rollout_companies(bnetza_name_normalized);",
                "CREATE INDEX idx_rollout_companies_bdew_code ON rollout_companies(bdew_code);",
                "CREATE INDEX idx_rollout_companies_created_at ON rollout_companies(created_at);",
                "CREATE INDEX idx_rollout_companies_updated_at ON rollout_companies(updated_at);",
            ]
            for index in indexes_rollout_companies:
                conn.execute(text(index))

            # Create indexes for rollout_quotas table
            print("🔍 Creating indexes for rollout_quotas table...")
            indexes_rollout_quotas = [
                "CREATE INDEX idx_rollout_quotas_company_id ON rollout_quotas(rollout_company_id);",
                "CREATE INDEX idx_rollout_quotas_reference_date ON rollout_quotas(reference_date);",
                "CREATE INDEX idx_rollout_quotas_report_quarter ON rollout_quotas(report_quarter);",
                "CREATE INDEX idx_rollout_quotas_report_year ON rollout_quotas(report_year);",
                "CREATE INDEX idx_rollout_quotas_quarter_year ON rollout_quotas(quarter_year);",
                "CREATE INDEX idx_rollout_quotas_source_file ON rollout_quotas(source_file);",
                "CREATE INDEX idx_rollout_quotas_excel_file_hash ON rollout_quotas(excel_file_hash);",
                "CREATE INDEX idx_rollout_quotas_created_at ON rollout_quotas(created_at);",
            ]
            for index in indexes_rollout_quotas:
                conn.execute(text(index))

            # Create indexes for rollout_update_logs table
            print("🔍 Creating indexes for rollout_update_logs table...")
            indexes_rollout_update_logs = [
                "CREATE INDEX idx_rollout_update_logs_article_url ON rollout_update_logs(article_url);",
                "CREATE INDEX idx_rollout_update_logs_excel_filename ON rollout_update_logs(excel_filename);",
                "CREATE INDEX idx_rollout_update_logs_excel_file_hash ON rollout_update_logs(excel_file_hash);",
                "CREATE INDEX idx_rollout_update_logs_status ON rollout_update_logs(status);",
                "CREATE INDEX idx_rollout_update_logs_report_quarter ON rollout_update_logs(report_quarter);",
                "CREATE INDEX idx_rollout_update_logs_report_year ON rollout_update_logs(report_year);",
                "CREATE INDEX idx_rollout_update_logs_quarter_year ON rollout_update_logs(report_quarter, report_year);",
                "CREATE INDEX idx_rollout_update_logs_download_timestamp ON rollout_update_logs(download_timestamp);",
                "CREATE INDEX idx_rollout_update_logs_processing_timestamp ON rollout_update_logs(processing_timestamp);",
                "CREATE INDEX idx_rollout_update_logs_created_at ON rollout_update_logs(created_at);",
            ]
            for index in indexes_rollout_update_logs:
                conn.execute(text(index))

            # Create indexes for rollout_reports table
            print("🔍 Creating indexes for rollout_reports table...")
            indexes_rollout_reports = [
                "CREATE INDEX idx_rollout_reports_filename ON rollout_reports(filename);",
                "CREATE INDEX idx_rollout_reports_quarter ON rollout_reports(quarter);",
                "CREATE INDEX idx_rollout_reports_year ON rollout_reports(year);",
                "CREATE INDEX idx_rollout_reports_quarter_year ON rollout_reports(quarter, year);",
                "CREATE INDEX idx_rollout_reports_confidence ON rollout_reports(confidence);",
                "CREATE INDEX idx_rollout_reports_method ON rollout_reports(method);",
                "CREATE INDEX idx_rollout_reports_download_session_id ON rollout_reports(download_session_id);",
                "CREATE INDEX idx_rollout_reports_is_latest ON rollout_reports(is_latest);",
                "CREATE INDEX idx_rollout_reports_is_processed ON rollout_reports(is_processed);",
                "CREATE INDEX idx_rollout_reports_created_at ON rollout_reports(created_at);",
                "CREATE INDEX idx_rollout_reports_updated_at ON rollout_reports(updated_at);",
            ]
            for index in indexes_rollout_reports:
                conn.execute(text(index))

            # Create indexes for download_sessions table
            print("🔍 Creating indexes for download_sessions table...")
            indexes_download_sessions = [
                "CREATE INDEX idx_download_sessions_session_id ON download_sessions(session_id);",
                "CREATE INDEX idx_download_sessions_status ON download_sessions(status);",
                "CREATE INDEX idx_download_sessions_created_at ON download_sessions(created_at);",
                "CREATE INDEX idx_download_sessions_updated_at ON download_sessions(updated_at);",
            ]
            for index in indexes_download_sessions:
                conn.execute(text(index))

            print("✅ Created all indexes")

            # Commit transaction
            trans.commit()
            print("🎉 Complete VNBdigitaler database schema created successfully!")

            # Print summary
            print("\n" + "=" * 80)
            print("DATABASE SCHEMA SUMMARY")
            print("=" * 80)
            print(
                "📋 companies: BDEW companies with vnbdigital.de integration and geocoding"
            )
            print(
                "🏢 rollout_companies: BNetzA company names linked to BDEW companies via bdew_code"
            )
            print(
                "📊 rollout_quotas: Time-series rollout quota data with quarter/year tracking"
            )
            print(
                "📝 rollout_update_logs: Automated report processing logs and statistics"
            )
            print("📄 rollout_reports: BNetzA report metadata and AI analysis results")
            print(
                "💾 download_sessions: Download session tracking for report automation"
            )
            print(
                "\n✅ Database ready for data import and automated rollout quota updates!"
            )
            print("✅ All indexes created for optimal query performance!")

        except Exception as e:
            trans.rollback()
            print(f"❌ Database schema creation failed: {e}")
            raise


def main():
    """Main function to initialize the database."""
    print("🚀 VNBdigitaler Database Initialization")
    print("=" * 50)

    response = input(
        "This will DROP ALL existing VNBdigitaler tables and recreate them.\nContinue? (y/N): "
    )
    if response.lower() != "y":
        print("❌ Aborted by user")
        return

    try:
        drop_all_vnbdigitaler_tables()
        create_complete_database_schema()
        print("\n🎯 Database initialization completed successfully!")
        print("You can now run data import scripts and start the application.")

    except Exception as e:
        print(f"\n❌ Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
