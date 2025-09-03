"""Tests for VNB client functionality."""

import geopandas as gpd
import matplotlib.pyplot as plt

from src.vnbclient import VNBClient

# Example GraphQL endpoint
GRAPHQL_URL = "https://www.vnbdigital.de/gateway/graphql"

# Example VNB ID
VNB_ID = "179"


def geojson_obj_to_image(geojson_obj: dict, output_file: str) -> None:
    """Convert FeatureCollection to image file."""
    # Convert FeatureCollection to GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(geojson_obj["features"])

    # Plot
    fig, ax = plt.subplots(figsize=(8, 8))
    gdf.plot(ax=ax, edgecolor="black", facecolor="lightblue")

    plt.axis("off")
    plt.savefig(output_file, bbox_inches="tight", pad_inches=0)
    print(f"Image saved as {output_file}")


def main() -> None:
    """Main test function."""
    client = VNBClient(GRAPHQL_URL)
    vnb = client.fetch_vnb_info(VNB_ID)

    print("Name:", vnb.name)
    print("Address:", f"{vnb.address}, {vnb.postcode} {vnb.city}")
    print("Website:", vnb.website)
    print("Contact:", vnb.contact)
    print("Regions:", ", ".join([r.name for r in vnb.regions]))

    if vnb.geojson:
        print(f"Network area: {len(vnb.geojson.get('features', []))} features loaded.")
        geojson_obj_to_image(vnb.geojson, "netzgebiet.png")
    else:
        print("No GeoJSON available.")


if __name__ == "__main__":
    main()
