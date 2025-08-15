from vnbclient import VNBClient  # Name des Moduls (Datei z. B. als vnb_client.py speichern)
import geopandas as gpd
import matplotlib.pyplot as plt

# Beispiel-GraphQL-Endpunkt
GRAPHQL_URL = "https://www.vnbdigital.de/gateway/graphql"

# Beispiel-VNB-ID
VNB_ID = "179"

def geojson_obj_to_image(geojson_obj, output_file):
    # Wandelt FeatureCollection in GeoDataFrame um
    gdf = gpd.GeoDataFrame.from_features(geojson_obj["features"])

    # Plot
    fig, ax = plt.subplots(figsize=(8, 8))
    gdf.plot(ax=ax, edgecolor='black', facecolor='lightblue')

    plt.axis('off')
    plt.savefig(output_file, bbox_inches='tight', pad_inches=0)
    print(f"Bild gespeichert als {output_file}")

def main():
    client = VNBClient(GRAPHQL_URL)
    vnb = client.fetch_vnb_info(VNB_ID)

    print("Name:", vnb.name)
    print("Adresse:", f"{vnb.address}, {vnb.postcode} {vnb.city}")
    print("Website:", vnb.website)
    print("Kontakt:", vnb.contact)
    print("Regionen:", ", ".join([r.name for r in vnb.regions]))

    if vnb.geojson:
        print(f"Netzgebiet: {len(vnb.geojson.get('features', []))} Features geladen.")
        geojson_obj_to_image(vnb.geojson, "netzgebiet.png")
    else:
        print("Kein GeoJSON verfügbar.")


if __name__ == "__main__":
    main()
