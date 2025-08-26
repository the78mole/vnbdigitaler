#!/usr/bin/env python3
"""
Migration: Fix rollout_companies table to use bdew_code instead of bdew_company_id

This migration:
1. Renames bdew_company_id column to bdew_code
2. Keeps the data type as INTEGER (BDEW codes are numeric)
3. Updates the foreign key reference from companies(id) to companies(bdew_code)
4. Converts companies.bdew_code from VARCHAR to INTEGER for consistency
5. Preserves existing data by converting company IDs to bdew_codes

Author: VNBdigitaler Project
Date: 2025-08-25
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

# ruff: noqa: E402
from sqlalchemy import create_engine, text

from src.database_config import get_database_url


def fix_rollout_companies_bdew_reference():
    """Fix rollout_companies table to use bdew_code instead of bdew_company_id"""

    database_url = get_database_url()
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://", 1
        )
        database_url = database_url.replace("ssl=require", "sslmode=require")

    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()

        try:
            print("🔧 Fixing rollout_companies table to use bdew_code reference...")
            print("🔧 Also converting companies.bdew_code from VARCHAR to INTEGER...")

            # Check if the column already exists and what type it is
            result = conn.execute(
                text(
                    """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'rollout_companies'
                AND column_name IN ('bdew_company_id', 'bdew_code')
                ORDER BY column_name;
            """
                )
            )
            columns = {row.column_name: row for row in result}

            if "bdew_code" in columns:
                print("✅ bdew_code column already exists")
                if columns["bdew_code"].data_type == "integer":
                    print("✅ bdew_code column already has correct type")
                    trans.commit()
                    return
                else:
                    print(
                        f"⚠️  bdew_code column exists but has wrong type: {columns['bdew_code'].data_type}"
                    )

            if "bdew_company_id" not in columns:
                print("ℹ️  bdew_company_id column doesn't exist - nothing to migrate")
                trans.commit()
                return

            # Step 0: Convert companies.bdew_code from VARCHAR to INTEGER
            print("� Converting companies.bdew_code from VARCHAR to INTEGER...")

            # Check current type of companies.bdew_code
            result = conn.execute(
                text(
                    """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = 'companies' AND column_name = 'bdew_code';
            """
                )
            )
            companies_bdew_type = result.fetchone()

            if companies_bdew_type and companies_bdew_type.data_type != "integer":
                print("   Converting companies.bdew_code to INTEGER...")
                # Drop foreign key constraints temporarily
                conn.execute(
                    text(
                        "ALTER TABLE rollout_companies DROP CONSTRAINT IF EXISTS fk_rollout_companies_bdew_code;"
                    )
                )

                # Check all values first
                result = conn.execute(
                    text(
                        "SELECT bdew_code FROM companies WHERE bdew_code !~ '^[0-9]+$' LIMIT 5"
                    )
                )
                non_numeric = list(result)
                if non_numeric:
                    print(f"   ⚠️  Warning: Found non-numeric bdew_codes:")
                    for row in non_numeric:
                        print(f"      - '{row.bdew_code}'")

                # Create new INTEGER column
                conn.execute(
                    text("ALTER TABLE companies ADD COLUMN bdew_code_int INTEGER;")
                )

                # Copy numeric values to new column
                conn.execute(
                    text(
                        """
                        UPDATE companies
                        SET bdew_code_int = bdew_code::INTEGER
                        WHERE bdew_code ~ '^[0-9]+$'
                    """
                    )
                )

                # Drop old column and rename new one
                conn.execute(text("ALTER TABLE companies DROP COLUMN bdew_code;"))
                conn.execute(
                    text(
                        "ALTER TABLE companies RENAME COLUMN bdew_code_int TO bdew_code;"
                    )
                )

                # Add unique constraint back
                conn.execute(
                    text(
                        "ALTER TABLE companies ADD CONSTRAINT companies_bdew_code_key UNIQUE (bdew_code);"
                    )
                )

                print("   ✅ companies.bdew_code converted to INTEGER")
            else:
                print("   ✅ companies.bdew_code is already INTEGER")

            print("📊 Checking existing data...")

            # Check if there are any existing references
            result = conn.execute(
                text(
                    "SELECT COUNT(*) as total, COUNT(bdew_company_id) as with_references FROM rollout_companies;"
                )
            )
            counts = result.fetchone()
            total_companies = counts.total if counts else 0
            with_references = counts.with_references if counts else 0

            print(f"   Total rollout companies: {total_companies}")
            print(f"   With BDEW references: {with_references}")

            # Step 1: Add the new bdew_code column as INTEGER
            print("🔧 Adding bdew_code column as INTEGER...")
            conn.execute(
                text(
                    "ALTER TABLE rollout_companies ADD COLUMN IF NOT EXISTS bdew_code INTEGER;"
                )
            )

            # Step 2: Populate bdew_code from existing bdew_company_id references
            if with_references > 0:
                print(
                    "🔄 Converting existing bdew_company_id references to bdew_codes..."
                )
                conn.execute(
                    text(
                        """
                    UPDATE rollout_companies
                    SET bdew_code = (
                        SELECT c.bdew_code
                        FROM companies c
                        WHERE c.id = rollout_companies.bdew_company_id
                    )
                    WHERE bdew_company_id IS NOT NULL;
                """
                    )
                )

                # Check how many were successfully converted
                result = conn.execute(
                    text(
                        "SELECT COUNT(*) as converted FROM rollout_companies WHERE bdew_code IS NOT NULL;"
                    )
                )
                converted_row = result.fetchone()
                converted = converted_row.converted if converted_row else 0
                print(f"   ✅ Successfully converted {converted} references")

            # Step 3: Drop the old foreign key constraint (if it exists)
            print("🗑️  Removing old foreign key constraint...")
            try:
                # Find the constraint name
                result = conn.execute(
                    text(
                        """
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE table_name = 'rollout_companies'
                    AND constraint_type = 'FOREIGN KEY'
                    AND constraint_name LIKE '%bdew_company_id%';
                """
                    )
                )
                constraints = [row.constraint_name for row in result]

                for constraint_name in constraints:
                    conn.execute(
                        text(
                            f"ALTER TABLE rollout_companies DROP CONSTRAINT IF EXISTS {constraint_name};"
                        )
                    )
                    print(f"   ✅ Dropped constraint: {constraint_name}")

            except Exception as e:
                print(f"   ⚠️  Warning: Could not drop foreign key constraint: {e}")

            # Step 4: Drop the old bdew_company_id column
            print("🗑️  Removing old bdew_company_id column...")
            conn.execute(
                text(
                    "ALTER TABLE rollout_companies DROP COLUMN IF EXISTS bdew_company_id;"
                )
            )

            # Step 5: Add foreign key constraint for the new bdew_code column
            print("🔗 Adding new foreign key constraint...")
            conn.execute(
                text(
                    """
                ALTER TABLE rollout_companies
                ADD CONSTRAINT fk_rollout_companies_bdew_code
                FOREIGN KEY (bdew_code) REFERENCES companies(bdew_code);
            """
                )
            )

            # Step 6: Update the index
            print("🔍 Updating indexes...")
            conn.execute(
                text("DROP INDEX IF EXISTS idx_rollout_companies_bdew_company_id;")
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_companies_bdew_code ON rollout_companies(bdew_code);"
                )
            )

            # Commit transaction
            trans.commit()
            print(
                "✅ Successfully fixed rollout_companies table to use bdew_code reference!"
            )

            # Print summary
            print("\n" + "=" * 60)
            print("MIGRATION SUMMARY")
            print("=" * 60)
            print(
                "🔧 Changed rollout_companies.bdew_company_id → rollout_companies.bdew_code"
            )
            print("🔧 Changed reference from companies.id → companies.bdew_code")
            print("🔧 Updated foreign key constraint and indexes")
            if counts and hasattr(counts, "with_references"):
                with_refs = getattr(counts, "with_references", 0)
                if with_refs > 0:
                    print(f"🔧 Converted references from existing data")
            print("✅ Migration completed successfully!")

        except Exception as e:
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    fix_rollout_companies_bdew_reference()
