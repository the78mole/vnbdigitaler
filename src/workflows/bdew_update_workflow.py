"""
Hamilton workflow for BDEW Code List Updates.

This module defines the data pipeline for updating the BDEW code registry
with official data from https://bdew-codes.de.

The workflow consists of several stages:
1. Data Source Configuration
2. BDEW Code Extraction
3. Data Validation & Quality Checks
4. Database Integration & Sync Logging
5. Change Detection & Notifications

Hamilton Functions Overview:
- fetch_bdew_codes: Download latest BDEW code data
- validate_bdew_data: Quality checks and validation
- detect_changes: Compare with existing database
- update_database: Apply changes to PostgreSQL
- log_sync_results: Track synchronization metadata
"""

import hashlib
import logging
from datetime import datetime
from typing import Any

import httpx
import pandas as pd
import psycopg2
from bs4 import BeautifulSoup
from hamilton.function_modifiers import config

logger = logging.getLogger(__name__)


@config.when(data_source="bdew_api")
def bdew_api_config() -> dict[str, Any]:
    """Configuration for BDEW API data source."""
    return {
        "base_url": "https://bdew-codes.de",
        "api_endpoint": "/api/codes",
        "timeout": 30,
        "retry_attempts": 3,
        "headers": {
            "User-Agent": "VNB-Digitaler/1.0 (BDEW Code Sync)",
            "Accept": "application/json",
        },
    }


@config.when(data_source="bdew_web")
def bdew_web_config() -> dict[str, Any]:
    """Configuration for BDEW website scraping."""
    return {
        "base_url": "https://bdew-codes.de",
        "code_list_url": "/Codenumbers/BDEWCodes/CodeOverview",
        "timeout": 30,
        "retry_attempts": 3,
        "headers": {
            "User-Agent": "VNB-Digitaler/1.0 (BDEW Code Sync)",
            "Accept": "text/html,application/xhtml+xml",
        },
    }


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


