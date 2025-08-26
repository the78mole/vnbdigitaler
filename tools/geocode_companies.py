#!/usr/bin/env python3
"""
Geocoding Tool - Company Address to Geolocation

This script geocodes company addresses using Nominatim (OpenStreetMap) service
and updates the company_latitude and company_longitude columns in the database.

Features:
- Uses geopy with Nominatim geocoding service
- Respects rate limits (1 request per second)
- Handles errors gracefully with retry logic
- Provides detailed progress tracking
- Supports dry-run mode for testing
- Filters companies by various criteria
- Caches results to avoid duplicate requests

Usage:
    python tools/geocode_companies.py --help
    python tools/geocode_companies.py --dry-run
    python tools/geocode_companies.py --limit 10
    python tools/geocode_companies.py --force-update
    python tools/geocode_companies.py --check-all
    python tools/geocode_companies.py --report
"""

import argparse
import asyncio
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim, OpenCage
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_manager
from src.models import Company

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Geocoding configuration
NOMINATIM_USER_AGENT = "vnbdigitaler/1.0 (daniel@thinkmoles.de)"
OPENCAGEDATA_API_KEY = os.getenv("OPENCAGEDATA_API_KEY")
REQUEST_TIMEOUT = 10  # seconds
RATE_LIMIT_DELAY = 1.1  # seconds between requests (Nominatim policy: max 1/sec)
OPENCAGE_RATE_LIMIT_DELAY = 1.0  # OpenCage allows 1 request/second for free tier
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
COORDINATE_TOLERANCE = 0.001  # degrees (~100m tolerance for coordinate updates)

# Report formatting constants
MAX_COMPANY_NAME_LENGTH = 38
MAX_CITY_NAME_LENGTH = 18


