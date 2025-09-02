"""Geo Transformer module for converting MVT tile coordinates to WGS84."""

from pyproj import Transformer


class GeoTransformer:
    """Transforms MVT tile coordinates to WGS 84 GeoJSON coordinates."""

    def __init__(
        self,
        # Die harte BBOX aus deiner VNBClient-Klasse
        mercator_bbox_str: str = "0,5009377.085697312,2504688.5428486555,7514065.628545968",
        extent: int = 4096,
    ):
        """Initializes the transformer.

        Args:
            mercator_bbox_str: The BBOX string in EPSG:3857 coordinates (min_x,min_y,max_x,max_y).
            extent: The resolution of the vector tile (e.g., 4096).
        """
        self.min_x, self.min_y, self.max_x, self.max_y = map(
            float, mercator_bbox_str.split(",")
        )
        self.x_span = self.max_x - self.min_x
        self.y_span = self.max_y - self.min_y
        self.extent = extent

        # Initialisiere den pyproj Transformer, der von Mercator (3857) zu WGS84 (4326) umrechnet
        self.transformer = Transformer.from_crs(
            "EPSG:3857", "EPSG:4326", always_xy=True
        )

    def _transform_point(self, point: list[float]) -> list[float]:
        """Transform a single point from tile coordinates to WGS 84."""
        local_x, local_y = point

        # 1. Lineare Interpolation zu Web-Mercator-Metern
        # MVT-Koordinaten sind bereits in einem 4096x4096 Raster normalisiert
        # und müssen auf die gesamte Deutschland-BBOX skaliert werden
        mercator_x = self.min_x + (local_x / self.extent) * self.x_span
        # Korrektur: Y-Achse NICHT spiegeln - die MVT-Daten haben bereits die richtige Orientierung
        mercator_y = self.min_y + (local_y / self.extent) * self.y_span

        # 2. Reprojektion von Mercator zu WGS 84 (Lon, Lat)
        lon, lat = self.transformer.transform(mercator_x, mercator_y)
        return [lon, lat]

    def transform_geometry(self, geometry: dict) -> dict:
        """Transform an entire GeoJSON-like geometry structure."""
        geom_type = geometry["type"]
        coords = geometry["coordinates"]
        new_coords: list

        if geom_type == "Point":
            new_coords = self._transform_point(coords)
        elif geom_type == "LineString":
            new_coords = [self._transform_point(p) for p in coords]
        elif geom_type == "Polygon":
            new_coords = []
            for ring in coords:
                new_coords.append([self._transform_point(p) for p in ring])
        elif geom_type in ("MultiPolygon", "MultiLineString"):
            # Für MultiPolygon und MultiLineString weiter verschachteln
            new_coords = []
            for polygon in coords:
                new_polygon = []
                for ring in polygon:
                    new_polygon.append([self._transform_point(p) for p in ring])
                new_coords.append(new_polygon)
        else:
            # Unbehandelten Geometrietyp zurückgeben
            return geometry

        return {"type": geom_type, "coordinates": new_coords}
