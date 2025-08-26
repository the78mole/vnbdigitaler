#!/usr/bin/env python3
"""
Migration: Add UNIQUE constraint to rollout_companies.bdew_code

This migration adds a unique constraint to the bdew_code column in rollout_companies table.
The constraint allows NULL values but ensures that non-NULL bdew_codes are unique.

Author: VNBdigitaler Project
Date: 2025-08-25
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

# ruff: noqa: E402
from sqlalchemy import create_engine, text

from src.database_config import get_database_url


def add_unique_constraint_rollout_bdew_code():
    """Add UNIQUE constraint to rollout_companies.bdew_code column"""

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
            print("🔧 Adding UNIQUE constraint to rollout_companies.bdew_code...")

            # Step 1: Check for duplicate bdew_codes first
            print("📊 Step 1: Checking for duplicate bdew_codes...")

            result = conn.execute(
                text(
                    """
                    SELECT bdew_code, COUNT(*) as count
                    FROM rollout_companies
                    WHERE bdew_code IS NOT NULL
                    GROUP BY bdew_code
                    HAVING COUNT(*) > 1
                    ORDER BY count DESC, bdew_code
                """
                )
            )
            duplicates = list(result)

            if duplicates:
                print(f"   ⚠️  Found {len(duplicates)} duplicate bdew_codes:")
                for dup in duplicates[:10]:  # Show first 10
                    print(f"      - BDEW-Code {dup.bdew_code}: {dup.count} companies")

                if len(duplicates) > 10:
                    print(f"      ... und {len(duplicates) - 10} weitere")

                print("\n   🔍 Details der Duplikate:")
                for dup in duplicates[:5]:  # Show details for first 5
                    detail_result = conn.execute(
                        text(
                            """
                            SELECT id, bnetza_name
                            FROM rollout_companies
                            WHERE bdew_code = :bdew_code
                            ORDER BY id
                        """
                        ),
                        {"bdew_code": dup.bdew_code},
                    )
                    companies = list(detail_result)
                    print(f"      BDEW-Code {dup.bdew_code}:")
                    for company in companies:
                        print(f"        - ID {company.id}: {company.bnetza_name}")

                print(
                    "\n❌ Kann UNIQUE Constraint nicht hinzufügen - Duplikate müssen erst bereinigt werden!"
                )
                trans.rollback()
                return False
            else:
                print("   ✅ Keine Duplikate gefunden")

            # Step 2: Check if constraint already exists
            print("📊 Step 2: Checking existing constraints...")

            result = conn.execute(
                text(
                    """
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE table_name = 'rollout_companies'
                    AND constraint_type = 'UNIQUE'
                    AND constraint_name LIKE '%bdew_code%'
                """
                )
            )
            existing_constraints = [row.constraint_name for row in result]

            if existing_constraints:
                print(
                    f"   ℹ️  UNIQUE constraint bereits vorhanden: {existing_constraints}"
                )
                trans.rollback()
                return True
            else:
                print("   ✅ Kein UNIQUE constraint vorhanden")

            # Step 3: Add UNIQUE constraint
            print("🔗 Step 3: Adding UNIQUE constraint...")

            try:
                conn.execute(
                    text(
                        """
                        ALTER TABLE rollout_companies
                        ADD CONSTRAINT rollout_companies_bdew_code_key
                        UNIQUE (bdew_code)
                    """
                    )
                )
                print("   ✅ UNIQUE constraint erfolgreich hinzugefügt")
            except Exception as e:
                print(f"   ❌ Fehler beim Hinzufügen der UNIQUE constraint: {e}")
                trans.rollback()
                return False

            # Step 4: Verify constraint
            print("🔍 Step 4: Verifying constraint...")

            result = conn.execute(
                text(
                    """
                    SELECT constraint_name, constraint_type
                    FROM information_schema.table_constraints
                    WHERE table_name = 'rollout_companies'
                    AND constraint_name = 'rollout_companies_bdew_code_key'
                """
                )
            )
            constraint_info = result.fetchone()

            if constraint_info:
                print(
                    f"   ✅ Constraint erfolgreich erstellt: {constraint_info.constraint_name} ({constraint_info.constraint_type})"
                )
            else:
                print("   ❌ Constraint konnte nicht verifiziert werden")
                trans.rollback()
                return False

            # Commit transaction
            trans.commit()
            print("✅ Migration completed successfully!")

            # Print summary
            print("\n" + "=" * 60)
            print("MIGRATION SUMMARY")
            print("=" * 60)
            print("✅ UNIQUE constraint für rollout_companies.bdew_code hinzugefügt")
            print("✅ NULL-Werte sind weiterhin erlaubt")
            print("✅ Duplikate von bdew_codes sind nun verhindert")
            print("\n🎉 Schema constraint migration completed successfully!")

            return True

        except Exception as e:
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    success = add_unique_constraint_rollout_bdew_code()
    if success:
        print("\n🎯 UNIQUE constraint erfolgreich hinzugefügt!")
    else:
        print(
            "\n⚠️  Migration nicht abgeschlossen - manuelle Bereinigung erforderlich!"
        )
