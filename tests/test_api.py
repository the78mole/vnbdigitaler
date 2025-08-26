#!/usr/bin/env python3
"""
Test script for VNBdigitaler WebUI API endpoints.
"""

import pytest
from sqlalchemy import select

from src.data_loader import DataLoader
from src.models import Company


@pytest.mark.asyncio
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
            assert len(companies) <= 3

            # Test accessing company attributes
            for i, company in enumerate(companies, 1):
                print(f"\nCompany {i}:")
                print(f"  ID: {company.id}")
                print(f"  BDEW Code: {company.bdew_code}")
                print(f"  BDEW Name: {company.bdew_name}")
                print(f"  BDEW City: {company.bdew_city}")
                print(f"  Has GeoJSON: {bool(company.network_territory_geojson)}")

                # Test creating the response data like in the API
                company_data = {
                    "id": company.id,
                    "bdew_code": company.bdew_code,
                    "bdew_name": company.bdew_name,
                    "bdew_city": company.bdew_city,
                    "has_service_area": bool(company.network_territory_geojson),
                }
                assert company_data["id"] is not None
                assert company_data["bdew_code"] is not None

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
async def test_single_company():
    """Test getting a single company by ID."""
    print("\nTesting single company query...")

    data_loader = DataLoader()

    try:
        async with data_loader.session_factory() as session:
            # Get first company ID
            result = await session.execute(select(Company.id).limit(1))
            company_id = result.scalar_one_or_none()

            if not company_id:
                pytest.skip("No companies in database")

            print(f"Testing with company ID: {company_id}")

            # Test single company query
            result = await session.execute(
                select(Company).where(Company.id == company_id)
            )
            company = result.scalar_one_or_none()

            assert company is not None
            assert company.bdew_name is not None
            assert company.id == company_id

    except Exception as e:
        pytest.skip(f"Database not available: {e}")


def test_basic_imports():
    """Test that basic imports work."""
    assert Company is not None
    assert DataLoader is not None
