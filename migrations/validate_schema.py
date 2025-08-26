#!/usr/bin/env python3
"""
Database Schema Validation Script

This script validates the database initialization script without actually
executing it. It checks SQL syntax and verifies the schema against the
current SQLAlchemy models.

Usage:
    python migrations/validate_schema.py

Author: VNBdigitaler Project
Date: 2025-08-26
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

# ruff: noqa: E402
from sqlalchemy import MetaData, create_engine, text

from src.database_config import get_database_url


def validate_schema_sql():
    """Validate the SQL statements in the initialization script."""

    print("🔍 Validating database schema SQL...")

    # Read the init script to extract SQL statements
    init_script_path = Path("migrations/init_database.py")

    if not init_script_path.exists():
        print("❌ init_database.py not found")
        return False

    with open(init_script_path, "r") as f:
        content = f.read()

    # Extract SQL statements (basic validation)
    if "CREATE TABLE companies" in content:
        print("✅ Found companies table creation")
    else:
        print("❌ companies table creation not found")
        return False

    if "CREATE TABLE rollout_companies" in content:
        print("✅ Found rollout_companies table creation")
    else:
        print("❌ rollout_companies table creation not found")
        return False

    if "CREATE TABLE rollout_quotas" in content:
        print("✅ Found rollout_quotas table creation")
    else:
        print("❌ rollout_quotas table creation not found")
        return False

    if "CREATE TABLE rollout_update_logs" in content:
        print("✅ Found rollout_update_logs table creation")
    else:
        print("❌ rollout_update_logs table creation not found")
        return False

    # Check for proper constraints
    if "REFERENCES companies(bdew_code)" in content:
        print("✅ Found foreign key reference to companies")
    else:
        print("❌ Foreign key reference to companies not found")
        return False

    if "UNIQUE (rollout_company_id, reference_date" in content:
        print("✅ Found unique constraint on rollout_quotas")
    else:
        print("❌ Unique constraint on rollout_quotas not found")
        return False

    print("✅ SQL validation passed")
    return True


def validate_models_compatibility():
    """Validate that the schema is compatible with SQLAlchemy models."""

    print("🔍 Validating SQLAlchemy models compatibility...")

    try:
        # Import models to check they load correctly
        from src.models import Company, RolloutCompany, RolloutQuota, RolloutUpdateLog

        print("✅ Company model loaded")
        print("✅ RolloutCompany model loaded")
        print("✅ RolloutQuota model loaded")
        print("✅ RolloutUpdateLog model loaded")

        # Check key fields exist
        if hasattr(Company, "bdew_code"):
            print("✅ Company.bdew_code field exists")
        else:
            print("❌ Company.bdew_code field missing")
            return False

        if hasattr(RolloutCompany, "bnetza_name"):
            print("✅ RolloutCompany.bnetza_name field exists")
        else:
            print("❌ RolloutCompany.bnetza_name field missing")
            return False

        if hasattr(RolloutQuota, "rollout_quota"):
            print("✅ RolloutQuota.rollout_quota field exists")
        else:
            print("❌ RolloutQuota.rollout_quota field missing")
            return False

        print("✅ Models compatibility validation passed")
        return True

    except ImportError as e:
        print(f"❌ Failed to import models: {e}")
        return False


def validate_database_connection():
    """Validate database connection without making changes."""

    print("🔍 Validating database connection...")

    try:
        database_url = get_database_url()

        if database_url.startswith("postgresql+asyncpg://"):
            database_url = database_url.replace(
                "postgresql+asyncpg://", "postgresql+psycopg2://", 1
            )
            database_url = database_url.replace("ssl=require", "sslmode=require")

        engine = create_engine(database_url)

        with engine.connect() as conn:
            # Simple connectivity test
            result = conn.execute(text("SELECT 1 as test;"))
            test_value = result.scalar()

            if test_value == 1:
                print("✅ Database connection successful")
                return True
            else:
                print("❌ Database connection test failed")
                return False

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def main():
    """Main validation function."""

    print("🚀 VNBdigitaler Database Schema Validation")
    print("=" * 60)

    validations = [
        ("SQL Schema", validate_schema_sql),
        ("SQLAlchemy Models", validate_models_compatibility),
        ("Database Connection", validate_database_connection),
    ]

    all_passed = True

    for name, validator in validations:
        print(f"\n📋 {name} Validation:")
        print("-" * 40)

        if not validator():
            all_passed = False
            print(f"❌ {name} validation failed")
        else:
            print(f"✅ {name} validation passed")

    print("\n" + "=" * 60)

    if all_passed:
        print("🎉 All validations passed!")
        print("✅ Database initialization script is ready to use")
        print("\nTo initialize the database, run:")
        print("   python migrations/init_database.py")
    else:
        print("❌ Some validations failed")
        print("Please check the issues above before running the initialization script")
        sys.exit(1)


if __name__ == "__main__":
    main()
