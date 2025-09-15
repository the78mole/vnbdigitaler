"""
Hamilton workflow for BDEW Code List Updates.

Simple workflow to update BDEW codes with proper type annotations.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any

import httpx
import pandas as pd
import psycopg2
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def database_config() -> dict[str, str]:
    """Database connection configuration."""
    return {
        "host": "localhost",
        "port": "5432",
        "database": "vnb_digitaler",
        "user": "vnb_admin",
        "password": "vnb_secure_password_2024",  # pragma: allowlist secret
        "schema": "vnb_digitaler",
    }


def bdew_web_config() -> dict[str, str]:
    """Configuration for BDEW website scraping."""
    return {
        "base_url": "https://bdew-codes.de",
        "code_list_url": "/Codenumbers/BDEWCodes/CodeOverview",
        "user_agent": "VNB-Digitaler/1.0 (BDEW Code Sync)",
    }


def sync_metadata() -> dict[str, str]:
    """Initialize synchronization metadata."""
    start_time = datetime.now()
    return {
        "sync_id": f"bdew_sync_{start_time.strftime('%Y%m%d_%H%M%S')}",
        "start_time": start_time.isoformat(),
        "sync_type": "full_sync",
        "data_source": "bdew_web",
    }


def fetch_bdew_codes(
    bdew_web_config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Fetch BDEW codes from the official BDEW website.

    Returns:
        Tuple of (raw_data_list, fetch_metadata)
    """
    # Constants for table parsing
    MIN_COLUMNS = 3
    STATUS_INDEX = 3
    REGISTRATION_DATE_INDEX = 4
    try:
        url = f"{bdew_web_config['base_url']}{bdew_web_config['code_list_url']}"
        headers = {"User-Agent": bdew_web_config["user_agent"]}

        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

            # Parse HTML content
            soup = BeautifulSoup(response.content, "html.parser")
            raw_data = []

            # Look for tables containing BDEW codes
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")

                for i, row in enumerate(rows):
                    if i == 0:  # Skip header row
                        continue

                    cells = row.find_all(["th", "td"])
                    if len(cells) >= MIN_COLUMNS:  # Ensure minimum expected columns
                        row_data = {
                            "bdew_code": cells[0].get_text(strip=True),
                            "company_name": cells[1].get_text(strip=True),
                            "role_code": cells[2].get_text(strip=True),
                            "status": (
                                cells[STATUS_INDEX].get_text(strip=True)
                                if len(cells) > STATUS_INDEX
                                else "ACTIVE"
                            ),
                            "registration_date": (
                                cells[REGISTRATION_DATE_INDEX].get_text(strip=True)
                                if len(cells) > REGISTRATION_DATE_INDEX
                                else ""
                            ),
                            "extracted_at": datetime.now().isoformat(),
                        }
                        if row_data["bdew_code"] and row_data["company_name"]:
                            raw_data.append(row_data)

            logger.info(f"Fetched {len(raw_data)} BDEW code records")
            return raw_data, {}

    except Exception as e:
        logger.error(f"Failed to fetch BDEW codes: {e}")
        return [], {}


def validate_bdew_data(fetch_bdew_codes: list[dict[str, str]]) -> pd.DataFrame:
    """
    Validate and clean the fetched BDEW data.

    Args:
        fetch_bdew_codes: Raw BDEW code data

    Returns:
        Validated DataFrame
    """
    if not fetch_bdew_codes:
        logger.warning("No raw data to validate")
        return pd.DataFrame()

    try:
        # Convert to DataFrame
        df = pd.DataFrame(fetch_bdew_codes)

        # Clean and standardize data
        df["bdew_code"] = df["bdew_code"].str.strip()
        df["company_name"] = df["company_name"].str.strip()
        df["role_code"] = df["role_code"].str.strip().str.upper()

        # Remove empty records
        df = df[df["bdew_code"] != ""]
        df = df[df["company_name"] != ""]

        # Remove duplicates
        df = df.drop_duplicates(subset=["bdew_code", "role_code"], keep="first")

        logger.info(f"Validation complete: {len(df)} valid records")
        return df

    except Exception as e:
        logger.error(f"Data validation failed: {e}")
        return pd.DataFrame()


