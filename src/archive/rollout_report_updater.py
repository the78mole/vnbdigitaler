"""Rollout Report Updater Module.

This module provides a high-level interface for discovering, downloading,
and processing BNetzA rollout reports using the BNetzAReportDiscovery service.
"""

import contextlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.rollout_report_discovery import BNetzAReportDiscovery

# Setup module logger
logger = logging.getLogger(__name__)


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
                    logger.info(f"🏷️  ETag: {self._etag}")
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
            logger.info(f"🔗 URL: {report_url}")
            logger.info(f"💾 Local path: {local_path}")

            # Use the discovery service to download the file
            downloaded_path, file_changed = self.discovery_service.download_report(
                report_url, local_path, force=force
            )

            self._local_file_path = downloaded_path
            self._file_changed = file_changed

            # Update our stored ETag if available
            if self._etag:
                logger.info(f"🏷️  File downloaded with ETag: {self._etag}")

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

    def __str__(self) -> str:
        """String representation of the updater."""
        if self._current_report:
            filename = self._current_report.get("filename", "unknown")
            status = f"Report: {filename}"
            if self._etag:
                status += f", ETag: {self._etag[:16]}..."
            if self._local_file_path:
                status += f", Local: {Path(self._local_file_path).name}"
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
