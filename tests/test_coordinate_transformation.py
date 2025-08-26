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

    # Correct MVT tile coordinates for Erlangen (calculated from WGS84 [11.005, 49.597])
    # These are actual tile coordinates in the 4096x4096 grid
    sample_mvt_coordinate = [2003.3991111111113, 2236.1488369529166]

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

    # Assert that coordinates are within Germany bounds
    assert (
        GERMANY_MIN_LON <= transformed[0] <= GERMANY_MAX_LON
        and GERMANY_MIN_LAT <= transformed[1] <= GERMANY_MAX_LAT
    ), f"Coordinates {transformed} are outside Germany bounds"

    print("✅ Coordinates are within Germany bounds")

    # Assert that transformation is accurate (within 0.001 degrees ≈ 100m)
    assert lon_diff < 0.001, f"Longitude difference too large: {lon_diff}"
    assert lat_diff < 0.001, f"Latitude difference too large: {lat_diff}"

    print("✅ Coordinate transformation is accurate")


if __name__ == "__main__":
    test_erlangen_coordinates()
