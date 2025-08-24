#!/usr/bin/env python3
"""Migration: Make excel_file_hash nullable in rollout_update_logs table.

This migration modifies the rollout_update_logs table to allow NULL values
for excel_file_hash, enabling a proper workflow where the hash is set only
after successful file processing.

Workflow:
1. Report discovered -> status: 'discovered', excel_file_hash: NULL
2. File downloaded -> status: 'downloaded', excel_file_hash: NULL
3. File processed -> status: 'completed', excel_file_hash: <actual_hash>

This ensures the hash is only computed and stored after successful processing,
preventing inconsistencies and allowing for better error handling.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import text

from src.database import get_db_manager


async def main():
    """Execute the migration to make excel_file_hash nullable."""
    print("🔄 Starting migration: Make excel_file_hash nullable")
    print("=" * 60)

    try:
        # Get database connection using async session
        db_manager = get_db_manager()

        async for session in db_manager.get_async_session():
            try:
                print("📊 Checking current table structure...")

                # Check current constraint
                result = await session.execute(
                    text(
                        """
                    SELECT column_name, is_nullable, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'rollout_update_logs'
                    AND column_name = 'excel_file_hash'
                """
                    )
                )

                current_info = result.fetchone()
                if current_info:
                    print(
                        f"   📋 Current status: {current_info.column_name} - nullable: {current_info.is_nullable}"
                    )
                else:
                    print("   ❌ Column not found!")
                    return False

                if current_info.is_nullable == "YES":
                    print("   ✅ Column is already nullable - no migration needed")
                    return True

                print("\n🔧 Modifying table structure...")

                # Step 1: Drop unique constraint temporarily (it will be recreated as partial index)
                print("   1️⃣ Dropping unique constraint on excel_file_hash...")
                await session.execute(
                    text(
                        """
                    ALTER TABLE rollout_update_logs
                    DROP CONSTRAINT IF EXISTS rollout_update_logs_excel_file_hash_key
                """
                    )
                )

                # Step 2: Make column nullable
                print("   2️⃣ Making excel_file_hash column nullable...")
                await session.execute(
                    text(
                        """
                    ALTER TABLE rollout_update_logs
                    ALTER COLUMN excel_file_hash DROP NOT NULL
                """
                    )
                )

                # Step 3: Create partial unique index (only for non-NULL values)
                print("   3️⃣ Creating partial unique index for non-NULL values...")
                await session.execute(
                    text(
                        """
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_rollout_update_logs_excel_file_hash_unique
                    ON rollout_update_logs (excel_file_hash)
                    WHERE excel_file_hash IS NOT NULL
                """
                    )
                )

                # Commit the transaction
                await session.commit()

                print("\n📊 Verifying changes...")

                # Verify the change
                result = await session.execute(
                    text(
                        """
                    SELECT column_name, is_nullable, data_type
                    FROM information_schema.columns
                    WHERE table_name = 'rollout_update_logs'
                    AND column_name = 'excel_file_hash'
                """
                    )
                )

                updated_info = result.fetchone()
                if updated_info and updated_info.is_nullable == "YES":
                    print(f"   ✅ Success: {updated_info.column_name} is now nullable")
                else:
                    print("   ❌ Migration failed - column is still not nullable")
                    return False

                # Check if partial unique index exists
                result = await session.execute(
                    text(
                        """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'rollout_update_logs'
                    AND indexname = 'idx_rollout_update_logs_excel_file_hash_unique'
                """
                    )
                )

                if result.fetchone():
                    print("   ✅ Partial unique index created successfully")
                else:
                    print("   ❌ Failed to create partial unique index")
                    return False

                print("\n🎉 Migration completed successfully!")
                print(
                    f"   ⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )

                return True

            except Exception as e:
                await session.rollback()
                raise e

    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        print(f"   💡 Error type: {type(e).__name__}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
