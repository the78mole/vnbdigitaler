#!/usr/bin/env python3
"""Test coordinate transformation with sample MVT data."""

from src.geo_transformer import GeoTransformer

# Germany geographical bounds
GERMANY_MIN_LON = 6.0
GERMANY_MAX_LON = 15.0
GERMANY_MIN_LAT = 47.0
GERMANY_MAX_LAT = 55.0


def test_erlangen_coordinates():
    """Test coordinate transformation with Erlangen sample data."""

    # Sample MVT coordinate from your example (should be around Erlangen)
    # This is a sample coordinate from the polygon you provided
    sample_mvt_coordinate = [10.9368896484375, 48.29050321714064]

    # Initialize transformer with the same bbox used in VNBClient
    transformer = GeoTransformer(
        mercator_bbox_str="0,5009377.085697312,2504688.5428486555,7514065.628545968",
        extent=4096,
    )

    print("🧪 Testing Coordinate Transformation")
    print("=" * 50)
    print(f"Input MVT coordinate: {sample_mvt_coordinate}")

    # Transform the coordinate
    transformed = transformer._transform_point(sample_mvt_coordinate)
    print(f"Transformed WGS84: {transformed}")

    # Expected Erlangen coordinates (longitude, latitude)
    expected_erlangen = [11.005, 49.597]
    print(f"Expected Erlangen: {expected_erlangen}")

    # Calculate difference
    lon_diff = abs(transformed[0] - expected_erlangen[0])
    lat_diff = abs(transformed[1] - expected_erlangen[1])

    print(f"Longitude difference: {lon_diff:.6f}")
    print(f"Latitude difference: {lat_diff:.6f}")
    if (
        GERMANY_MIN_LON <= transformed[0] <= GERMANY_MAX_LON
        and GERMANY_MIN_LAT <= transformed[1] <= GERMANY_MAX_LAT
    ):
        print("✅ Coordinates are within Germany bounds")
    else:
        print("❌ Coordinates are outside Germany bounds")

    return transformed


if __name__ == "__main__":
    test_erlangen_coordinates()
