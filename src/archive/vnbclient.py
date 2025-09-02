"""VNB Client for fetching and processing electricity grid operator data."""

import gzip
import io
from dataclasses import dataclass, field
from typing import Any

import requests
from mapbox_vector_tile import decode as decode_mvt

from .geo_transformer import GeoTransformer


@dataclass
class Region:
    """Represents a geographical region with ID and name."""

    id: str
    name: str


@dataclass
class VNBInfo:
    """Information about a electricity grid operator (Verteilnetzbetreiber)."""

    id: str
    name: str
    address: str
    postcode: str
    city: str
    website: str
    phone: str | None
    contact: str | None
    layer_url: str | None
    bbox: list[float] | None = field(default=None)
    geojson: dict[str, Any] | None = field(default=None)
    regions: list[Region] = field(default_factory=list)


class VNBClient:
    """Client for fetching VNB (electricity grid operator) information."""

    def __init__(self, graphql_url: str):
        """Initialize the VNB client.

        Args:
            graphql_url: The GraphQL endpoint URL for VNB data.
        """
        self.graphql_url = graphql_url
        self.transformer = GeoTransformer()

    def fetch_vnb_info(self, vnb_id: str) -> VNBInfo | None:
        """Fetch information about a specific VNB.

        Args:
            vnb_id: The unique identifier of the VNB.

        Returns:
            VNBInfo object if found, None otherwise.
        """
        query = """
        query ($id: ID!) {
          vnb_vnb(id: $id) {
            _id
            name
            address
            postcode
            city
            phone
            contact
            website
            layerUrl
            bbox
            regions {
              _id
              name
            }
          }
        }
        """
        variables = {"id": vnb_id}
        response = requests.post(
            self.graphql_url,
            json={"query": query, "variables": variables},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            raise RuntimeError(f"GraphQL error: {data['errors']}")

        vnb = data["data"]["vnb_vnb"]

        # Return None if VNB not found
        if vnb is None:
            return None

        # Hole GeoJSON aus MVT, falls verfügbar
        geojson = None

        req = {}
        req["SERVICE"] = "WMS"
        req["VERSION"] = "1.3.0"
        req["REQUEST"] = "GetMap"
        req["FORMAT"] = "application/vnd.mapbox-vector-tile"
        req["TRANSPARENT"] = "true"
        req["SRS"] = "EPSG:900913"
        req["WIDTH"] = "256"
        req["HEIGHT"] = "256"
        req["CRS"] = "EPSG:3857"
        req["STYLES"] = ""
        # Fixed BBOX required by vnbdigital.de server (covers larger European area)
        req["BBOX"] = "0,5009377.085697312,2504688.5428486555,7514065.628545968"

        if vnb.get("layerUrl"):
            try:
                r = requests.get(vnb["layerUrl"], params=req, timeout=30)

                r.raise_for_status()

                mvt_bytes = r.content

                # Falls gzip-komprimiert
                if mvt_bytes[:2] == b"\x1f\x8b":
                    with gzip.GzipFile(fileobj=io.BytesIO(mvt_bytes)) as f:
                        mvt_bytes = f.read()

                tile_layers = decode_mvt(mvt_bytes)
                features = []

                # Use the original BBOX that works with the vnbdigital.de server
                wms_request_bbox = (
                    "0,5009377.085697312,2504688.5428486555,7514065.628545968"
                )

                # Create transformer with the WMS request bbox
                mvt_transformer = GeoTransformer(
                    mercator_bbox_str=wms_request_bbox, extent=4096
                )

                # No position correction needed - transformation is now accurate
                POSITION_OFFSET_LON = 0.0  # No correction for testing
                POSITION_OFFSET_LAT = 0.0  # No correction for testing

                for layer_name, layer in tile_layers.items():
                    for feature in layer["features"]:
                        # Transform the geometry from tile coordinates to WGS84 using WMS request bbox
                        transformed_geometry = mvt_transformer.transform_geometry(
                            feature["geometry"]
                        )

                        # Apply position correction to fix systematic offset
                        corrected_geometry = self._apply_position_correction(
                            transformed_geometry,
                            POSITION_OFFSET_LON,
                            POSITION_OFFSET_LAT,
                        )

                        features.append(
                            {
                                "type": "Feature",
                                "geometry": corrected_geometry,
                                "properties": feature["properties"],
                                "layer": layer_name,
                            }
                        )

                # Calculate bounding box from transformed coordinates
                all_coords = []
                for feature in features:
                    geom = feature["geometry"]
                    if geom["type"] == "Polygon":
                        for ring in geom["coordinates"]:
                            all_coords.extend(ring)
                    elif geom["type"] == "LineString":
                        all_coords.extend(geom["coordinates"])
                    elif geom["type"] == "Point":
                        all_coords.append(geom["coordinates"])

                vnb_bbox = None
                if all_coords:
                    lons = [coord[0] for coord in all_coords]
                    lats = [coord[1] for coord in all_coords]
                    vnb_bbox = [min(lons), min(lats), max(lons), max(lats)]

                geojson = {
                    "type": "FeatureCollection",
                    "features": features,
                    "bbox": vnb_bbox,
                }
            except Exception as e:
                vnb_name = vnb.get("name", "Unbekannt")
                print(
                    f"Warnung: Konnte MVT nicht konvertieren für '{vnb_name}' (BDEW: {vnb_id}): {e}"
                )

        return VNBInfo(
            id=vnb["_id"],
            name=vnb["name"],
            address=vnb.get("address", ""),
            postcode=vnb.get("postcode", ""),
            city=vnb.get("city", ""),
            website=vnb.get("website", ""),
            phone=vnb.get("phone"),
            contact=vnb.get("contact"),
            layer_url=vnb.get("layerUrl"),
            bbox=vnb.get("bbox"),
            geojson=geojson,
            regions=[
                Region(id=region["_id"], name=region["name"])
                for region in vnb.get("regions", [])
            ],
        )

    def _apply_position_correction(
        self, geometry: dict, offset_lon: float, offset_lat: float
    ) -> dict:
        """Apply position correction to geometry coordinates.

        Args:
            geometry: GeoJSON geometry object
            offset_lon: Longitude offset to apply
            offset_lat: Latitude offset to apply

        Returns:
            Corrected geometry object
        """

        def correct_coordinates(coords: list) -> list:
            """Recursively correct coordinate arrays."""
            if isinstance(coords[0], int | float):
                # Single coordinate pair [lon, lat]
                return [coords[0] + offset_lon, coords[1] + offset_lat]
            else:
                # Nested coordinate array
                return [correct_coordinates(coord) for coord in coords]

        corrected_geometry = geometry.copy()
        if geometry["type"] in ["Point", "LineString", "Polygon"]:
            corrected_geometry["coordinates"] = correct_coordinates(
                geometry["coordinates"]
            )
        elif geometry["type"] in ["MultiPoint", "MultiLineString", "MultiPolygon"]:
            corrected_geometry["coordinates"] = [
                correct_coordinates(coords) for coords in geometry["coordinates"]
            ]

        return corrected_geometry
