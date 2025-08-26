#!/usr/bin/env python3
"""Test actual MVT data from VNBClient."""

import pytest

from src.vnbclient import VNBClient

# Germany geographical bounds
GERMANY_MIN_LON = 6.0
GERMANY_MAX_LON = 15.0
GERMANY_MIN_LAT = 47.0
GERMANY_MAX_LAT = 55.0


def test_real_mvt_data():
    """Test with real MVT data from VNBClient."""

    client = VNBClient("https://www.vnbdigital.de/app/graphql")

    print("🔍 Fetching real MVT data for Erlanger Stadtwerke (BDEW: 179)")
    print("=" * 60)

    try:
        vnb_info = client.fetch_vnb_info("179")
    except Exception as e:
        pytest.skip(f"VNB API not available: {e}")

    if vnb_info and vnb_info.geojson:
        print(f"✅ Found VNB: {vnb_info.name}")
        print(f"📍 Layer URL: {vnb_info.layer_url}")

        # Show first few coordinates from the polygon
        features = vnb_info.geojson.get("features", [])
        if features:
            first_feature = features[0]
            geometry = first_feature.get("geometry", {})
            if geometry.get("type") == "Polygon":
                coords = geometry.get("coordinates", [])
                if coords and coords[0]:
                    first_ring = coords[0]
                    print("🗺️ First 3 coordinates from polygon:")
                    for i, coord in enumerate(first_ring[:3]):
                        print(f"   {i+1}: [{coord[0]:.6f}, {coord[1]:.6f}]")

                    print(f"📦 Bounding box: {vnb_info.geojson.get('bbox')}")

                    # Check if coordinates are in reasonable German range
                    sample_coord = first_ring[0]
                    if (
                        GERMANY_MIN_LON <= sample_coord[0] <= GERMANY_MAX_LON
                        and GERMANY_MIN_LAT <= sample_coord[1] <= GERMANY_MAX_LAT
                    ):
                        print(
                            "✅ Coordinates appear to be in correct WGS84 range for Germany"
                        )
                        assert True  # Test passed
                    else:
                        print(
                            "❌ Coordinates appear to be outside German geographic bounds"
                        )
                        print("   Expected: longitude 6-15, latitude 47-55")
                        print(
                            f"   Got: longitude {sample_coord[0]:.6f}, latitude {sample_coord[1]:.6f}"
                        )
                        raise AssertionError(
                            "Coordinates outside expected German bounds"
                        )
    else:
        pytest.skip("No VNB data found or no GeoJSON available")


if __name__ == "__main__":
    test_real_mvt_data()
