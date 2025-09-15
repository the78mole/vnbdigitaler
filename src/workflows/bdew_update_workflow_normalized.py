"""
Hamilton workflow for BDEW Code List with normalized market functions.

Enhanced workflow to update BDEW codes with proper type annotations and market function mapping.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import psycopg2

logger = logging.getLogger(__name__)

# Load market function mapping
MARKET_FUNCTION_MAPPING_FILE = (
    Path(__file__).parent.parent.parent / "market_function_mapping.json"
)
try:
    with MARKET_FUNCTION_MAPPING_FILE.open(encoding="utf-8") as f:
        MARKET_FUNCTION_MAPPING = json.load(f)
except FileNotFoundError:
    # Fallback mapping if file doesn't exist
    MARKET_FUNCTION_MAPPING = {
        "Einsatzverantwortlicher": 1,
        "Betreiber einer technischen Ressource": 2,
        "Bilanzkreisverantwortlicher": 3,
        "Lieferant": 4,
        "Messstellenbetreiber": 5,
        "Netzbetreiber": 6,
        "Energieserviceanbieter des Anschlussnutzers": 7,
        "Netznutzer ohne All-Inklusiv-Vertrag": 8,
        "Bilanzkoordinator": 9,
        "Übertragungsnetzbetreiber": 10,
        "Data Provider": 11,
    }


def database_config() -> dict[str, Any]:
    """Database connection configuration."""
    return {
        "host": "localhost",
        "port": "5432",
        "database": "vnb_digitaler",
        "user": "vnb_admin",
        "password": "vnb_secure_password_2024",  # pragma: allowlist secret
    }


def database_schema() -> str:
    """Database schema name."""
    return "vnb_digitaler"


def bdew_web_config() -> dict[str, Any]:
    """Web scraping configuration for BDEW."""
    return {
        "base_url": "https://bdew-codes.de",
        "company_list_url": "https://bdew-codes.de/Codenumbers/BDEWCodes/GetCompanyList",
        "company_details_url": "https://bdew-codes.de/Codenumbers/BDEWCodes/GetBdewCodeListOfCompany",
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "timeout": 30,
        "test_mode": True,  # Enable test mode for limited data fetching
        "test_page_size": 5,  # Small page size for testing
        "test_max_pages": 2,  # Limit pages for testing
        "test_max_companies": 3,  # Limit companies for details in test mode
    }


def sync_metadata() -> dict[str, Any]:
    """Initialize synchronization metadata."""
    start_time = datetime.now()
    return {
        "sync_id": f"bdew_sync_{start_time.strftime('%Y%m%d_%H%M%S')}",
        "start_time": start_time.isoformat(),
        "sync_type": "full_sync",
        "data_source": "bdew_web",
    }


def _fetch_companies(
    client: httpx.Client, headers: dict, config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch companies from BDEW API with pagination."""
    companies = []
    page_size = config.get("test_page_size", 50)
    max_pages = config.get("test_max_pages", 5)

    try:
        for page in range(max_pages):
            start_index = page * page_size

            form_data = {"jtStartIndex": str(start_index), "jtPageSize": str(page_size)}

            logger.info(
                f"Fetching companies page {page + 1}, start_index={start_index}"
            )
            response = client.post(
                config["company_list_url"], data=form_data, headers=headers
            )
            response.raise_for_status()

            result = response.json()
            page_companies = result.get("Records", [])

            if not page_companies:
                logger.info("No more companies found, stopping pagination")
                break

            companies.extend(page_companies)
            logger.info(f"Fetched {len(page_companies)} companies from page {page + 1}")

            # Check if we've reached the end
            total_records = result.get("TotalRecordCount", 0)
            if len(companies) >= total_records:
                logger.info(f"Fetched all {total_records} companies")
                break

    except Exception as e:
        logger.error(f"Error fetching companies: {e}")
        raise

    logger.info(f"Total companies fetched: {len(companies)}")
    return companies


