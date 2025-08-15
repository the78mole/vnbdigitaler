import json

def geojson_to_ascii(geojson, width=80, height=25):
    features = geojson.get("features", [])
    if not features:
        print("No features to display.")
        return

    # Sammle alle Koordinaten
    coords = []
    for feat in features:
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            for ring in geom["coordinates"]:
                coords.extend(ring)
        elif geom["type"] == "MultiPolygon":
            for polygon in geom["coordinates"]:
                for ring in polygon:
                    coords.extend(ring)
        elif geom["type"] == "LineString":
            coords.extend(geom["coordinates"])
        elif geom["type"] == "Point":
            coords.append(geom["coordinates"])

    if not coords:
        print("No coordinates found.")
        return

    # BBox berechnen
    minx = min(c[0] for c in coords)
    maxx = max(c[0] for c in coords)
    miny = min(c[1] for c in coords)
    maxy = max(c[1] for c in coords)

    # Zeichenfeld vorbereiten
    grid = [[" " for _ in range(width)] for _ in range(height)]

    for x, y in coords:
        i = int((x - minx) / (maxx - minx + 1e-10) * (width - 1))
        j = int((y - miny) / (maxy - miny + 1e-10) * (height - 1))
        j = height - 1 - j  # y-Achse umdrehen
        grid[j][i] = "#"

    # Ausgabe
    for row in grid:
        print("".join(row))
