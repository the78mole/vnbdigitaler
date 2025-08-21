#!/usr/bin/env python3
# ruff: noqa: E402
"""
VNBdigitaler - Raw Data Fetcher

Fetches raw data (base data and GeoJSON) for a specific operator from vnbdigital.de
and saves it to the tmp directory for analysis and debugging.

Usage:
    python tools/fetch_raw_data.py --bdew-code 179
    python tools/fetch_raw_data.py --bdew-code 179 --name "Erlanger Stadtwerke"

Author: VNBdigitaler Project
Date: 2025-08-24
"""

# Add project root to path for imports
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

import argparse
import asyncio
import gzip
import io
import json
import logging
from datetime import datetime
from typing import Any

import httpx
import requests
from mapbox_vector_tile import decode as decode_mvt

from src.geo_transformer import GeoTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Disable HTTP request logging (too verbose)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Constants
VNBDIGITAL_GRAPHQL_URL = "https://www.vnbdigital.de/gateway/graphql"
VNBDIGITAL_GEOJSON_URL = "https://www.vnbdigital.de/assets/geojson"
HTTP_NOT_FOUND = 404

# Project directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
TMP_DIR = PROJECT_ROOT / "tmp"

# GraphQL query for basic operator data
OPERATOR_QUERY = """
query ($id: ID!) {
  vnb_vnb(id: $id) {
    _id
    name
    types
    image {
      url
    }
    logo {
      url
    }
    layerUrl
    bbox
    description
    address
    postcode
    city
    phone
    contact
    website
    publicRequired
    clicks
    regions {
      _id
      name
    }
    services {
      type {
        _id
        type
        name
        title
        description
      }
      title
      description
      activated
    }
    documents {
      _id
      name
      type
      category
      url
      currentFrom
      currentTo
    }
  }
}
"""


