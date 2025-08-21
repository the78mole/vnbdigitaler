#!/usr/bin/env python3
"""
VNBdigitaler - Script 03: Database Integration for BDEW and vnbdigital.de data

This script integrates BDEW grid operator data and vnbdigital.de enrichment data
into the PostgreSQL database, providing a comprehensive operator database.

Author: VNBdigitaler Project
Date: 2025-08-21
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database_config import get_database_url, validate_database_connection
from src.models import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
# Use relative path from script location to project data directory
SCRIPT_DIR = Path(__file__).parent
PROJECT_DATA_DIR = SCRIPT_DIR.parent / "data"
ENRICHED_DATA_FILE = PROJECT_DATA_DIR / "bdew_enriched_with_vnbdigital.json"
OUTPUT_STATS_FILE = PROJECT_DATA_DIR / "integration_stats.json"


class DatabaseIntegrator:
    """Handles database integration of BDEW operator data."""

    def __init__(self, db_url: str) -> None:
        """Initialize the database integrator."""
        self.db_url = db_url
        self.engine = create_async_engine(db_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.stats = {
            "companies_processed": 0,
            "companies_created": 0,
            "companies_updated": 0,
            "companies_skipped": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
        }

    async def create_tables(self) -> None:
        """Create database tables if they don't exist."""
        try:
            logger.info("Creating database tables...")
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            raise

    def load_enriched_data(self) -> dict[str, Any]:
        """Load the enriched operators data."""
        if not ENRICHED_DATA_FILE.exists():
            raise FileNotFoundError(
                f"Enriched data file not found: {ENRICHED_DATA_FILE}"
            )

        with ENRICHED_DATA_FILE.open(encoding="utf-8") as f:
            data = json.load(f)

        logger.info(
            f"Loaded {len(data.get('operators', []))} operators from enriched data"
        )
        return data

    def serialize_json_field(self, value: Any) -> str | None:
        """
        Serialize complex values to JSON string for database storage.

        Args:
            value: The value to serialize

        Returns:
            JSON string or None for null values
        """
        if value is None:
            return None
        if isinstance(value, dict | list):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def convert_ssl_params(self, url: str) -> str:
        """Convert SSL parameters from PostgreSQL to psycopg format."""
        return url.replace("sslmode=require", "ssl=require")

    def _clean_text_data(self, text: str) -> str:
        """
        Clean text data by removing unwanted characters and normalizing.

        Args:
            text: Raw text string

        Returns:
            Cleaned text string
        """
        if not text:
            return ""

        # Remove surrounding quotes
        cleaned = text.strip().strip('"').strip("'")

        # Normalize multiple spaces to single spaces
        cleaned = " ".join(cleaned.split())

        # Remove other problematic characters but keep essential ones
        # Keep: letters, numbers, spaces, hyphens, dots, slashes, parentheses, ampersands
        cleaned = re.sub(r"[^\w\s\-\.\/\(\)&]", "", cleaned)

        return cleaned.strip()

    def prepare_company_data(self, operator: dict[str, Any]) -> dict[str, Any]:
        """
        Prepare operator data for database insertion/update.

        Args:
            operator: Raw operator data dict

        Returns:
            Dict with prepared data for Company model
        """
        # Get vnbdigital data if available
        vnb_data = operator.get("vnbdigital_data")

        # Extract and clean the BDEW data
        company_name = (
            operator.get("company_name", "").strip()
            if operator.get("company_name")
            else ""
        )
        city_name = operator.get("city", "").strip() if operator.get("city") else ""

        # Clean company name: remove quotes, normalize spaces
        clean_company_name = self._clean_text_data(company_name)
        clean_city_name = self._clean_text_data(city_name)

        # Create normalized name with city for uniqueness: "company_name_city"
        normalized_name = ""
        if clean_company_name and clean_city_name:
            normalized_name = (
                f"{clean_company_name}_{clean_city_name}".lower()
                .replace(" ", "_")
                .replace("-", "_")
            )
        elif clean_company_name:
            normalized_name = (
                clean_company_name.lower().replace(" ", "_").replace("-", "_")
            )

        company_data: dict[str, Any] = {
            "bdew_code": str(operator.get("bdew_code", "")).strip()
            if operator.get("bdew_code")
            else "",
            "bdew_name": clean_company_name,
            "bdew_name_normalized": normalized_name,
            "bdew_city": clean_city_name,
        }

        # Add vnbdigital data if available
        if vnb_data:
            company_data.update(
                {
                    "vnbdigital_name": vnb_data.get("name", "").strip()
                    if vnb_data.get("name")
                    else "",
                    "vnbdigital_address": vnb_data.get("address", "").strip()
                    if vnb_data.get("address")
                    else "",
                    "vnbdigital_postcode": vnb_data.get("postcode", "").strip()
                    if vnb_data.get("postcode")
                    else "",
                    "vnbdigital_city": vnb_data.get("city", "").strip()
                    if vnb_data.get("city")
                    else "",
                    "vnbdigital_phone": vnb_data.get("phone", "").strip()
                    if vnb_data.get("phone")
                    else "",
                    "vnbdigital_email": vnb_data.get("email", "").strip()
                    if vnb_data.get("email")
                    else "",
                    "vnbdigital_website": vnb_data.get("website", "").strip()
                    if vnb_data.get("website")
                    else "",
                    "vnbdigital_grid_types": vnb_data.get("types")
                    if isinstance(vnb_data.get("types"), list)
                    else None,
                    "network_territory_layer_url": vnb_data.get("layer_url", "").strip()
                    if vnb_data.get("layer_url")
                    else "",
                    "vnbdigital_extended_data": json.dumps(
                        {
                            "id": vnb_data.get("id"),
                            "bbox": vnb_data.get("bbox"),
                            "description": vnb_data.get("description"),
                            "contact": vnb_data.get("contact"),
                            "public_required": vnb_data.get("public_required"),
                            "clicks": vnb_data.get("clicks"),
                            "regions": vnb_data.get("regions"),
                            "services": vnb_data.get("services"),
                            "documents": vnb_data.get("documents"),
                            "image_url": vnb_data.get("image_url"),
                            "logo_url": vnb_data.get("logo_url"),
                        }
                    )
                    if vnb_data
                    else None,
                    "vnbdigital_enrichment_status": operator.get("enrichment_status"),
                    "vnbdigital_last_enriched": datetime.fromisoformat(
                        operator["enrichment_timestamp"]
                    )
                    if operator.get("enrichment_timestamp")
                    and isinstance(operator["enrichment_timestamp"], str)
                    else None,
                }
            )

        # Clean empty string values and add manual_verification default
        for key, value in company_data.items():
            if value == "":
                company_data[key] = None

        # Add required manual_verification field with default value
        company_data["manual_verification"] = False

        return company_data

    async def process_operators(self, operators: list[dict[str, Any]]) -> None:
        """Process all operators and integrate them into the database."""
        self.stats["start_time"] = datetime.now()

        logger.info(f"Processing {len(operators)} operators...")

        for i, operator in enumerate(operators, 1):
            try:
                self.stats["companies_processed"] += 1

                # Log progress every 10 operators
                if i % 10 == 0:
                    logger.info(f"Processed {i}/{len(operators)} operators...")

                # Prepare company data
                company_data = self.prepare_company_data(operator)
                bdew_code = company_data.get("bdew_code")

                if not bdew_code:
                    logger.warning(f"Skipping operator {i}: Missing BDEW code")
                    self.stats["companies_skipped"] += 1
                    continue

                # Check if company exists
                async with self.session_factory() as session:
                    # Use raw SQL for better control and security
                    result = await session.execute(
                        text(
                            "SELECT id, bdew_name FROM companies WHERE bdew_code = :bdew_code"
                        ),
                        {"bdew_code": bdew_code},
                    )
                    existing_company = result.fetchone()

                    if existing_company:
                        # Update existing company
                        await self.update_company(
                            session, existing_company[0], company_data
                        )
                        self.stats["companies_updated"] += 1
                    else:
                        # Create new company
                        await self.create_company(session, company_data)
                        self.stats["companies_created"] += 1

                    await session.commit()

            except Exception as e:
                logger.error(
                    f"Error processing operator {i} (BDEW: {operator.get('bdew_data', {}).get('Code', 'N/A')}): {e}"
                )
                self.stats["errors"] += 1
                continue

        self.stats["end_time"] = datetime.now()
        await self.log_final_stats()

    async def update_company(
        self, session: AsyncSession, company_id: int, company_data: dict[str, Any]
    ) -> None:
        """Update an existing company record."""
        # Build dynamic update query
        update_fields = []
        update_values = {"company_id": company_id}

        for field, value in company_data.items():
            if field != "bdew_code":  # Don't update the primary identifier
                update_fields.append(f"{field} = :{field}")
                update_values[field] = value

        if update_fields:
            update_query = f"""
                UPDATE companies
                SET {', '.join(update_fields)}
                WHERE id = :company_id
            """  # nosec B608  # This is safe - fields are controlled by our data structure

            await session.execute(text(update_query), update_values)
            logger.debug(f"Updated company {company_id}")

    async def create_company(
        self, session: AsyncSession, company_data: dict[str, Any]
    ) -> None:
        """Create a new company record."""
        # Build dynamic insert query
        fields = list(company_data.keys())
        placeholders = [f":{field}" for field in fields]

        insert_query = f"""
            INSERT INTO companies ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            RETURNING id
        """  # nosec B608  # This is safe - fields are controlled by our data structure

        result = await session.execute(text(insert_query), company_data)
        row = result.fetchone()
        if row:
            new_id = row[0]
            logger.debug(f"Created company {new_id}")

    async def log_final_stats(self) -> None:
        """Log final integration statistics."""
        duration = self.stats["end_time"] - self.stats["start_time"]

        logger.info("\n" + "=" * 50)
        logger.info("DATABASE INTEGRATION COMPLETED")
        logger.info("=" * 50)
        logger.info(f"Total operators processed: {self.stats['companies_processed']}")
        logger.info(f"Companies created: {self.stats['companies_created']}")
        logger.info(f"Companies updated: {self.stats['companies_updated']}")
        logger.info(f"Companies skipped: {self.stats['companies_skipped']}")
        logger.info(f"Errors encountered: {self.stats['errors']}")
        logger.info(f"Duration: {duration}")
        logger.info("=" * 50)

        # Save stats to file
        stats_data = {
            "integration_stats": {
                **self.stats,
                "start_time": self.stats["start_time"].isoformat(),
                "end_time": self.stats["end_time"].isoformat(),
                "duration_seconds": duration.total_seconds(),
            },
            "generated_at": datetime.now().isoformat(),
        }

        with OUTPUT_STATS_FILE.open("w", encoding="utf-8") as f:
            json.dump(stats_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Integration statistics saved to {OUTPUT_STATS_FILE}")

    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()


async def main() -> None:
    """Main integration function."""
    try:
        # Get database URL and validate connection
        db_url = get_database_url()

        logger.info("Validating database connection...")
        validate_database_connection(db_url)
        logger.info("✅ Database connection validated")

        # Initialize integrator
        integrator = DatabaseIntegrator(db_url)

        try:
            # Create tables
            await integrator.create_tables()

            # Load data
            logger.info("Loading enriched operator data...")
            data = integrator.load_enriched_data()
            operators = data.get("operators", [])

            if not operators:
                logger.warning("No operators found in enriched data file")
                return

            # Process operators
            await integrator.process_operators(operators)

        finally:
            await integrator.close()

    except Exception as e:
        logger.error(f"❌ Integration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
