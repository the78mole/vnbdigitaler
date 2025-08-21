#!/usr/bin/env python3
"""
Test script to validate that GeoJSON coordinate transformation is working correctly.

This script tests various companies to ensure their coordinates are now in proper WGS84 format.
"""

import asyncio

import requests
from sqlalchemy import select

from src.config import get_settings
from src.database import DatabaseManager
from src.models import Company

# Germany geographical bounds
GERMANY_MIN_LON = 5.0
GERMANY_MAX_LON = 16.0
GERMANY_MIN_LAT = 47.0
GERMANY_MAX_LAT = 56.0


def validate_coordinates(geojson_data, company_name):  # noqa: ARG001
    """Validate that GeoJSON coordinates are in proper WGS84 format."""
    if not geojson_data or geojson_data.get("type") != "FeatureCollection":
        return False, "Not a valid FeatureCollection"

    features = geojson_data.get("features", [])
    if not features:
        return False, "No features found"

    for feature in features:
        geometry = feature.get("geometry", {})
        coordinates = geometry.get("coordinates", [])

        if geometry.get("type") == "Polygon" and coordinates and coordinates[0]:
            first_coord = coordinates[0][0]  # First coordinate pair
            lon, lat = first_coord[0], first_coord[1]

            # Valid WGS84 coordinates for Germany
            if not (
                GERMANY_MIN_LON <= lon <= GERMANY_MAX_LON
            ):  # Longitude range for Germany
                return False, f"Invalid longitude {lon} for Germany"
            if not (
                GERMANY_MIN_LAT <= lat <= GERMANY_MAX_LAT
            ):  # Latitude range for Germany
                return False, f"Invalid latitude {lat} for Germany"

            print(f"  ✅ Valid coordinates: [{lon:.4f}, {lat:.4f}]")
            return True, "Valid WGS84 coordinates"

    return False, "Could not find valid coordinates"


async def test_companies():
    """Test multiple companies to ensure coordinates are correct."""
    print("🗺️  Testing Company GeoJSON Coordinate Validation")
    print("=" * 50)

    settings = get_settings()
    db_manager = DatabaseManager(settings.database_url)

    # Test companies with known GeoJSON data
    test_companies = []

    async for session in db_manager.get_async_session():
        # Get companies that have GeoJSON data
        result = await session.execute(
            select(Company.id, Company.bdew_code, Company.bdew_name)
            .where(Company.network_territory_geojson.is_not(None))
            .limit(5)
        )
        test_companies = result.fetchall()
        break

    if not test_companies:
        print("❌ No companies with GeoJSON data found")
        return

    print(f"Found {len(test_companies)} companies with GeoJSON data\n")

    success_count = 0
    for company_id, bdew_code, bdew_name in test_companies:
        print(f"Testing: {bdew_name} (BDEW: {bdew_code})")

        try:
            # Test API endpoint
            response = requests.get(
                f"http://localhost:8000/companies/api/{company_id}/geojson", timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if not data.get("has_geojson"):
                print("  ❌ No GeoJSON data available")
                continue

            geojson_data = data.get("geojson")
            is_valid, message = validate_coordinates(geojson_data, bdew_name)

            if is_valid:
                print(f"  ✅ {message}")

                # Check bbox if available
                bbox = geojson_data.get("bbox")
                if bbox:
                    print(
                        f"  📍 Bbox: [{bbox[0]:.4f}, {bbox[1]:.4f}, {bbox[2]:.4f}, {bbox[3]:.4f}]"
                    )

                success_count += 1
            else:
                print(f"  ❌ {message}")

        except Exception as e:
            print(f"  ❌ Error: {e}")

        print()  # Empty line

    print("=" * 50)
    print(f"✅ Successfully validated: {success_count}/{len(test_companies)} companies")
    print(
        "🎯 Coordinate transformation working correctly!"
        if success_count > 0
        else "❌ Issues found!"
    )


if __name__ == "__main__":
    asyncio.run(test_companies())
