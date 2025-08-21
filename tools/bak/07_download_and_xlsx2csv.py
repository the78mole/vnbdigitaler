#!/usr/bin/env python3
"""
VNBdigitaler - Script 07: Excel Download and CSV Conversion

This script downloads the identified Roll-Out report Excel file and converts it to CSV format.
It processes the AI analysis results from Script 06 and handles the actual data extraction.

Usage:
    uv run python tools/07_download_and_xlsx2csv.py [--analysis-file PATH] [--verbose] [--dry-run]
"""

import argparse
import html
import json
import logging
import re
import sys
import traceback
from pathlib import Path
from typing import Any

try:
    import httpx
    import pandas as pd
except ImportError as e:
    print(f"❌ Required packages not installed: {e}")
    print("Run: uv add httpx pandas openpyxl")
    sys.exit(1)


# Constants for data validation and conversion
FLOATING_POINT_TOLERANCE = 1e-10
ZERO_VALUE_FLOAT = 0.0
ZERO_VALUE_STRING = "0"
ZERO_VALUE_STRING_FLOAT = "0.0"


# Constants
USER_AGENT = (
    "vnbdigitaler/1.0 (Excel Downloader; https://github.com/the78mole/vnbdigitaler)"
)
REQUEST_TIMEOUT = 60  # Longer timeout for Excel downloads
CHUNK_SIZE = 8192  # Download chunk size
MIN_HEADER_COLUMNS = 2  # Minimum columns required for header detection
MAX_HEADER_SEARCH_ROWS = 10  # Maximum rows to search for headers
MIN_QUOTA_VALUE = 0.0  # Minimum valid quota value
MAX_QUOTA_VALUE = 1.0  # Maximum valid quota value


def extract_quota_and_date(
    value_str: str, default_date: str = "31.03.2025"
) -> tuple[float, str]:
    """
    Extract numeric quota value and date from a string.

    Args:
        value_str: String containing quota value and potentially date information
        default_date: Default date to use if no date is found in the string

    Returns:
        tuple: (numeric_quota_value, date_string)

    Examples:
        "0% (Stichtag 31.12.2024)" -> (0.0, "31.12.2024")
        "4,22% (Stichtag 31.12.2024)" -> (0.0422, "31.12.2024")
        "0.1234" -> (0.1234, "31.03.2025")
        "15%" -> (0.15, "31.03.2025")
    """
    date_str = default_date
    value_str = str(value_str).strip()

    # Extract date from comments (Stichtag DD.MM.YYYY)
    stichtag_match = re.search(r"Stichtag\s+(\d{1,2}\.\d{1,2}\.\d{4})", value_str)
    if stichtag_match:
        date_str = stichtag_match.group(1)
        # Remove the comment part to get clean numeric value
        value_str = value_str.split("(")[0].strip()

    # Parse numeric value
    if value_str.endswith("%"):
        # Handle percentage values like "0%" or "15%" (support German decimal separator)
        clean_percent = value_str.rstrip("%").replace(",", ".")
        numeric_val = float(clean_percent) / 100
    else:
        # Try direct numeric parsing (handle German decimal separator)
        numeric_val = float(value_str.replace(",", "."))

    return numeric_val, date_str


