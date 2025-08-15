"""VNB Client for fetching and processing electricity grid operator data."""

import base64
import gzip
import io
from dataclasses import dataclass, field
from typing import Any

import requests
from mapbox_vector_tile import decode as decode_mvt


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
        # BBOX seems to be a fixed value???
        req["BBOX"] = "0,5009377.085697312,2504688.5428486555,7514065.628545968"

        if vnb.get("layerUrl"):
            try:
                r = requests.get(vnb["layerUrl"], params=req, timeout=30)

                print("Request response:", r.status_code, base64.b64encode(r.content))
                r.raise_for_status()

                mvt_bytes = r.content

                # Falls gzip-komprimiert
                if mvt_bytes[:2] == b"\x1f\x8b":
                    with gzip.GzipFile(fileobj=io.BytesIO(mvt_bytes)) as f:
                        mvt_bytes = f.read()

                tile_layers = decode_mvt(mvt_bytes)
                features = []
                for layer_name, layer in tile_layers.items():
                    for feature in layer["features"]:
                        features.append(
                            {
                                "type": "Feature",
                                "geometry": feature["geometry"],
                                "properties": feature["properties"],
                                "layer": layer_name,
                            }
                        )

                geojson = {"type": "FeatureCollection", "features": features}
            except Exception as e:
                print(f"Warnung: Konnte MVT nicht konvertieren: {e}")

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