class CompanyGeocoder:
    """Handles geocoding of company addresses with caching and retry logic."""

    def __init__(self, dry_run: bool = False):
        """Initialize the geocoder."""
        self.dry_run = dry_run

        # Primary geocoder: Nominatim (free)
        self.nominatim_geocoder = Nominatim(
            user_agent=NOMINATIM_USER_AGENT, timeout=REQUEST_TIMEOUT
        )

        # Fallback geocoder: OpenCageData (requires API key)
        self.opencage_geocoder = None
        if OPENCAGEDATA_API_KEY:
            self.opencage_geocoder = OpenCage(
                api_key=OPENCAGEDATA_API_KEY, timeout=REQUEST_TIMEOUT
            )
            print("🔑 OpenCageData API key found - fallback geocoding enabled")
        else:
            print("⚠️  No OpenCageData API key - using Nominatim only")

        self.processed_addresses = set()  # Cache for duplicate addresses
        self.stats = {
            "processed": 0,
            "skipped": 0,
            "successful": 0,
            "failed": 0,
            "cache_hits": 0,
            "nominatim_success": 0,
            "opencage_success": 0,
        }

    def _is_postfach_address(self, address: str) -> bool:
        """Check if address contains a P.O. Box (Postfach) which is not suitable for geocoding."""
        if not address:
            return False

        address_lower = address.lower().strip()
        postfach_patterns = [
            "postfach",
            "p.o. box",
            "po box",
            "p.o.box",
            "pobox",
            "schließfach",
            "postschließfach",
        ]

        # Check if address contains any postfach patterns
        return any(pattern in address_lower for pattern in postfach_patterns)

    def _build_address_string(self, company: Company) -> str:
        """Build an address string from company data with intelligent prioritization and Postfach filtering."""
        # Priority 1: VNBdigital full address (but skip if it's a Postfach)
        if company.vnbdigital_address and company.vnbdigital_city:
            if not self._is_postfach_address(company.vnbdigital_address):
                address_parts = [company.vnbdigital_address]
                if company.vnbdigital_postcode:
                    address_parts.append(
                        f"{company.vnbdigital_postcode} {company.vnbdigital_city}"
                    )
                else:
                    address_parts.append(company.vnbdigital_city)
                return ", ".join(address_parts)
            else:
                print(f"    ⚠️  Skipping Postfach address: {company.vnbdigital_address}")
                # Fall through to next priority level

        # Priority 2: VNBdigital city with postcode
        if company.vnbdigital_city:
            if company.vnbdigital_postcode:
                return (
                    f"{company.vnbdigital_postcode} {company.vnbdigital_city}, Germany"
                )
            else:
                return f"{company.vnbdigital_city}, Germany"

        # Priority 3: BDEW city data
        if company.bdew_city:
            return f"{company.bdew_city}, Germany"

        # Fallback: Company name
        if company.bdew_name:
            return f"{company.bdew_name}, Germany"

        return ""

    def _geocode_address(self, address: str) -> tuple[float, float] | None:
        """Geocode an address with retries and error handling, using Nominatim first, then OpenCage as fallback."""
        if address in self.processed_addresses:
            print(f"    🗂️  Using cached result for: {address}")
            self.stats["cache_hits"] += 1
            return None

        print(f"    🔍 Geocoding: {address}")

        # Try Nominatim first
        coords = self._try_nominatim_geocoding(address)
        if coords:
            self.stats["nominatim_success"] += 1
            self.processed_addresses.add(address)
            return coords

        # If Nominatim fails and OpenCage is available, try OpenCage
        if self.opencage_geocoder:
            print("    🔄 Nominatim failed, trying OpenCageData...")
            coords = self._try_opencage_geocoding(address)
            if coords:
                self.stats["opencage_success"] += 1
                self.processed_addresses.add(address)
                return coords

        print(f"    ❌ All geocoding services failed for: {address}")
        self.processed_addresses.add(address)
        return None

    def _try_nominatim_geocoding(self, address: str) -> tuple[float, float] | None:
        """Try geocoding with Nominatim service."""
        for attempt in range(MAX_RETRIES):
            try:
                print(f"    📍 Nominatim attempt {attempt + 1}/{MAX_RETRIES}")
                location = self.nominatim_geocoder.geocode(address)
                if location:
                    coords = (float(location.latitude), float(location.longitude))
                    print(f"    ✅ Nominatim found: {coords[0]:.6f}, {coords[1]:.6f}")
                    return coords
                else:
                    print("    ❌ Nominatim: No results found")
                    return None

            except (GeocoderTimedOut, GeocoderUnavailable) as e:
                print(f"    ⚠️  Nominatim attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    print(f"    🔄 Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    print("    ❌ Nominatim max retries exceeded")
                    return None

        return None

    def _try_opencage_geocoding(self, address: str) -> tuple[float, float] | None:
        """Try geocoding with OpenCageData service."""
        for attempt in range(MAX_RETRIES):
            try:
                print(f"    🗝️  OpenCage attempt {attempt + 1}/{MAX_RETRIES}")
                location = self.opencage_geocoder.geocode(address)
                if location:
                    coords = (float(location.latitude), float(location.longitude))
                    print(f"    ✅ OpenCage found: {coords[0]:.6f}, {coords[1]:.6f}")
                    return coords
                else:
                    print("    ❌ OpenCage: No results found")
                    return None

            except (GeocoderTimedOut, GeocoderUnavailable) as e:
                print(f"    ⚠️  OpenCage attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    print(f"    🔄 Retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    print("    ❌ OpenCage max retries exceeded")
                    return None

        return None

    async def geocode_company(
        self, company: Company, session: AsyncSession, check_all: bool = False
    ) -> bool:
        """Geocode a single company and update database."""
        print(f"\n📍 Processing: {company.bdew_name} (ID: {company.id})")

        self.stats["processed"] += 1

        # Check if already geocoded
        if company.company_latitude and company.company_longitude:
            if not check_all:
                print(
                    f"    ⏭️  Already geocoded: {company.company_latitude:.6f}, {company.company_longitude:.6f}"
                )
                self.stats["skipped"] += 1
                return True
            else:
                print("    🔍 Already geocoded, but checking for improvements...")
                print(
                    f"    📍 Current: {company.company_latitude:.6f}, {company.company_longitude:.6f}"
                )

        # Build address string
        address = self._build_address_string(company)
        if not address:
            print("    ❌ No address data available")
            self.stats["failed"] += 1
            return False

        # Geocode the address
        coords = self._geocode_address(address)

        if not coords:
            self.stats["failed"] += 1
            return False

        # For check_all mode: compare with existing coordinates
        if check_all and company.company_latitude and company.company_longitude:
            lat_diff = abs(coords[0] - float(company.company_latitude))
            lon_diff = abs(coords[1] - float(company.company_longitude))

            # If coordinates are very similar (within ~100m), skip update
            if lat_diff < COORDINATE_TOLERANCE and lon_diff < COORDINATE_TOLERANCE:
                print(
                    f"    ✅ Coordinates confirmed (diff: {lat_diff:.6f}, {lon_diff:.6f})"
                )
                self.stats["skipped"] += 1
                return True
            else:
                print(
                    f"    🔄 Updating coordinates (diff: {lat_diff:.6f}, {lon_diff:.6f})"
                )
                print(
                    f"    📍 Old: {company.company_latitude:.6f}, {company.company_longitude:.6f}"
                )
                print(f"    📍 New: {coords[0]:.6f}, {coords[1]:.6f}")

        # Update database
        if not self.dry_run:
            try:
                await session.execute(
                    update(Company)
                    .where(Company.id == company.id)
                    .values(
                        company_latitude=coords[0],
                        company_longitude=coords[1],
                    )
                )
                await session.commit()
                print("    💾 Database updated")
            except Exception as e:
                print(f"    ❌ Database error: {e}")
                await session.rollback()
                self.stats["failed"] += 1
                return False
        else:
            print("    🧪 DRY RUN - Would update database")

        self.stats["successful"] += 1

        # Respect rate limit - different delays for different services
        if self.stats["opencage_success"] > self.stats["nominatim_success"]:
            # Last success was OpenCage
            delay = OPENCAGE_RATE_LIMIT_DELAY
            print(f"    ⏳ Waiting {delay}s (OpenCage rate limit)...")
        else:
            # Last success was Nominatim or mixed
            delay = RATE_LIMIT_DELAY
            print(f"    ⏳ Waiting {delay}s (Nominatim rate limit)...")

        time.sleep(delay)

        return True

    def print_stats(self):
        """Print geocoding statistics."""
        print("\n📊 Geocoding Statistics:")
        print(f"   Processed:     {self.stats['processed']:>6}")
        print(f"   Successful:    {self.stats['successful']:>6}")
        print(f"   Skipped:       {self.stats['skipped']:>6}")
        print(f"   Failed:        {self.stats['failed']:>6}")
        print(f"   Cache hits:    {self.stats['cache_hits']:>6}")

        # Service breakdown
        if self.stats["nominatim_success"] > 0 or self.stats["opencage_success"] > 0:
            print("\n   Service Breakdown:")
            print(f"   📍 Nominatim:   {self.stats['nominatim_success']:>6}")
            if self.opencage_geocoder:
                print(f"   🗝️  OpenCage:    {self.stats['opencage_success']:>6}")

        if self.stats["processed"] > 0:
            success_rate = self.stats["successful"] / self.stats["processed"] * 100
            print(f"   Success rate:  {success_rate:>6.1f}%")


async def get_companies_to_geocode(
    session: AsyncSession,
    limit: int | None = None,
    force_update: bool = False,
    check_all: bool = False,
) -> list[Company]:
    """Get companies that need geocoding."""
    print("🔍 Finding companies to geocode...")

    if check_all:
        # Get all companies for validation
        query = select(Company).order_by(Company.id)
        print("   📊 Mode: Checking ALL companies for coordinate validation")
    elif force_update:
        # Get all companies regardless of existing coordinates
        query = select(Company).order_by(Company.id)
        print("   🔄 Mode: Force update ALL companies")
    else:
        # Get only companies without coordinates
        query = (
            select(Company)
            .where(
                (Company.company_latitude.is_(None))
                | (Company.company_longitude.is_(None))
            )
            .order_by(Company.id)
        )
        print("   📍 Mode: Only companies without coordinates")

    if limit:
        query = query.limit(limit)
        print(f"   🔢 Limit: {limit} companies")

    result = await session.execute(query)
    companies = result.scalars().all()

    print(f"   ✅ Found {len(companies)} companies to process")
    return companies


async def generate_geocoding_report(session: AsyncSession):
    """Generate a comprehensive geocoding coverage report."""
    print("📊 VNBdigitaler Geocoding Coverage Report")
    print("=" * 60)

    # Overall statistics
    total_companies = (
        await session.execute(select(func.count(Company.id)))
    ).scalar() or 0

    # Companies with complete geocoding (both lat and lon)
    fully_geocoded = (
        await session.execute(
            select(func.count(Company.id)).where(
                and_(
                    Company.company_latitude.is_not(None),
                    Company.company_longitude.is_not(None),
                )
            )
        )
    ).scalar() or 0

    # Companies with partial geocoding (only one coordinate)
    partially_geocoded = (
        await session.execute(
            select(func.count(Company.id)).where(
                and_(
                    (Company.company_latitude.is_not(None))
                    | (Company.company_longitude.is_not(None)),
                    ~and_(
                        Company.company_latitude.is_not(None),
                        Company.company_longitude.is_not(None),
                    ),
                )
            )
        )
    ).scalar() or 0

    not_geocoded = total_companies - fully_geocoded - partially_geocoded

    print("📈 OVERALL STATISTICS")
    print(f"   Total Companies:       {total_companies:>8}")
    print(
        f"   ✅ Fully Geocoded:     {fully_geocoded:>8} ({fully_geocoded/total_companies*100:>5.1f}%)"
    )
    print(
        f"   ⚠️  Partially Geocoded: {partially_geocoded:>8} ({partially_geocoded/total_companies*100:>5.1f}%)"
    )
    print(
        f"   ❌ Not Geocoded:       {not_geocoded:>8} ({not_geocoded/total_companies*100:>5.1f}%)"
    )

    # Progress visualization
    print("\n📊 PROGRESS VISUALIZATION")
    progress_bars = 50
    filled = int(fully_geocoded / total_companies * progress_bars)
    partial = int(partially_geocoded / total_companies * progress_bars)
    empty = progress_bars - filled - partial

    bar = "█" * filled + "▓" * partial + "░" * empty
    print(f"   [{bar}] {fully_geocoded/total_companies*100:.1f}%")
    print("   Legend: ██ Geocoded | ▓▓ Partial | ░░ Missing")

    # Address data quality analysis
    vnbdigital_address_count = (
        await session.execute(
            select(func.count(Company.id)).where(
                Company.vnbdigital_address.is_not(None)
            )
        )
    ).scalar() or 0

    vnbdigital_city_count = (
        await session.execute(
            select(func.count(Company.id)).where(Company.vnbdigital_city.is_not(None))
        )
    ).scalar() or 0

    bdew_city_only_count = (
        await session.execute(
            select(func.count(Company.id)).where(
                and_(Company.vnbdigital_city.is_(None), Company.bdew_city.is_not(None))
            )
        )
    ).scalar() or 0

    no_address_count = (
        await session.execute(
            select(func.count(Company.id)).where(
                and_(
                    Company.vnbdigital_address.is_(None),
                    Company.vnbdigital_city.is_(None),
                    Company.bdew_city.is_(None),
                )
            )
        )
    ).scalar() or 0

    print("\n🏠 ADDRESS DATA QUALITY")
    print(
        f"   📍 VNBdigital Address:  {vnbdigital_address_count:>8} ({vnbdigital_address_count/total_companies*100:>5.1f}%)"
    )
    print(
        f"   🏙️  VNBdigital City:    {vnbdigital_city_count:>8} ({vnbdigital_city_count/total_companies*100:>5.1f}%)"
    )
    print(
        f"   🏛️  BDEW City Only:     {bdew_city_only_count:>8} ({bdew_city_only_count/total_companies*100:>5.1f}%)"
    )
    print(
        f"   ❌ No Address Data:     {no_address_count:>8} ({no_address_count/total_companies*100:>5.1f}%)"
    )

    # Success rate by data quality
    print("\n🎯 SUCCESS RATE BY DATA QUALITY")

    # Companies with vnbdigital city data
    vnb_address_geocoded = (
        await session.execute(
            select(func.count(Company.id)).where(
                and_(
                    Company.vnbdigital_address.is_not(None),
                    Company.company_latitude.is_not(None),
                    Company.company_longitude.is_not(None),
                )
            )
        )
    ).scalar() or 0

    bdew_only_geocoded = (
        await session.execute(
            select(func.count(Company.id)).where(
                and_(
                    Company.vnbdigital_city.is_(None),
                    Company.bdew_city.is_not(None),
                    Company.company_latitude.is_not(None),
                    Company.company_longitude.is_not(None),
                )
            )
        )
    ).scalar() or 0

    if vnbdigital_address_count > 0:
        print(
            f"   📍 VNBdigital Address:  {vnb_address_geocoded}/{vnbdigital_address_count} ({vnb_address_geocoded/vnbdigital_address_count*100:>5.1f}%)"
        )

    if bdew_city_only_count > 0:
        print(
            f"   🏛️  BDEW City Only:     {bdew_only_geocoded}/{bdew_city_only_count} ({bdew_only_geocoded/bdew_city_only_count*100:>5.1f}%)"
        )

    # Work estimation
    print("\n⏱️  WORK ESTIMATION")
    remaining_work = not_geocoded
    estimated_hours = remaining_work * RATE_LIMIT_DELAY / 3600
    estimated_cost_eur = 0  # Nominatim is free

    print(f"   Companies to geocode:   {remaining_work:>6}")
    print(f"   Estimated time:         {estimated_hours:>6.1f} hours")
    print(f"   Rate limit delay:       {RATE_LIMIT_DELAY:>6.1f} seconds/request")
    print(f"   Service cost:           {estimated_cost_eur:>6} EUR (Nominatim is free)")

    # Top cities analysis
    print("\n🏙️  TOP CITIES (Not Geocoded)")

    # Find cities with most ungeocodied companies
    top_cities_result = await session.execute(
        select(
            func.coalesce(Company.vnbdigital_city, Company.bdew_city).label("city"),
            func.count(Company.id).label("count"),
        )
        .where(Company.company_latitude.is_(None))
        .where(Company.company_longitude.is_(None))
        .where(
            (Company.vnbdigital_city.is_not(None)) | (Company.bdew_city.is_not(None))
        )
        .group_by(func.coalesce(Company.vnbdigital_city, Company.bdew_city))
        .order_by(func.count(Company.id).desc())
        .limit(10)
    )

    top_cities = top_cities_result.fetchall()
    for i, row in enumerate(top_cities, 1):
        city_name = row.city or "Unknown"
        count = row.count
        print(f"   {i:>2}. {city_name:<25} {count:>3} companies")

    # Detailed entries for not geocoded companies
    print(f"\n📋 DETAILED LIST - Companies without Geocoding ({not_geocoded} entries)")
    print("-" * 100)
    print(
        f"{'BDEW-Code':<12} {'Company Name':<40} {'City':<20} {'Address Available':<15}"
    )
    print("-" * 100)

    not_geocoded_query = (
        select(Company)
        .where(
            and_(
                Company.company_latitude.is_(None), Company.company_longitude.is_(None)
            )
        )
        .order_by(Company.bdew_city, Company.bdew_name)
    )

    not_geocoded_result = await session.execute(not_geocoded_query)
    not_geocoded_companies = not_geocoded_result.scalars().all()

    for company in not_geocoded_companies:
        bdew_code = company.bdew_code or "N/A"

        # Company name with proper truncation
        company_name_raw = company.bdew_name or "N/A"
        if len(company_name_raw) > MAX_COMPANY_NAME_LENGTH:
            company_name = company_name_raw[: MAX_COMPANY_NAME_LENGTH - 3] + "..."
        else:
            company_name = company_name_raw

        # City name with proper truncation
        city_name_raw = company.vnbdigital_city or company.bdew_city or "N/A"
        if len(city_name_raw) > MAX_CITY_NAME_LENGTH:
            city = city_name_raw[: MAX_CITY_NAME_LENGTH - 3] + "..."
        else:
            city = city_name_raw

        # Check address availability
        has_vnb_address = bool(company.vnbdigital_address)
        has_vnb_city = bool(company.vnbdigital_city)

        if has_vnb_address:
            address_status = "📍 VNB Address"
        elif has_vnb_city:
            address_status = "🏙️ VNB City"
        else:
            address_status = "🏛️ BDEW Only"

        print(f"{bdew_code:<12} {company_name:<40} {city:<20} {address_status:<15}")

    print()
    print("=" * 60)
    print("🚀 Use 'python tools/geocode_companies.py' to continue geocoding")
    print("💡 Use '--city <name>' to focus on specific cities")
    print("🔍 Use '--check-all' to validate existing coordinates")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Geocode company addresses using Nominatim"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Test mode - don't update database"
    )
    parser.add_argument(
        "--limit", type=int, help="Limit number of companies to process"
    )
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Update even companies that already have coordinates",
    )
    parser.add_argument(
        "--check-all",
        action="store_true",
        help="Check and validate all existing coordinates",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate geocoding coverage report",
    )

    args = parser.parse_args()

    # Handle report mode first
    if args.report:
        db_manager = get_db_manager()
        async for session in db_manager.get_async_session():
            await generate_geocoding_report(session)
            return

    print("🗺️  VNBdigitaler Company Geocoding Tool")
    print("=" * 50)

    if args.dry_run:
        print("🧪 DRY RUN MODE - No database updates will be made")

    # Process companies
    db_manager = get_db_manager()
    geocoder = CompanyGeocoder(dry_run=args.dry_run)

    async for session in db_manager.get_async_session():
        try:
            companies = await get_companies_to_geocode(
                session, args.limit, args.force_update, args.check_all
            )

            if not companies:
                print("✅ No companies need geocoding!")
                return

            print(f"\n🚀 Starting geocoding of {len(companies)} companies...")

            for i, company in enumerate(companies, 1):
                print(f"\n🏢 Progress: {i}/{len(companies)}")
                await geocoder.geocode_company(company, session, args.check_all)

        except KeyboardInterrupt:
            print("\n⚠️  Interrupted by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            geocoder.print_stats()


if __name__ == "__main__":
    asyncio.run(main())
