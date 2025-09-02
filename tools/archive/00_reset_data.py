#!/usr/bin/env python3
"""
Reset Data Script for VNBdigitaler Project

This script completely resets the project data by:
1. Dropping all database tables
2. Removing ALL generated data files (except placeholder.md)
3. Cleaning up ALL temporary files and cache directories

This gives us a clean slate for running the complete pipeline from scratch.

Usage:
    python tools/00_reset_data.py [--confirm]

Author: VNBdigitaler Development Team
"""

import asyncio
import logging
import os
import shutil
import sys
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
# Use relative path from script location to project directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
TMP_DIR = PROJECT_ROOT / "tmp"


class DataReset:
    """Handles complete data reset for VNBdigitaler project."""

    def __init__(self) -> None:
        """Initialize the data reset handler."""
        self.db_url = os.getenv("NEON_DATABASE_URL")
        if not self.db_url:
            raise ValueError("NEON_DATABASE_URL environment variable not set")

        # Convert SSL parameter format for asyncpg
        self.db_url = self.convert_ssl_params(self.db_url)

    def convert_ssl_params(self, url: str) -> str:
        """Convert SSL parameters from PostgreSQL to psycopg format."""
        return url.replace("sslmode=require", "ssl=require")

    async def drop_all_tables(self) -> None:
        """Drop all tables in the database."""
        try:
            logger.info("🗑️  Connecting to database to drop all tables...")

            conn = await asyncpg.connect(self.db_url)

            # Get all table names in the public schema
            tables_query = """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            """

            tables = await conn.fetch(tables_query)
            table_names = [row["tablename"] for row in tables]

            if not table_names:
                logger.info("📭 No tables found in database")
                await conn.close()
                return

            logger.info(
                f"📋 Found {len(table_names)} tables to drop: {', '.join(table_names)}"
            )

            # Drop all tables with CASCADE to handle dependencies
            for table_name in table_names:
                drop_query = f"DROP TABLE IF EXISTS {table_name} CASCADE"
                await conn.execute(drop_query)
                logger.info(f"🗑️  Dropped table: {table_name}")

            await conn.close()
            logger.info("✅ All database tables dropped successfully")

        except Exception as e:
            logger.error(f"❌ Failed to drop database tables: {e}")
            raise

    def remove_data_files(self) -> None:
        """Remove ALL files in data directory (except placeholder.md)."""
        logger.info("🧹 Cleaning up ALL data files...")

        removed_count = 0
        if DATA_DIR.exists():
            for file_path in DATA_DIR.iterdir():
                # Keep placeholder.md and skip directories
                if file_path.is_file() and file_path.name != "placeholder.md":
                    file_path.unlink()
                    logger.info(f"🗑️  Removed: {file_path}")
                    removed_count += 1
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
                    logger.info(f"🗑️  Removed directory: {file_path}")
                    removed_count += 1

        if removed_count == 0:
            logger.info("📭 No data files to remove")
        else:
            logger.info(f"✅ Removed {removed_count} data files/directories")

    def remove_temp_files(self) -> None:
        """Remove ALL temporary files and __pycache__ directories."""
        logger.info("🧹 Cleaning up temporary files...")

        removed_count = 0

        # Remove ALL files in tmp directory
        if TMP_DIR.exists():
            for file_path in TMP_DIR.iterdir():
                if file_path.is_file():
                    file_path.unlink()
                    logger.info(f"🗑️  Removed: {file_path}")
                    removed_count += 1
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
                    logger.info(f"🗑️  Removed directory: {file_path}")
                    removed_count += 1

        # Remove any __pycache__ directories
        for pycache_dir in Path().rglob("__pycache__"):
            shutil.rmtree(pycache_dir)
            logger.info(f"🗑️  Removed: {pycache_dir}")
            removed_count += 1

        if removed_count == 0:
            logger.info("📭 No temporary files to remove")
        else:
            logger.info(f"✅ Removed {removed_count} temporary files/directories")

    def create_directories(self) -> None:
        """Ensure required directories exist."""
        logger.info("📁 Ensuring required directories exist...")

        directories = [DATA_DIR, TMP_DIR]
        for directory in directories:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"📁 Created directory: {directory}")
            else:
                logger.info(f"✅ Directory exists: {directory}")

    async def reset_all(self, confirm: bool = False) -> None:
        """Perform complete data reset."""
        if not confirm:
            logger.warning("⚠️  This will completely reset all project data!")
            logger.warning("   - All database tables will be dropped")
            logger.warning("   - All generated data files will be removed")
            logger.warning("   - All temporary files will be cleaned up")

            response = (
                input("\n🤔 Are you sure you want to continue? (yes/no): ")
                .strip()
                .lower()
            )
            if response not in ["yes", "y"]:
                logger.info("❌ Reset cancelled by user")
                return

        logger.info("🚀 Starting complete data reset...")

        try:
            # Step 1: Drop database tables
            await self.drop_all_tables()

            # Step 2: Remove data files
            self.remove_data_files()

            # Step 3: Remove temporary files
            self.remove_temp_files()

            # Step 4: Ensure directories exist
            self.create_directories()

            logger.info("🎉 Complete data reset finished successfully!")
            logger.info(
                "🌱 You now have a clean slate to run the pipeline from scratch"
            )

        except Exception as e:
            logger.error(f"❌ Reset failed: {e}")
            raise


async def main() -> None:
    """Main function."""
    # Check for confirmation flag
    confirm = "--confirm" in sys.argv

    logger.info("🔄 VNBdigitaler Data Reset Script")
    logger.info("=" * 50)

    try:
        reset_handler = DataReset()
        await reset_handler.reset_all(confirm=confirm)

    except Exception as e:
        logger.error(f"❌ Reset script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
