#!/usr/bin/env python3
"""
Archive Legacy Migrations

This script moves all legacy migration files to the archive folder,
keeping only the consolidated create_complete_schema.py for new installations.
"""

import shutil
from pathlib import Path


def archive_legacy_migrations():
    """Move legacy migrations to archive folder"""

    migrations_dir = Path(__file__).parent
    archive_dir = migrations_dir / "archive"

    # List of legacy migration files to archive
    legacy_files = [
        "add_company_geolocation.py",
        "add_report_year_to_rollout_quotas.py",
        "create_rollout_tables.py",
        "create_rollout_update_logs_table.py",
        "fix_quarter_fields.py",
        "replace_quarter_with_numeric_report_quarter.py",
        "update_rollout_logs_quarter_fields.py",
        "update_rollout_quotas_unique_constraint.py",
    ]

    print("📦 Archiving legacy migration files...")

    archived_count = 0
    for filename in legacy_files:
        source_file = migrations_dir / filename
        if source_file.exists():
            dest_file = archive_dir / filename
            shutil.move(str(source_file), str(dest_file))
            print(f"  ✅ Moved {filename} to archive/")
            archived_count += 1
        else:
            print(f"  ⚠️  File not found: {filename}")

    print(f"\n🎉 Archived {archived_count} legacy migration files")
    print("📋 Active migrations:")

    # List remaining files in migrations directory
    remaining_files = [
        f
        for f in migrations_dir.iterdir()
        if f.is_file() and f.suffix == ".py" and f.name != __file__.split("/")[-1]
    ]

    for f in sorted(remaining_files):
        print(f"  - {f.name}")

    print("\n✅ Migrations directory cleaned up!")
    print("💡 Use 'create_complete_schema.py' for new database installations")


if __name__ == "__main__":
    archive_legacy_migrations()
