#!/usr/bin/env python3
"""Debug MVT transformation by intercepting raw data."""

import gzip
import io

import requests
from mapbox_vector_tile import decode as decode_mvt

from src.geo_transformer import GeoTransformer


def debug_mvt_transformation():
    """Debug the MVT transformation process step by step."""

    print("🔍 Debugging MVT transformation for BDEW 179 (Erlanger Stadtwerke)")
    print("=" * 70)

    # GraphQL query to get the layer URL
    graphql_url = "https://www.vnbdigital.de/app/graphql"
    query = """
    query ($id: ID!) {
      vnb_vnb(id: $id) {
        _id
        name
        layerUrl
      }
    }
    """

    try:
        response = requests.post(
            graphql_url,
            json={"query": query, "variables": {"id": "179"}},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            print(f"❌ GraphQL error: {data['errors']}")
            return

        vnb = data["data"]["vnb_vnb"]
        if not vnb:
            print("❌ VNB not found")
            return

        print(f"🏢 Found: {vnb['name']}")
        print(f"🔗 Layer URL: {vnb['layerUrl']}")

        # Prepare WMS request
        req = {
            "SERVICE": "WMS",
            "VERSION": "1.3.0",
            "REQUEST": "GetMap",
            "FORMAT": "application/vnd.mapbox-vector-tile",
            "TRANSPARENT": "true",
            "SRS": "EPSG:900913",
            "WIDTH": "256",
            "HEIGHT": "256",
            "CRS": "EPSG:3857",
            "STYLES": "",
            "BBOX": "0,5009377.085697312,2504688.5428486555,7514065.628545968",
        }

        print("📡 Fetching MVT tile...")
        print(f"   BBOX: {req['BBOX']}")

        # Fetch MVT data
        r = requests.get(vnb["layerUrl"], params=req, timeout=30)
        r.raise_for_status()

        mvt_bytes = r.content

        # Handle gzip compression
        if mvt_bytes[:2] == b"\\x1f\\x8b":
            with gzip.GzipFile(fileobj=io.BytesIO(mvt_bytes)) as f:
                mvt_bytes = f.read()

        # Decode MVT
        tile_layers = decode_mvt(mvt_bytes)

        print(f"🗂️ Found {len(tile_layers)} layers in MVT:")
        for layer_name, layer in tile_layers.items():
            print(f"   Layer '{layer_name}': {len(layer['features'])} features")

            for i, feature in enumerate(layer["features"][:2]):  # Show first 2 features
                print(f"   🎯 Feature {i+1}:")
                print(f"      Type: {feature['geometry']['type']}")

                # Show raw MVT coordinates (should be integers 0-4096)
                if feature["geometry"]["type"] == "Polygon":
                    coords = feature["geometry"]["coordinates"]
                    if coords and coords[0]:
                        first_ring = coords[0]
                        print("      Raw MVT coordinates (first 3):")
                        for j, coord in enumerate(first_ring[:3]):
                            print(f"         {j+1}: [{coord[0]}, {coord[1]}] (raw MVT)")

                        # Now transform them
                        transformer = GeoTransformer()
                        transformed_coords = []
                        for coord in first_ring[:3]:
                            transformed = transformer._transform_point(coord)
                            transformed_coords.append(transformed)
                            print(
                                f"         {len(transformed_coords)}: [{transformed[0]:.6f}, {transformed[1]:.6f}] (WGS84)"
                            )

                        # The issue might be here - let's check what we expect
                        print("      🎯 Expected for Erlangen area: ~[11.0, 49.6]")

                print()

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    debug_mvt_transformation()
