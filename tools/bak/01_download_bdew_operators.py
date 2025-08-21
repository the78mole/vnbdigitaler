#!/usr/bin/env python3
"""
BDEW Electricity Grid Operator Downloader

This script downloads the complete list of German electricity grid operators
from the BDEW (Bundesverband der Energie- und Wasserwirtschaft) database.

The data is retrieved from the official AJAX endpoint:
https://bdew-codes.de/Codenumbers/ElectricityGridOperatorCodes/GetElectricityList

Each operator has:
- BDEW Code (unique identifier)
- Company name
- Valid from date
- Valid until date (if inactive)

Usage:
    uv run python tools/01_download_bdew_operators.py [--output-file PATH] [--verbose] [--dry-run]
"""

import argparse
import asyncio
import json
import logging
import re
import sys
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    import httpx
    import pandas as pd
except ImportError as e:
    print(f"❌ Required packages not installed: {e}")
    print("Run: uv add httpx pandas")
    sys.exit(1)

# Constants
BDEW_BASE_URL = "https://bdew-codes.de"
BDEW_AJAX_ENDPOINT = (
    "https://bdew-codes.de/Codenumbers/ElectricityGridOperatorCodes/GetElectricityList"
)
USER_AGENT = "vnbdigitaler/1.0 (BDEW Operator Downloader; +https://github.com/the78mole/vnbdigitaler)"
REQUEST_TIMEOUT = 30
# Use relative path from script location to project data directory
SCRIPT_DIR = Path(__file__).parent
PROJECT_DATA_DIR = SCRIPT_DIR.parent / "data"
DEFAULT_OUTPUT_FILE = PROJECT_DATA_DIR / "bdew_grid_operators.json"
PAGE_SIZE = 100  # Records per request
SAFETY_LIMIT = 1000  # Maximum pages to prevent infinite loops


