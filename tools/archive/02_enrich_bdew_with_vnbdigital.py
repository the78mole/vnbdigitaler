#!/usr/bin/env python3
"""
VNBdigitaler - Script 02: Enrich BDEW data with vnbdigital.de information

This script enriches the BDEW grid operator data with additional information
from the vnbdigital.de GraphQL API, providing comprehensive operator profiles
with contact data, geographic information, and service details.

Author: VNBdigitaler Project
Date: 2025-08-21
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
from pydantic import BaseModel, Field

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Disable HTTP request logging (too verbose)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Constants
VNBDIGITAL_GRAPHQL_URL = "https://www.vnbdigital.de/gateway/graphql"
# Use relative path from script location to project data directory
SCRIPT_DIR = Path(__file__).parent
PROJECT_DATA_DIR = SCRIPT_DIR.parent / "data"
BDEW_DATA_FILE = PROJECT_DATA_DIR / "bdew_grid_operators.json"
OUTPUT_FILE = PROJECT_DATA_DIR / "bdew_enriched_with_vnbdigital.json"
CSV_OUTPUT_FILE = PROJECT_DATA_DIR / "bdew_enriched_with_vnbdigital.csv"

# GraphQL query for vnbdigital.de
VNBDIGITAL_QUERY = """
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


class VNBDigitalData(BaseModel):
    """Model for vnbdigital.de API response data."""

    id: str = Field(alias="_id")
    name: str | None = None
    types: list[str] = Field(default_factory=list)
    image_url: str | None = None
    logo_url: str | None = None
    layer_url: str | None = None
    bbox: list[float] | None = None
    description: str | None = None
    address: str | None = None
    postcode: str | None = None
    city: str | None = None
    phone: str | None = None
    contact: str | None = None
    website: str | None = None
    public_required: bool | None = None
    clicks: int | None = None
    regions: list[dict[str, Any]] = Field(default_factory=list)
    services: list[dict[str, Any]] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "VNBDigitalData":
        """Create instance from vnbdigital.de API response."""
        return cls(
            _id=data["_id"],
            name=data.get("name"),
            types=data.get("types", []),
            image_url=data.get("image", {}).get("url") if data.get("image") else None,
            logo_url=data.get("logo", {}).get("url") if data.get("logo") else None,
            layer_url=data.get("layerUrl"),
            bbox=data.get("bbox"),
            description=data.get("description"),
            address=data.get("address"),
            postcode=data.get("postcode"),
            city=data.get("city"),
            phone=data.get("phone"),
            contact=data.get("contact"),
            website=data.get("website"),
            public_required=data.get("publicRequired"),
            clicks=data.get("clicks"),
            regions=data.get("regions", []),
            services=data.get("services", []),
            documents=data.get("documents", []),
        )