def get_existing_codes(database_config: dict[str, str]) -> pd.DataFrame:
    """
    Fetch existing BDEW codes from the database.

    Args:
        database_config: Database connection configuration

    Returns:
        DataFrame with existing codes
    """
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=database_config["host"],
            port=database_config["port"],
            database=database_config["database"],
            user=database_config["user"],
            password=database_config["password"],
        )

        # Query existing BDEW codes
        query = """
        SELECT
            bdew_code,
            company_name,
            role_code,
            registration_date,
            status_id,
            last_sync_date,
            data_hash
        FROM vnb_digitaler.bdew_code_registry
        WHERE bdew_code IS NOT NULL
        """

        df = pd.read_sql(query, conn)
        conn.close()

        logger.info(f"Fetched {len(df)} existing BDEW codes from database")
        return df

    except Exception as e:
        logger.error(f"Failed to fetch existing codes: {e}")
        return pd.DataFrame()


def detect_changes(
    validate_bdew_data: pd.DataFrame,
    get_existing_codes: pd.DataFrame,
) -> dict[str, list]:
    """
    Detect changes between new and existing BDEW data.

    Args:
        validate_bdew_data: New validated data
        get_existing_codes: Existing database data

    Returns:
        Dictionary with change lists
    """
    change_detection = {
        "new_records": [],
        "updated_records": [],
        "unchanged_records": [],
    }

    if validate_bdew_data.empty:
        logger.warning("No new data to compare")
        return change_detection

    if get_existing_codes.empty:
        # All records are new
        change_detection["new_records"] = validate_bdew_data.to_dict("records")
        logger.info(f"All {len(validate_bdew_data)} records are new (empty database)")
        return change_detection

    # Create comparison keys
    new_data = validate_bdew_data.copy()
    existing_data = get_existing_codes.copy()

    new_data["comparison_key"] = new_data["bdew_code"] + "_" + new_data["role_code"]
    existing_data["comparison_key"] = (
        existing_data["bdew_code"] + "_" + existing_data["role_code"]
    )

    # Find new records
    new_keys = set(new_data["comparison_key"])
    existing_keys = set(existing_data["comparison_key"])

    new_record_keys = new_keys - existing_keys
    new_records = new_data[new_data["comparison_key"].isin(new_record_keys)]

    # Find potentially updated records
    common_keys = new_keys & existing_keys
    updated_records = []
    unchanged_records = []

    for key in common_keys:
        new_record = new_data[new_data["comparison_key"] == key].iloc[0]
        existing_record = existing_data[existing_data["comparison_key"] == key].iloc[0]

        # Simple comparison
        if new_record["company_name"] != existing_record["company_name"]:
            updated_records.append(new_record.to_dict())
        else:
            unchanged_records.append(new_record.to_dict())

    change_detection["new_records"] = new_records.to_dict("records")
    change_detection["updated_records"] = updated_records
    change_detection["unchanged_records"] = unchanged_records

    logger.info(
        f"Change detection: {len(new_records)} new, "
        f"{len(updated_records)} updated, {len(unchanged_records)} unchanged"
    )

    return change_detection


def update_database(
    detect_changes: dict[str, list],
    database_config: dict[str, str],
) -> dict[str, int]:
    """
    Apply changes to the database.

    Args:
        detect_changes: Change detection results
        database_config: Database configuration

    Returns:
        Update statistics
    """
    update_results = {
        "records_inserted": 0,
        "records_updated": 0,
        "records_failed": 0,
    }

    has_changes = (
        len(detect_changes["new_records"]) > 0
        or len(detect_changes["updated_records"]) > 0
    )

    if not has_changes:
        logger.info("No changes detected, skipping database update")
        return update_results

    try:
        # Connect to database
        conn = psycopg2.connect(
            host=database_config["host"],
            port=database_config["port"],
            database=database_config["database"],
            user=database_config["user"],
            password=database_config["password"],
        )

        cursor = conn.cursor()

        # Insert new records
        for record in detect_changes["new_records"]:
            try:
                insert_query = """
                INSERT INTO vnb_digitaler.bdew_code_registry
                (bdew_code, company_name, role_code, registration_date, status_id, data_source_id, last_sync_date, data_hash)
                VALUES (%s, %s, %s, %s, 1, 1, %s, %s)
                """

                # Create data hash for this record
                record_str = f"{record['bdew_code']}_{record['company_name']}_{record['role_code']}"
                data_hash = hashlib.sha256(record_str.encode()).hexdigest()

                cursor.execute(
                    insert_query,
                    (
                        record["bdew_code"],
                        record["company_name"],
                        record["role_code"],
                        record.get("registration_date") or None,
                        datetime.now(),
                        data_hash,
                    ),
                )

                update_results["records_inserted"] += 1

            except Exception as e:
                logger.error(
                    f"Failed to insert record {record.get('bdew_code', 'unknown')}: {e}"
                )
                update_results["records_failed"] += 1

        # Update existing records
        for record in detect_changes["updated_records"]:
            try:
                update_query = """
                UPDATE vnb_digitaler.bdew_code_registry
                SET company_name = %s, last_sync_date = %s, data_hash = %s
                WHERE bdew_code = %s AND role_code = %s
                """

                # Create data hash for this record
                record_str = f"{record['bdew_code']}_{record['company_name']}_{record['role_code']}"
                data_hash = hashlib.sha256(record_str.encode()).hexdigest()

                cursor.execute(
                    update_query,
                    (
                        record["company_name"],
                        datetime.now(),
                        data_hash,
                        record["bdew_code"],
                        record["role_code"],
                    ),
                )

                update_results["records_updated"] += 1

            except Exception as e:
                logger.error(
                    f"Failed to update record {record.get('bdew_code', 'unknown')}: {e}"
                )
                update_results["records_failed"] += 1

        # Commit changes
        conn.commit()
        cursor.close()
        conn.close()

        logger.info(
            f"Database update complete: {update_results['records_inserted']} inserted, "
            f"{update_results['records_updated']} updated, "
            f"{update_results['records_failed']} failed"
        )

    except Exception as e:
        logger.error(f"Database update failed: {e}")
        update_results["records_failed"] = -1

    return update_results


