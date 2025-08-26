"""Rollout Report Updater Module.

This module provides a high-level interface for discovering, downloading,
and processing BNetzA rollout reports using the BNetzAReportDiscovery service.
"""

import contextlib
import csv
import hashlib
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from docopt import docopt
from sqlalchemy import text

from src.bnetza.rollout_report_discovery import BNetzAReportDiscovery
from src.bnetza.rollout_xlsx_converter import BNetzARolloutXlsx2CsvConverter
from src.database import DatabaseManager

# Constants for magic value compliance
MAX_URL_LENGTH = 80
MAX_ETAG_LENGTH = 20
MAX_STRING_LENGTH = 60
PROGRESS_INTERVAL = 10.0  # Progress logging interval in percentage
PROGRESS_THRESHOLD = 100.0  # Total progress percentage
SUBSTRING_ELLIPSIS_LENGTH = 3  # Length of "..."

# Setup module logger
logger = logging.getLogger("rollout_updater")


class RolloutReportUpdater:
    """High-level service for updating rollout reports and data.

    This class orchestrates the complete workflow:
    1. Discover new reports via BNetzAReportDiscovery
    2. Download Excel files if needed
    3. Process rollout data into database tables
    4. Update status tracking
    """

    def __init__(self, db_url: str | None = None, download_dir: str | None = None):
        """Initialize the RolloutReportUpdater.

        Args:
            db_url: Database connection URL. If None, uses config from environment.
            download_dir: Directory to save downloaded files. If None, uses default 'data' directory.
        """
        self.discovery_service = BNetzAReportDiscovery(db_url=db_url)
        self.xlsx_converter = BNetzARolloutXlsx2CsvConverter()

        # Set up download directory
        if download_dir:
            self.download_dir = Path(download_dir)
        else:
            self.download_dir = Path.cwd() / "data"

        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Report metadata properties
        self._current_report: dict[str, Any] | None = None
        self._etag: str | None = None
        self._local_file_path: str | None = None
        self._report_id: int | None = None
        self._file_changed: bool = False

        logger.info(
            f"RolloutReportUpdater initialized with download dir: {self.download_dir}"
        )

    @property
    def etag(self) -> str | None:
        """Get the current ETag of the discovered report."""
        return self._etag

    @property
    def current_report(self) -> dict[str, Any] | None:
        """Get the current report metadata."""
        return self._current_report

    @property
    def local_file_path(self) -> str | None:
        """Get the local file path of the downloaded Excel file."""
        return self._local_file_path

    @property
    def report_id(self) -> int | None:
        """Get the database ID of the current report."""
        return self._report_id

    @property
    def file_changed(self) -> bool:
        """Check if the file content actually changed since last download."""
        return self._file_changed

    def has_new_reports(self) -> bool:
        """Check if new reports are available.

        This is a convenience method that delegates to the discovery service.

        Returns:
            True if new reports are detected, False otherwise.
        """
        logger.info("🔍 Checking for new reports...")
        return self.discovery_service.has_new_reports()

    def discover_report(self) -> bool:
        """Discover and store new rollout reports.

        This method finds new reports, stores them in the database with 'discovered' status,
        and prepares metadata for subsequent download and processing.

        Returns:
            True if a new report was discovered, False otherwise.
        """
        try:
            logger.info("🔍 Starting report discovery...")

            # Use the discovery service to find and store reports
            discovered_reports = self.discovery_service.discover_and_store_reports()

            if not discovered_reports:
                logger.info("No new reports discovered")
                self._current_report = None
                self._etag = None
                self._report_id = None
                return False

            # Take the first (and usually only) discovered report
            self._current_report = discovered_reports[0]

            # Extract metadata
            database_id = self._current_report.get("database_id")
            self._report_id = int(database_id) if database_id is not None else None

            # Get ETag from the report URL via HEAD request
            report_url = str(self._current_report.get("url", ""))
            if report_url:
                try:
                    file_changed, metadata = self.discovery_service.check_file_changed(
                        report_url
                    )
                    self._etag = metadata.get("etag", "")
                    self._file_changed = file_changed

                    logger.info(
                        f"📊 Report discovered: {self._current_report.get('filename')}"
                    )
                    logger.info(
                        f"🏷️  ETag: {self._etag[:MAX_ETAG_LENGTH]}..."
                        if len(self._etag) > MAX_ETAG_LENGTH
                        else f"🏷️  ETag: {self._etag}"
                    )
                    logger.info(f"🔄 File changed: {self._file_changed}")

                except Exception as e:
                    logger.warning(
                        f"Could not retrieve ETag for discovered report: {e}"
                    )
                    self._etag = None
                    self._file_changed = True

            return True

        except Exception as e:
            logger.error(f"Report discovery failed: {e}")
            self._current_report = None
            self._etag = None
            self._report_id = None
            return False

    def download_excel_file(self, force: bool = False) -> bool:
        """Download the Excel file for the current report.

        Args:
            force: If True, download even if file hasn't changed according to ETag.

        Returns:
            True if file was downloaded successfully, False otherwise.
        """
        if not self._current_report:
            logger.error("No current report to download. Call discover_report() first.")
            return False

        report_url = str(self._current_report.get("url", ""))
        if not report_url:
            logger.error("No URL found in current report")
            return False

        try:
            # Determine local file path
            filename = str(self._current_report.get("filename", "unknown.xlsx"))
            local_path = str(self.download_dir / filename)

            # Update status to 'downloaded' when starting download
            if self._report_id:
                self.discovery_service.update_report_status(
                    self._report_id,
                    "downloaded",
                    f"Starting file download at {datetime.now().isoformat()}",
                )

            logger.info(f"📥 Downloading Excel file: {filename}")

            # Helper function to shorten URLs
            def _shorten_url(url: str) -> str:
                if len(url) <= MAX_URL_LENGTH:
                    return url
                if "/" in url:
                    filename = url.split("/")[-1]
                    if "?" in filename:
                        filename = filename.split("?")[0]
                    domain = (
                        url.split("//")[1].split("/")[0]
                        if "//" in url
                        else url.split("/")[0]
                    )
                    return f"{domain}/.../{filename}"
                return url[: MAX_URL_LENGTH - SUBSTRING_ELLIPSIS_LENGTH] + "..."

            logger.info(f"🔗 URL: {_shorten_url(report_url)}")
            logger.info(f"💾 Local path: {local_path}")

            # Use the discovery service to download the file
            downloaded_path, file_changed = self.discovery_service.download_report(
                report_url, local_path, force=force
            )

            self._local_file_path = downloaded_path
            self._file_changed = file_changed

            # Update our stored ETag if available
            if self._etag:
                logger.info(
                    f"🏷️  File downloaded with ETag: {self._etag[:MAX_ETAG_LENGTH]}..."
                    if len(self._etag) > MAX_ETAG_LENGTH
                    else f"🏷️  File downloaded with ETag: {self._etag}"
                )

            if file_changed:
                logger.info("✅ File download completed - content has changed")
            else:
                logger.info("✅ File download completed - content unchanged")

            return True

        except Exception as e:
            logger.error(f"Excel file download failed: {e}")

            # Update status to error if download fails
            if self._report_id:
                with contextlib.suppress(Exception):
                    self.discovery_service.update_report_status(
                        self._report_id, "error", f"Download failed: {e!s}"
                    )

            return False

    def get_latest_report_info(self) -> dict[str, Any] | None:
        """Get information about the latest stored report.

        This is a convenience method that delegates to the discovery service.

        Returns:
            Latest report metadata or None if no reports found.
        """
        return self.discovery_service.get_latest_report_info()

    def update_report_status(self, status: str, notes: str | None = None) -> bool:
        """Update the status of the current report.

        Args:
            status: New status value ('discovered', 'downloaded', 'processed', 'error')
            notes: Optional additional notes to append

        Returns:
            True if status was updated successfully, False otherwise.
        """
        if not self._report_id:
            logger.error("No current report ID. Call discover_report() first.")
            return False

        try:
            self.discovery_service.update_report_status(self._report_id, status, notes)
            logger.info(f"📊 Report status updated to: {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update report status: {e}")
            return False

    def convert_excel_to_csv(self, csv_filename: str | None = None) -> bool:
        """Convert the downloaded Excel file to CSV format.

        Args:
            csv_filename: Name for the output CSV file. If None, generates from Excel filename.

        Returns:
            True if conversion was successful, False otherwise.
        """
        if not self._local_file_path:
            logger.error("No Excel file available. Call download_excel_file() first.")
            return False

        if not Path(self._local_file_path).exists():
            logger.error(f"Excel file not found: {self._local_file_path}")
            return False

        try:
            # Update status to processing
            if self._report_id:
                self.update_report_status(
                    "processing", "Starting Excel to CSV conversion"
                )

            # Generate CSV filename if not provided
            if not csv_filename:
                excel_path = Path(self._local_file_path)
                csv_filename = f"{excel_path.stem}.csv"

            csv_path = self.download_dir / csv_filename

            # Extract quarter and year from current report metadata
            quarter = None
            year = None
            if self._current_report:
                quarter = self._current_report.get("report_quarter")
                year = self._current_report.get("report_year")

            logger.info("🔄 Converting Excel to CSV...")
            logger.info(f"   📥 Excel: {self._local_file_path}")
            logger.info(f"   📤 CSV:   {csv_path}")
            logger.info(f"   📅 Period: Q{quarter} {year}")

            # Convert Excel to CSV
            stats = self.xlsx_converter.convert_xlsx_to_csv(
                excel_path=self._local_file_path,
                csv_path=csv_path,
                quarter=quarter,
                year=year,
            )

            logger.info("✅ Excel to CSV conversion completed")
            logger.info(f"📊 Processed {stats['output_csv_rows']} companies")

            # Update status to completed and set file hash
            if self._report_id:
                # Calculate file hash of the original Excel file
                with Path(self._local_file_path).open("rb") as f:
                    file_content = f.read()
                    excel_hash = hashlib.sha256(file_content).hexdigest()

                # Set the hash and update status
                self.discovery_service.set_report_file_hash(
                    self._report_id, excel_hash, status="completed"
                )

                logger.info("📝 Report marked as completed with file hash")

            return True

        except Exception as e:
            logger.error(f"Excel to CSV conversion failed: {e}")

            # Update status to error
            if self._report_id:
                with contextlib.suppress(Exception):
                    self.update_report_status("failed", f"Conversion failed: {e!s}")

            return False

    def discover_and_download(self, force_download: bool = False) -> bool:
        """Complete workflow: discover report and download Excel file.

        This is a convenience method that combines discovery and download steps.

        Args:
            force_download: If True, download even if file hasn't changed.

        Returns:
            True if both discovery and download succeeded, False otherwise.
        """
        logger.info("🚀 Starting discover and download workflow...")

        # Step 1: Discover reports
        if not self.discover_report():
            logger.info("No new reports discovered, workflow complete")
            return False

        # Step 2: Download Excel file
        if not self.download_excel_file(force=force_download):
            logger.error("Download failed, workflow incomplete")
            return False

        logger.info("🎉 Discover and download workflow completed successfully")
        return True

    def discover_download_and_convert(self, force_download: bool = False) -> bool:
        """Complete workflow: discover, download and convert Excel file to CSV.

        This is a convenience method that combines all processing steps.

        Args:
            force_download: If True, download even if file hasn't changed.

        Returns:
            True if all steps succeeded, False otherwise.
        """
        logger.info("🚀 Starting complete workflow: discover → download → convert...")

        # Step 1: Discover and download
        if not self.discover_and_download(force_download=force_download):
            logger.info("Discovery/download phase completed without new files")
            return False

        # Step 2: Convert Excel to CSV
        if not self.convert_excel_to_csv():
            logger.error("Conversion failed, workflow incomplete")
            return False

        logger.info("🎉 Complete workflow finished successfully")
        logger.info("✅ Data ready for database import")
        return True

    def import_csv_to_database(
        self, csv_path: str | None = None, clear_existing: bool = True
    ) -> bool:
        """Import CSV data into rollout_companies and rollout_quotas tables.

        Args:
            csv_path: Path to CSV file. If None, uses the current report's CSV.
            clear_existing: If True, clear existing data for the period first.

        Returns:
            True if import succeeded, False otherwise.
        """
        # Determine CSV file path
        if csv_path:
            csv_file = Path(csv_path)
        elif self._local_file_path:
            csv_file = Path(self._local_file_path).with_suffix(".csv")
        else:
            logger.error("No CSV file available for import")
            return False

        if not csv_file.exists():
            logger.error(f"CSV file not found: {csv_file}")
            return False

        logger.info(f"🗄️ Importing CSV data to database: {csv_file}")

        try:
            # Initialize database connection
            db_manager = DatabaseManager()

            # Read CSV data
            companies_data = []
            quotas_data = []

            with Path(csv_file).open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    company_name = row["company_name"].strip()
                    ausstattungsquote = float(row["ausstattungsquote"])
                    stichtag = datetime.strptime(row["stichtag"], "%Y-%m-%d").date()

                    # Prepare company data for rollout_companies table
                    # Using bnetza_name as the primary field
                    companies_data.append(
                        {
                            "bnetza_name": company_name,
                            "normalized_name": company_name.lower().strip(),
                            "created_at": datetime.now(),
                            "updated_at": datetime.now(),
                        }
                    )

                    # Prepare quota data for rollout_quotas table
                    # Note: We need the rollout_company_id, so we'll do this in two steps
                    quotas_data.append(
                        {
                            "company_name": company_name,
                            "rollout_quota": ausstattungsquote,
                            "reference_date": stichtag,
                            "source_file": csv_file.name,
                            "import_date": datetime.now(),
                            "created_at": datetime.now(),
                        }
                    )

            # Import to database
            session = db_manager.get_sync_session()
            try:
                if clear_existing and self._report_id:
                    # Clear existing quota data for this report period
                    # We'll match by reference_date since we don't have report_id in rollout_quotas
                    reference_dates = list({q["reference_date"] for q in quotas_data})
                    logger.info(
                        f"🧹 Clearing existing quota data for dates: {reference_dates}"
                    )

                    for ref_date in reference_dates:
                        session.execute(
                            text(
                                "DELETE FROM rollout_quotas WHERE reference_date = :ref_date"
                            ),
                            {"ref_date": ref_date},
                        )

                # Step 1: Insert/update companies
                total_companies = len(companies_data)
                logger.info(f"📊 Upserting {total_companies} companies...")
                company_id_map = {}

                for i, company in enumerate(companies_data, 1):
                    # Insert or update company
                    result = session.execute(
                        text(
                            """
                            INSERT INTO rollout_companies (bnetza_name, normalized_name, created_at, updated_at)
                            VALUES (:bnetza_name, :normalized_name, :created_at, :updated_at)
                            ON CONFLICT (bnetza_name) DO UPDATE SET
                                normalized_name = EXCLUDED.normalized_name,
                                updated_at = EXCLUDED.updated_at
                            RETURNING id
                        """
                        ),
                        company,
                    )
                    company_id = result.scalar()
                    company_id_map[company["bnetza_name"]] = company_id

                    # Progress logging every 10% or significant milestones
                    progress = (i / total_companies) * PROGRESS_THRESHOLD
                    # Log at: 0%, 10%, 20%, 30%, ..., 90%, 100% (but avoid spam for small datasets)
                    show_progress = i in (1, total_companies) or (
                        total_companies >= PROGRESS_INTERVAL
                        and progress >= PROGRESS_INTERVAL
                        and progress % PROGRESS_INTERVAL
                        <= PROGRESS_THRESHOLD / total_companies
                    )  # Every 10%
                    if show_progress:
                        logger.info(
                            f"📊 Company upsert progress: {progress:.0f}% ({i}/{total_companies})"
                        )

                logger.info(
                    f"✅ Company upsert completed: {total_companies} companies processed"
                )

                # Step 2: Insert quotas with company IDs
                total_quotas = len(quotas_data)
                logger.info(f"📈 Inserting {total_quotas} quota records...")

                for i, quota in enumerate(quotas_data, 1):
                    company_id = company_id_map[quota["company_name"]]
                    session.execute(
                        text(
                            """
                            INSERT INTO rollout_quotas
                            (rollout_company_id, rollout_quota, reference_date, source_file, import_date, created_at)
                            VALUES (:rollout_company_id, :rollout_quota, :reference_date, :source_file, :import_date, :created_at)
                        """
                        ),
                        {
                            "rollout_company_id": company_id,
                            "rollout_quota": quota["rollout_quota"],
                            "reference_date": quota["reference_date"],
                            "source_file": quota["source_file"],
                            "import_date": quota["import_date"],
                            "created_at": quota["created_at"],
                        },
                    )

                    # Progress logging every 10% or significant milestones
                    progress = (i / total_quotas) * PROGRESS_THRESHOLD
                    # Log at: 0%, 10%, 20%, 30%, ..., 90%, 100% (but avoid spam for small datasets)
                    show_progress = i in (1, total_quotas) or (
                        total_quotas >= PROGRESS_INTERVAL
                        and progress >= PROGRESS_INTERVAL
                        and progress % PROGRESS_INTERVAL
                        <= PROGRESS_THRESHOLD / total_quotas
                    )  # Every 10%
                    if show_progress:
                        logger.info(
                            f"📈 Quota insert progress: {progress:.0f}% ({i}/{total_quotas})"
                        )

                logger.info(
                    f"✅ Quota insert completed: {total_quotas} quota records processed"
                )

                session.commit()
                logger.info("✅ Database import completed successfully")

            finally:
                session.close()

            return True

        except Exception as e:
            logger.error(f"❌ Database import failed: {e}")
            return False

    def discover_download_convert_and_import(
        self, force_download: bool = False, clear_existing: bool = True
    ) -> bool:
        """Complete end-to-end workflow: discover → download → convert → import.

        Args:
            force_download: If True, download even if file hasn't changed.
            clear_existing: If True, clear existing data for the period first.

        Returns:
            True if all steps succeeded, False otherwise.
        """
        logger.info(
            "🚀 Starting complete end-to-end workflow: discover → download → convert → import..."
        )

        # Step 1: Discover, download and convert
        if not self.discover_download_and_convert(force_download=force_download):
            logger.info("Discovery/download/convert phase completed without new files")
            return False

        # Step 2: Import to database
        if not self.import_csv_to_database(clear_existing=clear_existing):
            logger.error("Database import failed, workflow incomplete")
            return False

        logger.info("🎉 Complete end-to-end workflow finished successfully")
        logger.info("✅ Data available in database tables")
        return True

    def __str__(self) -> str:
        """String representation of the updater."""
        if self._current_report:
            filename = self._current_report.get("filename", "unknown")
            status = f"\n    Report: {filename}"
            if self._etag:
                status += f",\n    ETag: {self._etag[:16]}..."
            if self._local_file_path:
                status += f",\n    Local: {Path(self._local_file_path).name}"
            return status
        return "RolloutReportUpdater (no current report)"

    def __repr__(self) -> str:
        """Developer representation of the updater."""
        return (
            f"RolloutReportUpdater("
            f"download_dir={self.download_dir}, "
            f"report_id={self._report_id}, "
            f"etag={self._etag}, "
            f"has_file={self._local_file_path is not None})"
        )