def sync_metadata(
    start_time: datetime = datetime.now(),
) -> dict[str, Any]:
    """Initialize synchronization metadata."""
    return {
        "sync_id": f"bdew_sync_{start_time.strftime('%Y%m%d_%H%M%S')}",
        "start_time": start_time,
        "sync_type": "full_sync",
        "data_source": "bdew_web",  # Can be configured
        "records_processed": 0,
        "records_added": 0,
        "records_updated": 0,
        "records_failed": 0,
        "errors": [],
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
    ROLE_CODE_INDEX = 2
    STATUS_INDEX = 3
    REGISTRATION_DATE_INDEX = 4

    fetch_metadata = {
        "fetch_time": datetime.now(),
        "source_url": None,
        "response_status": None,
        "content_hash": None,
        "raw_size": 0,
    }

    try:
        url = f"{bdew_web_config['base_url']}{bdew_web_config['code_list_url']}"
        fetch_metadata["source_url"] = url

        with httpx.Client(timeout=bdew_web_config["timeout"]) as client:
            response = client.get(url, headers=bdew_web_config["headers"])
            response.raise_for_status()
            fetch_metadata["response_status"] = response.status_code

            # Parse HTML content
            soup = BeautifulSoup(response.content, "html.parser")

            # Extract BDEW code table data
            # This is a simplified extraction - in reality, we'd need to
            # analyze the actual structure of the BDEW website
            raw_data = []

            # Look for tables containing BDEW codes
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")

                for i, row in enumerate(rows):
                    cells = row.find_all(["th", "td"])
                    if i == 0:  # Header row
                        # Skip header row
                        continue
                    elif len(cells) >= MIN_COLUMNS:  # Ensure minimum expected columns
                        row_data = {
                            "bdew_code": cells[0].get_text(strip=True),
                            "company_name": cells[1].get_text(strip=True),
                            "role_code": (
                                cells[ROLE_CODE_INDEX].get_text(strip=True)
                                if len(cells) > ROLE_CODE_INDEX
                                else "UNKNOWN"
                            ),
                            "status": (
                                cells[STATUS_INDEX].get_text(strip=True)
                                if len(cells) > STATUS_INDEX
                                else "ACTIVE"
                            ),
                            "registration_date": (
                                cells[REGISTRATION_DATE_INDEX].get_text(strip=True)
                                if len(cells) > REGISTRATION_DATE_INDEX
                                else None
                            ),
                            "extracted_at": datetime.now().isoformat(),
                        }
                        raw_data.append(row_data)

            # Calculate content hash for change detection
            content_str = str(sorted(raw_data))
            fetch_metadata["content_hash"] = hashlib.sha256(
                content_str.encode()
            ).hexdigest()
            fetch_metadata["raw_size"] = len(raw_data)

            logger.info(f"Fetched {len(raw_data)} BDEW code records")
            return raw_data, fetch_metadata

    except Exception as e:
        error_msg = f"Failed to fetch BDEW codes: {e!s}"
        logger.error(error_msg)
        fetch_metadata["error"] = error_msg
        return [], fetch_metadata


def validate_bdew_data(
    fetch_bdew_codes: tuple[list[dict[str, Any]], dict[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Validate and clean the fetched BDEW data.

    Returns:
        Tuple of (validated_dataframe, validation_metadata)
    """
    raw_data, _fetch_metadata = fetch_bdew_codes

    validation_metadata = {
        "validation_time": datetime.now(),
        "input_records": len(raw_data),
        "valid_records": 0,
        "invalid_records": 0,
        "duplicate_records": 0,
        "validation_errors": [],
    }

    if not raw_data:
        logger.warning("No raw data to validate")
        return pd.DataFrame(), validation_metadata

    try:
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame(raw_data)

        initial_count = len(df)
        validation_metadata["input_records"] = initial_count

        # Basic validation rules
        validation_errors = []

        # Check for required fields
        required_fields = ["bdew_code", "company_name", "role_code"]
        for field in required_fields:
            if field not in df.columns:
                error = f"Missing required field: {field}"
                validation_errors.append(error)
                logger.error(error)

        if validation_errors:
            validation_metadata["validation_errors"] = validation_errors
            return pd.DataFrame(), validation_metadata

        # Remove records with missing essential data
        df = df.dropna(subset=["bdew_code", "company_name"])

        # Clean and standardize data
        df["bdew_code"] = df["bdew_code"].str.strip()
        df["company_name"] = df["company_name"].str.strip()
        df["role_code"] = df["role_code"].str.strip().str.upper()

        # Remove empty codes
        df = df[df["bdew_code"] != ""]
        df = df[df["company_name"] != ""]

        # Check for duplicates
        duplicates = df.duplicated(subset=["bdew_code", "role_code"], keep="first")
        duplicate_count = duplicates.sum()
        if duplicate_count > 0:
            logger.warning(f"Found {duplicate_count} duplicate records, keeping first")
            df = df[~duplicates]

        # Validate BDEW code format (simplified check)
        invalid_codes = df[~df["bdew_code"].str.match(r"^\d{13}$", na=False)]
        if len(invalid_codes) > 0:
            logger.warning(
                f"Found {len(invalid_codes)} records with invalid BDEW code format"
            )

        # Final counts
        validation_metadata["valid_records"] = len(df)
        validation_metadata["invalid_records"] = initial_count - len(df)
        validation_metadata["duplicate_records"] = duplicate_count

        logger.info(
            f"Validation complete: {validation_metadata['valid_records']} valid records from {initial_count} input records"
        )

        return df, validation_metadata

    except Exception as e:
        error_msg = f"Data validation failed: {e!s}"
        logger.error(error_msg)
        validation_metadata["validation_errors"].append(error_msg)
        return pd.DataFrame(), validation_metadata


def get_existing_codes(
    database_config: dict[str, str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Fetch existing BDEW codes from the database.

    Returns:
        Tuple of (existing_dataframe, fetch_metadata)
    """
    fetch_metadata = {
        "fetch_time": datetime.now(),
        "record_count": 0,
        "connection_successful": False,
        "error": None,
    }

    try:
        # Connect to database
        conn = psycopg2.connect(
            host=database_config["host"],
            port=database_config["port"],
            database=database_config["database"],
            user=database_config["user"],
            password=database_config["password"],
        )

        fetch_metadata["connection_successful"] = True

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

        fetch_metadata["record_count"] = len(df)
        logger.info(f"Fetched {len(df)} existing BDEW codes from database")

        return df, fetch_metadata

    except Exception as e:
        error_msg = f"Failed to fetch existing codes: {e!s}"
        logger.error(error_msg)
        fetch_metadata["error"] = error_msg
        return pd.DataFrame(), fetch_metadata


def detect_changes(
    validate_bdew_data: tuple[pd.DataFrame, dict[str, Any]],
    get_existing_codes: tuple[pd.DataFrame, dict[str, Any]],
) -> dict[str, Any]:
    """
    Detect changes between new and existing BDEW data.

    Returns:
        Dictionary with change detection results
    """
    new_data, _validation_metadata = validate_bdew_data
    existing_data, _existing_metadata = get_existing_codes

    change_detection = {
        "detection_time": datetime.now(),
        "new_records": [],
        "updated_records": [],
        "unchanged_records": [],
        "summary": {
            "total_new": 0,
            "total_updated": 0,
            "total_unchanged": 0,
            "changes_detected": False,
        },
    }

    if new_data.empty:
        logger.warning("No new data to compare")
        return change_detection

    if existing_data.empty:
        # All records are new
        change_detection["new_records"] = new_data.to_dict("records")
        change_detection["summary"]["total_new"] = len(new_data)
        change_detection["summary"]["changes_detected"] = True
        logger.info(f"All {len(new_data)} records are new (empty database)")
        return change_detection

    # Compare datasets
    # Create a key for comparison
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

        # Simple comparison - in practice, you'd want more sophisticated comparison
        if new_record["company_name"] != existing_record[
            "company_name"
        ] or new_record.get("status", "ACTIVE") != existing_record.get(
            "status", "ACTIVE"
        ):
            updated_records.append(new_record.to_dict())
        else:
            unchanged_records.append(new_record.to_dict())

    change_detection["new_records"] = new_records.to_dict("records")
    change_detection["updated_records"] = updated_records
    change_detection["unchanged_records"] = unchanged_records

    change_detection["summary"] = {
        "total_new": len(new_records),
        "total_updated": len(updated_records),
        "total_unchanged": len(unchanged_records),
        "changes_detected": len(new_records) > 0 or len(updated_records) > 0,
    }

    logger.info(
        f"Change detection complete: {change_detection['summary']['total_new']} new, "
        f"{change_detection['summary']['total_updated']} updated, "
        f"{change_detection['summary']['total_unchanged']} unchanged"
    )

    return change_detection


def update_database(
    detect_changes: dict[str, Any],
    database_config: dict[str, str],
    _sync_metadata: dict[str, Any],  # Used by Hamilton for graph dependencies
) -> dict[str, Any]:
    """
    Apply changes to the database.

    Returns:
        Dictionary with update results
    """
    update_results = {
        "update_time": datetime.now(),
        "records_inserted": 0,
        "records_updated": 0,
        "records_failed": 0,
        "success": False,
        "errors": [],
    }

    if not detect_changes["summary"]["changes_detected"]:
        logger.info("No changes detected, skipping database update")
        update_results["success"] = True
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
                        record.get("registration_date"),
                        datetime.now(),
                        data_hash,
                    ),
                )

                update_results["records_inserted"] += 1

            except Exception as e:
                error_msg = f"Failed to insert record {record.get('bdew_code', 'unknown')}: {e!s}"
                logger.error(error_msg)
                update_results["errors"].append(error_msg)
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
                error_msg = f"Failed to update record {record.get('bdew_code', 'unknown')}: {e!s}"
                logger.error(error_msg)
                update_results["errors"].append(error_msg)
                update_results["records_failed"] += 1

        # Commit changes
        conn.commit()
        cursor.close()
        conn.close()

        update_results["success"] = True
        logger.info(
            f"Database update complete: {update_results['records_inserted']} inserted, "
            f"{update_results['records_updated']} updated, "
            f"{update_results['records_failed']} failed"
        )

    except Exception as e:
        error_msg = f"Database update failed: {e!s}"
        logger.error(error_msg)
        update_results["errors"].append(error_msg)
        update_results["success"] = False

    return update_results


def log_sync_results(
    sync_metadata: dict[str, Any],
    update_database: dict[str, Any],
    database_config: dict[str, str],
) -> dict[str, Any]:
    """
    Log synchronization results to the database.

    Returns:
        Dictionary with logging results
    """
    log_results = {
        "log_time": datetime.now(),
        "sync_log_id": None,
        "success": False,
        "error": None,
    }

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
        status_id = 9 if update_database["success"] else 10  # SUCCESS or FAILED

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
                    "errors": update_database.get("errors", []),
                },
            ),
        )

        result = cursor.fetchone()
        if result:
            log_results["sync_log_id"] = result[0]
        conn.commit()
        cursor.close()
        conn.close()

        log_results["success"] = True
        logger.info(f"Sync results logged with ID: {log_results['sync_log_id']}")

    except Exception as e:
        error_msg = f"Failed to log sync results: {e!s}"
        logger.error(error_msg)
        log_results["error"] = error_msg

    return log_results


def workflow_summary(
    sync_metadata: dict[str, Any],
    update_database: dict[str, Any],
    log_sync_results: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate final workflow summary.

    Returns:
        Complete workflow execution summary
    """
    end_time = datetime.now()
    duration = end_time - sync_metadata["start_time"]

    summary = {
        "workflow_id": sync_metadata["sync_id"],
        "start_time": sync_metadata["start_time"],
        "end_time": end_time,
        "duration_seconds": duration.total_seconds(),
        "overall_success": update_database["success"] and log_sync_results["success"],
        "database_updates": {
            "records_inserted": update_database["records_inserted"],
            "records_updated": update_database["records_updated"],
            "records_failed": update_database["records_failed"],
        },
        "sync_log_id": log_sync_results.get("sync_log_id"),
        "errors": update_database.get("errors", [])
        + ([log_sync_results["error"]] if log_sync_results.get("error") else []),
    }

    logger.info(
        f"Workflow {sync_metadata['sync_id']} completed in {duration.total_seconds():.2f} seconds"
    )
    logger.info(f"Overall success: {summary['overall_success']}")

    return summary
