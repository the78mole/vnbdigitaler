"""
BDEW Web Data Source - Downloads operator data from BDEW website.

Automatischer Download von BDEW-Netzbetreiberdaten über die offizielle API.
"""

import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError as e:
    raise ImportError(
        "httpx is required for BDEW web downloads. Run: uv add httpx"
    ) from e

from .base import DataSource, DataSourceError, DataSourceMetadata

logger = logging.getLogger(__name__)


class BDEWWebDataSource(DataSource):
    """
    BDEW Web Data Source für automatischen Download von Netzbetreiberdaten.

    Lädt aktuelle BDEW-Daten direkt von der offiziellen Website über die
    AJAX-API und normalisiert sie für die weitere Verarbeitung.
    """

    # Constants from the working implementation
    BDEW_AJAX_ENDPOINT = "https://bdew-codes.de/Codenumbers/ElectricityGridOperatorCodes/GetElectricityList"
    USER_AGENT = "vnbdigitaler/1.0 (BDEW Operator Downloader; +https://github.com/the78mole/vnbdigitaler)"
    REQUEST_TIMEOUT = 30
    PAGE_SIZE = 100
    SAFETY_LIMIT = 1000

    # Quality scoring constants
    MIN_CODE_LENGTH = 3
    MIN_NAME_LENGTH = 5
    MIN_CITY_LENGTH = 3
    MIN_NAME_WORDS = 2

    def __init__(self, cache_dir: Path | None = None):
        """
        Initialize BDEW Web Data Source.

        Args:
            cache_dir: Directory to cache downloaded data (optional)
        """
        super().__init__(name="BDEW Web API")
        self.cache_dir = cache_dir or Path("data/cache/bdew")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.client: httpx.AsyncClient | None = None
        self.stats = {
            "total_downloaded": 0,
            "active_operators": 0,
            "inactive_operators": 0,
            "pages_fetched": 0,
            "errors": 0,
            "duplicates_removed": 0,
        }

    async def connect(self) -> bool:
        """Initialize HTTP client."""
        try:
            if not self.client:
                self.client = httpx.AsyncClient(
                    headers={"User-Agent": self.USER_AGENT},
                    timeout=self.REQUEST_TIMEOUT,
                    follow_redirects=True,
                )
            logger.info("🌐 Connected to BDEW web data source")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to BDEW API: {e}")
            return False

    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
            self.client = None
        logger.info("🔌 Disconnected from BDEW web data source")

    async def check_for_updates(self) -> bool:
        """
        Check if new data is available.

        Returns:
            True if updates are available
        """
        # For BDEW data, we assume updates are always possible
        return True

    async def fetch_data(self) -> list[dict[str, Any]]:
        """
        Download all BDEW operators from the official API.

        Returns:
            List of normalized operator records
        """
        logger.info("🚀 Starting BDEW operator download...")

        if not self.client:
            raise DataSourceError("Client not connected. Call connect() first.")

        try:
            # Download all operators
            raw_operators = await self._download_all_operators()

            # Normalize data
            normalized_operators = self._normalize_operator_data(raw_operators)

            # Update metadata
            self._metadata = DataSourceMetadata(
                source_name="BDEW Web API",
                last_updated=datetime.now(),
                record_count=len(normalized_operators),
                version=f"{date.today().isoformat()}",
            )

            logger.info(
                f"✅ Successfully downloaded {len(normalized_operators)} BDEW operators"
            )
            return normalized_operators

        except Exception as e:
            raise DataSourceError(f"Failed to download BDEW data: {e}") from e

    async def validate_data(self, data: list[dict[str, Any]]) -> bool:
        """
        Validate downloaded BDEW data.

        Args:
            data: List of operator dictionaries

        Returns:
            True if data is valid
        """
        if not data:
            logger.warning("No BDEW data to validate")
            return False

        # Check required fields
        required_fields = ["bdew_code", "company_name", "valid_from"]

        for i, operator in enumerate(data[:5]):  # Sample first 5 records
            missing_fields = [
                field for field in required_fields if not operator.get(field)
            ]
            if missing_fields:
                logger.error(f"Operator {i} missing required fields: {missing_fields}")
                return False

        logger.info(f"✅ BDEW data validation passed for {len(data)} operators")
        return True

    async def _fetch_operators_page(
        self, start_index: int, page_size: int
    ) -> dict[str, Any]:
        """
        Fetch a page of operators from the BDEW AJAX endpoint.

        Args:
            start_index: Starting index for pagination
            page_size: Number of records to fetch

        Returns:
            API response as dictionary
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")

        params = {
            "jtStartIndex": start_index,
            "jtPageSize": page_size,
        }

        try:
            logger.debug(
                f"Fetching operators page: start={start_index}, size={page_size}"
            )

            # JTable uses POST requests with form data
            response = await self.client.post(
                self.BDEW_AJAX_ENDPOINT,
                data=params,
                headers={
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Referer": "https://bdew-codes.de/Codenumbers/ElectricityGridOperatorCodes/ElectricityGridCodeNumbers",
                },
            )

            response.raise_for_status()
            data = response.json()

            # Validate response structure
            if not isinstance(data, dict):
                raise ValueError(f"Expected dict response, got {type(data)}")

            if data.get("Result") != "OK":
                raise ValueError(
                    f"API returned error: {data.get('Message', 'Unknown error')}"
                )

            if "Records" not in data:
                raise ValueError("Response missing 'Records' field")

            records = data["Records"]
            logger.debug(
                f"✅ Fetched {len(records)} operators from page {start_index // page_size + 1}"
            )

            return data

        except httpx.RequestError as e:
            logger.error(f"Network error fetching page {start_index}: {e}")
            self.stats["errors"] += 1
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response for page {start_index}: {e}")
            self.stats["errors"] += 1
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching page {start_index}: {e}")
            self.stats["errors"] += 1
            raise

    async def _download_all_operators(self) -> list[dict[str, Any]]:
        """
        Download all operators by paginating through the API.

        Returns:
            List of all operator records
        """
        all_operators = []
        start_index = 0

        while True:
            try:
                # Fetch one page
                page_data = await self._fetch_operators_page(
                    start_index, self.PAGE_SIZE
                )
                records = page_data.get("Records", [])
                total_count = page_data.get("TotalRecordCount", 0)

                # Add records to our collection
                all_operators.extend(records)
                self.stats["pages_fetched"] += 1

                logger.info(
                    f"📄 Page {self.stats['pages_fetched']}: "
                    f"Downloaded {len(records)} operators "
                    f"(Total: {len(all_operators)}/{total_count})"
                )

                # Check if we have all records
                if len(all_operators) >= total_count or len(records) < self.PAGE_SIZE:
                    logger.info(f"✅ Download complete: {len(all_operators)} operators")
                    break

                # Move to next page
                start_index += self.PAGE_SIZE

                # Safety check to prevent infinite loops
                if self.stats["pages_fetched"] > self.SAFETY_LIMIT:
                    logger.warning("⚠️ Safety limit reached: stopping after 1000 pages")
                    break

            except Exception as e:
                logger.error(f"❌ Failed to fetch page starting at {start_index}: {e}")

                # If we have some data, continue with what we have
                if all_operators:
                    logger.warning(
                        f"⚠️ Continuing with {len(all_operators)} operators downloaded so far"
                    )
                    break
                else:
                    # No data at all, re-raise the error
                    raise

        # Deduplicate operators based on BDEW code
        initial_count = len(all_operators)
        seen_codes = set()
        deduplicated_operators = []

        for operator in all_operators:
            bdew_code = str(operator.get("Number", "")).strip()

            if bdew_code not in seen_codes:
                seen_codes.add(bdew_code)
                deduplicated_operators.append(operator)
            else:
                logger.warning(f"🔄 Duplicate BDEW code found: {bdew_code}")

        duplicates_removed = initial_count - len(deduplicated_operators)
        if duplicates_removed > 0:
            logger.info(f"✂️ Removed {duplicates_removed} duplicate entries")

        self.stats["total_downloaded"] = len(deduplicated_operators)
        self.stats["duplicates_removed"] = duplicates_removed

        return deduplicated_operators

    def _normalize_operator_data(
        self, operators: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Normalize and enrich the operator data.

        Args:
            operators: Raw operator data from API

        Returns:
            Normalized operator data
        """
        logger.info("🔧 Normalizing operator data...")

        normalized = []

        for i, op in enumerate(operators):
            try:
                # Extract basic fields (BDEW API field names)
                code = str(op.get("Number", "")).strip()
                name = str(op.get("Company", "")).strip()
                city = str(op.get("City", "")).strip()
                valid_from_str = str(op.get("ValidFrom", "")).strip()
                valid_until_str = str(op.get("ValidUntil", "")).strip()

                # Skip invalid records
                if not code or not name:
                    logger.warning(
                        f"Skipping invalid operator at index {i}: missing code or name"
                    )
                    continue

                # Parse dates
                valid_from_date = self._parse_german_date(valid_from_str)
                valid_until_date = (
                    self._parse_german_date(valid_until_str)
                    if valid_until_str
                    else None
                )

                # Determine if operator is active
                current_date = datetime.now().date()
                is_active = True

                if valid_until_date and valid_until_date < current_date:
                    is_active = False

                # Calculate data quality score
                quality_score = self._calculate_quality_score(
                    code, name, city, valid_from_date
                )

                # Create normalized record
                normalized_operator = {
                    "bdew_code": code,
                    "company_name": name,
                    "city": city,
                    "valid_from": (
                        valid_from_date.isoformat() if valid_from_date else None
                    ),
                    "valid_until": (
                        valid_until_date.isoformat() if valid_until_date else None
                    ),
                    "is_active": is_active,
                    "data_quality_score": quality_score,
                    "import_timestamp": datetime.now().isoformat(),
                    "data_source": "BDEW Web API",
                    "raw_data": op,  # Keep original for debugging
                }

                normalized.append(normalized_operator)

                # Update stats
                if is_active:
                    self.stats["active_operators"] += 1
                else:
                    self.stats["inactive_operators"] += 1

            except Exception as e:
                logger.warning(f"Failed to normalize operator at index {i}: {e}")
                continue

        logger.info(
            f"✅ Normalized {len(normalized)} operators "
            f"({self.stats['active_operators']} active, {self.stats['inactive_operators']} inactive)"
        )

        return normalized

    def _parse_german_date(self, date_str: str) -> date | None:
        """
        Parse German date format (DD.MM.YYYY) to Python date.

        Args:
            date_str: Date string in German format

        Returns:
            Parsed date or None if invalid
        """
        if not date_str or date_str.strip() == "":
            return None

        try:
            # Remove any whitespace and try to match DD.MM.YYYY format
            clean_date = date_str.strip()
            match = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", clean_date)

            if match:
                day, month, year = map(int, match.groups())
                return date(year, month, day)
            else:
                logger.warning(f"Invalid date format: '{date_str}'")
                return None

        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None

    def _calculate_quality_score(
        self, code: str, name: str, city: str, valid_from: date | None
    ) -> float:
        """
        Calculate data quality score for an operator.

        Args:
            code: BDEW code
            name: Company name
            city: City name
            valid_from: Valid from date

        Returns:
            Quality score between 0.0 and 100.0
        """
        score = 0.0

        # BDEW code quality (30 points)
        if code and len(code) >= self.MIN_CODE_LENGTH:
            score += 30.0

        # Company name quality (40 points)
        if name:
            if len(name) >= self.MIN_NAME_LENGTH:
                score += 20.0
            if not any(char in name.lower() for char in ["test", "dummy", "example"]):
                score += 10.0
            if (
                len(name.split()) >= self.MIN_NAME_WORDS
            ):  # Multi-word company names are usually better
                score += 10.0

        # City information (20 points)
        if city and len(city) >= self.MIN_CITY_LENGTH:
            score += 20.0

        # Valid from date (10 points)
        if valid_from:
            score += 10.0

        return round(score, 1)

    def get_download_stats(self) -> dict[str, Any]:
        """
        Get download statistics.

        Returns:
            Dictionary with download statistics
        """
        return self.stats.copy()