class BDEWVNBDigitalEnricher:
    """Enriches BDEW data with vnbdigital.de information."""

    def __init__(self):
        """Initialize the enricher."""
        self.session: httpx.AsyncClient | None = None
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

    async def fetch_vnbdigital_data(self, bdew_code: str) -> VNBDigitalData | None:
        """
        Fetch operator data from vnbdigital.de GraphQL API.

        Args:
            bdew_code: BDEW operator code

        Returns:
            VNBDigitalData if found, None otherwise
        """
        if not self.session:
            raise RuntimeError("Session not initialized")

        payload = {"query": VNBDIGITAL_QUERY, "variables": {"id": bdew_code}}

        try:
            response = await self.session.post(VNBDIGITAL_GRAPHQL_URL, json=payload)
            response.raise_for_status()

            data = response.json()

            if "errors" in data:
                logger.warning(
                    f"GraphQL errors for BDEW code {bdew_code}: {data['errors']}"
                )
                return None

            vnb_data = data.get("data", {}).get("vnb_vnb")

            if vnb_data is None:
                logger.debug(f"No vnbdigital.de data found for BDEW code {bdew_code}")
                return None

            return VNBDigitalData.from_api_response(vnb_data)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching vnbdigital.de data for {bdew_code}: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error fetching vnbdigital.de data for {bdew_code}: {e}"
            )
            return None

    def load_bdew_data(self) -> list[dict[str, Any]]:
        """Load BDEW grid operators data."""
        if not BDEW_DATA_FILE.exists():
            raise FileNotFoundError(f"BDEW data file not found: {BDEW_DATA_FILE}")

        with BDEW_DATA_FILE.open(encoding="utf-8") as f:
            data = json.load(f)

        return data.get("operators", [])

    def truncate_name(self, name: str, max_length: int = 40) -> str:
        """Truncate company name to specified length with ellipsis if needed."""
        if len(name) <= max_length:
            return name
        return name[: max_length - 3] + "..."

    async def enrich_operators(self) -> list[dict[str, Any]]:
        """
        Enrich all BDEW operators with vnbdigital.de data.

        Returns:
            List of enriched operator data
        """
        logger.info("Loading BDEW operators data...")
        bdew_operators = self.load_bdew_data()
        logger.info(f"Loaded {len(bdew_operators)} BDEW operators")

        enriched_operators = []
        found_count = 0

        for i, operator in enumerate(bdew_operators, 1):
            bdew_code = operator.get("bdew_code")
            company_name = operator.get("company_name", "Unknown")
            display_name = self.truncate_name(company_name)

            # Start with BDEW data
            enriched_operator = operator.copy()
            enriched_operator["vnbdigital_data"] = None
            enriched_operator["enrichment_status"] = "not_found"
            enriched_operator["enrichment_timestamp"] = datetime.now().isoformat()

            if bdew_code:
                vnb_data = await self.fetch_vnbdigital_data(bdew_code)

                if vnb_data:
                    found_count += 1
                    logger.info(
                        f"✅ Found [{i}/{len(bdew_operators)}] {display_name} (BDEW: {bdew_code})"
                    )

                    enriched_operator["vnbdigital_data"] = vnb_data.model_dump()
                    enriched_operator["enrichment_status"] = "found"

                    # Add comparison fields
                    enriched_operator["name_comparison"] = {
                        "bdew_name": company_name,
                        "vnbdigital_name": vnb_data.name,
                        "names_match": (
                            company_name.lower() == vnb_data.name.lower()
                            if vnb_data.name
                            else False
                        ),
                    }
                else:
                    # Log all not found entries for consistency
                    logger.info(
                        f"❌ Not found [{i}/{len(bdew_operators)}] {display_name} (BDEW: {bdew_code})"
                    )
            elif i % 50 == 0:
                # No BDEW code provided
                logger.info(
                    f"⚠️  No BDEW code [{i}/{len(bdew_operators)}] {display_name}"
                )

            enriched_operators.append(enriched_operator)

            # Rate limiting - be respectful to the API
            await asyncio.sleep(0.1)

        logger.info(
            f"Enrichment complete: {found_count}/{len(bdew_operators)} operators found in vnbdigital.de"
        )
        return enriched_operators

    def save_enriched_data(self, enriched_operators: list[dict[str, Any]]) -> None:
        """Save enriched data to JSON and CSV files."""

        # Save JSON
        enriched_data = {
            "metadata": {
                "total_operators": len(enriched_operators),
                "enriched_operators": len(
                    [
                        op
                        for op in enriched_operators
                        if op["enrichment_status"] == "found"
                    ]
                ),
                "enrichment_timestamp": datetime.now().isoformat(),
                "source_bdew_file": str(BDEW_DATA_FILE),
                "vnbdigital_api_url": VNBDIGITAL_GRAPHQL_URL,
            },
            "operators": enriched_operators,
        }

        with Path(OUTPUT_FILE).open("w", encoding="utf-8") as f:
            json.dump(enriched_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved enriched JSON data to {OUTPUT_FILE}")

        # Save CSV with flattened data
        csv_data = []
        for operator in enriched_operators:
            row = {
                "bdew_code": operator.get("bdew_code"),
                "bdew_company_name": operator.get("company_name"),
                "bdew_city": operator.get("city"),
                "enrichment_status": operator.get("enrichment_status"),
                "vnbdigital_name": None,
                "vnbdigital_address": None,
                "vnbdigital_postcode": None,
                "vnbdigital_city": None,
                "vnbdigital_phone": None,
                "vnbdigital_contact": None,
                "vnbdigital_website": None,
                "vnbdigital_types": None,
                "names_match": None,
            }

            vnb_data = operator.get("vnbdigital_data")
            if vnb_data:
                row.update(
                    {
                        "vnbdigital_name": vnb_data.get("name"),
                        "vnbdigital_address": vnb_data.get("address"),
                        "vnbdigital_postcode": vnb_data.get("postcode"),
                        "vnbdigital_city": vnb_data.get("city"),
                        "vnbdigital_phone": vnb_data.get("phone"),
                        "vnbdigital_contact": vnb_data.get("contact"),
                        "vnbdigital_website": vnb_data.get("website"),
                        "vnbdigital_types": "|".join(vnb_data.get("types", [])),
                    }
                )

            name_comp = operator.get("name_comparison", {})
            row["names_match"] = name_comp.get("names_match")

            csv_data.append(row)

        df = pd.DataFrame(csv_data)
        df.to_csv(CSV_OUTPUT_FILE, index=False, encoding="utf-8")
        logger.info(f"Saved enriched CSV data to {CSV_OUTPUT_FILE}")


async def main():
    """Main function."""
    logger.info("🚀 Starting BDEW data enrichment with vnbdigital.de")

    try:
        async with BDEWVNBDigitalEnricher() as enricher:
            enriched_operators = await enricher.enrich_operators()
            enricher.save_enriched_data(enriched_operators)

        logger.info("✅ BDEW data enrichment completed successfully")

    except Exception as e:
        logger.error(f"❌ Error during enrichment: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
