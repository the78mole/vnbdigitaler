#!/usr/bin/env python3
"""
Test script for VNBdigitaler WebUI API endpoints.
"""

import asyncio
import traceback

from sqlalchemy import select

from src.data_loader import DataLoader
from src.models import Company


async def test_companies_query():
    """Test the companies query directly."""
    print("Testing companies database query...")

    data_loader = DataLoader()

    try:
        async with data_loader.session_factory() as session:
            # Test the basic query
            query = select(Company).limit(3)
            result = await session.execute(query)
            companies = result.scalars().all()

            print(f"Found {len(companies)} companies")

            # Test accessing company attributes
            for i, company in enumerate(companies, 1):
                print(f"\nCompany {i}:")
                print(f"  ID: {company.id}")
                print(f"  BDEW Code: {company.bdew_code}")
                print(f"  BDEW Name: {company.bdew_name}")
                print(f"  BDEW City: {company.bdew_city}")
                print(f"  Rollout Name: {company.rollout_report_name}")
                print(f"  Rollout Variations: {company.rollout_name_variations}")
                print(f"  Manual Verification: {company.manual_verification}")
                print(f"  Has GeoJSON: {bool(company.network_territory_geojson)}")

                # Test creating the response data like in the API
                company_data = {
                    "id": company.id,
                    "bdew_code": company.bdew_code,
                    "bdew_name": company.bdew_name,
                    "bdew_city": company.bdew_city,
                    "rollout_report_name": company.rollout_report_name,
                    "rollout_name_variations": company.rollout_name_variations or [],
                    "manual_verification": company.manual_verification or False,
                    "has_service_area": bool(company.network_territory_geojson),
                }
                print(f"  API Data: {company_data}")

    except Exception as e:
        print(f"Database error: {e}")
        traceback.print_exc()


async def test_single_company():
    """Test getting a single company by ID."""
    print("\nTesting single company query...")

    data_loader = DataLoader()

    try:
        async with data_loader.session_factory() as session:
            # Get first company ID
            result = await session.execute(select(Company.id).limit(1))
            company_id = result.scalar_one()

            print(f"Testing with company ID: {company_id}")

            # Test single company query
            result = await session.execute(
                select(Company).where(Company.id == company_id)
            )
            company = result.scalar_one_or_none()

            if company:
                print(f"Successfully retrieved company: {company.bdew_name}")
                print(
                    f"All attributes accessible: {bool(company.id and company.bdew_code)}"
                )
            else:
                print("Company not found")

    except Exception as e:
        print(f"Single company test error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_companies_query())
    asyncio.run(test_single_company())