class RawDataFetcher:
    """Fetches raw data for a specific operator from vnbdigital.de."""

    def __init__(self):
        """Initialize the fetcher."""
        self.session: httpx.AsyncClient | None = None
        self.transformer = GeoTransformer()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient(
            timeout=30.0, headers=self.headers, follow_redirects=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()

    async def fetch_operator_data(self, bdew_code: str) -> dict[str, Any] | None:
        """
        Fetch operator base data from vnbdigital.de GraphQL API.

        Args:
            bdew_code: BDEW operator code

        Returns:
            Operator data dict if found, None otherwise
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        payload = {"query": OPERATOR_QUERY, "variables": {"id": bdew_code}}

        try:
            logger.info(f"Fetching operator data for BDEW code: {bdew_code}")
            response = await self.session.post(VNBDIGITAL_GRAPHQL_URL, json=payload)
            response.raise_for_status()

            data = response.json()

            if "errors" in data:
                logger.error(
                    f"GraphQL errors for BDEW code {bdew_code}: {data['errors']}"
                )
                return None

            operator_data = data.get("data", {}).get("vnb_vnb")

            if operator_data is None:
                logger.warning(f"No operator data found for BDEW code {bdew_code}")
                return None

            logger.info(f"✅ Found operator: {operator_data.get('name', 'Unknown')}")
            return operator_data

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching operator data for {bdew_code}: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error fetching operator data for {bdew_code}: {e}"
            )
            return None

    def extract_geojson_from_mvt(self, layer_url: str) -> dict[str, Any] | None:
        """
        Extract GeoJSON data from MVT (Mapbox Vector Tile) URL.
        Based on VNBClient implementation.

        Args:
            layer_url: Layer URL from operator data

        Returns:
            GeoJSON data dict if successful, None otherwise
        """
        try:
            # MVT request parameters (from VNBClient)
            params = {
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

            logger.info(f"Fetching MVT data from: {layer_url}")
            response = requests.get(layer_url, params=params, timeout=30)
            response.raise_for_status()

            mvt_bytes = response.content

            # Handle gzip compression
            if mvt_bytes[:2] == b"\x1f\x8b":
                with gzip.GzipFile(fileobj=io.BytesIO(mvt_bytes)) as f:
                    mvt_bytes = f.read()

            # Decode MVT to features
            tile_layers = decode_mvt(mvt_bytes)
            features = []

            for layer_name, layer in tile_layers.items():
                for feature in layer["features"]:
                    # Transform the geometry from tile coordinates to WGS84
                    transformed_geometry = self.transformer.transform_geometry(
                        feature["geometry"]
                    )

                    features.append(
                        {
                            "type": "Feature",
                            "geometry": transformed_geometry,
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
                "metadata": {
                    "source": "vnbdigital.de MVT",
                    "layer_url": layer_url,
                    "extraction_method": "mapbox-vector-tile",
                    "coordinate_system": "WGS84 (EPSG:4326)",
                    "transformed": True,
                },
            }

            logger.info(f"✅ Extracted {len(features)} features from MVT")
            return geojson

        except Exception as e:
            logger.error(f"Error extracting GeoJSON from MVT: {e}")
            return None

    async def fetch_geojson_data(
        self, operator_data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """
        Fetch GeoJSON data using MVT approach from operator data.

        Args:
            operator_data: Operator data containing layerUrl

        Returns:
            GeoJSON data dict if found, None otherwise
        """
        layer_url = operator_data.get("layerUrl")

        if not layer_url:
            logger.warning("No layerUrl found in operator data")
            return None

        return self.extract_geojson_from_mvt(layer_url)

    def save_raw_data(
        self,
        bdew_code: str,
        operator_name: str | None,
        operator_data: dict[str, Any] | None,
        geojson_data: dict[str, Any] | None,
    ) -> None:
        """
        Save raw data to tmp directory.

        Args:
            bdew_code: BDEW operator code
            operator_name: Operator name for file naming
            operator_data: Base operator data
            geojson_data: GeoJSON service area data
        """
        # Ensure tmp directory exists
        TMP_DIR.mkdir(exist_ok=True)

        # Generate safe filename
        safe_name = (
            operator_name.replace(" ", "_").replace("/", "_")
            if operator_name
            else f"operator_{bdew_code}"
        )
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save operator base data
        if operator_data:
            operator_file = (
                TMP_DIR / f"{safe_name}_{bdew_code}_operator_{timestamp}.json"
            )
            with operator_file.open("w", encoding="utf-8") as f:
                json.dump(operator_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved operator data to: {operator_file}")

        # Save GeoJSON data
        if geojson_data:
            geojson_file = TMP_DIR / f"{safe_name}_{bdew_code}_geojson_{timestamp}.json"
            with geojson_file.open("w", encoding="utf-8") as f:
                json.dump(geojson_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved GeoJSON data to: {geojson_file}")

        # Save summary file
        summary = {
            "fetch_metadata": {
                "bdew_code": bdew_code,
                "operator_name": operator_name,
                "fetch_timestamp": datetime.now().isoformat(),
                "operator_data_found": operator_data is not None,
                "geojson_data_found": geojson_data is not None,
            },
            "operator_data_summary": {
                "name": operator_data.get("name") if operator_data else None,
                "city": operator_data.get("city") if operator_data else None,
                "types": operator_data.get("types", []) if operator_data else [],
                "services_count": len(operator_data.get("services", []))
                if operator_data
                else 0,
                "documents_count": len(operator_data.get("documents", []))
                if operator_data
                else 0,
            }
            if operator_data
            else None,
            "geojson_data_summary": {
                "features_count": len(geojson_data.get("features", []))
                if geojson_data
                else 0,
                "coordinate_system": geojson_data.get("crs", {})
                .get("properties", {})
                .get("name")
                if geojson_data
                else None,
                "bbox": geojson_data.get("bbox") if geojson_data else None,
            }
            if geojson_data
            else None,
        }

        summary_file = TMP_DIR / f"{safe_name}_{bdew_code}_summary_{timestamp}.json"
        with summary_file.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved summary to: {summary_file}")

    async def fetch_raw_data(
        self, bdew_code: str, operator_name: str | None = None
    ) -> None:
        """
        Fetch and save all raw data for an operator.

        Args:
            bdew_code: BDEW operator code
            operator_name: Optional operator name for better file naming
        """
        logger.info(f"🚀 Starting raw data fetch for BDEW code: {bdew_code}")
        if operator_name:
            logger.info(f"   Operator name: {operator_name}")

        # Fetch operator base data
        operator_data = await self.fetch_operator_data(bdew_code)

        # Fetch GeoJSON data using operator data
        geojson_data = None
        if operator_data:
            geojson_data = await self.fetch_geojson_data(operator_data)

        # Use fetched name if not provided
        if not operator_name and operator_data:
            operator_name = operator_data.get("name")

        # Save all data
        self.save_raw_data(bdew_code, operator_name, operator_data, geojson_data)

        # Summary
        if operator_data or geojson_data:
            logger.info("✅ Raw data fetch completed successfully")
            if operator_data:
                logger.info(
                    f"   - Operator data: ✅ ({operator_data.get('name', 'Unknown')})"
                )
            else:
                logger.info("   - Operator data: ❌")
            if geojson_data:
                logger.info(
                    f"   - GeoJSON data: ✅ ({len(geojson_data.get('features', []))} features)"
                )
            else:
                logger.info("   - GeoJSON data: ❌")
        else:
            logger.warning("❌ No data found for this operator")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Fetch raw data for a specific operator from vnbdigital.de"
    )
    parser.add_argument("--bdew-code", required=True, help="BDEW operator code")
    parser.add_argument("--name", help="Operator name for better file naming")

    args = parser.parse_args()

    try:
        async with RawDataFetcher() as fetcher:
            await fetcher.fetch_raw_data(args.bdew_code, args.name)

    except Exception as e:
        logger.error(f"❌ Error during data fetch: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
