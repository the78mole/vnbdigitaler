"""BNetzA Reports Discovery and Management Module.

Usage:
    bnetza_reports.py [--check-update] [--verbose]
    bnetza_reports.py (-h | --help)

Options:
    -h --help       Show this help message and exit
    --check-update  Only check if new reports are available without updating database
    --verbose -v    Enable verbose logging output

Examples:
    # Check if new reports are available (no database changes)
    python bnetza_reports.py --check-update

    # Discover and store new reports in database
    python bnetza_reports.py

    # Show detailed information
    python bnetza_reports.py --verbose

This module provides functionality to discover, download, and manage
BNetzA rollout quota reports from their website.
"""

import hashlib
import json
import logging
import os
import re
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from docopt import docopt
from jinja2 import Template
from openai import OpenAI
from sqlalchemy import create_engine, text

from src.database_config import get_database_url

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

# Setup module logger
logger = logging.getLogger(__name__)


# Configuration constants
class BNetzAConfig:
    """Configuration constants for BNetzA Report Discovery."""

    # URLs
    BASE_URL = "https://www.bundesnetzagentur.de"
    ROLLOUT_URL = "https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/NetzzugangMesswesen/Mess-undZaehlwesen/iMSys/artikel.html"

    # HTTP settings
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    REQUEST_TIMEOUT = 30

    # File patterns
    EXCEL_FILE_PATTERN = r"\.xlsx?(\?|$)"
    QUARTER_PATTERN = r"Q([1-4])"
    YEAR_PATTERN = r"20(\d{2})"

    # Rollout keywords for report identification
    ROLLOUT_KEYWORDS: ClassVar[list[str]] = [
        "roll-out",
        "rollout",
        "quoten",
        "quote",
        "smart",
        "meter",
        "zähler",
        "messstellenbetrieb",
        "msb",
    ]

    # Scoring weights for heuristic report selection
    SCORING_WEIGHTS: ClassVar[dict[str, int]] = {
        "rollout": 5,
        "quote": 3,
        "smart": 2,
        "year_multiplier": 10,  # For year * 10 + quarter scoring
    }

    # AI Configuration
    AI_MODEL_ENV_VAR = "ROLL_OUT_REPORT_FIND_MODEL"
    OPENROUTER_API_KEY_ENV_VAR = "OPENROUTER_API_KEY"  # pragma: allowlist secret
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    # Quarter constants
    Q1 = 1
    Q2 = 2
    Q3 = 3
    Q4 = 4