class ExcelDownloader:
    """Downloads and converts Excel files from BNetzA Roll-Out reports."""

    def __init__(
        self,
        verbose: bool = False,
        dry_run: bool = False,
        output_dir: Path | None = None,
    ):
        self.verbose = verbose
        self.dry_run = dry_run
        self.output_dir = output_dir

        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def load_analysis_results(self, analysis_file: Path) -> dict[str, Any]:
        """Load analysis results from previous AI classification step."""
        self.logger.info(f"Loading analysis results from: {analysis_file}")

        if not analysis_file.exists():
            raise FileNotFoundError(f"Analysis file not found: {analysis_file}")

        with analysis_file.open("r", encoding="utf-8") as f:
            analysis_data = json.load(f)

        # Validate required fields - support both old and new format
        selected_report = self.get_selected_report(analysis_data)

        if not selected_report.get("url"):
            raise ValueError("No Roll-Out report URL found in analysis results")

        self.logger.info(
            f"Found Roll-Out report: {selected_report.get('filename', 'unknown')}"
        )
        return analysis_data

    def get_selected_report(self, analysis_data: dict[str, Any]) -> dict[str, Any]:
        """Extract selected report from analysis data (supports both old and new format)."""
        if "selected_report" in analysis_data:
            # Old format
            return analysis_data["selected_report"]
        elif "identified_file" in analysis_data:
            # New format from Script 06
            return analysis_data["identified_file"]
        else:
            raise ValueError(
                "Analysis file missing 'selected_report' or 'identified_file' section"
            )

    def clean_url(self, url: str) -> str:
        """Clean URL by unescaping HTML entities."""
        # Unescape HTML entities like &amp; -> &
        cleaned_url = html.unescape(url)
        self.logger.debug(f"Cleaned URL: {url} -> {cleaned_url}")
        return cleaned_url

    def generate_filenames(self, analysis_data: dict[str, Any]) -> dict[str, str]:
        """Generate appropriate filenames for downloaded and converted files."""
        # Extract base filename from URL or use analysis data
        selected_report = self.get_selected_report(analysis_data)
        base_filename = selected_report.get("filename", "Roll-out-Quoten.xlsx")

        # Remove URL parameters and ensure .xlsx extension
        if "?" in base_filename:
            base_filename = base_filename.split("?")[0]
        if not base_filename.endswith(".xlsx"):
            base_filename += ".xlsx"

        # Generate CSV filename - no timestamps, clean filenames
        csv_filename = base_filename.replace(".xlsx", ".csv")
        excel_filename = base_filename

        return {
            "excel": excel_filename,
            "csv": csv_filename,
            "base": base_filename,
        }

    def download_excel_file(self, url: str, output_path: Path) -> bool:
        """Download Excel file from URL."""
        if self.dry_run:
            self.logger.info(f"DRY RUN: Would download {url} to {output_path}")
            return True

        self.logger.info(f"Downloading Excel file from: {url}")
        self.logger.info(f"Saving to: {output_path}")

        try:
            with httpx.Client(
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True,
            ) as client, client.stream("GET", url) as response:
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("content-type", "")
                self.logger.debug(f"Content-Type: {content_type}")

                # Check file size
                content_length = response.headers.get("content-length")
                if content_length:
                    file_size = int(content_length)
                    self.logger.info(
                        f"File size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)"
                    )

                # Download file in chunks
                bytes_downloaded = 0
                with output_path.open("wb") as f:
                    for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
                        f.write(chunk)
                        bytes_downloaded += len(chunk)

                        # Log progress for large files
                        if (
                            content_length
                            and bytes_downloaded % (CHUNK_SIZE * 100) == 0
                        ):
                            progress = (bytes_downloaded / file_size) * 100
                            self.logger.debug(f"Download progress: {progress:.1f}%")

            self.logger.info(f"Successfully downloaded {bytes_downloaded:,} bytes")
            return True

        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"HTTP error downloading file: {e.response.status_code} {e.response.reason_phrase}"
            )
            return False
        except httpx.RequestError as e:
            self.logger.error(f"Request error downloading file: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error downloading file: {e}")
            return False

    def detect_data_start_row(self, df: pd.DataFrame) -> tuple[int, list[str]]:
        """
        Detect where actual data starts in a DataFrame with header rows.

        Returns:
            tuple: (data_start_row, column_names)
        """
        self.logger.debug(f"Analyzing DataFrame shape: {df.shape}")

        # Look for the first row that contains meaningful column headers
        # This is typically indicated by:
        # 1. Non-empty values in multiple columns
        # 2. Text that looks like column names (not just titles)
        # 3. Followed by data rows

        for i in range(min(MAX_HEADER_SEARCH_ROWS, len(df))):  # Check first 10 rows max
            row = df.iloc[i]
            non_null_count = row.notna().sum()

            self.logger.debug(
                f"Row {i}: {non_null_count} non-null values: {row.tolist()}"
            )

            # Skip completely empty rows
            if non_null_count == 0:
                continue

            # Skip rows with only one value (likely titles)
            if non_null_count == 1:
                continue

            # Check if this looks like a header row
            # Look for text values that could be column names
            text_values = [str(val).strip() for val in row if pd.notna(val)]

            # If we have multiple text values and they look like headers
            if len(text_values) >= MIN_HEADER_COLUMNS and i + 1 < len(df):
                # Check if next row has data (not just text)
                next_row = df.iloc[i + 1]
                next_non_null = next_row.notna().sum()

                if next_non_null > 0:  # Next row has data
                    # Create proper column names
                    column_names = []
                    for j, val in enumerate(row):
                        if pd.notna(val):
                            column_names.append(str(val).strip())
                        else:
                            column_names.append(f"Column_{j+1}")

                    self.logger.info(
                        f"Detected header row at index {i}: {column_names}"
                    )
                    return i, column_names

        # Fallback: assume data starts from row 0
        self.logger.warning("Could not detect header row, using default column names")
        return 0, [f"Column_{i+1}" for i in range(len(df.columns))]

    def analyze_and_clean_columns(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """
        Analyze DataFrame columns and remove empty/irrelevant ones using AI-like logic.

        Returns:
            tuple: (cleaned_dataframe, analysis_info)
        """
        analysis_info = {
            "original_columns": list(df.columns),
            "original_shape": df.shape,
            "columns_analysis": {},
            "removed_columns": [],
            "kept_columns": [],
            "cleaning_applied": False,
        }

        self.logger.debug(f"Analyzing {len(df.columns)} columns for relevance")

        columns_to_keep = []

        for col in df.columns:
            # Analyze column content
            non_null_count = df[col].notna().sum()
            total_count = len(df[col])
            null_percentage = (total_count - non_null_count) / total_count * 100
            unique_count = df[col].nunique()

            # Check if column has meaningful content
            has_content = non_null_count > 0
            has_variety = unique_count > 1 or (
                unique_count == 1 and non_null_count > total_count * 0.1
            )

            # Analyze column name for relevance
            col_name = str(col).strip()
            is_auto_generated = col_name.startswith("Column_") or col_name.startswith(
                "Unnamed:"
            )

            analysis_info["columns_analysis"][col] = {
                "non_null_count": int(non_null_count),
                "null_percentage": round(float(null_percentage), 2),
                "unique_count": int(unique_count),
                "has_content": bool(has_content),
                "has_variety": bool(has_variety),
                "is_auto_generated": bool(is_auto_generated),
                "keep": False,
            }

            # Decision logic: Keep column if it has meaningful content
            if has_content and (has_variety or not is_auto_generated):
                columns_to_keep.append(col)
                analysis_info["columns_analysis"][col]["keep"] = True
                analysis_info["kept_columns"].append(col)

                self.logger.debug(
                    f"Keeping column '{col}': {non_null_count} values, "
                    f"{unique_count} unique, {null_percentage:.1f}% null"
                )
            else:
                analysis_info["removed_columns"].append(col)
                reason = "empty" if not has_content else "no_variety"
                self.logger.info(f"Removing column '{col}': {reason}")

        # Create cleaned dataframe
        if len(columns_to_keep) < len(df.columns):
            cleaned_df = df[columns_to_keep].copy()
            analysis_info["cleaning_applied"] = True
            analysis_info["final_shape"] = cleaned_df.shape

            self.logger.info(
                f"Column cleaning: {len(df.columns)} → {len(columns_to_keep)} columns "
                f"({len(analysis_info['removed_columns'])} removed)"
            )
        else:
            cleaned_df = df.copy()
            analysis_info["final_shape"] = cleaned_df.shape
            self.logger.info("No column cleaning needed - all columns are relevant")

        return cleaned_df, analysis_info

    def validate_quota_column(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Validate the Ausstattungsquote column for proper numeric values between 0.0 and 1.0.

        Returns:
            dict: Validation results and warnings
        """
        validation_info = {
            "quota_column_found": False,
            "quota_column_name": None,
            "total_values": 0,
            "valid_numeric_values": 0,
            "invalid_values": [],
            "warnings": [],
            "data_quality_issues": [],
        }

        # Look for the quota column (Ausstattungsquote)
        quota_columns = [
            col for col in df.columns if "ausstattungsquote" in col.lower()
        ]

        if not quota_columns:
            validation_info["warnings"].append("No Ausstattungsquote column found")
            self.logger.warning("No Ausstattungsquote column found for validation")
            return validation_info

        quota_col = quota_columns[0]  # Use first match
        validation_info["quota_column_found"] = True
        validation_info["quota_column_name"] = quota_col
        validation_info["total_values"] = len(df[quota_col])

        self.logger.info(f"Validating quota column: '{quota_col}'")

        invalid_entries = []
        valid_count = 0

        for idx, value in enumerate(df[quota_col]):
            if pd.isna(value):
                continue

            value_str = str(value).strip()
            is_valid = False
            issue_type = None
            numeric_val = None

            try:
                # Try to parse as float
                if value_str.endswith("%"):
                    # Handle percentage values like "0%" or "15%" (support German decimal separator)
                    clean_percent = value_str.rstrip("%").replace(",", ".")
                    numeric_val = float(clean_percent) / 100
                    issue_type = "percentage_format"
                elif "(" in value_str or ")" in value_str:
                    # Handle values with comments like "0% (Stichtag 31.12.2024)"
                    clean_val = value_str.split("(")[0].strip()
                    if clean_val.endswith("%"):
                        clean_percent = clean_val.rstrip("%").replace(",", ".")
                        numeric_val = float(clean_percent) / 100
                    else:
                        numeric_val = float(clean_val.replace(",", "."))
                    issue_type = "has_comments"
                else:
                    # Try direct numeric parsing (handle German decimal separator)
                    numeric_val = float(value_str.replace(",", "."))

                # Check if value is in valid range (0.0 to 1.0)
                if MIN_QUOTA_VALUE <= numeric_val <= MAX_QUOTA_VALUE:
                    is_valid = True
                    valid_count += 1
                    # Even valid values with issues should be reported as warnings
                    if issue_type in ["percentage_format", "has_comments"]:
                        # Keep the entry for warning but mark as valid
                        pass
                else:
                    issue_type = f"out_of_range_{numeric_val}"

            except (ValueError, TypeError):
                issue_type = "non_numeric"

            # Add entry to invalid_entries if it has any issues (including valid values with formatting issues)
            if issue_type:
                invalid_entries.append(
                    {
                        "row_index": idx,
                        "value": value_str,
                        "issue_type": issue_type,
                        "company": df.iloc[idx].get("Unternehmen", "Unknown")
                        if "Unternehmen" in df.columns
                        else "Unknown",
                        "is_numeric_valid": is_valid,  # Track if numerically valid
                    }
                )

        validation_info["valid_numeric_values"] = valid_count
        validation_info["invalid_values"] = invalid_entries

        # Generate warnings and data quality issues
        if invalid_entries:
            # Separate truly invalid values from formatting issues
            truly_invalid = [
                e for e in invalid_entries if not e.get("is_numeric_valid", False)
            ]
            formatting_issues = [
                e for e in invalid_entries if e.get("is_numeric_valid", False)
            ]

            total_count = validation_info["total_values"]

            if truly_invalid:
                invalid_count = len(truly_invalid)
                invalid_percentage = (invalid_count / total_count) * 100
                validation_info["warnings"].append(
                    f"Found {invalid_count} truly invalid quota values out of {total_count} "
                    f"({invalid_percentage:.1f}%)"
                )

            if formatting_issues:
                formatting_count = len(formatting_issues)
                formatting_percentage = (formatting_count / total_count) * 100
                validation_info["warnings"].append(
                    f"Found {formatting_count} values with formatting issues out of {total_count} "
                    f"({formatting_percentage:.1f}%)"
                )

            # Categorize issues
            issue_types = {}
            for entry in invalid_entries:
                issue_type = entry["issue_type"]
                if issue_type not in issue_types:
                    issue_types[issue_type] = []
                issue_types[issue_type].append(entry)

            for issue_type, entries in issue_types.items():
                count = len(entries)
                validation_info["data_quality_issues"].append(
                    {
                        "issue_type": issue_type,
                        "count": count,
                        "examples": entries[:3],  # First 3 examples
                    }
                )

                # Log specific warnings
                if issue_type == "percentage_format":
                    self.logger.warning(
                        f"Found {count} values in percentage format (should be decimal)"
                    )
                    # Log each percentage format value as a warning
                    for entry in entries:
                        self.logger.warning(
                            f"⚠️  Row {entry['row_index']}: '{entry['company']}' "
                            f"has percentage format value: '{entry['value']}' "
                            f"({'valid' if entry.get('is_numeric_valid', False) else 'invalid'})"
                        )
                elif issue_type == "has_comments":
                    self.logger.warning(
                        f"Found {count} values with comments/annotations"
                    )
                    # Log each commented value as a warning
                    for entry in entries:
                        self.logger.warning(
                            f"⚠️  Row {entry['row_index']}: '{entry['company']}' "
                            f"has annotated value: '{entry['value']}' "
                            f"({'valid' if entry.get('is_numeric_valid', False) else 'invalid'})"
                        )
                elif issue_type == "non_numeric":
                    self.logger.warning(f"Found {count} non-numeric values")
                    # Log each non-numeric value directly as a warning
                    for entry in entries:
                        self.logger.warning(
                            f"⚠️  Row {entry['row_index']}: '{entry['company']}' "
                            f"has invalid quota value: '{entry['value']}' (non_numeric)"
                        )
                elif issue_type.startswith("out_of_range"):
                    self.logger.warning(
                        f"Found {count} values outside valid range (0.0-1.0)"
                    )
                    # Log each out-of-range value directly as a warning
                    for entry in entries:
                        self.logger.warning(
                            f"⚠️  Row {entry['row_index']}: '{entry['company']}' "
                            f"has out-of-range quota value: '{entry['value']}' ({issue_type})"
                        )

        if not invalid_entries:
            # No issues at all
            self.logger.info(
                f"✅ All {valid_count} quota values are valid numeric values between 0.0 and 1.0"
            )
        elif valid_count == validation_info["total_values"]:
            # All values are numerically valid, but some have formatting issues
            formatting_count = len(
                [e for e in invalid_entries if e.get("is_numeric_valid", False)]
            )
            self.logger.info(
                f"✅ All {valid_count} quota values are numerically valid between 0.0 and 1.0 "
                f"({formatting_count} have formatting issues)"
            )
        else:
            # Some values are truly invalid
            truly_invalid_count = len(
                [e for e in invalid_entries if not e.get("is_numeric_valid", False)]
            )
            self.logger.warning(
                f"⚠️  Data quality issues found: {valid_count}/{validation_info['total_values']} "
                f"values are valid ({(valid_count/validation_info['total_values']*100):.1f}%), "
                f"{truly_invalid_count} are truly invalid"
            )

        return validation_info

    def process_quota_and_dates(
        self, df: pd.DataFrame, default_date: str = "31.03.2025"
    ) -> pd.DataFrame:
        """
        Process DataFrame to extract quota values and dates, adding a Stichtag column.

        Args:
            df: DataFrame with quota column containing values and potential date comments
            default_date: Default date for entries without explicit date information

        Returns:
            DataFrame: Processed DataFrame with clean quota values and Stichtag column
        """
        processed_df = df.copy()

        # Find the quota column
        quota_columns = [
            col for col in df.columns if "ausstattungsquote" in col.lower()
        ]

        if not quota_columns:
            self.logger.warning("No Ausstattungsquote column found for date extraction")
            return processed_df

        quota_col = quota_columns[0]
        self.logger.info(
            f"Processing quota values and extracting dates from column: '{quota_col}'"
        )

        # Create new columns for processed data
        clean_quota_values = []
        stichtag_values = []
        processing_info = {
            "total_processed": 0,
            "dates_extracted": 0,
            "default_dates_used": 0,
            "processing_errors": 0,
            "conversions_applied": 0,
            "unusual_conversions": [],
        }

        for idx, value in enumerate(processed_df[quota_col]):
            try:
                if pd.isna(value):
                    clean_quota_values.append(value)
                    stichtag_values.append(default_date)
                    processing_info["default_dates_used"] += 1
                else:
                    original_value = str(value).strip()
                    # Extract quota and date using our helper function
                    numeric_quota_unrounded, extracted_date = extract_quota_and_date(
                        original_value, default_date
                    )

                    # Round numeric quota to 6 decimal places to avoid floating point precision issues
                    numeric_quota = round(numeric_quota_unrounded, 6)

                    clean_quota_values.append(numeric_quota)
                    stichtag_values.append(extracted_date)

                    processing_info["total_processed"] += 1

                    # Check if this was an "unusual" conversion that needs reporting
                    conversion_needed = False
                    conversion_details = []

                    if extracted_date != default_date:
                        processing_info["dates_extracted"] += 1
                        conversion_needed = True
                        conversion_details.append(f"date extracted: {extracted_date}")
                    else:
                        processing_info["default_dates_used"] += 1

                    # Check if original value needed conversion (percentage, comments, etc.)
                    # Use unrounded value for comparison to avoid rounding artifacts
                    original_is_simple_numeric = False
                    try:
                        # Check if original value is already a simple numeric value
                        original_float = float(original_value.replace(",", "."))
                        original_is_simple_numeric = (
                            abs(original_float - numeric_quota_unrounded)
                            < FLOATING_POINT_TOLERANCE
                            and "%" not in original_value
                            and "(" not in original_value
                        )
                    except (ValueError, TypeError):
                        pass

                    if not original_is_simple_numeric and (
                        original_value != str(numeric_quota_unrounded)
                        and not (
                            original_value == ZERO_VALUE_STRING
                            and numeric_quota == ZERO_VALUE_FLOAT
                        )
                        and not (
                            original_value == ZERO_VALUE_STRING_FLOAT
                            and numeric_quota == ZERO_VALUE_FLOAT
                        )
                    ):
                        conversion_needed = True
                        conversion_details.append(
                            f"value converted: '{original_value}' → {numeric_quota}"
                        )
                        processing_info[
                            "conversions_applied"
                        ] += 1  # Log unusual conversions
                    if conversion_needed:
                        company_name = (
                            processed_df.iloc[idx].get("Unternehmen", "Unknown")
                            if "Unternehmen" in processed_df.columns
                            else "Unknown"
                        )
                        conversion_info = {
                            "row_index": idx,
                            "company": company_name,
                            "original_value": original_value,
                            "converted_quota": numeric_quota,
                            "extracted_date": extracted_date,
                            "details": conversion_details,
                        }
                        processing_info["unusual_conversions"].append(conversion_info)

                        # Log detailed warning
                        details_str = ", ".join(conversion_details)
                        self.logger.warning(
                            f"🔄 Row {idx}: '{company_name}' - Conversion applied ({details_str})"
                        )

            except Exception as e:
                self.logger.warning(f"Error processing row {idx}: {e}")
                clean_quota_values.append(value)  # Keep original value
                stichtag_values.append(default_date)
                processing_info["processing_errors"] += 1

        # Update the quota column with clean numeric values
        processed_df[quota_col] = clean_quota_values

        # Add the Stichtag column
        processed_df["Stichtag"] = stichtag_values

        # Log processing summary
        self.logger.info(
            f"✅ Processed {processing_info['total_processed']} quota values"
        )
        if processing_info["dates_extracted"] > 0:
            self.logger.info(
                f"📅 Extracted {processing_info['dates_extracted']} specific dates from comments"
            )
        if processing_info["conversions_applied"] > 0:
            self.logger.info(
                f"� Applied {processing_info['conversions_applied']} value conversions (percentage/format)"
            )
        self.logger.info(
            f"�📅 Used default date '{default_date}' for {processing_info['default_dates_used']} entries"
        )

        if processing_info["processing_errors"] > 0:
            self.logger.warning(
                f"⚠️  {processing_info['processing_errors']} processing errors occurred"
            )

        # Summary of unusual conversions
        if processing_info["unusual_conversions"]:
            total_unusual = len(processing_info["unusual_conversions"])
            self.logger.info(
                f"🔍 Summary: {total_unusual} entries required unusual conversions (see warnings above)"
            )

        return processed_df

    def convert_excel_to_csv(self, excel_path: Path, csv_path: Path) -> dict[str, Any]:
        """Convert Excel file to CSV with intelligent header detection."""
        if self.dry_run:
            self.logger.info(f"DRY RUN: Would convert {excel_path} to {csv_path}")
            return {
                "success": True,
                "sheets_processed": 1,
                "total_rows": 100,
                "method": "dry_run",
                "header_detection": "skipped_in_dry_run",
            }

        self.logger.info(f"Converting Excel to CSV: {excel_path} -> {csv_path}")

        try:
            # Read Excel file without assuming header structure
            excel_data = pd.read_excel(
                excel_path, sheet_name=None, engine="openpyxl", header=None
            )

            # Log sheet information
            sheet_names = list(excel_data.keys())
            self.logger.info(f"Found {len(sheet_names)} sheet(s): {sheet_names}")

            conversion_info = {
                "success": True,
                "sheets_found": len(sheet_names),
                "sheet_names": sheet_names,
                "sheets_processed": 0,
                "total_rows": 0,
                "method": "pandas_with_header_detection",
                "header_info": {},
                "column_cleaning": {},
                "quota_validation": {},
            }

            # Determine which sheet to process
            if len(sheet_names) == 1:
                sheet_name = sheet_names[0]
                raw_df = excel_data[sheet_name]
                conversion_info["primary_sheet"] = sheet_name
            else:
                # Multiple sheets - convert largest sheet
                largest_sheet = max(excel_data.keys(), key=lambda k: len(excel_data[k]))
                raw_df = excel_data[largest_sheet]
                conversion_info["primary_sheet"] = largest_sheet
                conversion_info[
                    "conversion_note"
                ] = f"Converted largest sheet '{largest_sheet}' out of {len(sheet_names)} sheets"
                # Save metadata about other sheets
                conversion_info["other_sheets"] = {
                    name: {"rows": len(data), "columns": len(data.columns)}
                    for name, data in excel_data.items()
                    if name != largest_sheet
                }

            # Detect header row and proper column names
            header_row_idx, column_names = self.detect_data_start_row(raw_df)

            # Extract the actual data starting from the detected row
            if header_row_idx > 0:
                # Skip header/title rows and use detected header
                data_df = raw_df.iloc[header_row_idx + 1 :].copy()
                data_df.columns = column_names[: len(data_df.columns)]

                conversion_info["header_info"] = {
                    "header_row_index": header_row_idx,
                    "title_rows_skipped": header_row_idx,
                    "data_rows_start": header_row_idx + 1,
                    "detected_columns": column_names,
                    "original_total_rows": len(raw_df),
                    "data_rows_after_header": len(data_df),
                }

                self.logger.info(
                    f"Header detected at row {header_row_idx}, skipped {header_row_idx} title rows"
                )
                self.logger.info(
                    f"Extracted {len(data_df)} data rows from {len(raw_df)} total rows"
                )
            else:
                # No header detected, use all data with detected column names
                data_df = raw_df.copy()
                data_df.columns = column_names[: len(data_df.columns)]

                conversion_info["header_info"] = {
                    "header_row_index": 0,
                    "title_rows_skipped": 0,
                    "data_rows_start": 0,
                    "detected_columns": column_names,
                    "original_total_rows": len(raw_df),
                    "data_rows_after_header": len(data_df),
                }

            # Remove completely empty rows
            data_df = data_df.dropna(how="all")

            # Apply intelligent column cleaning
            cleaned_df, column_analysis = self.analyze_and_clean_columns(data_df)
            conversion_info["column_cleaning"] = column_analysis

            # Validate quota column data quality and extract dates
            quota_validation = self.validate_quota_column(cleaned_df)
            conversion_info["quota_validation"] = quota_validation

            # Process quota values and extract dates for Stichtag column
            processed_df = self.process_quota_and_dates(cleaned_df)

            # Save to CSV
            processed_df.to_csv(csv_path, index=False, encoding="utf-8")

            conversion_info["sheets_processed"] = 1
            conversion_info["total_rows"] = len(processed_df)

            self.logger.info(
                f"Converted sheet '{conversion_info['primary_sheet']}' with {len(processed_df)} data rows to CSV"
            )
            self.logger.info(f"Final column headers: {list(processed_df.columns)}")

            return conversion_info

        except Exception as e:
            self.logger.error(f"Error converting Excel to CSV: {e}")
            return {"success": False, "error": str(e), "method": "pandas"}

    def save_processing_metadata(
        self,
        analysis_data: dict[str, Any],
        download_info: dict[str, Any],
        conversion_info: dict[str, Any],
        output_file: Path,
    ):
        """Save complete processing metadata."""
        metadata = {
            "processing_session": {
                "script_version": "1.0",
                "dry_run": self.dry_run,
            },
            "input_analysis": {
                "source_file": str(
                    analysis_data.get("analysis_session", {}).get(
                        "timestamp", "unknown"
                    )
                ),
                "ai_confidence": self.get_selected_report(analysis_data).get(
                    "confidence", "unknown"
                ),
                "ai_method": analysis_data.get("method_used", "unknown"),
                "selected_url": self.get_selected_report(analysis_data).get("url"),
                "filename": self.get_selected_report(analysis_data).get("filename"),
            },
            "download_process": download_info,
            "conversion_process": conversion_info,
            "output_files": {
                "excel_file": download_info.get("excel_path"),
                "csv_file": download_info.get("csv_path"),
                "metadata_file": str(output_file),
            },
        }

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Processing metadata saved to: {output_file}")

    def run(self, analysis_file: Path) -> dict[str, Any]:
        """Run the complete download and conversion process."""
        self.logger.info("Starting Excel download and CSV conversion...")

        try:
            # Load analysis results
            analysis_data = self.load_analysis_results(analysis_file)

            # Get URL and clean it
            selected_report = self.get_selected_report(analysis_data)
            raw_url = selected_report["url"]
            clean_url = self.clean_url(raw_url)

            # Determine output directory
            if not self.output_dir:
                self.output_dir = analysis_file.parent

            # Generate filenames
            filenames = self.generate_filenames(analysis_data)

            excel_path = self.output_dir / filenames["excel"]
            csv_path = self.output_dir / filenames["csv"]
            metadata_path = self.output_dir / "download_conversion_metadata.json"

            self.logger.info(f"Output directory: {self.output_dir}")
            self.logger.info(f"Excel file: {filenames['excel']}")
            self.logger.info(f"CSV file: {filenames['csv']}")

            # Download Excel file
            download_info = {
                "url": clean_url,
                "excel_path": str(excel_path),
                "csv_path": str(csv_path),
                "success": False,
            }

            if self.download_excel_file(clean_url, excel_path):
                download_info["success"] = True
                download_info["file_size"] = (
                    excel_path.stat().st_size if not self.dry_run else 0
                )
                self.logger.info("✅ Excel download completed")
            else:
                raise RuntimeError("Excel download failed")

            # Convert to CSV
            conversion_info = self.convert_excel_to_csv(excel_path, csv_path)

            if conversion_info["success"]:
                self.logger.info("✅ CSV conversion completed")
            else:
                raise RuntimeError(
                    f"CSV conversion failed: {conversion_info.get('error', 'Unknown error')}"
                )

            # Save metadata
            self.save_processing_metadata(
                analysis_data, download_info, conversion_info, metadata_path
            )

            # Return summary
            result = {
                "excel_path": str(excel_path),
                "csv_path": str(csv_path),
                "metadata_path": str(metadata_path),
                "download_success": download_info["success"],
                "conversion_success": conversion_info["success"],
                "total_rows": conversion_info.get("total_rows", 0),
                "file_size": download_info.get("file_size", 0),
            }

            self.logger.info("Processing completed successfully!")
            return result

        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            raise


def find_latest_analysis_file() -> Path | None:
    """Find the most recent analysis file from AI classification step."""
    workspace_root = Path(__file__).parent.parent
    data_dir = workspace_root / "data"

    if not data_dir.exists():
        return None

    # Look for BNetzA rollout identification file
    analysis_file = data_dir / "bnetza_rollout_identification.json"
    if analysis_file.exists():
        return analysis_file

    return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download and convert Roll-Out report Excel to CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--analysis-file",
        type=Path,
        help="Path to analysis JSON file from AI classification step (default: auto-detect latest)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for downloaded and converted files (default: same as analysis file)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate download and conversion without actually processing files",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Find analysis file if not specified
    if not args.analysis_file:
        args.analysis_file = find_latest_analysis_file()
        if not args.analysis_file:
            print("❌ No analysis file found. Run 02_find_roll_out_report.py first.")
            sys.exit(1)
        print(f"📁 Using analysis file: {args.analysis_file}")

    # Create downloader
    try:
        downloader = ExcelDownloader(
            verbose=args.verbose,
            dry_run=args.dry_run,
            output_dir=args.output_dir,
        )

        # Run download and conversion
        result = downloader.run(analysis_file=args.analysis_file)

        # Show results
        print("\n✅ Download and conversion completed!")
        print(f"📥 Excel file: {Path(result['excel_path']).name}")
        print(f"📊 CSV file: {Path(result['csv_path']).name}")
        if not args.dry_run:
            print(
                f"📏 File size: {result['file_size']:,} bytes ({result['file_size'] / 1024 / 1024:.2f} MB)"
            )
            print(f"📋 Total rows: {result['total_rows']:,}")
        print(f"📄 Metadata: {Path(result['metadata_path']).name}")

    except KeyboardInterrupt:
        print("\n❌ Processing interrupted by user")
    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
