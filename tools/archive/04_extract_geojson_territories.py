#!/usr/bin/env python3
"""
VNBdigitaler - Script 04: GeoJSON Territory Extraction

This script extracts network territory boundary data from vnbdigital.de
and exports it as GeoJSON files for database integration.

Author: VNBdigitaler Project
Date: 2025-08-21
"""

import argparse
import asyncio
import json
import logging
import sys
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database_config import get_database_url
from src.models import Company
from src.vnbclient import VNBClient

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
MAX_NAME_DISPLAY_LENGTH = 50


class GeoJSONExtractor:
    """Extracts GeoJSON territory data from vnbdigital.de using MVT approach."""

    def __init__(self, database_url: str, update_existing: bool = False):
        """Initialize GeoJSON extractor."""
        self.database_url = database_url
        self.update_existing = update_existing
        self.vnb_client = VNBClient("https://www.vnbdigital.de/gateway/graphql")

    async def extract_geojson_for_vnbdigital_id(
        self, vnbdigital_id: str
    ) -> dict[str, Any] | None:
        """Extract GeoJSON data for a specific vnbdigital.de ID using VNBClient."""
        try:
            vnb_info = self.vnb_client.fetch_vnb_info(vnbdigital_id)
            if vnb_info and vnb_info.geojson:
                return vnb_info.geojson
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to extract GeoJSON for VNB ID {vnbdigital_id}: {e}")
            return None

    def extract_vnbdigital_id_from_layer_url(self, _layer_url: str) -> str | None:
        """Extract vnbdigital.de ID from GraphQL data."""
        # The vnbdigital ID is typically stored in the database from previous enrichment
        # We'll need to look it up in the database query
        return None

    async def update_company_geojson(
        self, session: AsyncSession, company, geojson_data: dict[str, Any]
    ) -> bool:
        """Update company record with GeoJSON territory data."""
        try:
            await session.execute(
                text(
                    "UPDATE companies SET network_territory_geojson = :geojson WHERE id = :company_id"
                ),
                {"geojson": json.dumps(geojson_data), "company_id": company.id},
            )
            await session.commit()
            return True

        except Exception as e:
            logger.error(
                f"Failed to update GeoJSON for company {company.bdew_name}: {e}"
            )
            await session.rollback()
            return False

    async def process_companies_with_vnbdigital_data(self) -> dict[str, int]:
        """Process territory extraction for companies with vnbdigital.de data."""
        engine = create_async_engine(self.database_url, echo=False)
        session_factory = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )

        stats = {
            "total_companies": 0,
            "companies_with_vnbdigital": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
        }

        async with session_factory() as session:
            # Build SQL query based on update mode
            if self.update_existing:
                # Update mode: Process all companies with vnbdigital.de data
                sql_query = """
                    SELECT id, bdew_code, bdew_name, vnbdigital_extended_data
                    FROM companies
                    WHERE vnbdigital_enrichment_status = 'found'
                """
                mode_description = "updating all existing"
            else:
                # Default mode: Only process companies without GeoJSON data
                sql_query = """
                    SELECT id, bdew_code, bdew_name, vnbdigital_extended_data
                    FROM companies
                    WHERE vnbdigital_enrichment_status = 'found'
                    AND network_territory_geojson IS NULL
                """
                mode_description = "extracting missing"

            result = await session.execute(text(sql_query))

            companies_data = result.fetchall()
            stats["companies_with_vnbdigital"] = len(companies_data)

            logger.info(
                f"Found {len(companies_data)} companies for GeoJSON extraction ({mode_description})"
            )

            if not companies_data:
                if self.update_existing:
                    logger.warning(
                        "No companies with vnbdigital.de data found for update"
                    )
                else:
                    logger.warning("No companies need GeoJSON extraction")
                return stats

            logger.info(f"Processing {len(companies_data)} companies...")

            # Process each company
            for i, company_data in enumerate(companies_data, 1):
                stats["total_companies"] += 1
                company_id, bdew_code, bdew_name, extended_data = company_data

                # Use BDEW code as vnbdigital ID (they are identical)
                vnbdigital_id = bdew_code

                # Truncate name for display
                display_name = (
                    bdew_name[:MAX_NAME_DISPLAY_LENGTH] + "..."
                    if len(bdew_name) > MAX_NAME_DISPLAY_LENGTH
                    else bdew_name
                )

                try:
                    # Extract GeoJSON data using vnbdigital ID (= BDEW code)
                    geojson_data = await self.extract_geojson_for_vnbdigital_id(
                        vnbdigital_id
                    )

                    if geojson_data:
                        # Get company object for update
                        company_result = await session.execute(
                            select(Company).where(Company.id == company_id)
                        )
                        company = company_result.scalar_one_or_none()

                        if company:
                            success = await self.update_company_geojson(
                                session, company, geojson_data
                            )
                            if success:
                                stats["successful_extractions"] += 1
                                feature_count = len(geojson_data.get("features", []))
                                logger.info(
                                    f"✅ GeoJSON extracted [{i}/{len(companies_data)}] {display_name} ({feature_count} features)"
                                )
                            else:
                                stats["failed_extractions"] += 1
                                logger.info(
                                    f"❌ Database update failed [{i}/{len(companies_data)}] {display_name}"
                                )
                        else:
                            logger.error(f"Company not found: {company_id}")
                            stats["failed_extractions"] += 1
                    else:
                        stats["failed_extractions"] += 1
                        logger.info(
                            f"❌ No GeoJSON data [{i}/{len(companies_data)}] {display_name} (BDEW: {bdew_code})"
                        )

                except Exception as e:
                    logger.error(f"Error processing company {display_name}: {e}")
                    stats["failed_extractions"] += 1

                # Rate limiting - be respectful to the API
                await asyncio.sleep(0.1)

        await engine.dispose()

        # Log completion summary like script 02
        logger.info(
            f"GeoJSON extraction complete: {stats['successful_extractions']}/{stats['companies_with_vnbdigital']} territories extracted"
        )

        return stats


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract GeoJSON territory data from vnbdigital.de"
    )
    parser.add_argument(
        "-u",
        "--update",
        action="store_true",
        help="Update existing GeoJSON data (default: only extract missing data)",
    )
    return parser.parse_args()