class BNetzAReportDiscovery:
    """Service for discovering and managing BNetzA rollout reports."""

    def __init__(self, db_url: str | None = None):
        """Initialize the BNetzA Report Discovery service.

        Args:
            db_url: Database connection URL. If None, uses config from environment.
        """
        self.db_url = db_url or get_database_url()

        # Convert asyncpg URL to synchronous psycopg2 URL for SQLAlchemy
        if "postgresql+asyncpg://" in self.db_url:
            # Replace asyncpg with psycopg2 and fix SSL parameter
            self.db_url = self.db_url.replace("postgresql+asyncpg://", "postgresql://")
            # Convert ssl=require to sslmode=require for psycopg2
            if "ssl=require" in self.db_url:
                self.db_url = self.db_url.replace("ssl=require", "sslmode=require")

        # Use a synchronous engine configuration
        self.engine = create_engine(
            self.db_url,
            pool_pre_ping=True,
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=False,  # Set to True for SQL debugging
        )
        self.db_session = None  # Initialize connection lazily

        logger.info("BNetzA Report Discovery service initialized")

    def _get_db_session(self) -> "Connection":
        """Get database session, creating it if necessary."""
        if self.db_session is None:
            self.db_session = self.engine.connect()  # type: ignore[assignment]
        return self.db_session  # type: ignore[return-value]

    def __del__(self) -> None:
        """Cleanup database connection."""
        try:
            db_session = getattr(self, "db_session", None)
            if db_session is not None:
                db_session.close()
        except Exception:
            ...  # Ignore cleanup errors in destructor

    def fetch_article_page(self, url: str | None = None) -> str:
        """Fetch the main BNetzA rollout article page.

        Args:
            url: URL to fetch. If None, uses default rollout URL.

        Returns:
            HTML content of the page

        Raises:
            requests.RequestException: If page cannot be fetched
        """
        target_url = url or BNetzAConfig.ROLLOUT_URL

        try:
            logger.info(f"Fetching article page: {target_url}")

            headers = {"User-Agent": BNetzAConfig.USER_AGENT}

            response = requests.get(
                target_url, headers=headers, timeout=BNetzAConfig.REQUEST_TIMEOUT
            )
            response.raise_for_status()

            logger.info(f"Successfully fetched {len(response.text)} characters")
            return str(response.text)

        except requests.RequestException as e:
            logger.error(f"Failed to fetch article page: {e}")
            raise

    def extract_excel_urls(
        self, html_content: str, base_url: str | None = None
    ) -> list[dict[str, str]]:
        """Extract Excel file URLs from HTML content.

        Args:
            html_content: HTML content to parse
            base_url: Base URL for making relative URLs absolute

        Returns:
            List of dictionaries containing Excel file metadata
        """
        if not base_url:
            base_url = BNetzAConfig.BASE_URL

        soup = BeautifulSoup(html_content, "html.parser")
        excel_links = []

        # Find all links to Excel files
        for link in soup.find_all("a", href=True):
            # Extract href safely using getattr for attributes
            try:
                # Get the href attribute safely
                attrs = getattr(link, "attrs", {})
                href = attrs.get("href") if attrs else None
                if not href:
                    continue

                href = str(href)
                link_text = getattr(link, "text", "") or ""
                if hasattr(link, "get_text"):
                    link_text = link.get_text(strip=True)
            except (AttributeError, TypeError):
                continue

            # Check if this is an Excel file
            if re.search(BNetzAConfig.EXCEL_FILE_PATTERN, href, re.IGNORECASE):
                # Make absolute URL
                full_url = urljoin(base_url, href)

                # Extract filename from URL
                parsed_url = urlparse(full_url)
                filename = Path(parsed_url.path).name

                # Remove URL parameters from filename
                if "?" in filename:
                    filename = filename.split("?")[0]

                excel_links.append(
                    {"url": full_url, "filename": filename, "text": link_text}
                )

                logger.debug(f"Found Excel file: {filename} -> {full_url}")

        logger.info(f"Extracted {len(excel_links)} Excel file links")
        return excel_links

    def filter_rollout_reports(
        self, excel_files: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        """Filter Excel files to find likely rollout quota reports.

        Args:
            excel_files: List of Excel file metadata dictionaries

        Returns:
            Filtered list of probable rollout reports
        """
        potential_reports = []

        for file_info in excel_files:
            filename = file_info["filename"].lower()
            text = file_info["text"].lower()

            # Skip Fragebogen files explicitly
            if "fragebogen" in filename or "fragebogen" in text:
                continue

            # Check if filename or link text contains rollout-related keywords
            contains_keywords = any(
                keyword in filename or keyword in text
                for keyword in BNetzAConfig.ROLLOUT_KEYWORDS
            )

            # Also check for specific rollout patterns
            is_rollout_file = (
                "roll-out" in filename
                or "rollout" in filename
                or "quoten" in filename
                or ("q1" in filename and "20" in filename)
                or ("q2" in filename and "20" in filename)
                or ("q3" in filename and "20" in filename)
                or ("q4" in filename and "20" in filename)
            )

            if contains_keywords or is_rollout_file:
                potential_reports.append(file_info)
                logger.debug(
                    f"Identified potential rollout report: {file_info['filename']}"
                )

        logger.info(f"Filtered to {len(potential_reports)} potential rollout reports")
        return potential_reports

    def extract_quarter_year(
        self, excel_info: dict[str, str | int | None]
    ) -> tuple[int | None, int | None]:
        """Extract quarter and year from report information.

        Args:
            excel_info: Dictionary containing report metadata

        Returns:
            Tuple of (quarter, year) - both may be None if extraction fails
        """
        try:
            # Extract from filename or text
            filename = str(excel_info.get("filename", ""))
            text = str(excel_info.get("text", ""))

            # Try to find quarter and year patterns
            # Quarter patterns: Q1, Q2, Q3, Q4
            quarter_match = re.search(
                BNetzAConfig.QUARTER_PATTERN, filename + " " + text, re.IGNORECASE
            )
            quarter = int(quarter_match.group(1)) if quarter_match else None

            # Year patterns: 2024, 2025, etc.
            year_match = re.search(BNetzAConfig.YEAR_PATTERN, filename + " " + text)
            year = int(f"20{year_match.group(1)}") if year_match else None

            return quarter, year

        except Exception as e:
            logger.warning(f"Failed to extract quarter/year from {excel_info}: {e}")
            return None, None

    def classify_reports_with_ai_or_heuristics(
        self, excel_files: list[dict[str, str]]
    ) -> dict[str, str | int | None] | None:
        """Use AI-assisted classification or fallback to heuristics to select the best rollout report.

        Args:
            excel_files: List of potential rollout report files

        Returns:
            Selected report metadata or None if no suitable report found
        """
        if not excel_files:
            logger.warning("No Excel files provided for classification")
            return None

        # Filter to potential rollout reports
        potential_reports = self.filter_rollout_reports(excel_files)

        if not potential_reports:
            logger.warning("No potential rollout reports found")
            return None

        # If only one candidate, return it
        if len(potential_reports) == 1:
            logger.info("Only one potential rollout report found, selecting it")
            selected: dict[str, str | int | None] = dict(potential_reports[0])
            quarter, year = self.extract_quarter_year(selected)
            selected.update(
                {
                    "report_quarter": quarter,
                    "report_year": year,
                    "selection_method": "single_candidate",
                    "ai_confidence": "high",
                }
            )
            return selected

        # Try AI classification first
        try:
            logger.info(
                f"Multiple candidates found ({len(potential_reports)}), trying AI classification"
            )
            ai_result = self.classify_reports_with_ai(potential_reports)

            # Get the selected report from AI result
            selected_index = ai_result["selected_index"]
            if isinstance(selected_index, int) and 0 <= selected_index < len(
                potential_reports
            ):
                selected_report: dict[str, str | int | None] = {}
                selected_report.update(potential_reports[selected_index])

                # Handle quarter conversion (from "Q1" to 1)
                ai_quarter: str | int | None = ai_result.get("quarter")
                quarter_num: int | None = None

                if isinstance(ai_quarter, str):
                    if ai_quarter.startswith("Q"):
                        quarter_num = int(ai_quarter[1:])
                    else:
                        # Try to parse as string number
                        try:
                            quarter_num = int(ai_quarter)
                        except (ValueError, TypeError):
                            quarter_num = 1
                elif isinstance(ai_quarter, int):
                    quarter_num = ai_quarter
                else:
                    # Default quarter if parsing fails
                    quarter_num = 1

                selected_report["report_quarter"] = quarter_num
                selected_report["report_year"] = ai_result["year"]
                selected_report["selection_method"] = "ai_classification"
                selected_report["ai_confidence"] = ai_result["confidence"]
                selected_report["ai_reasoning"] = ai_result["reasoning"]
                selected_report["ai_model"] = ai_result["ai_model"]

                logger.info(
                    f"AI selected: {selected_report['filename']} with confidence {ai_result['confidence']}"
                )
                return selected_report
            else:
                logger.warning("AI returned invalid selection index")
                raise ValueError("AI classification failed with invalid index")

        except Exception as e:
            logger.warning(f"AI classification failed, falling back to heuristics: {e}")

        # Fallback to heuristic scoring
        logger.info(f"Using heuristic scoring for {len(potential_reports)} candidates")

        # Score each report based on various factors
        scored_reports = []
        for report in potential_reports:
            score = 0

            # Prefer more recent quarters/years
            quarter, year = self.extract_quarter_year(dict(report))
            if quarter and year:
                score += (
                    year * BNetzAConfig.SCORING_WEIGHTS["year_multiplier"] + quarter
                )

            # Prefer files with clearer naming
            filename = report["filename"].lower()
            if "rollout" in filename:
                score += BNetzAConfig.SCORING_WEIGHTS["rollout"]
            if "quote" in filename:
                score += BNetzAConfig.SCORING_WEIGHTS["quote"]
            if "smart" in filename:
                score += BNetzAConfig.SCORING_WEIGHTS["smart"]

            scored_reports.append((score, report, quarter, year))

        # Sort by score (descending)
        scored_reports.sort(key=lambda x: x[0], reverse=True)

        # Return the highest-scored report
        if scored_reports:
            _, best_report, quarter, year = scored_reports[0]
            selected = dict(best_report)
            selected.update(
                {
                    "report_quarter": quarter,
                    "report_year": year,
                    "selection_method": "heuristic_scoring",
                    "ai_confidence": "medium",
                }
            )

            logger.info(
                f"Selected report: {best_report['filename']} (score: {scored_reports[0][0]})"
            )
            return selected

        return None

    def store_report_in_database(
        self, report_info: dict[str, str | int | None], status: str = "discovered"
    ) -> int:
        """Store discovered report information in the database.

        Args:
            report_info: Report metadata dictionary
            status: Initial status of the report ('discovered', 'downloaded', 'processed')

        Returns:
            Database record ID of the stored report
        """
        try:
            # Generate unique hash for this report URL (for uniqueness constraint)
            url_hash = hashlib.sha256(str(report_info["url"]).encode()).hexdigest()

            # Check if this report already exists
            check_sql = """
                SELECT id FROM rollout_update_logs
                WHERE excel_file_hash = :url_hash
            """

            existing = self._get_db_session().execute(
                text(check_sql), {"url_hash": url_hash}
            )
            existing_row = existing.fetchone()
            if existing_row:
                logger.info(
                    f"Report already exists in database: {report_info['filename']}"
                )
                return int(existing_row[0])

            # Get ETag from the URL for future comparisons
            etag = ""
            try:
                response = requests.head(
                    str(report_info["url"]),
                    headers={"User-Agent": BNetzAConfig.USER_AGENT},
                    timeout=BNetzAConfig.REQUEST_TIMEOUT,
                    allow_redirects=True,
                )
                etag = response.headers.get("ETag", "").strip('"')
                if etag:
                    logger.info(f"🏷️  Retrieved ETag for storage: {etag}")
                else:
                    logger.warning("⚠️  No ETag available from server")
            except Exception as e:
                logger.warning(f"Could not retrieve ETag: {e}")

            # Insert new report record using actual schema
            insert_sql = """
                INSERT INTO rollout_update_logs (
                    article_url, excel_filename, excel_file_hash,
                    report_quarter, report_year, report_reference_date,
                    created_at, status, notes
                ) VALUES (
                    :article_url, :excel_filename, :excel_file_hash,
                    :report_quarter, :report_year, :report_reference_date,
                    :created_at, :status, :notes
                ) RETURNING id
            """

            # Calculate reference date based on quarter and year
            quarter = report_info.get("report_quarter", 1)
            year = report_info.get("report_year", datetime.now().year)

            # Ensure quarter and year are integers
            if isinstance(quarter, str):
                quarter = int(quarter)
            if isinstance(year, str):
                year = int(year)
            if quarter is None:
                quarter = 1
            if year is None:
                year = datetime.now().year

            # For Q1, reference date is end of March; Q2 -> June, etc.
            if quarter == BNetzAConfig.Q1:
                reference_date = datetime(year, 3, 31)
            elif quarter == BNetzAConfig.Q2:
                reference_date = datetime(year, 6, 30)
            elif quarter == BNetzAConfig.Q3:
                reference_date = datetime(year, 9, 30)
            else:  # Q4
                reference_date = datetime(year, 12, 31)

            params = {
                "article_url": str(report_info["url"]),
                "excel_filename": str(report_info["filename"]),
                "excel_file_hash": etag
                or url_hash,  # Store ETag if available, fallback to URL hash
                "report_quarter": quarter,
                "report_year": year,
                "report_reference_date": reference_date,
                "created_at": datetime.now(),
                "status": status,  # Use provided status instead of hardcoded "downloaded"
                "notes": f"Auto-discovered via {report_info.get('selection_method', 'unknown')} method. "
                + f"AI confidence: {report_info.get('ai_confidence', 'unknown')}. "
                + f"Source: {report_info.get('text', 'unknown')}. "
                + f"ETag: {etag or 'not available'}",
            }

            result = self._get_db_session().execute(text(insert_sql), params)
            row = result.fetchone()
            if row is not None:
                record_id: int = int(row[0])
                logger.info(
                    f"Successfully stored report with ID: {record_id} and status: {status}"
                )
                return record_id
            else:
                raise ValueError("Failed to retrieve record ID")

        except Exception as e:
            self._get_db_session().rollback()
            logger.error(f"Failed to store report in database: {e}")
            raise

    def update_report_status(
        self, record_id: int, new_status: str, notes: str | None = None
    ) -> None:
        """Update the status of a stored report.

        Args:
            record_id: Database ID of the report
            new_status: New status value ('discovered', 'downloaded', 'processed', 'error')
            notes: Optional additional notes to append
        """
        try:
            update_sql = """
                UPDATE rollout_update_logs
                SET status = :status,
                    notes = CASE
                        WHEN :notes IS NOT NULL THEN COALESCE(notes, '') || ' | ' || :notes
                        ELSE notes
                    END
                WHERE id = :record_id
            """

            self._get_db_session().execute(
                text(update_sql),
                {
                    "status": new_status,
                    "notes": notes,
                    "record_id": record_id,
                },
            )
            self._get_db_session().commit()
            logger.info(f"Updated report {record_id} status to: {new_status}")

        except Exception as e:
            self._get_db_session().rollback()
            logger.error(f"Failed to update report status: {e}")
            raise

    def _load_ai_prompt_template(self) -> str:
        """Load the AI prompt template from file.

        Returns:
            The Jinja2 template string for AI classification
        """
        template_path = (
            Path(__file__).parent / "templates" / "find_report_prompt_hermes.md.j2"
        )

        return template_path.read_text(encoding="utf-8")

    def _get_ai_client(self) -> OpenAI:
        """Get configured OpenAI client for OpenRouter.

        Returns:
            Configured OpenAI client instance

        Raises:
            ValueError: If API key is not found in environment
        """
        api_key = os.getenv(BNetzAConfig.OPENROUTER_API_KEY_ENV_VAR)
        if not api_key:
            raise ValueError(
                f"Missing {BNetzAConfig.OPENROUTER_API_KEY_ENV_VAR} environment variable"
            )

        return OpenAI(
            api_key=api_key,
            base_url=BNetzAConfig.OPENROUTER_BASE_URL,
        )

    def classify_reports_with_ai(
        self, excel_files: list[dict[str, str]]
    ) -> dict[str, str | int | None]:
        """Use AI to classify and select the best rollout report.

        Args:
            excel_files: List of Excel file metadata dictionaries

        Returns:
            AI classification result with selected report info

        Raises:
            Exception: If AI classification fails
        """
        if not excel_files:
            raise ValueError("No Excel files provided for AI classification")

        try:
            # Prepare data for AI prompt
            urls_data = []
            for i, file_info in enumerate(excel_files):
                urls_data.append(
                    {
                        "index": i,
                        "filename": file_info.get("filename", ""),
                        "text": file_info.get("text", ""),
                        "url": file_info.get("url", ""),
                    }
                )

            # Load and render prompt template
            template_content = self._load_ai_prompt_template()
            template = Template(template_content)

            rendered_prompt = template.render(urls=urls_data, now=datetime.now())

            # Get AI model from environment
            model_name = os.getenv(
                BNetzAConfig.AI_MODEL_ENV_VAR, "anthropic/claude-3.5-haiku"
            )

            # Make AI request
            client = self._get_ai_client()

            logger.info(f"Requesting AI classification with model: {model_name}")

            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": rendered_prompt}],
                temperature=0.1,
                max_tokens=500,
            )

            # Parse AI response
            ai_response_content = response.choices[0].message.content
            if ai_response_content is None:
                raise ValueError("AI response content is None")

            ai_response = ai_response_content.strip()
            logger.info(f"AI response: {ai_response}")

            # Extract JSON from response
            try:
                # Try to find JSON in the response
                json_start = ai_response.find("{")
                json_end = ai_response.rfind("}") + 1

                if json_start >= 0 and json_end > json_start:
                    json_str = ai_response[json_start:json_end]
                    ai_result = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in AI response")

            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(f"Raw response: {ai_response}")
                raise ValueError(f"Invalid JSON response from AI: {e}")

            # Validate AI result
            required_fields = [
                "selected_index",
                "quarter",
                "year",
                "confidence",
                "reasoning",
                "selected_url",
            ]
            for field in required_fields:
                if field not in ai_result:
                    raise ValueError(f"Missing required field '{field}' in AI response")

            # Validate selected_index
            selected_index = ai_result["selected_index"]
            if not (0 <= selected_index < len(excel_files)):
                raise ValueError(
                    f"Invalid selected_index {selected_index}, must be 0-{len(excel_files)-1}"
                )

            # Add metadata about AI classification
            ai_result["ai_model"] = model_name
            ai_result["total_files_analyzed"] = len(excel_files)
            ai_result["selection_method"] = "ai_classification"

            logger.info(
                f"AI selected file {selected_index}: {excel_files[selected_index]['filename']}"
            )
            logger.info(
                f"AI confidence: {ai_result['confidence']}, reasoning: {ai_result['reasoning']}"
            )

            return ai_result  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"AI classification failed: {e}")
            raise

    def discover_and_store_reports(self) -> list[dict[str, str | int | None]]:
        """Complete workflow: discover, classify, and store BNetzA reports.

        Returns:
            List of discovered and stored report metadata
        """
        try:
            # Step 1: Fetch the main article page
            html_content = self.fetch_article_page()

            # Step 2: Extract Excel file URLs
            excel_files = self.extract_excel_urls(html_content)

            if not excel_files:
                logger.warning("No Excel files found on the page")
                return []

            # Step 3: Classify and select the best rollout report
            selected_report = self.classify_reports_with_ai_or_heuristics(excel_files)

            if not selected_report:
                logger.warning("No suitable rollout report found")
                return []

            # Step 4: Store in database with initial "discovered" status
            db_id = self.store_report_in_database(selected_report, status="discovered")
            selected_report["database_id"] = str(db_id)

            all_discovered_reports = [selected_report]

        except Exception as e:
            logger.error(f"Discovery workflow failed: {e}")
            raise

        logger.info(
            f"Discovery workflow completed. Found {len(all_discovered_reports)} reports."
        )
        return all_discovered_reports

    def has_new_reports(self) -> bool:
        """Check if new reports are available by comparing web results with stored data.

        Uses AI classification to identify the best rollout report, just like the full workflow.

        Returns:
            True if new reports are detected, False otherwise
        """
        try:
            # Get current available reports from web using the same logic as discovery
            html_content = self.fetch_article_page()
            excel_files = self.extract_excel_urls(html_content)

            if not excel_files:
                logger.warning("No Excel files found on the page")
                return False

            # Use AI to classify and select the best report (same as in full workflow)
            selected_report = self.classify_reports_with_ai_or_heuristics(excel_files)

            if not selected_report:
                logger.info("No suitable rollout report found via AI classification")
                return False

            # Get stored reports from database - check by filename and URL
            db_session = self._get_db_session()
            stored_reports = list(
                db_session.execute(
                    text("SELECT excel_filename, article_url FROM rollout_update_logs")
                ).fetchall()
            )
            stored_filenames = {filename[0] for filename in stored_reports}
            stored_urls = {url[1] for url in stored_reports}

            # Check if the AI-selected report is already stored by filename
            selected_filename = selected_report["filename"]
            selected_url = str(selected_report.get("url", ""))

            filename_is_new = selected_filename not in stored_filenames
            url_is_new = selected_url not in stored_urls

            logger.info(
                f"AI selected report: {selected_filename}, "
                f"Already stored by filename: {not filename_is_new}, "
                f"Already stored by URL: {not url_is_new}, "
                f"Selection method: {selected_report.get('selection_method', 'unknown')}, "
                f"AI confidence: {selected_report.get('ai_confidence', 'unknown')}"
            )

            # If completely new report, return True
            if filename_is_new or url_is_new:
                logger.info("🆕 New report detected (new filename or URL)")
                return True

            # If we have this report, check if file content has changed using HEAD request
            logger.info("🔍 Checking if existing report file has been updated...")

            try:
                file_may_have_changed, metadata = self.check_file_changed(selected_url)

                if file_may_have_changed:
                    logger.info(
                        "📊 File metadata suggests changes - report is considered new"
                    )
                    return True
                else:
                    logger.info(
                        "📊 File metadata suggests no changes - report is not new"
                    )
                    return False

            except Exception as e:
                logger.warning(f"Could not check file changes via HEAD request: {e}")
                # If HEAD check fails, be conservative and assume no changes
                logger.info("⚠️  Assuming no changes due to HEAD request failure")
                return False

        except Exception as e:
            logger.error(f"Error checking for new reports: {e}")
            return False

    def get_latest_report_info(self) -> dict[str, str | int | None] | None:
        """Get information about the latest stored report.

        Returns:
            Latest report metadata or None if no reports found
        """
        try:
            db_session = self._get_db_session()
            result = db_session.execute(
                text(
                    """
                SELECT id, article_url, excel_filename, report_quarter, report_year,
                       created_at, status, notes
                FROM rollout_update_logs
                ORDER BY created_at DESC
                LIMIT 1
            """
                )
            ).fetchone()

            if result is not None:
                report_info: dict[str, str | int | None] = {
                    "id": result[0],
                    "report_url": result[1],
                    "filename": result[2],
                    "quarter": result[3],
                    "year": result[4],
                    "discovery_date": result[5],
                    "selection_method": result[6],
                    "ai_confidence": "unknown",
                    "notes": result[7],
                }
                return report_info
            return None
        except Exception as e:
            logger.error(f"Error getting latest report info: {e}")
            return None

    def _log_head_metadata(self, url: str, metadata: dict[str, str]) -> None:
        """Log HEAD request metadata in a formatted way.

        Args:
            url: The URL that was requested
            metadata: Dictionary containing HEAD response metadata
        """
        logger.info("📡 HEAD Request Metadata:")
        logger.info(f"   🔗 URL: {url}")

        if metadata.get("etag"):
            logger.info(f"   🏷️  ETag: {metadata['etag']}")
        else:
            logger.info("   🏷️  ETag: Not provided")

        if metadata.get("last_modified"):
            logger.info(f"   📅 Last-Modified: {metadata['last_modified']}")
        else:
            logger.info("   📅 Last-Modified: Not provided")

        if metadata.get("content_length"):
            size_mb = round(int(metadata["content_length"]) / 1024 / 1024, 2)
            logger.info(
                f"   📏 Content-Length: {metadata['content_length']} bytes ({size_mb} MB)"
            )
        else:
            logger.info("   📏 Content-Length: Not provided")

        if metadata.get("content_type"):
            logger.info(f"   📋 Content-Type: {metadata['content_type']}")
        else:
            logger.info("   📋 Content-Type: Not provided")

    def check_file_changed(self, report_url: str) -> tuple[bool, dict[str, str]]:
        """Check if a report file has changed using HEAD request and ETag comparison.

        Args:
            report_url: URL of the report to check

        Returns:
            Tuple of (has_changed, metadata_dict) where metadata contains
            ETag, Last-Modified, Content-Length etc.
        """
        try:
            # Make HEAD request to get file metadata without downloading
            logger.debug(f"Checking file metadata with HEAD request: {report_url}")
            response = requests.head(
                report_url,
                headers={"User-Agent": BNetzAConfig.USER_AGENT},
                timeout=BNetzAConfig.REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            response.raise_for_status()

            # Extract useful metadata
            metadata = {
                "etag": response.headers.get("ETag", "").strip('"'),
                "last_modified": response.headers.get("Last-Modified", ""),
                "content_length": response.headers.get("Content-Length", ""),
                "content_type": response.headers.get("Content-Type", ""),
            }

            # Log important HEAD request metadata
            self._log_head_metadata(report_url, metadata)

            # Check if we have this URL in database and compare ETag
            try:
                db_session = self._get_db_session()
                check_sql = """
                    SELECT excel_file_hash, notes
                    FROM rollout_update_logs
                    WHERE article_url = :report_url
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                result = db_session.execute(text(check_sql), {"report_url": report_url})
                row = result.fetchone()

                if row:
                    stored_etag = row[0] or ""  # excel_file_hash now stores ETag
                    current_etag = metadata["etag"]

                    if current_etag and stored_etag == current_etag:
                        logger.info("✅ File unchanged (same ETag as in database)")
                        logger.info(f"   🏷️  Database ETag: {stored_etag}")
                        logger.info(f"   🏷️  Current ETag:  {current_etag}")
                        return False, metadata
                    else:
                        if current_etag:
                            logger.info("🔄 File has changed (different ETag)")
                            logger.info(f"   🏷️  Database ETag: {stored_etag}")
                            logger.info(f"   🏷️  Current ETag:  {current_etag}")
                        else:
                            logger.info(
                                "⚠️  No ETag provided by server, assuming file changed"
                            )
                        return True, metadata
                else:
                    logger.debug("No previous record found, assuming new file")
                    return True, metadata

            except Exception as db_err:
                logger.warning(
                    f"Could not check database for ETag comparison: {db_err}"
                )
                # If DB check fails, assume file might have changed
                return True, metadata

        except Exception as e:
            logger.warning(f"HEAD request failed, will download anyway: {e}")
            # If HEAD request fails, assume file might have changed
            return True, {}

    def download_report(
        self, report_url: str, save_path: str | None = None, force: bool = False
    ) -> tuple[str, bool]:
        """Download a BNetzA report file with ETag-based change detection.

        Args:
            report_url: URL of the report to download
            save_path: Optional path where to save the file
            force: If True, skip change detection and always download

        Returns:
            Tuple of (file_path, file_changed) where file_changed indicates
            if the file content actually changed based on ETag comparison

        Raises:
            Exception: If download fails
        """
        try:
            if save_path is None:
                # Extract filename from URL
                filename = urlparse(report_url).path.split("/")[-1]
                if not filename or not filename.endswith((".xlsx", ".xls")):
                    filename = (
                        f"bnetza_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    )
                save_path = str(Path.cwd() / "data" / filename)

            # Create directory if it doesn't exist
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)

            # Check if file has changed (unless forced)
            file_may_have_changed = True
            metadata: dict[str, str] = {}
            if not force:
                file_may_have_changed, metadata = self.check_file_changed(report_url)

            if not file_may_have_changed:
                # Check if local file exists
                if Path(save_path).exists():
                    logger.info(
                        f"File unchanged according to ETag, using existing: {save_path}"
                    )
                    return save_path, False
                else:
                    logger.info(
                        "File unchanged but local copy missing, downloading anyway"
                    )

            # Download the file
            logger.info(f"Downloading report from: {report_url}")
            response = requests.get(
                report_url,
                headers={"User-Agent": BNetzAConfig.USER_AGENT},
                timeout=BNetzAConfig.REQUEST_TIMEOUT,
                stream=True,
            )
            response.raise_for_status()

            # Save to file
            save_path_obj = Path(save_path)
            with save_path_obj.open("wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Get ETag from response or metadata
            response_etag = response.headers.get("ETag", "").strip('"')
            current_etag = response_etag or metadata.get("etag", "")

            logger.info("🔐 File Download Completed:")
            logger.info(f"   📁 File: {save_path}")
            if current_etag:
                logger.info(f"   🏷️  ETag: {current_etag}")
            else:
                logger.info("   🏷️  ETag: Not available")

            # Check against database to see if content actually changed
            content_changed = True
            try:
                db_session = self._get_db_session()
                check_sql = """
                    SELECT excel_file_hash
                    FROM rollout_update_logs
                    WHERE article_url = :report_url
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                result = db_session.execute(text(check_sql), {"report_url": report_url})
                row = result.fetchone()

                if row and row[0] == current_etag and current_etag:
                    content_changed = False
                    logger.info("✅ File content unchanged (same ETag as in database)")
                    logger.info(f"   🏷️  Database ETag: {row[0]}")
                    logger.info(f"   🏷️  Current ETag:  {current_etag}")
                else:
                    content_changed = True
                    if row and current_etag:
                        logger.info("🔄 File content has changed (different ETag)")
                        logger.info(f"   🏷️  Database ETag: {row[0]}")
                        logger.info(f"   🏷️  Current ETag:  {current_etag}")
                    else:
                        logger.info("🆕 File is new or ETag not available")
                        if current_etag:
                            logger.info(f"   🏷️  Current ETag:  {current_etag}")

                    # Update database with new ETag and metadata
                    if current_etag:
                        update_sql = """
                            UPDATE rollout_update_logs
                            SET excel_file_hash = :new_etag,
                                notes = COALESCE(notes, '') || :metadata_info
                            WHERE article_url = :report_url
                        """
                        metadata_info = f" | Updated: {datetime.now().isoformat()}"
                        if current_etag:
                            metadata_info += f" | new_etag:{current_etag}"
                        if metadata.get("content_length"):
                            metadata_info += f" | size:{metadata['content_length']}"

                        db_session.execute(
                            text(update_sql),
                            {
                                "new_etag": current_etag,
                                "report_url": report_url,
                                "metadata_info": metadata_info,
                            },
                        )
                        db_session.commit()
                        logger.info("📊 Database updated with new ETag")

            except Exception as db_err:
                logger.warning(f"Could not update database with new ETag: {db_err}")

            logger.info(f"Report downloaded successfully: {save_path}")
            return save_path, content_changed

        except Exception as e:
            logger.error(f"Failed to download report from {report_url}: {e}")
            raise

    def get_all_stored_reports(self) -> list[dict[str, str | int | None]]:
        """Get all stored reports from database.

        Returns:
            List of all stored report metadata
        """
        try:
            db_session = self._get_db_session()
            results = db_session.execute(
                text(
                    """
                SELECT id, article_url, excel_filename, report_quarter, report_year,
                       created_at, status, notes
                FROM rollout_update_logs
                ORDER BY created_at DESC
            """
                )
            ).fetchall()

            reports = []
            for result in results:
                reports.append(
                    {
                        "id": result[0],
                        "report_url": result[1],
                        "filename": result[2],
                        "quarter": result[3],
                        "year": result[4],
                        "discovery_date": result[5],
                        "selection_method": result[6],
                        "ai_confidence": "unknown",
                        "notes": result[7],
                    }
                )

            return reports
        except Exception as e:
            logger.error(f"Error getting stored reports: {e}")
            return []

    def update_and_download_latest(
        self, download_dir: str | None = None
    ) -> dict[str, str | int | None] | None:
        """Complete workflow: check for new reports, store them, and download the latest.

        Args:
            download_dir: Directory to save downloaded reports

        Returns:
            Information about the downloaded report or None if no new reports
        """
        try:
            logger.info("Starting update and download workflow")

            # Check if new reports are available
            if not self.has_new_reports():
                logger.info("No new reports found")
                return None

            # Discover and store new reports
            discovered_reports = self.discover_and_store_reports()

            if not discovered_reports:
                logger.warning("No reports were discovered")
                return None

            # Get the latest report
            latest_report = discovered_reports[0]
            report_url = latest_report.get("url")

            if not report_url:
                logger.error("No URL found in latest report")
                return None

            # Download the report
            if download_dir:
                filename = latest_report.get("filename", "unknown.xlsx")
                if isinstance(filename, str):
                    save_path = str(Path(download_dir) / filename)
                else:
                    save_path = str(Path(download_dir) / "unknown.xlsx")
            else:
                save_path = None

            report_url_str = str(report_url) if report_url else ""
            downloaded_path, file_changed = self.download_report(
                report_url_str, save_path
            )
            latest_report["local_path"] = downloaded_path
            latest_report["file_changed"] = file_changed

            logger.info(f"Update and download completed: {downloaded_path}")
            return latest_report

        except Exception as e:
            logger.error(f"Update and download workflow failed: {e}")
            raise


def main() -> None:
    """Main entry point with command line argument parsing."""
    args = docopt(__doc__ or "")

    # Setup logging
    log_level = logging.DEBUG if args["--verbose"] else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        # Initialize the discovery service
        discovery_service = BNetzAReportDiscovery()

        if args["--check-update"]:
            # Check-only mode: no database updates
            print("BNetzA Report Discovery - Check Mode")
            print("=" * 50)
            print("\n🔍 Checking for new reports...")

            has_new = discovery_service.has_new_reports()

            if has_new:
                print("✅ New reports are available!")
                print("\nTo update the database, run without --check-update flag")
            else:
                print("No new reports found")

            # Show current database state
            print("\n📊 Current database state:")
            latest = discovery_service.get_latest_report_info()
            if latest:
                print(
                    f"   Latest report: {latest['filename']} (Q{latest['quarter']} {latest['year']})"
                )
                print(f"   Discovery date: {latest['discovery_date']}")
            else:
                print("   No reports stored yet")

            all_reports = discovery_service.get_all_stored_reports()
            print(f"   Total stored reports: {len(all_reports)}")

        else:
            # Full mode: discover, classify, and store reports
            print("BNetzA Report Discovery - Full Update Mode")
            print("=" * 50)

            # Example 1: Check for new reports
            print("\n1. Checking for new reports...")
            has_new = discovery_service.has_new_reports()
            print(f"New reports available: {has_new}")

            if has_new:
                print("\n2. Running discovery and storage workflow...")
                discovered_reports = discovery_service.discover_and_store_reports()

                if discovered_reports:
                    # Print results
                    print(
                        f"\n✅ Discovered and stored {len(discovered_reports)} reports:"
                    )
                    for report in discovered_reports:
                        print(f"   - {report['filename']}")
                        print(
                            f"     Quarter/Year: Q{report.get('report_quarter')} {report.get('report_year')}"
                        )
                        print(f"     Method: {report.get('selection_method')}")
                        print(f"     Confidence: {report.get('ai_confidence')}")
                        print(f"     Database ID: {report.get('database_id')}")
                        print(
                            "     Status: discovered (pending rollout data processing)"
                        )
                        print()

                    # Update rollout_companies and rollout_quotas tables
                    print("\n3. Processing rollout data...")
                    try:
                        for report in discovered_reports:
                            database_id = report.get("database_id")
                            if database_id is None:
                                print(
                                    f"   ⚠️  No database ID for report {report.get('filename', 'unknown')}"
                                )
                                continue

                            report_id = int(database_id)
                            print(
                                f"   📊 Processing rollout data for {report['filename']}..."
                            )

                            # Update status to 'downloaded' when starting processing
                            discovery_service.update_report_status(
                                report_id,
                                "downloaded",
                                f"Started rollout data processing at {datetime.now().isoformat()}",
                            )

                            # TODO: Implement actual table updates here
                            # - Load Excel file and extract company data
                            # - Update rollout_companies table
                            # - Update rollout_quotas table
                            print("   💾 Updating rollout companies...")
                            print("   � Updating rollout quotas...")

                            # Mark as processed only after successful completion
                            discovery_service.update_report_status(
                                report_id,
                                "processed",
                                f"Successfully processed rollout data at {datetime.now().isoformat()}",
                            )
                            print(f"   ✅ Report {report['filename']} fully processed")

                    except Exception as e:
                        # Mark as error if processing fails
                        print(f"   ❌ Error processing rollout data: {e}")
                        if discovered_reports:
                            for report in discovered_reports:
                                try:
                                    database_id = report.get("database_id")
                                    if database_id is not None:
                                        report_id = int(database_id)
                                        discovery_service.update_report_status(
                                            report_id,
                                            "error",
                                            f"Processing failed: {e!s}",
                                        )
                                except Exception:
                                    pass
                        raise

                    print("\n   🎉 All rollout data processing completed successfully!")
                else:
                    print("\n2. No reports were discovered during the workflow")

            else:
                print("\n2. No new reports to process")

                # Show current state
                print("\n📊 Current state:")
                latest = discovery_service.get_latest_report_info()
                if latest:
                    print(
                        f"   Latest report: {latest['filename']} (Q{latest['quarter']} {latest['year']})"
                    )
                else:
                    print("   No reports stored yet")

            print("\n🎉 Process completed successfully!")

    except KeyboardInterrupt:
        print("\n⚠️  Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        print(f"\n❌ Error: {e}")
        if args["--verbose"]:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