class BDEWOperatorDownloader:
    """Downloads BDEW electricity grid operator data via AJAX API."""

    def __init__(self, verbose: bool = False, dry_run: bool = False):
        self.verbose = verbose
        self.dry_run = dry_run

        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.logger = logging.getLogger(__name__)

        # HTTP client
        self.client = None

        # Data storage
        self.all_operators = []
        self.stats = {
            "total_downloaded": 0,
            "active_operators": 0,
            "inactive_operators": 0,
            "pages_fetched": 0,
            "errors": 0,
        }

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def fetch_operators_page(
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
        params = {
            "jtStartIndex": start_index,
            "jtPageSize": page_size,
        }

        if self.dry_run:
            self.logger.info(f"DRY RUN: Would fetch page starting at {start_index}")
            # Return mock data for dry run
            return {
                "Result": "OK",
                "Records": [
                    {
                        "Code": f"990000000000{i}",
                        "Name": f"Test Operator {i}",
                        "ValidFrom": "01.01.2020",
                        "ValidUntil": "" if i % 3 != 0 else "31.12.2023",
                    }
                    for i in range(1, min(4, page_size + 1))
                ],
                "TotalRecordCount": 3 if start_index == 0 else 0,
            }

        try:
            self.logger.debug(
                f"Fetching operators page: start={start_index}, size={page_size}"
            )

            # JTable uses POST requests with form data
            response = await self.client.post(
                BDEW_AJAX_ENDPOINT,
                data=params,  # Send as form data instead of query params
                headers={
                    "Accept": "application/json, text/javascript, */*; q=0.01",
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                    "Referer": "https://bdew-codes.de/Codenumbers/ElectricityGridOperatorCodes/ElectricityGridCodeNumbers",
                },
            )

            response.raise_for_status()

            # Parse JSON response
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
            self.logger.info(
                f"✅ Fetched {len(records)} operators from page {start_index // page_size + 1}"
            )

            return data

        except httpx.RequestError as e:
            self.logger.error(f"Network error fetching page {start_index}: {e}")
            self.stats["errors"] += 1
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response for page {start_index}: {e}")
            self.stats["errors"] += 1
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error fetching page {start_index}: {e}")
            self.stats["errors"] += 1
            raise

    async def download_all_operators(self) -> list[dict[str, Any]]:
        """
        Download all operators by paginating through the API.

        Returns:
            List of all operator records
        """
        self.logger.info("🚀 Starting BDEW operator download...")

        all_operators = []
        start_index = 0

        while True:
            try:
                # Fetch one page
                page_data = await self.fetch_operators_page(start_index, PAGE_SIZE)
                records = page_data.get("Records", [])
                total_count = page_data.get("TotalRecordCount", 0)

                # Add records to our collection
                all_operators.extend(records)
                self.stats["pages_fetched"] += 1

                self.logger.info(
                    f"📄 Page {self.stats['pages_fetched']}: "
                    f"Downloaded {len(records)} operators "
                    f"(Total: {len(all_operators)}/{total_count})"
                )

                # Check if we have all records
                if len(all_operators) >= total_count or len(records) < PAGE_SIZE:
                    self.logger.info(
                        f"✅ Download complete: {len(all_operators)} operators"
                    )
                    break

                # Move to next page
                start_index += PAGE_SIZE

                # Safety check to prevent infinite loops
                if self.stats["pages_fetched"] > SAFETY_LIMIT:
                    self.logger.warning(
                        "⚠️ Safety limit reached: stopping after 1000 pages"
                    )
                    break

            except Exception as e:
                self.logger.error(
                    f"❌ Failed to fetch page starting at {start_index}: {e}"
                )

                # If we have some data, continue with what we have
                if all_operators:
                    self.logger.warning(
                        f"⚠️ Continuing with {len(all_operators)} operators downloaded so far"
                    )
                    break
                else:
                    # No data at all, re-raise the error
                    raise

        # Deduplicate operators based on BDEW code only
        initial_count = len(all_operators)
        seen_codes = set()
        deduplicated_operators = []

        for operator in all_operators:
            bdew_code = str(operator.get("Number", "")).strip()

            if bdew_code not in seen_codes:
                seen_codes.add(bdew_code)
                deduplicated_operators.append(operator)
            else:
                self.logger.warning(
                    f"🔄 Duplicate BDEW code found: {bdew_code} - {operator.get('Company', 'N/A')}"
                )

        duplicates_removed = initial_count - len(deduplicated_operators)
        if duplicates_removed > 0:
            self.logger.info(
                f"✂️ Removed {duplicates_removed} duplicate entries (kept {len(deduplicated_operators)} unique operators)"
            )
        else:
            self.logger.info(
                f"✅ No duplicates found - all {len(deduplicated_operators)} operators have unique BDEW codes"
            )

        all_operators = deduplicated_operators

        self.stats["total_downloaded"] = len(all_operators)
        self.stats["duplicates_removed"] = duplicates_removed
        return all_operators

    def normalize_operator_data(
        self, operators: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Normalize and enrich the operator data.

        Args:
            operators: Raw operator data from API

        Returns:
            Normalized operator data
        """
        self.logger.info("🔧 Normalizing operator data...")

        normalized = []

        for i, op in enumerate(operators):
            try:
                # Extract basic fields
                code = str(op.get("Number", "")).strip()  # BDEW uses "Number" field
                name = str(op.get("Company", "")).strip()  # BDEW uses "Company" field
                city = str(op.get("City", "")).strip()  # Additional city field
                valid_from_str = str(op.get("ValidFrom", "")).strip()
                valid_until_str = str(op.get("ValidUntil", "")).strip()

                # Skip invalid records
                if not code or not name:
                    self.logger.warning(
                        f"Skipping invalid operator at index {i}: missing code or name"
                    )
                    continue

                # Parse dates
                valid_from_date = self.parse_german_date(valid_from_str)
                valid_until_date = (
                    self.parse_german_date(valid_until_str) if valid_until_str else None
                )

                # Determine if operator is active
                current_date = datetime.now().date()
                is_active = True

                if valid_until_date and valid_until_date < current_date:
                    is_active = False
                    self.stats["inactive_operators"] += 1
                else:
                    self.stats["active_operators"] += 1

                # Create normalized record
                # Clean original name too (remove surrounding quotes)
                clean_name = name.strip().strip('"').strip("'") if name else ""
                normalized_op = {
                    "bdew_code": code,
                    "company_name": clean_name,
                    "company_name_normalized": self.normalize_company_name(name),
                    "city": city,
                    "valid_from": valid_from_str,
                    "valid_until": valid_until_str,
                    "valid_from_date": valid_from_date.isoformat()
                    if valid_from_date
                    else None,
                    "valid_until_date": valid_until_date.isoformat()
                    if valid_until_date
                    else None,
                    "is_active": is_active,
                    "downloaded_at": datetime.now().isoformat(),
                    "source_index": i,
                }

                normalized.append(normalized_op)

            except Exception as e:
                self.logger.warning(f"Error normalizing operator at index {i}: {e}")
                self.stats["errors"] += 1
                continue

        self.logger.info(f"✅ Normalized {len(normalized)} operators")
        return normalized

    def parse_german_date(self, date_str: str) -> date | None:
        """
        Parse German date string (DD.MM.YYYY) to date object.

        Args:
            date_str: Date string in format DD.MM.YYYY

        Returns:
            date object or None if parsing fails
        """
        if not date_str or date_str.lower() in ["", "-", "n/a", "null"]:
            return None

        # Try different date formats
        date_formats = [
            "%d.%m.%Y",  # DD.MM.YYYY
            "%d/%m/%Y",  # DD/MM/YYYY
            "%Y-%m-%d",  # YYYY-MM-DD
            "%d.%m.%y",  # DD.MM.YY
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        self.logger.warning(f"Could not parse date: '{date_str}'")
        return None

    def normalize_company_name(self, name: str) -> str:
        """
        Normalize company name for better matching.

        Args:
            name: Original company name

        Returns:
            Normalized company name
        """
        if not name:
            return ""

        # Basic normalization - remove surrounding quotes first
        normalized = name.strip().strip('"').strip("'")

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Standardize common abbreviations
        replacements = [
            (r"\bGmbH\s*&\s*Co\.\s*KG\b", "GmbH & Co. KG"),
            (r"\bGmbH\s*&\s*Co\s*KG\b", "GmbH & Co. KG"),
            (r"\bAktiengesellschaft\b", "AG"),
            (r"\bGesellschaft\s+mit\s+beschränkter\s+Haftung\b", "GmbH"),
        ]

        for pattern, replacement in replacements:
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        return normalized.strip()

    async def save_results(
        self, operators: list[dict[str, Any]], output_file: Path
    ) -> None:
        """
        Save operator data to JSON file.

        Args:
            operators: Processed operator data
            output_file: Output file path
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Prepare result data
        result_data = {
            "metadata": {
                "download_timestamp": datetime.now().isoformat(),
                "source_url": BDEW_AJAX_ENDPOINT,
                "script_version": "1.0",
                "dry_run": self.dry_run,
                "total_operators": len(operators),
                "active_operators": self.stats["active_operators"],
                "inactive_operators": self.stats["inactive_operators"],
                "pages_fetched": self.stats["pages_fetched"],
                "errors_encountered": self.stats["errors"],
                "duplicates_removed": self.stats.get("duplicates_removed", 0),
            },
            "operators": operators,
        }

        if self.dry_run:
            self.logger.info(
                f"DRY RUN: Would save {len(operators)} operators to {output_file}"
            )
            return

        # Save to JSON file
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"💾 Results saved to: {output_file}")

        # Also create a simple CSV for easy viewing
        csv_file = output_file.with_suffix(".csv")
        df = pd.DataFrame(operators)
        df.to_csv(csv_file, index=False, encoding="utf-8")
        self.logger.info(f"📊 CSV version saved to: {csv_file}")

    def print_summary(self, operators: list[dict[str, Any]]) -> None:
        """Print download summary."""
        active_count = sum(1 for op in operators if op.get("is_active", True))
        inactive_count = len(operators) - active_count

        print("\n📊 BDEW Operator Download Summary:")
        print(f"🏢 Total operators: {len(operators)}")
        print(f"✅ Active operators: {active_count}")
        print(f"❌ Inactive operators: {inactive_count}")
        print(f"📄 Pages fetched: {self.stats['pages_fetched']}")
        print(f"⚠️ Errors encountered: {self.stats['errors']}")

        if operators:
            print("\n📋 Sample operators:")
            for i, op in enumerate(operators[:5], 1):
                status = "🟢" if op.get("is_active") else "🔴"
                print(f"  {i}. {op['bdew_code']} - {op['company_name']} {status}")

        print("\n💡 Use this data to:")
        print("   - Validate company names in Roll-Out reports")
        print("   - Create company lookup tables")
        print("   - Identify missing or incorrect operator codes")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Download BDEW electricity grid operator data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all operators to default file
  uv run python tools/01_download_bdew_operators.py

  # Download with verbose logging
  uv run python tools/01_download_bdew_operators.py --verbose

  # Test without downloading
  uv run python tools/01_download_bdew_operators.py --dry-run --verbose

  # Save to custom location
  uv run python tools/01_download_bdew_operators.py --output-file tmp/operators.json
        """,
    )

    parser.add_argument(
        "--output-file",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help=f"Output JSON file path (default: {DEFAULT_OUTPUT_FILE})",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate download without making actual requests",
    )

    args = parser.parse_args()

    try:
        async with BDEWOperatorDownloader(
            verbose=args.verbose,
            dry_run=args.dry_run,
        ) as downloader:
            # Download operators
            raw_operators = await downloader.download_all_operators()

            # Normalize data
            operators = downloader.normalize_operator_data(raw_operators)

            # Save results
            await downloader.save_results(operators, args.output_file)

            # Print summary
            downloader.print_summary(operators)

            print("\n✅ BDEW operator download completed successfully!")

    except KeyboardInterrupt:
        print("\n❌ Download cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
