#!/usr/bin/env python3
"""
BNetzA Smart Meter Roll-out Data Downloader

This script downloads the BNetzA iMSys article page and associated Excel files
to a temporary directory for analysis and processing.

Usage:
    uv run python tools/01_download_bnetza_data.py [--temp-dir <path>] [--dry-run] [--verbose]
"""

import argparse
import hashlib
import json
import logging
import re
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

# Constants
BNETZA_ARTICLE_URL = "https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/NetzzugangMesswesen/Mess-undZaehlwesen/iMSys/artikel.html"
USER_AGENT = (
    "vnbdigitaler/1.0 (Data Collection Bot; https://github.com/the78mole/vnbdigitaler)"
)
REQUEST_TIMEOUT = 30
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2


class BNetzADownloader:
    """Downloads BNetzA Smart Meter data and metadata."""

    def __init__(self, temp_dir: Path | None = None, verbose: bool = False):
        # Use workspace tmp directory instead of system temp
        if temp_dir is None:
            workspace_root = Path(__file__).parent.parent
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_dir = workspace_root / "tmp" / f"bnetza_download_{timestamp}"

        self.temp_dir = temp_dir
        self.verbose = verbose
        self.client = httpx.Client(
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "de-DE,de;q=0.8,en;q=0.6",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            timeout=REQUEST_TIMEOUT,
        )

        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

        # Ensure temp directory exists
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Using temporary directory: {self.temp_dir}")

    def _make_request(self, url: str, method: str = "GET", **kwargs) -> httpx.Response:
        """Make HTTP request with retry logic and error handling."""
        last_exception = None

        for attempt in range(RETRY_ATTEMPTS):
            try:
                self.logger.debug(
                    f"Making {method} request to: {url} (attempt {attempt + 1})"
                )

                response = self.client.request(method=method, url=url, **kwargs)
                response.raise_for_status()
                return response

            except httpx.RequestError as e:
                last_exception = e
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < RETRY_ATTEMPTS - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))

        # If we get here, all attempts failed
        if last_exception:
            raise last_exception
        else:
            raise httpx.RequestError("All request attempts failed")

    def _get_headers(self, url: str) -> dict[str, Any]:
        """Get HTTP headers for a URL."""
        try:
            response = self._make_request(url, method="HEAD")
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": str(response.url),
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Failed to get headers for {url}: {e}")
            return {}

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with file_path.open("rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def download_article_page(self) -> dict[str, Any]:
        """Download the main BNetzA article page and extract metadata."""
        self.logger.info("Downloading BNetzA article page...")

        # Get headers first
        headers_info = self._get_headers(BNETZA_ARTICLE_URL)

        # Download page content
        response = self._make_request(BNETZA_ARTICLE_URL)

        # Save to file
        article_file = self.temp_dir / "bnetza_artikel.html"
        with article_file.open("w", encoding="utf-8") as f:
            f.write(response.text)

        # Calculate hash
        file_hash = self._calculate_file_hash(article_file)

        # Prepare metadata
        metadata = {
            "url": BNETZA_ARTICLE_URL,
            "file_path": str(article_file),
            "file_size": article_file.stat().st_size,
            "file_hash": file_hash,
            "download_timestamp": datetime.now().isoformat(),
            "content_length": len(response.text),
            "encoding": response.encoding,
            "headers_info": headers_info,
        }

        self.logger.info(
            f"Article page downloaded: {article_file} ({metadata['file_size']} bytes)"
        )
        return metadata

    def extract_excel_links(self, html_content: str) -> list[str]:
        """Extract Excel download links from HTML content."""
        # Pattern for Excel files (.xlsx)
        excel_pattern = r'href="([^"]*\.xlsx[^"]*)"'
        matches = re.findall(excel_pattern, html_content)

        # Convert relative URLs to absolute
        excel_urls = []
        for match in matches:
            if match.startswith("http"):
                excel_urls.append(match)
            else:
                # Handle relative URLs
                base_url = "https://www.bundesnetzagentur.de"
                if match.startswith("/"):
                    excel_urls.append(base_url + match)
                else:
                    excel_urls.append(urljoin(BNETZA_ARTICLE_URL, match))

        # Remove duplicates while preserving order
        unique_urls = []
        seen = set()
        for url in excel_urls:
            if url not in seen:
                unique_urls.append(url)
                seen.add(url)

        self.logger.info(f"Found {len(unique_urls)} Excel file URLs")
        return unique_urls

    def save_metadata(self, metadata: dict[str, Any]) -> Path:
        """Save metadata to JSON file."""
        metadata_file = self.temp_dir / "download_metadata.json"
        with metadata_file.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Metadata saved to: {metadata_file}")
        return metadata_file

    def run(self, dry_run: bool = False) -> dict[str, Any]:
        """Run the complete download process."""
        self.logger.info("Starting BNetzA data download process...")

        if dry_run:
            self.logger.info("DRY RUN MODE - No files will be downloaded")
            return {}

        try:
            # Download article page
            article_metadata = self.download_article_page()

            # Read the downloaded HTML content
            article_file = Path(article_metadata["file_path"])
            with article_file.open(encoding="utf-8") as f:
                html_content = f.read()

            # Extract Excel links
            excel_links = self.extract_excel_links(html_content)

            # Prepare complete metadata
            complete_metadata = {
                "download_session": {
                    "timestamp": datetime.now().isoformat(),
                    "temp_directory": str(self.temp_dir),
                    "script_version": "1.0",
                },
                "article_page": article_metadata,
                "excel_files": {"found_urls": excel_links, "count": len(excel_links)},
            }

            # Save metadata
            self.save_metadata(complete_metadata)

            self.logger.info("Download process completed successfully!")
            self.logger.info(f"Results saved to: {self.temp_dir}")

            return complete_metadata

        except Exception as e:
            self.logger.error(f"Download process failed: {e}")
            raise

    def cleanup(self):
        """Clean up resources."""
        self.client.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download BNetzA Smart Meter Roll-out data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--temp-dir",
        type=Path,
        help="Temporary directory for downloads (default: auto-generated)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Create downloader
    downloader = BNetzADownloader(temp_dir=args.temp_dir, verbose=args.verbose)

    try:
        # Run download process
        metadata = downloader.run(dry_run=args.dry_run)

        if not args.dry_run:
            print("\n✅ Download completed successfully!")
            print(f"📁 Files saved to: {downloader.temp_dir}")
            print(f"📊 Found {metadata['excel_files']['count']} Excel files")

            # Show found Excel URLs
            if metadata["excel_files"]["found_urls"]:
                print("\n📋 Found Excel files:")
                for i, url in enumerate(metadata["excel_files"]["found_urls"], 1):
                    filename = Path(urlparse(url).path).name.split("?")[0]
                    print(f"  {i}. {filename}")
                    print(f"     {url}")

    except KeyboardInterrupt:
        print("\n❌ Download interrupted by user")
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        if args.verbose:
            traceback.print_exc()
    finally:
        downloader.cleanup()


if __name__ == "__main__":
    main()