def _fetch_company_bdew_codes(
    client: httpx.Client, headers: dict, companies: list[dict], config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Fetch BDEW codes for each company."""
    all_records = []
    max_companies = config.get("test_max_companies", len(companies))

    for i, company in enumerate(companies[:max_companies]):
        try:
            company_name = company.get("Company", "Unknown").strip().replace("\t", "")
            logger.info(
                f"Fetching BDEW codes for company {i+1}/{max_companies}: {company_name[:30]}..."
            )

            form_data = {"companyId": str(company["Id"]), "filter": ""}

            response = client.post(
                config["company_details_url"], data=form_data, headers=headers
            )
            response.raise_for_status()

            result = response.json()
            bdew_records = result.get("Records", [])

            logger.info(
                f"Found {len(bdew_records)} BDEW codes for company {company_name[:30]}"
            )

            # Process each BDEW record
            for record in bdew_records:
                market_function_name = record.get("MarketFunctionName", "")
                market_function_id = MARKET_FUNCTION_MAPPING.get(market_function_name)

                if market_function_id is None:
                    logger.warning(
                        f"Unknown market function: '{market_function_name}' - skipping record"
                    )
                    continue

                processed_record = {
                    "id": record.get("Id"),
                    "company_uid": record.get("CompanyUId"),
                    "bdew_code": record.get("BdewCode"),
                    "market_function": market_function_name,
                    "market_function_id": market_function_id,  # Normalized ID
                    "contact_name": record.get("ContactName"),
                    "company_id": company["Id"],
                    "company_name": company_name,
                    "extracted_at": datetime.now().isoformat(),
                    "source_api": "bdew_two_stage",
                    # Legacy fields for compatibility
                    "status": "ACTIVE",
                    "registration_date": "",
                    "city": "",
                    "postal_code": "",
                    "country": "",
                }

                all_records.append(processed_record)

        except Exception as e:
            logger.error(
                f"Error fetching BDEW codes for company {company.get('Id', 'Unknown')}: {e}"
            )
            continue

    logger.info(f"Total BDEW records fetched: {len(all_records)}")
    return all_records


def fetch_bdew_codes(
    bdew_web_config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Fetch BDEW codes using two-stage API approach."""
    logger.info("Starting BDEW code fetch with two-stage approach")

    headers = {
        "User-Agent": bdew_web_config["user_agent"],
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
    }

    all_records = []

    try:
        with httpx.Client(timeout=bdew_web_config["timeout"]) as client:
            # Stage 1: Fetch companies
            logger.info("Stage 1: Fetching companies...")
            companies = _fetch_companies(client, headers, bdew_web_config)
            logger.info(f"Stage 1 complete: {len(companies)} companies fetched")

            if not companies:
                logger.warning("No companies found, stopping workflow")
                return []

            # Stage 2: Fetch BDEW codes for companies
            logger.info("Stage 2: Fetching BDEW codes for companies...")
            all_records = _fetch_company_bdew_codes(
                client, headers, companies, bdew_web_config
            )
            logger.info(f"Stage 2 complete: {len(all_records)} BDEW codes fetched")

    except Exception as e:
        logger.error(f"Error in BDEW fetch process: {e}")
        raise

    return all_records


def validate_bdew_data(fetch_bdew_codes: list[dict[str, Any]]) -> pd.DataFrame:
    """Validate and clean fetched BDEW data."""
    logger.info(f"Validating {len(fetch_bdew_codes)} BDEW records")

    if not fetch_bdew_codes:
        logger.warning("No BDEW codes to validate")
        return pd.DataFrame()

    df = pd.DataFrame(fetch_bdew_codes)

    # Validation rules
    initial_count = len(df)

    # Remove records with empty BDEW codes
    df = df.dropna(subset=["bdew_code"])
    df = df[df["bdew_code"].str.strip() != ""]

    # Remove records without market function mapping
    df = df.dropna(subset=["market_function_id"])

    # Normalize company names
    df["company_name"] = df["company_name"].str.strip()

    # Remove duplicates based on bdew_code and market_function_id
    df = df.drop_duplicates(subset=["bdew_code", "market_function_id"], keep="first")

    final_count = len(df)
    logger.info(
        f"Validation complete: {initial_count} → {final_count} records ({initial_count - final_count} removed)"
    )

    return df


def get_existing_codes(
    database_config: dict[str, Any], database_schema: str
) -> pd.DataFrame:
    """Fetch existing BDEW codes from database."""
    logger.info("Fetching existing BDEW codes from database")

    connection = psycopg2.connect(**database_config)

    try:
        query = f"""
        SELECT
            id,
            bdew_code,
            company_name,
            market_function_id,
            registration_date,
            status,
            last_sync_date,
            data_hash
        FROM {database_schema}.bdew_code_registry
        WHERE status = 'ACTIVE'
        """  # nosec B608

        existing_df = pd.read_sql(query, connection)
        logger.info(f"Found {len(existing_df)} existing BDEW codes")

        return existing_df

    finally:
        connection.close()


def analyze_changes(
    validate_bdew_data: pd.DataFrame,
    get_existing_codes: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Analyze differences between new and existing data."""
    logger.info("Analyzing changes between new and existing data")

    new_data = validate_bdew_data.copy()
    existing_data = get_existing_codes.copy()

    if existing_data.empty:
        logger.info("No existing data found - all records are new")
        return {
            "new_records": new_data,
            "updated_records": pd.DataFrame(),
            "unchanged_records": pd.DataFrame(),
        }

    # Create comparison keys
    new_data["comparison_key"] = (
        new_data["bdew_code"] + "_" + new_data["market_function_id"].astype(str)
    )
    existing_data["comparison_key"] = (
        existing_data["bdew_code"]
        + "_"
        + existing_data["market_function_id"].astype(str)
    )

    # Find new, updated, and unchanged records
    new_keys = set(new_data["comparison_key"])
    existing_keys = set(existing_data["comparison_key"])

    new_record_keys = new_keys - existing_keys
    common_keys = new_keys & existing_keys

    new_records = new_data[new_data["comparison_key"].isin(new_record_keys)]

    # For common keys, check if data has actually changed
    updated_records = []
    unchanged_records = []

    for key in common_keys:
        new_record = new_data[new_data["comparison_key"] == key].iloc[0]
        existing_record = existing_data[existing_data["comparison_key"] == key].iloc[0]

        # Simple comparison - in practice you might want more sophisticated comparison
        new_hash = hashlib.md5(  # nosec B324
            f"{new_record['company_name']}_{new_record['bdew_code']}_{new_record['market_function_id']}".encode(),
            usedforsecurity=False,
        ).hexdigest()
        existing_hash = existing_record.get("data_hash", "")

        if new_hash != existing_hash:
            updated_records.append(new_record)
        else:
            unchanged_records.append(new_record)

    updated_df = pd.DataFrame(updated_records) if updated_records else pd.DataFrame()
    unchanged_df = (
        pd.DataFrame(unchanged_records) if unchanged_records else pd.DataFrame()
    )

    logger.info(
        f"Change analysis: {len(new_records)} new, {len(updated_df)} updated, {len(unchanged_df)} unchanged"
    )

    return {
        "new_records": new_records,
        "updated_records": updated_df,
        "unchanged_records": unchanged_df,
    }


def save_to_database(
    analyze_changes: dict[str, pd.DataFrame],
    database_config: dict[str, Any],
    database_schema: str,
    sync_metadata: dict[str, Any],
) -> dict[str, Any]:
    """Save changes to database with normalized market function IDs."""
    logger.info("Saving changes to database")

    new_records = analyze_changes["new_records"]
    updated_records = analyze_changes["updated_records"]

    connection = psycopg2.connect(**database_config)
    sync_stats = {"inserted": 0, "updated": 0, "errors": 0}

    try:
        with connection.cursor() as cursor:
            # Insert new records
            if not new_records.empty:
                insert_query = f"""
                INSERT INTO {database_schema}.bdew_code_registry
                (bdew_code, company_name, market_function_id, registration_date, status, last_sync_date, data_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """  # nosec B608

                for _, record in new_records.iterrows():
                    try:
                        data_hash = hashlib.md5(  # nosec B324
                            f"{record['company_name']}_{record['bdew_code']}_{record['market_function_id']}".encode(),
                            usedforsecurity=False,
                        ).hexdigest()
                        record_str = f"{record['bdew_code']}_{record['company_name']}_{record['market_function_id']}"
                        logger.debug(f"Inserting new record: {record_str}")

                        cursor.execute(
                            insert_query,
                            (
                                record["bdew_code"],
                                record["company_name"],
                                record["market_function_id"],
                                record.get("registration_date", ""),
                                record.get("status", "ACTIVE"),
                                datetime.now(),
                                data_hash,
                            ),
                        )
                        sync_stats["inserted"] += 1

                    except Exception as e:
                        logger.error(f"Error inserting record {record_str}: {e}")
                        sync_stats["errors"] += 1

            # Update existing records
            if not updated_records.empty:
                update_query = f"""
                UPDATE {database_schema}.bdew_code_registry
                SET company_name = %s, last_sync_date = %s, data_hash = %s
                WHERE bdew_code = %s AND market_function_id = %s
                """  # nosec B608

                for _, record in updated_records.iterrows():
                    try:
                        data_hash = hashlib.md5(  # nosec B324
                            f"{record['company_name']}_{record['bdew_code']}_{record['market_function_id']}".encode(),
                            usedforsecurity=False,
                        ).hexdigest()
                        record_str = f"{record['bdew_code']}_{record['company_name']}_{record['market_function_id']}"
                        logger.debug(f"Updating record: {record_str}")

                        cursor.execute(
                            update_query,
                            (
                                record["company_name"],
                                datetime.now(),
                                data_hash,
                                record["bdew_code"],
                                record["market_function_id"],
                            ),
                        )
                        sync_stats["updated"] += 1

                    except Exception as e:
                        logger.error(f"Error updating record {record_str}: {e}")
                        sync_stats["errors"] += 1

        connection.commit()
        logger.info(f"Database save complete: {sync_stats}")

    except Exception as e:
        connection.rollback()
        logger.error(f"Database transaction failed: {e}")
        raise
    finally:
        connection.close()

    return {
        "sync_metadata": sync_metadata,
        "statistics": sync_stats,
        "completion_time": datetime.now().isoformat(),
    }