async def main():
    """Main execution function."""
    # Parse command line arguments
    args = parse_arguments()

    logger.info("🗺️  VNBdigitaler - GeoJSON Territory Data Extraction")
    logger.info("=" * 60)

    if args.update:
        logger.info("Update mode: Will update ALL existing GeoJSON data")
    else:
        logger.info("Default mode: Will only extract missing GeoJSON data")

    logger.info("=" * 60)

    try:
        # Get database configuration
        database_url = get_database_url()
        logger.info("Database connection configured")

        # Initialize extractor with update mode
        extractor = GeoJSONExtractor(database_url, update_existing=args.update)

        # Process territory extraction
        logger.info("Starting territory data extraction...")
        stats = await extractor.process_companies_with_vnbdigital_data()

        # Report results
        logger.info("\n" + "=" * 50)
        logger.info("GEOJSON TERRITORY EXTRACTION COMPLETED")
        logger.info("=" * 50)
        logger.info(
            f"Companies with vnbdigital.de data: {stats['companies_with_vnbdigital']}"
        )
        logger.info(f"Successful extractions: {stats['successful_extractions']}")
        logger.info(f"Failed extractions: {stats['failed_extractions']}")

        if stats["companies_with_vnbdigital"] > 0:
            success_rate = (
                stats["successful_extractions"] / stats["companies_with_vnbdigital"]
            ) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")

        logger.info("=" * 50)

        if stats["successful_extractions"] > 0:
            logger.info("✅ Territory extraction completed successfully!")
        elif stats["failed_extractions"] > 0:
            logger.warning(
                "⚠️  Some territory extractions failed - check logs for details"
            )

    except Exception as e:
        logger.error(f"❌ Territory extraction failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
