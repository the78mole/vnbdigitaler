import requests
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import tempfile
import json
from mapbox_vector_tile import decode as decode_mvt
import gzip
import io
import base64
from urllib.parse import quote


@dataclass
class Region:
    id: str
    name: str


@dataclass
class VNBInfo:
    id: str
    name: str
    address: str
    postcode: str
    city: str
    website: str
    phone: Optional[str]
    contact: Optional[str]
    layer_url: Optional[str]
    bbox: Optional[List[float]] = field(default=None)
    geojson: Optional[Dict[str, Any]] = field(default=None)
    regions: List[Region] = field(default_factory=list)


class VNBClient:
    def __init__(self, graphql_url: str):
        self.graphql_url = graphql_url

    def fetch_vnb_info(self, vnb_id: str) -> VNBInfo:
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
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            raise RuntimeError(f"GraphQL error: {data['errors']}")

        vnb = data["data"]["vnb_vnb"]

        # Hole GeoJSON aus MVT, falls verfügbar
        geojson = None

        layer_url = vnb.get("layerUrl")

        # Raw from graphql-request
        # https://www.vnbdigital.de/mapproxy/geoserver?
        #   LAYERS=vnbdigital:VNBGeoFeatures&
        # PROXY_PARAMS=eyJpZHMiOlsiUkVGYWpFSmZpTmFwaHNwN1ciXSwi
        #              c3RhdGVzIjpbIkFDVElWRSJdfQ==
        #
        # Real:
        # https://www.vnbdigital.de/mapproxy/geoserver?
        #   LAYERS=vnbdigital:VNBGeoFeatures&
        # PROXY_PARAMS=eyJpZHMiOlsiUkVGYWpFSmZpTmFwaHNwN1ciXSwi
        #              c3RhdGVzIjpbIkFDVElWRSJdfQ==&
        # SERVICE=WMS&
        # VERSION=1.3.0&
        # REQUEST=GetMap&
        # FORMAT=application%2Fvnd.mapbox-vector-tile&
        # TRANSPARENT=true&
        # SRS=EPSG%3A900913&
        # WIDTH=256&HEIGHT=256&
        # CRS=EPSG%3A3857&
        # STYLES=&
        # BBOX=0%2C5009377.085697312%2C2504688.5428486555%2C7514065.628545968

        req = dict()
        req["SERVICE"]    = "WMS"
        req["VERSION"]    = "1.3.0"
        req["REQUEST"]     = "GetMap"
        req["FORMAT"]      = "application/vnd.mapbox-vector-tile"
        req["TRANSPARENT"] = "true"
        req["SRS"]         = "EPSG:900913"
        req["WIDTH"]       = "256"
        req["HEIGHT"]      = "256"
        req["CRS"]         = "EPSG:3857"
        req["STYLES"]      = ""
        # BBOX seems to be a fixed value???
        req["BBOX"]        = "0,5009377.085697312,2504688.5428486555,7514065.628545968"

        #print(json.dumps(req, indent=4))

        if vnb.get("layerUrl"):
            try:
                r = requests.get(vnb["layerUrl"], params=req)

                print("Request response:", r.status_code, base64.b64encode(r.content))
                r.raise_for_status()

                mvt_bytes = r.content

                # Falls gzip-komprimiert
                if mvt_bytes[:2] == b'\x1f\x8b':
                    with gzip.GzipFile(fileobj=io.BytesIO(mvt_bytes)) as f:
                        mvt_bytes = f.read()

                tile_layers = decode_mvt(mvt_bytes)
                features = []
                for layer_name, layer in tile_layers.items():
                    for feature in layer['features']:
                        features.append({
                            "type": "Feature",
                            "geometry": feature["geometry"],
                            "properties": feature["properties"],
                            "layer": layer_name
                        })

                geojson = {
                    "type": "FeatureCollection",
                    "features": features
                }
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
            ]
        )
