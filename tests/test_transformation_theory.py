#!/usr/bin/env python3
"""Test coordinate transformation theory."""

from pyproj import Transformer


def test_coordinate_transformation_theory():
    """Test the coordinate transformation logic."""

    print("🧮 Testing Coordinate Transformation Theory")
    print("=" * 50)

    # The fixed BBOX from VNBClient in Web Mercator (EPSG:3857)
    mercator_bbox = "0,5009377.085697312,2504688.5428486555,7514065.628545968"
    min_x, min_y, max_x, max_y = map(float, mercator_bbox.split(","))

    print("📦 Mercator BBOX:")
    print(f"   Min: [{min_x}, {min_y}]")
    print(f"   Max: [{max_x}, {max_y}]")

    # Convert the corners to WGS84 to see what area this covers
    transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    # Convert corners
    bottom_left = transformer.transform(min_x, min_y)
    top_right = transformer.transform(max_x, max_y)

    print("🌍 WGS84 Coverage:")
    print(f"   Bottom-left: [{bottom_left[0]:.3f}, {bottom_left[1]:.3f}]")
    print(f"   Top-right: [{top_right[0]:.3f}, {top_right[1]:.3f}]")

    # This should cover Germany roughly

    # Now let's see where the stored Erlangen coordinates come from
    # Current stored coordinate: [10.936890, 48.290503]
    stored_coord = [10.936890, 48.290503]

    # Reverse transform to see what MVT coordinate this came from
    mercator_coord = transformer.transform(
        stored_coord[0], stored_coord[1], direction="INVERSE"
    )
    print("🔄 Reverse transform of stored coordinate:")
    print(f"   WGS84: [{stored_coord[0]:.6f}, {stored_coord[1]:.6f}]")
    print(f"   Mercator: [{mercator_coord[0]:.1f}, {mercator_coord[1]:.1f}]")

    # Calculate what MVT tile coordinate this would be
    x_span = max_x - min_x
    y_span = max_y - min_y
    extent = 4096

    mvt_x = ((mercator_coord[0] - min_x) / x_span) * extent
    mvt_y = extent - ((mercator_coord[1] - min_y) / y_span) * extent  # Y is flipped

    print(f"📍 Calculated MVT coordinate: [{mvt_x:.1f}, {mvt_y:.1f}]")

    # Now let's check where Erlangen city center should be
    erlangen_center = [11.005, 49.597]  # Approximate city center
    erlangen_mercator = transformer.transform(
        erlangen_center[0], erlangen_center[1], direction="INVERSE"
    )

    erlangen_mvt_x = ((erlangen_mercator[0] - min_x) / x_span) * extent
    erlangen_mvt_y = extent - ((erlangen_mercator[1] - min_y) / y_span) * extent

    print("🎯 Erlangen city center:")
    print(f"   WGS84: [{erlangen_center[0]:.3f}, {erlangen_center[1]:.3f}]")
    print(f"   MVT coordinate: [{erlangen_mvt_x:.1f}, {erlangen_mvt_y:.1f}]")

    print("🤔 Analysis:")
    print("   The stored coordinates are south of Erlangen city center")
    print("   This could be correct if the network area is different from city center")

    # Test with a known wrong coordinate to see the pattern
    # Let's say the MVT coordinate should have been around Erlangen area
    # and see where it gets transformed to

    test_mvt_coord = [erlangen_mvt_x, erlangen_mvt_y]
    print("🧪 Testing transformation with Erlangen-area MVT coordinate:")
    print(f"   Input MVT: [{test_mvt_coord[0]:.1f}, {test_mvt_coord[1]:.1f}]")

    # Transform using our current logic
    test_mercator_x = min_x + (test_mvt_coord[0] / extent) * x_span
    test_mercator_y = max_y - (test_mvt_coord[1] / extent) * y_span

    test_wgs84 = transformer.transform(test_mercator_x, test_mercator_y)
    print(f"   Output WGS84: [{test_wgs84[0]:.6f}, {test_wgs84[1]:.6f}]")

    # Compare with expected
    print(f"   Expected: [{erlangen_center[0]:.6f}, {erlangen_center[1]:.6f}]")
    print(
        f"   Difference: [{abs(test_wgs84[0] - erlangen_center[0]):.6f}, {abs(test_wgs84[1] - erlangen_center[1]):.6f}]"
    )


if __name__ == "__main__":
    test_coordinate_transformation_theory()