def log_sync_results(
    sync_metadata: dict[str, str],
    update_database: dict[str, int],
    database_config: dict[str, str],
) -> dict[str, str]:
    """
    Log synchronization results to the database.

    Args:
        sync_metadata: Sync metadata
        update_database: Update results
        database_config: Database configuration

    Returns:
        Logging results
    """
    log_results = {"sync_log_id": "", "success": "false"}

    try:
        # Connect to database
        conn = psycopg2.connect(
            host=database_config["host"],
            port=database_config["port"],
            database=database_config["database"],
            user=database_config["user"],
            password=database_config["password"],
        )

        cursor = conn.cursor()

        # Insert sync log entry
        log_query = """
        INSERT INTO vnb_digitaler.bdew_sync_log
        (sync_type, data_source_id, start_time, end_time, status_id,
         records_processed, records_added, records_updated, records_failed, sync_metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        # Determine status_id based on success
        success = update_database["records_failed"] != -1
        status_id = 9 if success else 10  # SUCCESS or FAILED

        cursor.execute(
            log_query,
            (
                sync_metadata["sync_type"],
                1,  # BDEW data source ID
                sync_metadata["start_time"],
                datetime.now(),
                status_id,
                update_database["records_inserted"]
                + update_database["records_updated"],
                update_database["records_inserted"],
                update_database["records_updated"],
                update_database["records_failed"],
                {
                    "sync_id": sync_metadata["sync_id"],
                    "update_results": update_database,
                },
            ),
        )

        log_results["sync_log_id"] = str(cursor.fetchone()[0])
        log_results["success"] = "true"

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Sync results logged with ID: {log_results['sync_log_id']}")

    except Exception as e:
        logger.error(f"Failed to log sync results: {e}")
        log_results["success"] = "false"

    return log_results


def workflow_summary(
    sync_metadata: dict[str, str],
    update_database: dict[str, int],
    log_sync_results: dict[str, str],
) -> dict[str, str]:
    """
    Generate final workflow summary.

    Args:
        sync_metadata: Sync metadata
        update_database: Update results
        log_sync_results: Logging results

    Returns:
        Complete workflow execution summary
    """
    end_time = datetime.now()
    start_time = datetime.fromisoformat(sync_metadata["start_time"])
    duration = end_time - start_time

    summary = {
        "workflow_id": sync_metadata["sync_id"],
        "start_time": sync_metadata["start_time"],
        "end_time": end_time.isoformat(),
        "duration_seconds": str(duration.total_seconds()),
        "overall_success": str(
            update_database["records_failed"] != -1
            and log_sync_results["success"] == "true"
        ),
        "records_inserted": str(update_database["records_inserted"]),
        "records_updated": str(update_database["records_updated"]),
        "records_failed": str(update_database["records_failed"]),
        "sync_log_id": log_sync_results.get("sync_log_id", ""),
    }

    logger.info(
        f"Workflow {sync_metadata['sync_id']} completed in {duration.total_seconds():.2f} seconds"
    )
    logger.info(f"Overall success: {summary['overall_success']}")

    return summary
