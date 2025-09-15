#!/usr/bin/env python3
"""
Analyze all available market functions from BDEW API to create a normalized lookup table.
"""

import json
from collections import Counter
from pathlib import Path

import httpx

# Constants
MAX_SAMPLE_COMPANIES = 200


def analyze_market_functions():
    """Fetch all companies and their market functions to create a complete list."""
    print("🔍 Analyzing market functions from BDEW API...")

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
    }

    company_list_url = "https://bdew-codes.de/Codenumbers/BDEWCodes/GetCompanyList"
    company_details_url = (
        "https://bdew-codes.de/Codenumbers/BDEWCodes/GetBdewCodeListOfCompany"
    )

    market_functions = Counter()
    total_companies = 0
    processed_companies = 0

    with httpx.Client(timeout=30) as client:
        # Get first batch of companies to estimate total
        form_data = {"jtStartIndex": "0", "jtPageSize": "50"}
        response = client.post(company_list_url, data=form_data, headers=headers)
        result = response.json()
        companies = result.get("Records", [])
        total_companies = result.get("TotalRecordCount", 0)

        print(
            f"📊 Found {total_companies} total companies. Sampling first 200 companies..."
        )

        # Get more companies in batches to ensure we capture all market functions
        all_sample_companies = companies.copy()

        # Fetch additional batches
        for batch_start in range(50, min(1000, total_companies), 50):
            form_data = {"jtStartIndex": str(batch_start), "jtPageSize": "50"}
            response = client.post(company_list_url, data=form_data, headers=headers)
            batch_companies = response.json().get("Records", [])
            all_sample_companies.extend(batch_companies)
            if len(all_sample_companies) >= MAX_SAMPLE_COMPANIES:
                break

        sample_companies = all_sample_companies[:MAX_SAMPLE_COMPANIES]

        for i, company in enumerate(sample_companies):
            print(
                f"  Processing company {i+1}/{MAX_SAMPLE_COMPANIES}: {company.get('Company', 'Unknown')[:30]}..."
            )

            # Get BDEW codes for this company
            form_data = {"companyId": str(company["Id"]), "filter": ""}
            try:
                response = client.post(
                    company_details_url, data=form_data, headers=headers
                )
                bdew_records = response.json().get("Records", [])

                for record in bdew_records:
                    market_function = record.get("MarketFunctionName", "Unknown")
                    market_functions[market_function] += 1

                processed_companies += 1

            except Exception as e:
                print(f"    ⚠️  Error processing company {company['Id']}: {e}")

    print(f"\n📋 Market Function Analysis (from {processed_companies} companies):")
    print("=" * 70)

    # Create normalized mapping
    market_function_mapping = {}
    for i, (function_name, count) in enumerate(market_functions.most_common(), 1):
        market_function_mapping[function_name] = i
        print(f"  {i:2d}. {function_name:50s} ({count:3d} entries)")

    print(f"\n🎯 Total unique market functions found: {len(market_functions)}")

    # Generate SQL for lookup table
    print("\n📝 SQL to create market_functions lookup table:")
    print("-" * 50)

    print("CREATE TABLE IF NOT EXISTS vnb_digitaler.market_functions (")
    print("    id INTEGER PRIMARY KEY,")
    print("    name VARCHAR(100) NOT NULL UNIQUE,")
    print("    description TEXT,")
    print("    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    print(");")
    print()

    print("-- Insert market functions")
    for function_name, function_id in market_function_mapping.items():
        escaped_name = function_name.replace("'", "''")
        print(
            f"INSERT INTO vnb_digitaler.market_functions (id, name) VALUES ({function_id}, '{escaped_name}') ON CONFLICT (id) DO NOTHING;"  # nosec B608
        )

    print("\n📝 Updated bdew_code_registry schema suggestion:")
    print("-" * 50)
    print("ALTER TABLE vnb_digitaler.bdew_code_registry")
    print(
        "ADD COLUMN IF NOT EXISTS market_function_id INTEGER REFERENCES vnb_digitaler.market_functions(id);"
    )
    print()
    print("-- Remove old role_code column if desired")
    print(
        "-- ALTER TABLE vnb_digitaler.bdew_code_registry DROP COLUMN IF EXISTS role_code;"
    )

    return market_function_mapping


if __name__ == "__main__":
    mapping = analyze_market_functions()

    # Save mapping for use in workflow
    with Path("market_function_mapping.json").open("w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)

    print("\n💾 Mapping saved to market_function_mapping.json")
