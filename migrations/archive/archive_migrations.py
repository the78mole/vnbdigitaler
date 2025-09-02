#!/usr/bin/env python3
"""
Archive Legacy Migrations Script

This script moves all legacy migration files to an archive folder,
keeping only the new comprehensive init_database.py script.

The new init_database.py replaces all previous migrations and creates
the complete database schema from scratch.

Author: VNBdigitaler Project
Date: 2025-08-26
"""

import shutil
from pathlib import Path


def archive_legacy_migrations():
    """Archive all legacy migration files."""

    migrations_dir = Path("migrations")
    archive_dir = migrations_dir / "archive"

    # Create archive directory if it doesn't exist
    archive_dir.mkdir(exist_ok=True)

    # Files to keep (not archive)
    keep_files = {
        "init_database.py",  # New comprehensive init script
        "README.md",  # Documentation
        "archive_migrations.py",  # This script
        "archive",  # Archive directory
    }

    # Files to archive
    files_to_archive = [
        "add_company_geolocation.py",
        "add_discovered_status.py",
        "add_report_year_to_rollout_quotas.py",
        "add_unique_constraint_rollout_bdew_code.py",
        "archive_legacy_migrations.py",
        "convert_bdew_code_to_integer.py",
        "create_complete_schema.py",
        "create_rollout_update_logs_table.py",
        "fix_quarter_fields.py",
        "fix_rollout_companies_bdew_reference.py",
        "make_excel_file_hash_nullable.py",
        "remove_manual_verification_from_rollout.py",
        "remove_rollout_columns_from_companies.py",
        "remove_unused_rollout_column.py",
        "remove_verification_columns.py",
        "replace_quarter_with_numeric_report_quarter.py",
        "test_complete_schema.py",
        "update_rollout_logs_quarter_fields.py",
        "update_rollout_quotas_unique_constraint.py",
    ]

    print("📦 Archiving legacy migration files...")
    print("=" * 50)

    archived_count = 0

    for filename in files_to_archive:
        file_path = migrations_dir / filename

        if file_path.exists():
            # Move to archive
            archive_path = archive_dir / filename
            try:
                shutil.move(str(file_path), str(archive_path))
                print(f"✅ Archived: {filename}")
                archived_count += 1
            except Exception as e:
                print(f"❌ Failed to archive {filename}: {e}")
        else:
            print(f"⚠️  File not found: {filename}")

    print("\n" + "=" * 50)
    print(f"📦 Archived {archived_count} legacy migration files")
    print("✅ New migrations folder structure:")
    print("   - init_database.py (comprehensive database initialization)")
    print("   - README.md (documentation)")
    print(f"   - archive/ ({archived_count} legacy migrations)")
    print("\n🎯 Use 'python migrations/init_database.py' to initialize the database")


if __name__ == "__main__":
    archive_legacy_migrations()
