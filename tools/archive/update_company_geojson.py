#!/usr/bin/env python3
"""
Update Company GeoJSON Script

This script updates all companies in the database with correct transformed
GeoJSON data from vnbdigital.de. It fetches the MVT data, transforms the
coordinates from the proprietary grid system to WGS84, and saves the
corrected GeoJSON back to the database.

Usage:
    python tools/update_company_geojson.py [--dry-run] [--limit N] [--bdew-code CODE]

Examples:
    python tools/update_company_geojson.py --dry-run  # Test without changes
    python tools/update_company_geojson.py --limit 5  # Update only first 5 companies
    python tools/update_company_geojson.py --bdew-code 179  # Update specific company
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import DatabaseManager
from src.models import Company
from src.vnbclient import VNBClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("company_geojson_update.log"),
    ],
)
logger = logging.getLogger(__name__)

# Disable HTTP request logging (too verbose)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

# Constants
VNBDIGITAL_GRAPHQL_URL = "https://www.vnbdigital.de/gateway/graphql"


class CompanyGeoJSONUpdater:
    """Updates company GeoJSON data with transformed coordinates."""

    def __init__(self, dry_run: bool = False):
        """Initialize the updater.

        Args:
            dry_run: If True, will not save changes to database.
        """
        self.dry_run = dry_run
        self.vnb_client = VNBClient(VNBDIGITAL_GRAPHQL_URL)
        self.stats = {
            "total_companies": 0,
            "updated_companies": 0,
            "failed_companies": 0,
            "skipped_companies": 0,
            "errors": [],
        }

    async def update_all_companies(
        self,
        session: AsyncSession,
        limit: int | None = None,
        bdew_code: str | None = None,
    ) -> None:
        """Update GeoJSON data for all companies (or a subset).

        Args:
            session: Database session
            limit: Maximum number of companies to process
            bdew_code: If provided, only update this specific company
        """
        logger.info("Starting company GeoJSON update process")
        if self.dry_run:
            logger.info("DRY RUN MODE - No changes will be saved")

        # Build query
        query = select(Company).order_by(Company.bdew_code)

        if bdew_code:
            query = query.where(Company.bdew_code == bdew_code)
            logger.info(f"Updating specific company with BDEW code: {bdew_code}")
        elif limit:
            query = query.limit(limit)
            logger.info(f"Updating first {limit} companies")
        else:
            logger.info("Updating all companies")

        # Execute query
        result = await session.execute(query)
        companies = result.scalars().all()

        self.stats["total_companies"] = len(companies)
        logger.info(f"Found {len(companies)} companies to process")

        # Process each company
        for i, company in enumerate(companies, 1):
            logger.info(
                f"Processing {i}/{len(companies)}: {company.bdew_name} (BDEW: {company.bdew_code})"
            )

            try:
                await self._update_company_geojson(session, company)
            except Exception as e:
                error_msg = f"Failed to update company {company.bdew_code} ({company.bdew_name}): {e}"
                logger.error(error_msg)
                self.stats["failed_companies"] += 1
                self.stats["errors"].append(error_msg)

        # Commit changes if not in dry run mode
        if not self.dry_run:
            await session.commit()
            logger.info("Changes committed to database")
        else:
            logger.info("DRY RUN - Changes not committed")

        self._print_summary()

    async def _update_company_geojson(
        self, session: AsyncSession, company: Company
    ) -> None:
        """Update GeoJSON data for a single company.

        Args:
            session: Database session
            company: Company to update
        """
        try:
            # Fetch VNB info with transformed coordinates
            vnb_info = self.vnb_client.fetch_vnb_info(company.bdew_code)

            if not vnb_info:
                logger.warning(f"No VNB info found for {company.bdew_code}")
                self.stats["skipped_companies"] += 1
                return

            # Check if we got GeoJSON data
            if not vnb_info.geojson:
                logger.warning(f"No GeoJSON data available for {company.bdew_code}")
                self.stats["skipped_companies"] += 1
                return

            # Check if GeoJSON data has changed
            current_geojson = company.network_territory_geojson
            new_geojson = vnb_info.geojson

            if current_geojson == new_geojson:
                logger.info(f"GeoJSON data unchanged for {company.bdew_code}")
                self.stats["skipped_companies"] += 1
                return

            # Update company data
            if not self.dry_run:
                await session.execute(
                    update(Company)
                    .where(Company.id == company.id)
                    .values(
                        network_territory_geojson=new_geojson,
                        vnbdigital_name=vnb_info.name,
                        vnbdigital_address=vnb_info.address,
                        vnbdigital_postcode=vnb_info.postcode,
                        vnbdigital_city=vnb_info.city,
                        vnbdigital_phone=vnb_info.phone,
                        vnbdigital_email=vnb_info.contact,
                        vnbdigital_website=vnb_info.website,
                        network_territory_layer_url=vnb_info.layer_url,
                        vnbdigital_last_enriched=datetime.utcnow(),
                        vnbdigital_enrichment_status="found",
                        vnbdigital_extended_data={
                            "bbox": vnb_info.bbox,
                            "regions": [
                                {"id": r.id, "name": r.name} for r in vnb_info.regions
                            ],
                        },
                    )
                )

            # Log feature count
            feature_count = len(new_geojson.get("features", []))
            bbox = new_geojson.get("bbox")
            bbox_str = (
                f"[{bbox[0]:.4f}, {bbox[1]:.4f}, {bbox[2]:.4f}, {bbox[3]:.4f}]"
                if bbox
                else "None"
            )

            logger.info(
                f"{'[DRY RUN] ' if self.dry_run else ''}Updated {company.bdew_code}: "
                f"{feature_count} features, bbox: {bbox_str}"
            )

            self.stats["updated_companies"] += 1

        except Exception as e:
            logger.error(f"Error updating {company.bdew_code}: {e}")

            # Mark as error in database if not dry run
            if not self.dry_run:
                await session.execute(
                    update(Company)
                    .where(Company.id == company.id)
                    .values(
                        vnbdigital_last_enriched=datetime.utcnow(),
                        vnbdigital_enrichment_status="error",
                    )
                )
            raise

    def _print_summary(self) -> None:
        """Print update summary statistics."""
        logger.info("=== UPDATE SUMMARY ===")
        logger.info(f"Total companies processed: {self.stats['total_companies']}")
        logger.info(f"Successfully updated: {self.stats['updated_companies']}")
        logger.info(f"Skipped (no changes/data): {self.stats['skipped_companies']}")
        logger.info(f"Failed: {self.stats['failed_companies']}")

        if self.stats["errors"]:
            logger.error("Errors encountered:")
            for error in self.stats["errors"]:
                logger.error(f"  - {error}")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Update company GeoJSON data with transformed coordinates"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without saving changes to database",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of companies to process",
    )
    parser.add_argument(
        "--bdew-code",
        type=str,
        help="Update only the company with this BDEW code",
    )

    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY RUN MODE enabled - no changes will be made to the database")

    # Initialize updater
    updater = CompanyGeoJSONUpdater(dry_run=args.dry_run)

    # Get database session
    settings = get_settings()
    db_manager = DatabaseManager(settings.database_url)

    async for session in db_manager.get_async_session():
        await updater.update_all_companies(
            session=session,
            limit=args.limit,
            bdew_code=args.bdew_code,
        )
        break  # We only need one session


if __name__ == "__main__":
    asyncio.run(main())
