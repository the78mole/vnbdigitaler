#!/usr/bin/env python3
"""
Migration: Convert bdew_code to INTEGER and update rollout_companies table

This migration performs the following steps:
1. Convert companies.bdew_code from VARCHAR to INTEGER
2. Add bdew_code INTEGER column to rollout_companies table
3. Populate bdew_code by looking up via bdew_company_id → companies.id → companies.bdew_code
4. Drop the old bdew_company_id column
5. Add foreign key constraint from rollout_companies.bdew_code to companies.bdew_code

Author: VNBdigitaler Project
Date: 2025-08-25
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

# ruff: noqa: E402
from sqlalchemy import create_engine, text

from src.database_config import get_database_url


def convert_bdew_code_to_integer():
    """Convert bdew_code columns to INTEGER and update references"""

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
            print("🔧 Converting bdew_code to INTEGER and updating rollout_companies...")

            # Step 1: Check current state of companies.bdew_code
            print("📊 Step 1: Checking companies.bdew_code column...")

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

            if not companies_bdew_type:
                print("❌ companies.bdew_code column not found!")
                trans.rollback()
                return

            print(f"   Current type: {companies_bdew_type.data_type}")

            # Step 2: Convert companies.bdew_code to INTEGER if needed
            if companies_bdew_type.data_type != "integer":
                print("🔄 Step 2: Converting companies.bdew_code to INTEGER...")

                # Check for non-numeric values first
                result = conn.execute(
                    text(
                        "SELECT COUNT(*) as count FROM companies WHERE bdew_code !~ '^[0-9]+$'"
                    )
                )
                non_numeric_count = result.fetchone().count

                if non_numeric_count > 0:
                    print(
                        f"   ⚠️  Found {non_numeric_count} non-numeric bdew_codes - showing samples:"
                    )
                    result = conn.execute(
                        text(
                            "SELECT bdew_code FROM companies WHERE bdew_code !~ '^[0-9]+$' LIMIT 5"
                        )
                    )
                    for row in result:
                        print(f"      - '{row.bdew_code}'")

                # Create new INTEGER column
                print("   Creating temporary bdew_code_int column...")
                conn.execute(
                    text("ALTER TABLE companies ADD COLUMN bdew_code_int INTEGER;")
                )

                # Copy numeric values
                print("   Copying numeric values...")
                result = conn.execute(
                    text(
                        """
                        UPDATE companies
                        SET bdew_code_int = bdew_code::INTEGER
                        WHERE bdew_code ~ '^[0-9]+$'
                        RETURNING id
                    """
                    )
                )
                converted_count = len(list(result))
                print(f"   ✅ Converted {converted_count} numeric bdew_codes")

                # Drop old column and rename new one
                print("   Replacing old column...")
                conn.execute(
                    text("ALTER TABLE companies DROP COLUMN bdew_code CASCADE;")
                )
                conn.execute(
                    text(
                        "ALTER TABLE companies RENAME COLUMN bdew_code_int TO bdew_code;"
                    )
                )

                # Add constraints back
                conn.execute(
                    text(
                        "ALTER TABLE companies ADD CONSTRAINT companies_bdew_code_key UNIQUE (bdew_code);"
                    )
                )
                conn.execute(
                    text("ALTER TABLE companies ALTER COLUMN bdew_code SET NOT NULL;")
                )

                print("   ✅ companies.bdew_code converted to INTEGER")
            else:
                print("   ✅ companies.bdew_code is already INTEGER")

            # Step 3: Check rollout_companies table state
            print("📊 Step 3: Checking rollout_companies table...")

            result = conn.execute(
                text(
                    """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'rollout_companies'
                AND column_name IN ('bdew_company_id', 'bdew_code')
                ORDER BY column_name;
            """
                )
            )
            rollout_columns = {row.column_name: row.data_type for row in result}
            print(f"   Existing columns: {rollout_columns}")

            # Check existing data
            result = conn.execute(
                text(
                    "SELECT COUNT(*) as total, COUNT(bdew_company_id) as with_refs FROM rollout_companies"
                )
            )
            counts = result.fetchone()
            total_companies = counts.total if counts else 0
            with_references = counts.with_refs if counts else 0

            print(f"   Total rollout companies: {total_companies}")
            print(f"   With BDEW references: {with_references}")

            # Step 4: Add bdew_code column if it doesn't exist
            if "bdew_code" not in rollout_columns:
                print("🔧 Step 4: Adding bdew_code column to rollout_companies...")
                conn.execute(
                    text("ALTER TABLE rollout_companies ADD COLUMN bdew_code INTEGER;")
                )
                print("   ✅ bdew_code column added")
            else:
                print("   ✅ bdew_code column already exists")

            # Step 5: Populate bdew_code from bdew_company_id lookups
            if "bdew_company_id" in rollout_columns and with_references > 0:
                print("🔄 Step 5: Populating bdew_code via ID lookups...")

                # Use Python to do the lookup (safer than complex SQL)
                result = conn.execute(
                    text(
                        """
                        SELECT rc.id, rc.bdew_company_id, c.bdew_code
                        FROM rollout_companies rc
                        JOIN companies c ON c.id = rc.bdew_company_id
                        WHERE rc.bdew_company_id IS NOT NULL
                    """
                    )
                )

                lookup_data = list(result)
                print(f"   Found {len(lookup_data)} companies to update")

                # Update in batches
                for i, row in enumerate(lookup_data, 1):
                    conn.execute(
                        text(
                            "UPDATE rollout_companies SET bdew_code = :bdew_code WHERE id = :id"
                        ),
                        {"id": row.id, "bdew_code": row.bdew_code},
                    )

                    if i % 100 == 0 or i == len(lookup_data):
                        print(f"   Progress: {i}/{len(lookup_data)} companies updated")

                print(
                    f"   ✅ Successfully populated {len(lookup_data)} bdew_code values"
                )
            else:
                print("   ℹ️  No bdew_company_id references to convert")

            # Step 6: Drop old bdew_company_id column
            if "bdew_company_id" in rollout_columns:
                print("🗑️  Step 6: Removing old bdew_company_id column...")

                # Drop any foreign key constraints first
                result = conn.execute(
                    text(
                        """
                        SELECT constraint_name
                        FROM information_schema.table_constraints tc
                        WHERE tc.table_name = 'rollout_companies'
                        AND tc.constraint_type = 'FOREIGN KEY'
                    """
                    )
                )
                constraints = [row.constraint_name for row in result]

                for constraint in constraints:
                    try:
                        conn.execute(
                            text(
                                f"ALTER TABLE rollout_companies DROP CONSTRAINT {constraint}"
                            )
                        )
                        print(f"   Dropped constraint: {constraint}")
                    except Exception as e:
                        print(
                            f"   Warning: Could not drop constraint {constraint}: {e}"
                        )

                # Drop the column
                conn.execute(
                    text("ALTER TABLE rollout_companies DROP COLUMN bdew_company_id")
                )
                print("   ✅ bdew_company_id column removed")
            else:
                print("   ℹ️  No bdew_company_id column to remove")

            # Step 7: Add foreign key constraint
            print("🔗 Step 7: Adding foreign key constraint...")
            try:
                conn.execute(
                    text(
                        """
                        ALTER TABLE rollout_companies
                        ADD CONSTRAINT fk_rollout_companies_bdew_code
                        FOREIGN KEY (bdew_code) REFERENCES companies(bdew_code)
                    """
                    )
                )
                print("   ✅ Foreign key constraint added")
            except Exception as e:
                print(f"   ⚠️  Warning: Could not add foreign key constraint: {e}")

            # Step 8: Update indexes
            print("🔍 Step 8: Updating indexes...")

            # Drop old index if it exists
            conn.execute(
                text("DROP INDEX IF EXISTS idx_rollout_companies_bdew_company_id")
            )

            # Create new index
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_rollout_companies_bdew_code ON rollout_companies(bdew_code)"
                )
            )
            print("   ✅ Indexes updated")

            # Commit transaction
            trans.commit()
            print("✅ Migration completed successfully!")

            # Print summary
            print("\n" + "=" * 60)
            print("MIGRATION SUMMARY")
            print("=" * 60)
            print("✅ companies.bdew_code converted to INTEGER")
            print("✅ rollout_companies.bdew_code column added as INTEGER")
            if with_references > 0:
                print(f"✅ Converted {with_references} company references")
            print("✅ rollout_companies.bdew_company_id column removed")
            print("✅ Foreign key constraint established")
            print("✅ Indexes updated")
            print("\n🎉 Schema migration completed successfully!")

        except Exception as e:
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    convert_bdew_code_to_integer()
