#!/usr/bin/env python3
"""
VNBdigitaler - Intelligent Company Matching System

This script combines the functionality of tools 13, 14, and 15 into a unified intelligent
company matching system that:
1. Automatically marks exact matches as manually_checked=True
2. Uses LLM assistance for ambiguous cases
3. Updates the database with high-confidence matches

Usage:
    python tools/16_intelligent_company_matching.py [--dry-run] [--max-llm-requests=50]

Author: GitHub Copilot
Date: 2025-08-22
"""

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path

import aiohttp
from jinja2 import Template
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# isort: off
from src.config import get_settings  # noqa: E402

# isort: on

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Configuration constants
EXACT_MATCH_THRESHOLD = 100  # Only perfect string matches
HIGH_CONFIDENCE_THRESHOLD = 97  # Auto-accept LLM matches above this
LOW_CONFIDENCE_THRESHOLD = 80  # All other matches below this must be low
MAX_LLM_RETRIES = 3
LLM_TIMEOUT = 30  # seconds


class CompanyMatcher:
    """Intelligent company matching system with LLM assistance."""

    def __init__(self, dry_run: bool = False, max_llm_requests: int = 50):
        """Initialize the company matcher."""
        self.dry_run = dry_run
        self.max_llm_requests = max_llm_requests
        self.llm_requests_made = 0
        self.settings = get_settings()

        # Setup database connection
        db_url = self.settings.neon_database_url
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql+psycopg2://"):
            db_url = db_url.replace(
                "postgresql+psycopg2://", "postgresql+asyncpg://", 1
            )

        # Remove URL parameters for asyncpg compatibility
        if "?" in db_url:
            db_url = db_url.split("?")[0]

        self.engine = create_async_engine(db_url, echo=False, future=True)
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        # Load prompt template
        self.prompt_template = self._load_prompt_template()

        # Statistics
        self.stats = {
            "total_companies": 0,
            "exact_matches": 0,
            "llm_high_confidence": 0,
            "llm_low_confidence": 0,
            "manual_review_needed": 0,
            "already_checked": 0,
            "errors": 0,
        }

    def _load_prompt_template(self) -> str:
        """Load the LLM prompt template."""
        template_path = (
            Path(__file__).parent / "templates" / "company_matching_prompt.txt"
        )
        try:
            return template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.error(f"❌ Prompt template not found: {template_path}")
            raise

    async def get_companies_needing_matching(self) -> list[dict]:
        """Get companies that need matching (rollout_company_manually_checked = FALSE)."""
        query = """
        SELECT
            id,
            bdew_code,
            bdew_name,
            rollout_report_name,
            rollout_company_manually_checked
        FROM companies
        WHERE rollout_report_name IS NOT NULL
        AND (rollout_company_manually_checked IS NULL OR rollout_company_manually_checked = FALSE)
        ORDER BY bdew_code;
        """

        async with self.session_factory() as session:
            result = await session.execute(text(query))
            companies = []
            for row in result:
                companies.append(
                    {
                        "id": row.id,
                        "bdew_code": row.bdew_code,
                        "bdew_name": row.bdew_name,
                        "rollout_report_name": row.rollout_report_name,
                        "manually_checked": row.rollout_company_manually_checked
                        or False,
                    }
                )
            return companies

    async def get_available_bdew_companies(self) -> list[dict]:
        """Get BDEW companies that haven't been manually checked yet for LLM matching context."""
        query = """
        SELECT
            bdew_code,
            bdew_name,
            bdew_city
        FROM companies
        WHERE bdew_name IS NOT NULL
        AND (rollout_company_manually_checked IS NULL OR rollout_company_manually_checked = FALSE)
        ORDER BY LENGTH(bdew_name) DESC, bdew_name;
        """

        async with self.session_factory() as session:
            result = await session.execute(text(query))
            companies = []
            for row in result:
                companies.append(
                    {
                        "bdew_code": row.bdew_code,
                        "bdew_name": row.bdew_name,
                        "bdew_city": row.bdew_city,
                    }
                )
            return companies

    def check_exact_match(self, rollout_name: str, bdew_name: str) -> bool:
        """Check if two company names are exactly the same."""
        if not rollout_name or not bdew_name:
            return False
        return rollout_name.strip().lower() == bdew_name.strip().lower()

    def format_bdew_companies_for_llm(self, bdew_companies: list[dict]) -> str:
        """Format BDEW companies list for LLM prompt."""
        formatted_companies = []
        for company in bdew_companies:
            city_info = f" [{company['bdew_city']}]" if company["bdew_city"] else ""
            formatted_companies.append(
                f"Code: {company['bdew_code']} | Name: {company['bdew_name']}{city_info}"
            )
        return "\n".join(formatted_companies)

    async def query_llm(
        self, rollout_company_name: str, bdew_companies: list[dict]
    ) -> dict | None:
        """Query LLM for company matching assistance."""
        if self.llm_requests_made >= self.max_llm_requests:
            logger.warning(f"⚠️ Maximum LLM requests ({self.max_llm_requests}) reached")
            return None

        # Render the complete template with Jinja2
        bdew_list = self.format_bdew_companies_for_llm(bdew_companies)
        template = Template(self.prompt_template)
        rendered_prompt = template.render(
            rollout_company_name=rollout_company_name, bdew_companies_list=bdew_list
        )

        # Use OpenRouter API
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/the78mole/vnbdigitaler",
            "X-Title": "VNB-Digitaler Company Matching",
        }

        payload = {
            "model": self.settings.roll_out_report_find_model,
            "messages": [{"role": "user", "content": rendered_prompt}],
            "temperature": 0.1,
            "max_tokens": 1000,
        }

        # HTTP status constants
        HTTP_OK = 200

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=LLM_TIMEOUT)
            ) as session, session.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                if response.status == HTTP_OK:
                    data = await response.json()
                    raw_content = data["choices"][0]["message"]["content"]

                    # Log the completely raw response
                    logger.info(f"🔍 RAW LLM RESPONSE: {raw_content!r}")

                    content = raw_content.strip() if raw_content else ""

                    # Try to extract JSON from response
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif content.startswith("```") and content.endswith("```"):
                        content = content[3:-3].strip()

                    # Look for JSON object start/end
                    if not content.startswith("{"):
                        start_idx = content.find("{")
                        if start_idx != -1:
                            content = content[start_idx:]

                    if not content.endswith("}"):
                        end_idx = content.rfind("}")
                        if end_idx != -1:
                            content = content[: end_idx + 1]

                    self.llm_requests_made += 1

                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as json_error:
                        logger.error(f"❌ JSON parsing failed for response: {content!r}")
                        logger.error(f"❌ JSON Error: {json_error}")

                        # Try regex extraction
                        json_pattern = r"\{(?:[^{}]|{[^{}]*})*\}"
                        matches = re.findall(json_pattern, content, re.DOTALL)

                        for i, match in enumerate(matches):
                            logger.info(f"🔧 Trying regex match {i+1}")
                            try:
                                return json.loads(match)
                            except json.JSONDecodeError:
                                continue

                        logger.error("❌ All JSON parsing attempts failed")
                        return None
                else:
                    logger.error(f"❌ LLM API error: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"❌ LLM query failed: {e}")
            return None

    async def update_company_manually_checked(
        self, company_id: int, checked: bool = True
    ) -> None:
        """Update the manually_checked status of a company."""
        if self.dry_run:
            logger.info(
                f"🔍 DRY RUN: Would set company {company_id} manually_checked = {checked}"
            )
            return

        async with self.session_factory() as session:
            try:
                query = text(
                    """
                    UPDATE companies
                    SET rollout_company_manually_checked = :checked
                    WHERE id = :company_id
                """
                )
                await session.execute(
                    query, {"checked": checked, "company_id": company_id}
                )
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Failed to update company {company_id}: {e}")
                raise

    async def process_exact_matches(self, companies: list[dict]) -> list[dict]:
        """Process exact matches and return remaining companies."""
        remaining_companies = []

        for company in companies:
            if self.check_exact_match(
                company["rollout_report_name"], company["bdew_name"]
            ):
                logger.info(
                    f"✅ Exact match: {company['bdew_code']} - {company['bdew_name']}"
                )
                await self.update_company_manually_checked(company["id"], True)
                self.stats["exact_matches"] += 1
            else:
                remaining_companies.append(company)

        return remaining_companies

    async def process_llm_matching(
        self, companies: list[dict], bdew_companies: list[dict]
    ) -> None:
        """Process companies using LLM assistance - one by one."""
        for company in companies:
            if self.llm_requests_made >= self.max_llm_requests:
                logger.warning("⚠️ Stopping LLM processing - max requests reached")
                break

            rollout_name = company["rollout_report_name"]
            logger.info(f"🤖 LLM analysis: {company['bdew_code']} - {rollout_name}")

            # Query LLM
            llm_result = await self.query_llm(rollout_name, bdew_companies)

            if not llm_result:
                logger.warning(f"⚠️ LLM query failed for: {rollout_name}")
                self.stats["errors"] += 1
                continue

            try:
                matches = llm_result.get("matches", [])
                recommendation = llm_result.get("recommendation", {})

                if not matches:
                    logger.warning(f"⚠️ No matches found for: {rollout_name}")
                    self.stats["manual_review_needed"] += 1
                    continue

                # Check if we have a high-confidence single match
                best_match = matches[0]
                best_confidence = best_match.get("confidence", 0)

                # Check if all other matches are below threshold
                other_matches_low = all(
                    match.get("confidence", 0) < LOW_CONFIDENCE_THRESHOLD
                    for match in matches[1:]
                )

                if (
                    best_confidence > HIGH_CONFIDENCE_THRESHOLD
                    and other_matches_low
                    and recommendation.get("is_high_confidence", False)
                ):
                    logger.info(
                        f"🎯 High confidence LLM match ({best_confidence}%): "
                        f"{rollout_name} -> {best_match['bdew_name']}"
                    )
                    await self.update_company_manually_checked(company["id"], True)
                    self.stats["llm_high_confidence"] += 1
                else:
                    logger.info(
                        f"🤔 Manual review needed ({best_confidence}%): {rollout_name}"
                    )
                    self.stats["manual_review_needed"] += 1

            except Exception as e:
                logger.error(f"❌ Error processing LLM result for {rollout_name}: {e}")
                self.stats["errors"] += 1

    async def run_matching(self) -> bool:
        """Run the complete intelligent matching process."""
        try:
            logger.info("🚀 VNBdigitaler - Intelligent Company Matching System")
            logger.info("=" * 60)

            # Get companies needing matching
            logger.info("📊 Loading companies needing matching...")
            companies = await self.get_companies_needing_matching()
            self.stats["total_companies"] = len(companies)

            if not companies:
                logger.info("✅ No companies need matching!")
                return True

            logger.info(f"📋 Found {len(companies)} companies needing matching")

            # Process exact matches first
            logger.info("🔍 Processing exact matches...")
            remaining_companies = await self.process_exact_matches(companies)

            logger.info(f"✅ Processed {self.stats['exact_matches']} exact matches")
            logger.info(
                f"📝 {len(remaining_companies)} companies remain for LLM analysis"
            )

            # Get BDEW companies for LLM context
            if remaining_companies and self.llm_requests_made < self.max_llm_requests:
                logger.info("📚 Loading available BDEW companies for LLM context...")
                bdew_companies = await self.get_available_bdew_companies()
                logger.info(f"📖 Loaded {len(bdew_companies)} available BDEW companies")

                # Process remaining companies with LLM
                logger.info("🤖 Starting LLM-assisted matching...")
                await self.process_llm_matching(remaining_companies, bdew_companies)

            # Print final statistics
            self._print_final_stats()
            return True

        except Exception as e:
            logger.error(f"❌ Matching process failed: {e}")
            return False
        finally:
            await self.engine.dispose()

    def _print_final_stats(self) -> None:
        """Print final statistics summary."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 INTELLIGENT MATCHING RESULTS")
        logger.info("=" * 60)
        logger.info(f"📋 Total companies processed: {self.stats['total_companies']}")
        logger.info(f"✅ Exact matches (auto-approved): {self.stats['exact_matches']}")
        logger.info(
            f"🎯 LLM high-confidence matches: {self.stats['llm_high_confidence']}"
        )
        logger.info(f"🤔 Manual review needed: {self.stats['manual_review_needed']}")
        logger.info(f"❌ Errors encountered: {self.stats['errors']}")
        logger.info(
            f"🤖 LLM requests made: {self.llm_requests_made}/{self.max_llm_requests}"
        )

        total_automated = (
            self.stats["exact_matches"] + self.stats["llm_high_confidence"]
        )
        if self.stats["total_companies"] > 0:
            automation_rate = (total_automated / self.stats["total_companies"]) * 100
            logger.info(f"🎉 Automation rate: {automation_rate:.1f}%")


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Intelligent company matching with LLM assistance"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )
    parser.add_argument(
        "--max-llm-requests",
        type=int,
        default=50,
        help="Maximum number of LLM requests to make (default: 50)",
    )

    args = parser.parse_args()

    matcher = CompanyMatcher(
        dry_run=args.dry_run, max_llm_requests=args.max_llm_requests
    )
    success = await matcher.run_matching()

    if success:
        logger.info("✅ Intelligent matching completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Intelligent matching failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
