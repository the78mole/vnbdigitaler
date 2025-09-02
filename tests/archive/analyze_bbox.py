#!/usr/bin/env python
"""Analyze company bbox data to understand scaling issues."""

import asyncio
import math

from sqlalchemy import select

from src.config import get_settings
from src.database import DatabaseManager
from src.models import Company

# Constants
BBOX_COORDINATE_COUNT = 4


async def analyze_company_bbox(bdew_code: str = "179"):
    """Analyze the original bbox data for a company."""
    settings = get_settings()
    db_manager = DatabaseManager(settings.database_url)

    async for session in db_manager.get_async_session():
        # Get company data by BDEW code
        result = await session.execute(
            select(Company).where(Company.bdew_code == bdew_code)
        )
        company = result.scalar_one_or_none()

        if not company:
            print(f"Company with BDEW code {bdew_code} not found")
            return

        print(f"Company: {company.bdew_name} (BDEW: {bdew_code})")

        # Check vnbdigital extended data
        if company.vnbdigital_extended_data:
            bbox = company.vnbdigital_extended_data.get("bbox")
            if bbox and isinstance(bbox, list) and len(bbox) == BBOX_COORDINATE_COUNT:
                print(f"Original bbox: {bbox}")

                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                print(f"Original bbox dimensions: {width:.6f} x {height:.6f} degrees")
                print(f"Original bbox area: {width * height:.8f} square degrees")

                # Convert to approximate meters (at latitude ~49.5°)
                lat_center = (bbox[1] + bbox[3]) / 2

                # Approximate conversion at this latitude
                deg_to_m_lat = 111320  # meters per degree latitude
                deg_to_m_lon = 111320 * math.cos(math.radians(lat_center))

                width_m = width * deg_to_m_lon
                height_m = height * deg_to_m_lat

                print(f"Original bbox in meters: {width_m:.1f} x {height_m:.1f} meters")
                print(f"Original area: {width_m * height_m / 1e6:.2f} km²")
            else:
                print("No valid bbox found in extended data")
        else:
            print("No vnbdigital_extended_data found")

        # Check transformed GeoJSON
        if company.network_territory_geojson:
            geojson = company.network_territory_geojson
            print(f"\nTransformed GeoJSON type: {geojson.get('type')}")

            if "bbox" in geojson:
                transformed_bbox = geojson["bbox"]
                print(f"Transformed bbox: {transformed_bbox}")

                t_width = transformed_bbox[2] - transformed_bbox[0]
                t_height = transformed_bbox[3] - transformed_bbox[1]

                print(f"Transformed dimensions: {t_width:.6f} x {t_height:.6f} degrees")

                # Convert to meters
                lat_center = (transformed_bbox[1] + transformed_bbox[3]) / 2
                t_width_m = t_width * 111320 * math.cos(math.radians(lat_center))
                t_height_m = t_height * 111320

                print(
                    f"Transformed in meters: {t_width_m:.1f} x {t_height_m:.1f} meters"
                )
                print(f"Transformed area: {t_width_m * t_height_m / 1e6:.2f} km²")

        break


if __name__ == "__main__":
    asyncio.run(analyze_company_bbox())