def main() -> None:
    """BNetzA Rollout Report Updater CLI.

    Usage:
        rollout_report_updater.py [options]
        rollout_report_updater.py --check-update [options]
        rollout_report_updater.py --dry-run [options]
        rollout_report_updater.py --force-update [options]

    Options:
        --check-update          Only check if updates are available, don't write to database
        --dry-run              Show what would be updated without writing to database
        --force-update         Force update even if files haven't changed
        --download-dir=<dir>   Directory to save downloaded files [default: ./tmp]
        --verbose              Enable verbose logging
        --help                 Show this help message

    Examples:
        # Check if new reports are available
        python -m src.bnetza.rollout_report_updater --check-update

        # Show what would be updated
        python -m src.bnetza.rollout_report_updater --dry-run

        # Force update all data
        python -m src.bnetza.rollout_report_updater --force-update

        # Regular update (download and import new data)
        python -m src.bnetza.rollout_report_updater
    """
    # Use the docstring directly to avoid type issues
    docstring = main.__doc__ or ""
    args = docopt(docstring)

    # Configure logging with shorter logger names
    log_level = logging.INFO if args["--verbose"] else logging.WARNING

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # Replace any existing handlers
    )

    download_dir = args["--download-dir"]
    check_only = args["--check-update"]
    dry_run = args["--dry-run"]
    force_update = args["--force-update"]

    print("🔄 BNetzA Rollout Report Updater")
    print("=" * 50)

    try:
        # Initialize updater
        updater = RolloutReportUpdater(download_dir=download_dir)

        if check_only:
            print("\n🔍 Checking for new reports...")
            has_new = updater.has_new_reports()
            if has_new:
                print("✅ New reports are available")
                print(f"📊 Current state: {updater}")
                sys.exit(0)
            else:
                print("ℹ No new reports available")  # noqa: RUF001
                sys.exit(1)

        elif dry_run:
            print("\n🔍 Dry run: Checking what would be updated...")

            # Check for new reports
            has_new = updater.has_new_reports()
            if not has_new and not force_update:
                print("ℹ No new reports available")  # noqa: RUF001
                sys.exit(0)

            # Simulate discovery and download
            print("\n📥 Would discover and download:")
            if updater.discover_and_download(force_download=force_update):
                print(f"✅ Would download: {updater}")

                # Simulate conversion
                if updater._local_file_path:
                    csv_file = Path(updater._local_file_path).with_suffix(".csv")
                    if updater.convert_excel_to_csv():
                        print(f"🔄 Would convert to: {csv_file}")

                        # Show what would be imported
                        if csv_file.exists():
                            with csv_file.open(encoding="utf-8") as f:
                                reader = csv.DictReader(f)
                                row_count = sum(1 for _ in reader)
                            print(f"📊 Would import {row_count} company quota records")

                            # Show sample data
                            with csv_file.open(encoding="utf-8") as f:
                                reader = csv.DictReader(f)
                                samples = [
                                    next(reader) for _ in range(min(3, row_count))
                                ]

                            print("📋 Sample data that would be imported:")
                            for i, sample in enumerate(samples, 1):
                                print(
                                    f"   {i}. {sample['company_name']}: {float(sample['ausstattungsquote']):.1%} (Date: {sample['stichtag']})"
                                )
                        else:
                            print("❌ CSV conversion failed in dry run")
                    else:
                        print("❌ Would fail to convert Excel to CSV")
                else:
                    print("❌ No local file path available")
            else:
                print("ℹ No files would be downloaded")  # noqa: RUF001

            print("\n🔍 Dry run completed - no changes made to database")

        else:
            # Regular or forced update
            mode_text = (
                "🔄 Running forced update..."
                if force_update
                else "🔄 Running regular update..."
            )
            print(f"\n{mode_text}")

            success = updater.discover_download_convert_and_import(
                force_download=force_update
            )

            if success:
                print("\n✅ Update completed successfully!")
                print(f"📊 Final state: {updater}")

                # Show import statistics
                if updater._local_file_path:
                    csv_file = Path(updater._local_file_path).with_suffix(".csv")
                    if csv_file.exists():
                        with csv_file.open(encoding="utf-8") as f:
                            reader = csv.DictReader(f)
                            row_count = sum(1 for _ in reader)
                        print(f"📊 Imported {row_count} company quota records")

                sys.exit(0)
            else:
                print("ℹ No updates were necessary")  # noqa: RUF001
                sys.exit(0)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args["--verbose"]:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
