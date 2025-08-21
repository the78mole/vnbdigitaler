#!/usr/bin/env python3
"""
VNBdigitaler - LLM-based BDEW to BNetzA Company Matching

This script performs LLM-assisted matching for BDEW companies that:
1. Are not already manually checked
2. Don't have exact string matches with BNetzA rollout names
3. Need intelligent matching using LLM analysis

Usage:
    python tools/17_llm_bdew_bnetza_company_match.py data/Roll-out-Quoten_Q1_2025.csv [--dry-run] [--max-llm-requests=50]

Author: GitHub Copilot
Date: 2025-08-22
"""

import argparse
import asyncio
import csv
import json
import logging
import re
import sys
from pathlib import Path

from jinja2 import Template
from openai import AsyncOpenAI
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
HIGH_CONFIDENCE_THRESHOLD = 97  # Auto-accept LLM matches above this
LLM_TIMEOUT = 30  # seconds


class BDEWBNetzAMatcher:
    """LLM-based matcher for BDEW companies against BNetzA rollout names."""

    def __init__(
        self, bnetz_csv_path: str, dry_run: bool = False, max_llm_requests: int = 50
    ):
        """Initialize the matcher."""
        self.bnetz_csv_path = Path(bnetz_csv_path)
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

        # Load Jinja2 template
        self.template = self._load_template()

        # Setup OpenAI client for OpenRouter
        self.openai_client = AsyncOpenAI(
            api_key=self.settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
        )

        # Statistics
        self.stats = {
            "total_bdew_companies": 0,
            "already_checked": 0,
            "exact_matches": 0,
            "llm_high_confidence": 0,
            "manual_review_needed": 0,
            "no_matches": 0,
            "errors": 0,
        }

    def _load_template(self) -> Template:
        """Load the Jinja2 template for LLM prompts."""
        template_path = (
            Path(__file__).parent / "templates" / "match_bdew_to_BNetzA.md.j2"
        )
        try:
            template_content = template_path.read_text(encoding="utf-8")
            return Template(template_content)
        except FileNotFoundError:
            logger.error(f"❌ Template not found: {template_path}")
            raise

    async def get_bdew_companies_for_matching(self) -> list[dict]:
        """Get BDEW companies that need LLM matching."""
        query = """
        SELECT
            id,
            bdew_code,
            bdew_name,
            bdew_city,
            rollout_report_name,
            rollout_company_manually_checked
        FROM companies
        WHERE bdew_name IS NOT NULL
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
                        "bdew_city": row.bdew_city,
                        "rollout_report_name": row.rollout_report_name,
                        "manually_checked": row.rollout_company_manually_checked
                        or False,
                    }
                )
            return companies

    def get_unmatched_bnetz_companies(self) -> list[str]:
        """Get all BNetzA rollout company names from CSV file."""
        if not self.bnetz_csv_path.exists():
            logger.error(f"❌ BNetzA CSV file not found: {self.bnetz_csv_path}")
            return []

        bnetz_companies = []
        try:
            with self.bnetz_csv_path.open(encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    company_name = row.get("Unternehmen", "").strip()
                    if company_name:
                        bnetz_companies.append(company_name)

            logger.info(f"📋 Loaded {len(bnetz_companies)} BNetzA companies from CSV")
            return sorted(bnetz_companies)

        except Exception as e:
            logger.error(f"❌ Error reading BNetzA CSV file: {e}")
            return []

    async def filter_bnetz_companies_by_db(
        self, bnetz_companies: list[str]
    ) -> list[str]:
        """Filter out BNetzA companies that are already manually verified in DB."""
        if not bnetz_companies:
            return []

        query = """
        SELECT DISTINCT rollout_report_name
        FROM companies
        WHERE rollout_report_name IS NOT NULL
        AND rollout_company_manually_checked = TRUE;
        """

        try:
            async with self.session_factory() as session:
                result = await session.execute(text(query))
                manually_checked_names = {row.rollout_report_name for row in result}

            # Filter out already verified companies
            filtered_companies = [
                company
                for company in bnetz_companies
                if company not in manually_checked_names
            ]

            removed_count = len(bnetz_companies) - len(filtered_companies)
            logger.info(
                f"🔍 Filtered out {removed_count} already manually verified BNetzA companies"
            )
            logger.info(
                f"📋 Remaining {len(filtered_companies)} unverified BNetzA companies"
            )

            return filtered_companies

        except Exception as e:
            logger.error(f"❌ Error filtering BNetzA companies by DB: {e}")
            return bnetz_companies  # Return original list on error

    async def perform_string_matching(
        self, bdew_companies: list[dict], bnetz_companies: list[str]
    ) -> tuple[list[dict], list[str], list[dict]]:
        """Perform exact string matching between BDEW and BNetzA companies.

        Returns:
            tuple: (unmatched_bdew, remaining_bnetz, matched_pairs)
        """
        unmatched_bdew = []
        remaining_bnetz = bnetz_companies.copy()
        matched_pairs = []

        for bdew_company in bdew_companies:
            bdew_name = bdew_company["bdew_name"]
            match_found = False

            # Check for exact matches in remaining BNetzA companies
            for bnetz_name in remaining_bnetz:
                if self.check_exact_match(bdew_name, bnetz_name):
                    matched_pairs.append(
                        {
                            "bdew_company": bdew_company,
                            "bnetz_name": bnetz_name,
                            "match_type": "exact_string",
                        }
                    )
                    remaining_bnetz.remove(bnetz_name)
                    match_found = True
                    logger.info(f"✅ String match: {bdew_name} -> {bnetz_name}")
                    break

            if not match_found:
                unmatched_bdew.append(bdew_company)

        logger.info("🔍 String matching results:")
        logger.info(f"  📊 Exact matches found: {len(matched_pairs)}")
        logger.info(f"  📋 Unmatched BDEW companies: {len(unmatched_bdew)}")
        logger.info(f"  📋 Remaining BNetzA companies: {len(remaining_bnetz)}")

        return unmatched_bdew, remaining_bnetz, matched_pairs

    def check_exact_match(self, bdew_name: str, rollout_name: str) -> bool:
        """Check if two company names are exactly the same."""
        if not bdew_name or not rollout_name:
            return False
        return bdew_name.strip().lower() == rollout_name.strip().lower()

    async def query_llm(
        self, bdew_company: dict, bnetz_companies: list[str]
    ) -> dict | None:
        """Query LLM for company matching using Jinja2 template."""
        if self.llm_requests_made >= self.max_llm_requests:
            logger.warning(f"⚠️ Maximum LLM requests ({self.max_llm_requests}) reached")
            return None

        # Render the template
        prompt = self.template.render(
            bdew_company=bdew_company, bnetz_companies=bnetz_companies
        )

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.settings.roll_out_report_find_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500,
                timeout=LLM_TIMEOUT,
                extra_headers={
                    "HTTP-Referer": "https://github.com/the78mole/vnbdigitaler",
                    "X-Title": "VNB-Digitaler BDEW-BNetzA Matching",
                },
            )

            raw_content = response.choices[0].message.content
            logger.info(
                f"🔍 RAW LLM RESPONSE for {bdew_company['bdew_name']}: {raw_content!r}"
            )

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
                logger.error(
                    f"❌ JSON parsing failed for {bdew_company['bdew_name']}: {content!r}"
                )
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

        except Exception as e:
            logger.error(f"❌ LLM query failed for {bdew_company['bdew_name']}: {e}")
            return None

    async def update_company_rollout_match(
        self, company_id: int, matched_name: str | None
    ) -> None:
        """Update the rollout_report_name for a company and mark as manually checked."""
        if self.dry_run:
            logger.info(
                f"🔍 DRY RUN: Would update company {company_id} with rollout_report_name='{matched_name}' and manually_checked=True"
            )
            return

        async with self.session_factory() as session:
            try:
                if matched_name:
                    # Update with matched name
                    query = text(
                        """
                        UPDATE companies
                        SET rollout_report_name = :matched_name,
                            rollout_company_manually_checked = TRUE
                        WHERE id = :company_id
                    """
                    )
                    await session.execute(
                        query, {"matched_name": matched_name, "company_id": company_id}
                    )
                else:
                    # Just mark as manually checked (no match found)
                    query = text(
                        """
                        UPDATE companies
                        SET rollout_company_manually_checked = TRUE
                        WHERE id = :company_id
                    """
                    )
                    await session.execute(query, {"company_id": company_id})

                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Failed to update company {company_id}: {e}")
                raise

    async def process_bdew_company(
        self, bdew_company: dict, bnetz_companies: list[str]
    ) -> None:
        """Process a single BDEW company for matching."""
        bdew_name = bdew_company["bdew_name"]

        # Skip if already manually checked
        if bdew_company["manually_checked"]:
            self.stats["already_checked"] += 1
            return

        # Check for exact match with existing rollout_report_name
        if bdew_company["rollout_report_name"] and self.check_exact_match(
            bdew_name, bdew_company["rollout_report_name"]
        ):
            logger.info(f"✅ Exact match already exists: {bdew_name}")
            await self.update_company_rollout_match(
                bdew_company["id"], bdew_company["rollout_report_name"]
            )
            self.stats["exact_matches"] += 1
            return

        # Query LLM for matching
        logger.info(f"🤖 LLM analysis for BDEW: {bdew_name}")
        llm_result = await self.query_llm(bdew_company, bnetz_companies)

        if not llm_result:
            logger.warning(f"⚠️ LLM query failed for: {bdew_name}")
            self.stats["errors"] += 1
            return

        try:
            best_match = llm_result.get("best_match")
            recommendation = llm_result.get("recommendation", {})

            # Handle case where best_match is None/null
            if best_match is None:
                confidence = 0
                matched_name = None
            else:
                confidence = best_match.get("confidence", 0)
                matched_name = best_match.get("bnetz_name")

            action = recommendation.get("action", "manual_review")

            if (
                action == "auto_approve"
                and confidence > HIGH_CONFIDENCE_THRESHOLD
                and matched_name
            ):
                logger.info(
                    f"🎯 High confidence LLM match ({confidence}%): {bdew_name} -> {matched_name}"
                )
                await self.update_company_rollout_match(
                    bdew_company["id"], matched_name
                )
                self.stats["llm_high_confidence"] += 1
            elif action == "no_match":
                logger.info(f"❌ No match found for: {bdew_name}")
                await self.update_company_rollout_match(bdew_company["id"], None)
                self.stats["no_matches"] += 1
            else:
                logger.info(f"🤔 Manual review needed ({confidence}%): {bdew_name}")
                self.stats["manual_review_needed"] += 1

        except Exception as e:
            logger.error(f"❌ Error processing LLM result for {bdew_name}: {e}")
            self.stats["errors"] += 1

    async def run_matching(self) -> bool:
        """Run the optimized BDEW to BNetzA matching process."""
        try:
            logger.info("🚀 VNBdigitaler - LLM BDEW to BNetzA Company Matching")
            logger.info("=" * 60)

            # Step 1: Get BDEW companies needing matching
            logger.info("📊 Loading BDEW companies needing matching...")
            bdew_companies = await self.get_bdew_companies_for_matching()
            self.stats["total_bdew_companies"] = len(bdew_companies)

            if not bdew_companies:
                logger.info("✅ No BDEW companies need matching!")
                return True

            # Step 2: Load BNetzA companies from CSV
            logger.info("📋 Loading BNetzA companies from CSV...")
            all_bnetz_companies = self.get_unmatched_bnetz_companies()

            # Step 3: Filter BNetzA companies - remove already manually verified ones
            logger.info(
                "� Filtering BNetzA companies by database verification status..."
            )
            available_bnetz_companies = await self.filter_bnetz_companies_by_db(
                all_bnetz_companies
            )

            if not available_bnetz_companies:
                logger.warning(
                    "⚠️ No unverified BNetzA companies available for matching!"
                )
                return True

            # Step 4: Filter BDEW companies - remove those already checked
            unprocessed_bdew = [
                company for company in bdew_companies if not company["manually_checked"]
            ]

            checked_count = len(bdew_companies) - len(unprocessed_bdew)
            self.stats["already_checked"] = checked_count
            logger.info(f"📊 Skipping {checked_count} already checked BDEW companies")
            logger.info(
                f"📋 Processing {len(unprocessed_bdew)} unprocessed BDEW companies"
            )

            # Step 5: Perform exact string matching
            logger.info("🔍 Performing exact string matching...")
            (
                unmatched_bdew,
                remaining_bnetz,
                string_matches,
            ) = await self.perform_string_matching(
                unprocessed_bdew, available_bnetz_companies
            )

            # Update database with string matches
            for match in string_matches:
                bdew_company = match["bdew_company"]
                bnetz_name = match["bnetz_name"]
                logger.info(
                    f"💾 Updating string match: {bdew_company['bdew_name']} -> {bnetz_name}"
                )
                await self.update_company_rollout_match(bdew_company["id"], bnetz_name)
                self.stats["exact_matches"] += 1

            # Step 6: LLM matching for remaining companies
            if unmatched_bdew and remaining_bnetz:
                logger.info(
                    f"🤖 Starting LLM matching for {len(unmatched_bdew)} remaining BDEW companies..."
                )

                for bdew_company in unmatched_bdew:
                    if self.llm_requests_made >= self.max_llm_requests:
                        logger.warning("⚠️ Stopping - max LLM requests reached")
                        break

                    await self.process_bdew_company(bdew_company, remaining_bnetz)
            else:
                logger.info(
                    "✅ All companies matched via string matching - no LLM matching needed!"
                )

            # Print final statistics
            self._print_final_stats()
            return True

        except Exception as e:
            logger.error(f"❌ Matching process failed: {e}")
            return False
        finally:
            await self.engine.dispose()
            await self.openai_client.close()

    def _print_final_stats(self) -> None:
        """Print final statistics summary."""
        logger.info("\n" + "=" * 60)
        logger.info("📊 LLM BDEW-BNETZA MATCHING RESULTS")
        logger.info("=" * 60)
        logger.info(
            f"📋 Total BDEW companies processed: {self.stats['total_bdew_companies']}"
        )
        logger.info(f"✅ Already checked: {self.stats['already_checked']}")
        logger.info(f"🔄 Exact matches found: {self.stats['exact_matches']}")
        logger.info(
            f"🎯 LLM high-confidence matches: {self.stats['llm_high_confidence']}"
        )
        logger.info(f"🤔 Manual review needed: {self.stats['manual_review_needed']}")
        logger.info(f"❌ No matches found: {self.stats['no_matches']}")
        logger.info(f"⚠️ Errors encountered: {self.stats['errors']}")
        logger.info(
            f"🤖 LLM requests made: {self.llm_requests_made}/{self.max_llm_requests}"
        )

        total_automated = (
            self.stats["exact_matches"] + self.stats["llm_high_confidence"]
        )
        processed = self.stats["total_bdew_companies"] - self.stats["already_checked"]
        if processed > 0:
            automation_rate = (total_automated / processed) * 100
            logger.info(f"🎉 Automation rate: {automation_rate:.1f}%")


async def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="LLM-based BDEW to BNetzA company matching"
    )
    parser.add_argument(
        "bnetz_csv",
        help="Path to the BNetzA CSV file (e.g., data/Roll-out-Quoten_Q1_2025.csv)",
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

    matcher = BDEWBNetzAMatcher(
        bnetz_csv_path=args.bnetz_csv,
        dry_run=args.dry_run,
        max_llm_requests=args.max_llm_requests,
    )
    success = await matcher.run_matching()

    if success:
        logger.info("✅ LLM BDEW-BNetzA matching completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ LLM BDEW-BNetzA matching failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
