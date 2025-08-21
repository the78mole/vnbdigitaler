#!/usr/bin/env python3
"""
VNBdigitaler - Structured Company Matching Script

This script implements a structured approach to company matching with clear steps:
1. Load BNetzA companies from CSV
2. Match existing rollout_report_name entries from database
3. Match rollout_name_variations from database
4. Find exact matches and update database
5. Find normalized exact matches and update database
6. LLM-assisted matching with user interaction
7. Mark remaining as UNMATCHED

Author: VNBdigitaler Project
Date: 2025-08-22
"""

import asyncio
import contextlib
import csv
import json
import logging
import os
import re
import sys
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
from fuzzywuzzy import fuzz
from sqlalchemy import text

try:
    from dotenv import load_dotenv

    load_dotenv()  # Load .env file if it exists
except ImportError:
    pass  # dotenv is optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from sqlalchemy import update

    from src.models import Company

    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

# Add src to path for imports
_src_path = str(Path(__file__).parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from src.data_loader import DataLoader  # noqa: E402
from src.matching_models import BDEWCompany, BNetzACompany  # noqa: E402

# Constants
LLM_MODEL = "openai/gpt-4o-mini"  # OpenRouter model for classification tasks
LLM_MIN_CONFIDENCE = 0.95  # High confidence threshold for automatic matching
FUZZY_THRESHOLD = 70  # Minimum fuzzy match score
UNMATCHED_RETRY_THRESHOLD = 95  # Minimum score to retry previously unmatched companies
NORMALIZED_FUZZY_THRESHOLD = 0.85  # High threshold for normalized fuzzy matching (85%)
UNMATCHED_MARKER = "UNMATCHED"
MIN_WORD_LENGTH = 3  # Minimum length for meaningful words in matching
PROGRESS_LOG_THRESHOLD = (
    50  # Log progress for operations with more than this many items
)
PROGRESS_CHECK_INTERVAL = 25  # Check interval for progress logging

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class StructuredCompanyMatcher:
    """Structured company matcher with clear step-by-step processing."""

    def __init__(self, data_loader: DataLoader):
        """Initialize the structured matcher."""
        self.data_loader = data_loader
        self.bnetza_companies: list[BNetzACompany] = []
        self.bdew_companies: list[BDEWCompany] = []
        self.remaining_bnetza: list[BNetzACompany] = []

        # Statistics tracking
        self.stats = {
            "initial_bnetza_count": 0,
            "rollout_name_matches": 0,
            "variation_matches": 0,
            "exact_matches": 0,
            "normalized_matches": 0,
            "llm_matches": 0,
            "user_matches": 0,
            "unmatched": 0,
        }

    async def step_1_load_bnetza_companies(self, csv_path: Path) -> bool:
        """Step 1: Load BNetzA companies from CSV."""
        logger.info("=" * 60)
        logger.info("📝 STEP 1: Loading BNetzA companies from CSV")
        logger.info("=" * 60)

        try:
            if not csv_path.exists():
                logger.error(f"❌ BNetzA CSV file not found: {csv_path}")
                return False

            logger.info(f"📖 Reading CSV file: {csv_path}")

            df = pd.read_csv(csv_path)
            self.bnetza_companies = []

            row_index = 0
            for _index, row in df.iterrows():
                # Extract company name - try different possible column names
                name = ""
                possible_name_columns = [
                    "Unternehmen",  # German BNetzA reports
                    "company_name",
                    "name",
                    "original_name",
                    "Company",  # English reports
                    "Netzbetreiber",  # Another common German column
                ]

                for col in possible_name_columns:
                    if col in row and pd.notna(row[col]):
                        name = str(row[col]).strip()
                        break

                # Extract rollout quote if available
                rollout_quote = None
                possible_quote_columns = [
                    "Ausstattungsquote zum 31. März 2025",  # German BNetzA reports
                    "rollout_quote",
                    "quote",
                    "percentage",
                ]

                for col in possible_quote_columns:
                    if col in row and pd.notna(row[col]):
                        with contextlib.suppress(ValueError, TypeError):
                            rollout_quote = float(row[col])
                        break

                if name:
                    company = BNetzACompany(
                        index=row_index,
                        original_name=name,
                        rollout_quote=rollout_quote,
                    )
                    self.bnetza_companies.append(company)
                    row_index += 1

            self.remaining_bnetza = self.bnetza_companies.copy()
            self.stats["initial_bnetza_count"] = len(self.bnetza_companies)

            logger.info(
                f"✅ Successfully loaded {len(self.bnetza_companies)} BNetzA companies"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load BNetzA companies: {e}")
            return False

    async def step_2_load_bdew_and_match_rollout_names(self) -> bool:
        """Step 2: Load BDEW companies and match existing rollout_report_name entries."""
        logger.info("=" * 60)
        logger.info("📊 STEP 2: Matching existing rollout_report_name entries")
        logger.info("=" * 60)

        try:
            logger.info("📖 Loading BDEW companies from database...")
            self.bdew_companies = await self.data_loader.load_bdew_companies_from_db()
            logger.info(
                f"✅ Loaded {len(self.bdew_companies)} BDEW companies from database"
            )

            # Match existing rollout_report_name entries
            matches_found = 0
            bnetza_names = {
                company.original_name.lower().strip()
                for company in self.remaining_bnetza
            }

            for bdew_company in self.bdew_companies:
                if bdew_company.rollout_report_name:
                    normalized_rollout_name = (
                        bdew_company.rollout_report_name.lower().strip()
                    )
                    if normalized_rollout_name in bnetza_names:
                        # Remove from remaining list
                        self.remaining_bnetza = [
                            c
                            for c in self.remaining_bnetza
                            if c.original_name.lower().strip()
                            != normalized_rollout_name
                        ]
                        matches_found += 1

            self.stats["rollout_name_matches"] = matches_found
            remaining_count = len(self.remaining_bnetza)

            logger.info(f"✅ Found {matches_found} existing rollout_report_name matches")
            logger.info(f"📊 Remaining BNetzA companies to process: {remaining_count}")

            if matches_found > 0:
                logger.info(
                    f"   Removed {matches_found} already matched companies from processing list"
                )

            return True

        except Exception as e:
            logger.error(f"❌ Failed in step 2: {e}")
            return False

    async def step_3_match_variations(self) -> bool:
        """Step 3: Match rollout_name_variations and update database."""
        logger.info("=" * 60)
        logger.info("🔍 STEP 3: Matching rollout_name_variations")
        logger.info("=" * 60)

        try:
            matches_found = 0
            companies_to_update = []

            # Build BNetzA lookup
            bnetza_lookup = {
                company.original_name.lower().strip(): company
                for company in self.remaining_bnetza
            }

            for bdew_company in self.bdew_companies:
                if bdew_company.rollout_name_variations:
                    for variation in bdew_company.rollout_name_variations:
                        if variation:
                            normalized_variation = variation.lower().strip()
                            if normalized_variation in bnetza_lookup:
                                matched_bnetza = bnetza_lookup[normalized_variation]

                                # Prepare database update
                                update_data = {
                                    "rollout_report_name": matched_bnetza.original_name
                                }

                                # Add old rollout_report_name to variations if it exists and is different
                                variations = list(
                                    bdew_company.rollout_name_variations or []
                                )
                                if (
                                    bdew_company.rollout_report_name
                                    and bdew_company.rollout_report_name
                                    != matched_bnetza.original_name
                                    and bdew_company.rollout_report_name
                                    not in variations
                                ):
                                    variations.insert(
                                        0, bdew_company.rollout_report_name
                                    )

                                # Add current match to variations if not already there
                                if matched_bnetza.original_name not in variations:
                                    variations.append(matched_bnetza.original_name)

                                update_data["rollout_name_variations"] = variations

                                companies_to_update.append(
                                    (bdew_company.bdew_code, update_data)
                                )

                                # Remove from remaining list
                                bnetza_lookup.pop(normalized_variation, None)

                                matches_found += 1
                                logger.info(
                                    f"  ✓ Matched: {matched_bnetza.original_name} → {bdew_company.name}"
                                )
                                break  # Only match first variation found

            # Update remaining list
            self.remaining_bnetza = list(bnetza_lookup.values())

            # Perform database updates
            if companies_to_update:
                await self._update_companies_in_db(companies_to_update)

            self.stats["variation_matches"] = matches_found
            remaining_count = len(self.remaining_bnetza)

            logger.info(f"✅ Found {matches_found} variation matches")
            logger.info(f"📊 Remaining BNetzA companies to process: {remaining_count}")

            if matches_found > 0:
                logger.info(f"   Updated {len(companies_to_update)} database records")

            return True

        except Exception as e:
            logger.error(f"❌ Failed in step 3: {e}")
            return False

    async def step_4_exact_matches(self) -> bool:
        """Step 4: Find exact matches and update database."""
        logger.info("=" * 60)
        logger.info("🎯 STEP 4: Finding exact matches")
        logger.info("=" * 60)

        try:
            matches_found = 0
            companies_to_update = []

            # Build BDEW lookup by exact name
            bdew_lookup = {}
            for bdew_company in self.bdew_companies:
                normalized_name = bdew_company.name.lower().strip()
                bdew_lookup[normalized_name] = bdew_company

            remaining_after_exact = []
            total_remaining = len(self.remaining_bnetza)

            logger.info(
                f"🔍 Checking {total_remaining} BNetzA companies for exact matches..."
            )

            for i, bnetza_company in enumerate(self.remaining_bnetza, 1):
                normalized_bnetza = bnetza_company.original_name.lower().strip()

                if normalized_bnetza in bdew_lookup:
                    bdew_company = bdew_lookup[normalized_bnetza]

                    # Prepare database update
                    update_data = {"rollout_report_name": bnetza_company.original_name}

                    # Handle existing rollout_report_name
                    variations = list(bdew_company.rollout_name_variations or [])
                    if (
                        bdew_company.rollout_report_name
                        and bdew_company.rollout_report_name
                        != bnetza_company.original_name
                        and bdew_company.rollout_report_name not in variations
                    ):
                        variations.insert(0, bdew_company.rollout_report_name)

                    update_data["rollout_name_variations"] = variations

                    companies_to_update.append((bdew_company.bdew_code, update_data))
                    matches_found += 1
                    logger.info(
                        f"  ✓ Exact match: {bnetza_company.original_name} → {bdew_company.name}"
                    )
                else:
                    remaining_after_exact.append(bnetza_company)

                # Progress indicator every 50 companies
                if i % 50 == 0 or i == total_remaining:
                    percentage = (i / total_remaining) * 100
                    logger.info(
                        f"📊 Progress: {i}/{total_remaining} ({percentage:.1f}%) - Found {matches_found} matches so far"
                    )

            # Update remaining list
            self.remaining_bnetza = remaining_after_exact

            # Perform database updates
            if companies_to_update:
                await self._update_companies_in_db(companies_to_update)

            self.stats["exact_matches"] = matches_found
            remaining_count = len(self.remaining_bnetza)

            logger.info(f"✅ Found {matches_found} exact matches")
            logger.info(f"📊 Remaining BNetzA companies to process: {remaining_count}")

            if matches_found > 0:
                logger.info(f"   Updated {len(companies_to_update)} database records")

            return True

        except Exception as e:
            logger.error(f"❌ Failed in step 4: {e}")
            return False

    async def step_5_normalized_matches(self) -> bool:
        """Step 5: Find normalized exact matches and fuzzy matches using consistent normalization."""
        logger.info("=" * 60)
        logger.info("🔧 STEP 5: Finding normalized exact matches and fuzzy matches")
        logger.info("=" * 60)

        try:
            matches_found = 0
            companies_to_update = []

            # Build BDEW lookup by normalized name (using consistent normalization)
            bdew_normalized_lookup = {}
            bdew_companies_list = []

            for bdew_company in self.bdew_companies:
                normalized_name = self._normalize_company_name(bdew_company.name)
                if normalized_name:
                    bdew_normalized_lookup[normalized_name] = bdew_company
                    bdew_companies_list.append((bdew_company, normalized_name))

            remaining_after_normalized = []
            total_remaining = len(self.remaining_bnetza)

            if total_remaining > 0:
                logger.info(
                    f"🔍 Checking {total_remaining} BNetzA companies for normalized matches..."
                )
                # Debug: Show some normalization examples
                if total_remaining > 0:
                    sample_company = self.remaining_bnetza[0]
                    normalized_sample = self._normalize_company_name(
                        sample_company.original_name
                    )
                    logger.info(
                        f"📝 Normalization example: '{sample_company.original_name}' → '{normalized_sample}'"
                    )

            for i, bnetza_company in enumerate(self.remaining_bnetza, 1):
                # Normalize BNetzA name with same function as BDEW
                normalized_bnetza = self._normalize_company_name(
                    bnetza_company.original_name
                )
                bdew_match = None

                # 1. Try exact normalized match first
                if normalized_bnetza in bdew_normalized_lookup:
                    bdew_match = bdew_normalized_lookup[normalized_bnetza]
                    logger.info(
                        f"  ✓ Normalized exact match: {bnetza_company.original_name} → {bdew_match.name}"
                    )
                    logger.info(
                        f"    Normalized forms: '{normalized_bnetza}' = '{self._normalize_company_name(bdew_match.name)}'"
                    )
                else:
                    # 2. Try fuzzy matching with core location/company names
                    bnetza_words = set(normalized_bnetza.split())
                    # Remove tokens and get meaningful words
                    meaningful_bnetza_words = {
                        w
                        for w in bnetza_words
                        if not w.startswith("__") and len(w) >= MIN_WORD_LENGTH
                    }

                    if (
                        len(meaningful_bnetza_words) >= 1
                    ):  # Need at least one meaningful word
                        best_match = None
                        best_score = 0

                        for bdew_company, bdew_normalized in bdew_companies_list:
                            bdew_words = set(bdew_normalized.split())
                            meaningful_bdew_words = {
                                w
                                for w in bdew_words
                                if not w.startswith("__") and len(w) >= MIN_WORD_LENGTH
                            }

                            if len(meaningful_bdew_words) >= 1:
                                # Calculate overlap score
                                common_words = (
                                    meaningful_bnetza_words & meaningful_bdew_words
                                )
                                if common_words:
                                    # Score based on how many words match and their importance
                                    # Require high overlap AND meaningful specificity
                                    overlap_ratio = len(common_words) / max(
                                        len(meaningful_bnetza_words),
                                        len(meaningful_bdew_words),
                                    )
                                    coverage_ratio = len(common_words) / min(
                                        len(meaningful_bnetza_words),
                                        len(meaningful_bdew_words),
                                    )

                                    # Base score: Average of overlap and coverage (max 1.0)
                                    score = (overlap_ratio + coverage_ratio) / 2

                                    # Penalty for very generic matches (only "energie", "stadtwerke" etc.)
                                    generic_words = {
                                        "energie",
                                        "stadtwerke",
                                        "gas",
                                        "wasser",
                                        "strom",
                                        "netz",
                                    }
                                    if (
                                        common_words.issubset(generic_words)
                                        and len(common_words) == 1
                                    ):
                                        score *= 0.3  # Heavy penalty for single generic word matches

                                    # Bonus for location names or specific company identifiers (multiplicative, not additive!)
                                    specific_words = common_words - generic_words
                                    if specific_words:
                                        # Multiplicative bonus: 1.0 to 1.2 max (20% bonus)
                                        specificity_bonus = 1.0 + min(
                                            0.2, len(specific_words) * 0.05
                                        )
                                        score *= specificity_bonus

                                    # Cap the score at 1.0 to avoid "impossible" scores
                                    score = min(score, 1.0)

                                    # Require much higher threshold: 85% AND at least one specific word
                                    if (
                                        score > best_score
                                        and score >= NORMALIZED_FUZZY_THRESHOLD
                                        and len(specific_words) > 0
                                    ):
                                        best_score = score
                                        best_match = bdew_company

                        if best_match:
                            bdew_match = best_match
                            logger.info(
                                f"  ✓ Fuzzy match (score: {best_score:.2f}): {bnetza_company.original_name} → {bdew_match.name}"
                            )
                            logger.info(f"    BNetzA words: {meaningful_bnetza_words}")
                            logger.info(
                                f"    BDEW words: {set(self._normalize_company_name(bdew_match.name).split()) - {w for w in self._normalize_company_name(bdew_match.name).split() if w.startswith('__')}}"
                            )

                if bdew_match:
                    # Prepare database update
                    update_data = {"rollout_report_name": bnetza_company.original_name}

                    # Handle existing rollout_report_name
                    variations = list(bdew_match.rollout_name_variations or [])
                    if (
                        bdew_match.rollout_report_name
                        and bdew_match.rollout_report_name
                        != bnetza_company.original_name
                        and bdew_match.rollout_report_name not in variations
                    ):
                        variations.insert(0, bdew_match.rollout_report_name)

                    update_data["rollout_name_variations"] = variations

                    companies_to_update.append((bdew_match.bdew_code, update_data))
                    matches_found += 1
                else:
                    remaining_after_normalized.append(bnetza_company)

                # Progress indicator every 25 companies for normalized matches
                if total_remaining > PROGRESS_LOG_THRESHOLD and (
                    i % PROGRESS_CHECK_INTERVAL == 0 or i == total_remaining
                ):
                    percentage = (i / total_remaining) * 100
                    logger.info(
                        f"📊 Progress: {i}/{total_remaining} ({percentage:.1f}%) - Found {matches_found} normalized/fuzzy matches so far"
                    )

            # Update remaining list
            self.remaining_bnetza = remaining_after_normalized

            # Perform database updates
            if companies_to_update:
                await self._update_companies_in_db(companies_to_update)

            self.stats["normalized_matches"] = matches_found
            remaining_count = len(self.remaining_bnetza)

            logger.info(f"✅ Found {matches_found} normalized/fuzzy matches")
            logger.info(f"📊 Remaining BNetzA companies to process: {remaining_count}")

            if matches_found > 0:
                logger.info(f"   Updated {len(companies_to_update)} database records")

            return True

        except Exception as e:
            logger.error(f"❌ Failed in step 5: {e}")
            return False

    async def step_6_llm_assisted_matching(
        self, api_key: str | None = None, base_url: str | None = None
    ) -> bool:
        """Step 6: LLM-assisted matching with user interaction."""
        logger.info("=" * 60)
        logger.info("🤖 STEP 6: LLM-assisted matching with user interaction")
        logger.info("=" * 60)

        if not api_key:
            logger.info("⏭️  No API key provided, skipping LLM-assisted matching")
            return True

        if not OpenAI:
            logger.warning(
                "⚠️  OpenAI package not available, skipping LLM-assisted matching"
            )
            return True

        try:
            client = OpenAI(
                api_key=api_key, base_url=base_url or "https://openrouter.ai/api/v1"
            )

            # Load previously unmatched companies once at the beginning
            previously_unmatched = await self._get_previously_unmatched_companies()
            if previously_unmatched:
                logger.info(
                    f"📝 Found {len(previously_unmatched)} previously UNMATCHED companies (will skip unless score ≥ {UNMATCHED_RETRY_THRESHOLD}%)"
                )

            llm_matches = 0
            user_matches = 0
            skipped_companies = []  # Track skipped companies
            companies_to_update = []
            remaining_after_llm = []

            for i, bnetza_company in enumerate(self.remaining_bnetza, 1):
                logger.info(
                    f"\n--- Processing {i}/{len(self.remaining_bnetza)}: {bnetza_company.original_name} ---"
                )

                # Find fuzzy candidates
                candidates = self._find_fuzzy_candidates(bnetza_company)

                if not candidates:
                    logger.info("  No fuzzy candidates found")
                    remaining_after_llm.append(bnetza_company)
                    continue

                # Check if this company was previously marked as UNMATCHED
                # Only proceed with LLM/user interaction if:
                # 1. Not previously marked as UNMATCHED, OR
                # 2. Best fuzzy score >= 95% (very high confidence)
                best_score = candidates[0][1]
                was_previously_unmatched = (
                    bnetza_company.original_name in previously_unmatched
                )

                if was_previously_unmatched and best_score < UNMATCHED_RETRY_THRESHOLD:
                    logger.info(
                        f"  ⏭️ Skipping previously UNMATCHED company (best score: {best_score}% < {UNMATCHED_RETRY_THRESHOLD}%)"
                    )
                    remaining_after_llm.append(bnetza_company)
                    continue  # Ask LLM for evaluation
                llm_result = await self._ask_llm_for_match(
                    client, bnetza_company, candidates[:5]
                )

                if llm_result and llm_result.get("confidence", 0) >= LLM_MIN_CONFIDENCE:
                    # High confidence LLM match
                    bdew_code = llm_result["bdew_code"]
                    bdew_company = next(
                        (c for c in self.bdew_companies if c.bdew_code == bdew_code),
                        None,
                    )

                    if bdew_company:
                        update_data = {
                            "rollout_report_name": bnetza_company.original_name
                        }

                        # Handle existing rollout_report_name
                        variations = list(bdew_company.rollout_name_variations or [])
                        if (
                            bdew_company.rollout_report_name
                            and bdew_company.rollout_report_name
                            != bnetza_company.original_name
                            and bdew_company.rollout_report_name not in variations
                        ):
                            variations.insert(0, bdew_company.rollout_report_name)

                        update_data["rollout_name_variations"] = variations

                        companies_to_update.append(
                            (bdew_company.bdew_code, update_data)
                        )
                        llm_matches += 1
                        logger.info(
                            f"  ✓ LLM match (confidence: {llm_result['confidence']:.2f}): {bdew_company.name}"
                        )
                        continue

                # Ask user for decision
                user_choice = self._ask_user_for_choice(
                    bnetza_company, candidates[:5], llm_result
                )

                if user_choice == "SKIP":
                    logger.info("  ⏭️ User skipped - will mark as UNMATCHED")
                    skipped_companies.append(bnetza_company)
                    remaining_after_llm.append(bnetza_company)
                elif user_choice and user_choice != "skip":
                    bdew_company = next(
                        (c for c in self.bdew_companies if c.bdew_code == user_choice),
                        None,
                    )

                    if bdew_company:
                        update_data = {
                            "rollout_report_name": bnetza_company.original_name
                        }

                        # Handle existing rollout_report_name
                        variations = list(bdew_company.rollout_name_variations or [])
                        if (
                            bdew_company.rollout_report_name
                            and bdew_company.rollout_report_name
                            != bnetza_company.original_name
                            and bdew_company.rollout_report_name not in variations
                        ):
                            variations.insert(0, bdew_company.rollout_report_name)

                        update_data["rollout_name_variations"] = variations

                        companies_to_update.append(
                            (bdew_company.bdew_code, update_data)
                        )
                        user_matches += 1
                        logger.info(f"  ✓ User choice: {bdew_company.name}")
                        continue
                else:
                    # No choice made
                    remaining_after_llm.append(bnetza_company)

            # Mark skipped companies as UNMATCHED in database
            if skipped_companies:
                await self._mark_companies_as_unmatched(skipped_companies)

            # Update remaining list
            self.remaining_bnetza = remaining_after_llm

            # Perform database updates
            if companies_to_update:
                await self._update_companies_in_db(companies_to_update)

            self.stats["llm_matches"] = llm_matches
            self.stats["user_matches"] = user_matches
            remaining_count = len(self.remaining_bnetza)

            logger.info(
                f"✅ Found {llm_matches} LLM matches and {user_matches} user-confirmed matches"
            )
            logger.info(f"📊 Remaining BNetzA companies to process: {remaining_count}")

            if llm_matches + user_matches > 0:
                logger.info(f"   Updated {len(companies_to_update)} database records")

            return True

        except Exception as e:
            logger.error(f"❌ Failed in step 6: {e}")
            return False

    async def step_7_mark_unmatched(self) -> bool:
        """Step 7: Mark remaining companies as UNMATCHED."""
        logger.info("=" * 60)
        logger.info("❌ STEP 7: Marking remaining companies as UNMATCHED")
        logger.info("=" * 60)

        try:
            if not self.remaining_bnetza:
                logger.info("✅ No remaining companies to mark as unmatched")
                return True

            # For now, just log the unmatched companies
            # In a real implementation, you might want to create a separate table or log file
            unmatched_count = len(self.remaining_bnetza)

            logger.info(f"📝 Marking {unmatched_count} companies as UNMATCHED:")
            for company in self.remaining_bnetza:
                logger.info(f"  ❌ {company.original_name}")

            # Save unmatched companies to CSV for review
            unmatched_file = Path("data") / "unmatched_bnetza_companies.csv"
            unmatched_file.parent.mkdir(exist_ok=True)

            with unmatched_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["index", "original_name", "rollout_quote"]
                )
                writer.writeheader()
                for company in self.remaining_bnetza:
                    writer.writerow(
                        {
                            "index": company.index,
                            "original_name": company.original_name,
                            "rollout_quote": company.rollout_quote or "",
                        }
                    )

            self.stats["unmatched"] = unmatched_count

            logger.info(
                f"✅ Saved {unmatched_count} unmatched companies to: {unmatched_file}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed in step 7: {e}")
            return False

    def print_final_statistics(self) -> None:
        """Print final matching statistics."""
        logger.info("=" * 60)
        logger.info("📊 FINAL MATCHING STATISTICS")
        logger.info("=" * 60)

        total_processed = self.stats["initial_bnetza_count"]
        total_matched = (
            self.stats["rollout_name_matches"]
            + self.stats["variation_matches"]
            + self.stats["exact_matches"]
            + self.stats["normalized_matches"]
            + self.stats["llm_matches"]
            + self.stats["user_matches"]
        )

        logger.info(f"📈 Initial BNetzA companies: {total_processed}")
        logger.info(
            f"🎯 Existing rollout_report_name matches: {self.stats['rollout_name_matches']}"
        )
        logger.info(f"🔍 Variation matches: {self.stats['variation_matches']}")
        logger.info(f"✅ Exact matches: {self.stats['exact_matches']}")
        logger.info(f"🔧 Normalized matches: {self.stats['normalized_matches']}")
        logger.info(f"🤖 LLM matches: {self.stats['llm_matches']}")
        logger.info(f"👤 User-confirmed matches: {self.stats['user_matches']}")
        logger.info(f"❌ Unmatched: {self.stats['unmatched']}")
        logger.info("-" * 60)
        logger.info(
            f"📊 Total matched: {total_matched}/{total_processed} ({total_matched/total_processed*100:.1f}%)"
        )
        logger.info(f"🎉 Success rate: {total_matched/total_processed*100:.1f}%")

    def _normalize_company_name(self, name: str) -> str:
        """Normalize company name for matching (consistent normalization for both BDEW and BNetzA)."""
        if not name:
            return ""

        # Convert to lowercase
        normalized = name.lower().strip()

        # Remove extra whitespace and special characters, but keep basic structure
        normalized = re.sub(r"[^\w\s&\.\-()]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)

        # Normalize common company prefixes/types
        prefix_replacements = [
            (r"\bstadtwerke\b", "__stadtwerke__"),
            (r"\bgemeindewerke\b", "__gemeindewerke__"),
            (r"\benergieversorgung\b", "__energieversorgung__"),
            (r"\belektrizitätswerk\b", "__elektrizitaetswerk__"),
            (r"\bgasversorgung\b", "__gasversorgung__"),
            (r"\bwasserwerk\b", "__wasserwerk__"),
            (r"\bfernwärme\b", "__fernwaerme__"),
        ]

        # Apply prefix normalizations
        for pattern, replacement in prefix_replacements:
            normalized = re.sub(pattern, replacement, normalized)

        # Normalize legal forms to standardized tokens
        legal_form_replacements = [
            # GmbH variations
            (r"\bgesellschaft\s+mit\s+beschr[aä]nkter\s+haftung\b", "__gmbh__"),
            (r"\bgmbh\b", "__gmbh__"),
            # AG variations
            (r"\baktiengesellschaft\b", "__ag__"),
            (r"\bag\b", "__ag__"),
            # KG variations
            (r"\bkommanditgesellschaft\b", "__kg__"),
            (r"\bkg\b", "__kg__"),
            # eG variations
            (r"\beingetragene\s+genossenschaft\b", "__eg__"),
            (r"\beg\b", "__eg__"),
            # Combined forms
            (r"\b__gmbh__\s*[&+und]*\s*co\.?\s*__kg__\b", "__gmbh_co_kg__"),
            (r"\b__gmbh__\s*[&+und]*\s*co\.?\s*kg\b", "__gmbh_co_kg__"),
            (r"\bgmbh\s*[&+und]*\s*co\.?\s*kg\b", "__gmbh_co_kg__"),
            # Other legal forms
            (r"\bmb[hH]\b", "__mbh__"),
            (r"\bk\.?u\.?\b", "__ku__"),
            (r"\ba\.?\s*ö\.?\s*r\.?\b", "__aoer__"),
            (r"\baoer\b", "__aoer__"),
        ]

        # Apply legal form normalizations
        for pattern, replacement in legal_form_replacements:
            normalized = re.sub(pattern, replacement, normalized)

        # Clean up extra spaces
        normalized = re.sub(r"\s+", " ", normalized).strip()

        return normalized

    def _find_fuzzy_candidates(
        self, bnetza_company: BNetzACompany
    ) -> list[tuple[BDEWCompany, float]]:
        """Find fuzzy match candidates for a BNetzA company."""
        candidates = []

        for bdew_company in self.bdew_companies:
            # Skip if already has rollout_report_name matching this BNetzA company
            if (
                bdew_company.rollout_report_name
                and bdew_company.rollout_report_name.lower().strip()
                == bnetza_company.original_name.lower().strip()
            ):
                continue

            # Calculate fuzzy score
            score = fuzz.ratio(
                bnetza_company.original_name.lower(), bdew_company.name.lower()
            )

            if score >= FUZZY_THRESHOLD:
                candidates.append((bdew_company, score))

        # Sort by score (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)

        return candidates

    async def _ask_llm_for_match(
        self,
        client: OpenAI,
        bnetza_company: BNetzACompany,
        candidates: list[tuple[BDEWCompany, float]],
    ) -> dict | None:
        """Ask LLM to evaluate fuzzy candidates with timeout and retry."""
        max_retries = 3
        timeout_seconds = 30

        for attempt in range(max_retries):
            try:
                # Create prompt
                prompt = f"""
Du bewertest deutsche Energieversorgungsunternehmen für ein Matching-System.

BNetzA Unternehmen: "{bnetza_company.original_name}"

Kandidaten:
"""
                for i, (bdew_company, score) in enumerate(candidates, 1):
                    prompt += f"{i}. {bdew_company.name} (Code: {bdew_company.bdew_code}, Fuzzy: {score}%)"
                    if bdew_company.city:
                        prompt += f" - {bdew_company.city}"
                    prompt += "\n"

                prompt += """
Bewerte ob eines der Kandidaten das gleiche Unternehmen ist wie das BNetzA Unternehmen.

Antworte nur mit gültigem JSON:
{
  "match": true/false,
  "bdew_code": "Code des passenden Kandidaten oder null",
  "confidence": 0.0-1.0,
  "reasoning": "Kurze Begründung"
}"""

                # Execute with timeout
                logger.debug(
                    f"LLM attempt {attempt + 1}/{max_retries} for {bnetza_company.original_name}"
                )

                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.chat.completions.create,
                        model=LLM_MODEL,
                        messages=[
                            {
                                "role": "system",
                                "content": "Du bist ein Experte für deutsche Energieversorgungsunternehmen. Antworte ausschließlich mit gültigem JSON.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.1,
                        max_tokens=500,
                    ),
                    timeout=timeout_seconds,
                )

                response_content = response.choices[0].message.content
                if not response_content:
                    logger.warning(f"Empty response from LLM on attempt {attempt + 1}")
                    continue

                # Parse JSON response
                response_text = response_content.strip()
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1]

                result = json.loads(response_text)

                if result.get("match") and result.get("bdew_code"):
                    logger.info(f"✅ LLM success on attempt {attempt + 1}")
                    return result

                logger.info(f"📝 LLM result on attempt {attempt + 1}: No match found")
                return None

            except TimeoutError:
                logger.warning(
                    f"⏱️ LLM timeout ({timeout_seconds}s) on attempt {attempt + 1}/{max_retries}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # Brief pause before retry
                    continue
                else:
                    logger.error(f"❌ LLM failed after {max_retries} timeout attempts")
                    return None

            except json.JSONDecodeError as e:
                logger.warning(f"📝 JSON parsing failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.error(
                        f"❌ LLM JSON parsing failed after {max_retries} attempts"
                    )
                    return None

            except Exception as e:
                logger.warning(f"⚠️ LLM error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Longer pause for other errors
                    continue
                else:
                    logger.error(f"❌ LLM failed after {max_retries} attempts: {e}")
                    return None

        return None

    def _ask_user_for_choice(
        self,
        bnetza_company: BNetzACompany,
        candidates: list[tuple[BDEWCompany, float]],
        llm_result: dict | None,
    ) -> str | None:
        """Ask user to choose from candidates."""
        print(f"\n🤔 Manual review needed for: {bnetza_company.original_name}")

        if llm_result:
            confidence = llm_result.get("confidence", 0)
            reasoning = llm_result.get("reasoning", "No reasoning provided")
            print(f"🤖 LLM suggestion (confidence: {confidence:.2f}): {reasoning}")

        print("\nCandidates:")
        for i, (bdew_company, score) in enumerate(candidates, 1):
            print(
                f"{i}. {bdew_company.name} (Code: {bdew_company.bdew_code}, Fuzzy: {score}%)"
            )
            if bdew_company.city:
                print(f"   City: {bdew_company.city}")

        print("s. Skip this company")

        while True:
            try:
                choice = input("Enter your choice (1-5, s): ").strip().lower()

                if choice == "s":
                    return "SKIP"  # Changed to indicate skip

                choice_num = int(choice)
                if 1 <= choice_num <= len(candidates):
                    return candidates[choice_num - 1][0].bdew_code
                else:
                    print("Invalid choice. Please try again.")

            except ValueError:
                print("Invalid input. Please enter a number or 's'.")
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
                return "SKIP"

    async def _update_companies_in_db(
        self, companies_to_update: list[tuple[str, dict]]
    ) -> None:
        """Update companies in database."""
        if not SQLALCHEMY_AVAILABLE:
            logger.warning("SQLAlchemy not available, skipping database updates")
            return

        try:
            total_updates = len(companies_to_update)
            logger.info(f"💾 Updating {total_updates} companies in database...")

            async with self.data_loader.session_factory() as session:
                for i, (bdew_code, update_data) in enumerate(companies_to_update, 1):
                    stmt = (
                        update(Company)
                        .where(Company.bdew_code == bdew_code)
                        .values(**update_data)
                    )
                    await session.execute(stmt)

                    # Progress indicator every 100 updates
                    if i % 100 == 0 or i == total_updates:
                        percentage = (i / total_updates) * 100
                        logger.info(
                            f"📊 Database progress: {i}/{total_updates} ({percentage:.1f}%)"
                        )

                await session.commit()

        except Exception as e:
            logger.error(f"Database update failed: {e}")
            raise

    async def _mark_companies_as_unmatched(self, companies: list) -> None:
        """Mark companies as UNMATCHED in database."""
        if not SQLALCHEMY_AVAILABLE:
            logger.warning("SQLAlchemy not available, skipping UNMATCHED marking")
            return

        try:
            company_names = [company.original_name for company in companies]
            logger.info(
                f"💾 Marking {len(company_names)} companies as UNMATCHED in database..."
            )

            async with self.data_loader.session_factory() as session:
                # Create table to track unmatched companies if it doesn't exist
                await session.execute(
                    text(
                        """
                    CREATE TABLE IF NOT EXISTS unmatched_companies (
                        id SERIAL PRIMARY KEY,
                        bnetza_name VARCHAR(500) UNIQUE,
                        marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        retry_threshold FLOAT DEFAULT 0.95
                    )
                """
                    )
                )

                # Insert/update companies as UNMATCHED
                for company_name in company_names:
                    await session.execute(
                        text(
                            """
                        INSERT INTO unmatched_companies (bnetza_name)
                        VALUES (:name)
                        ON CONFLICT (bnetza_name) DO UPDATE SET
                            marked_at = CURRENT_TIMESTAMP,
                            retry_threshold = 0.95
                    """
                        ),
                        {"name": company_name},
                    )

                await session.commit()
                logger.info(
                    f"✅ Successfully marked {len(company_names)} companies as UNMATCHED"
                )

        except Exception as e:
            logger.error(f"Failed to mark companies as UNMATCHED: {e}")
            raise

    async def _get_previously_unmatched_companies(self) -> set[str]:
        """Get set of previously unmatched company names."""
        if not SQLALCHEMY_AVAILABLE:
            return set()

        try:
            async with self.data_loader.session_factory() as session:
                result = await session.execute(
                    text(
                        """
                    SELECT bnetza_name FROM unmatched_companies
                    WHERE retry_threshold > 0
                """
                    )
                )
                return {row[0] for row in result.fetchall()}

        except Exception as e:
            logger.warning(f"Could not retrieve previously unmatched companies: {e}")
            return set()


async def main() -> int:
    """Main entry point."""
    # Explicitly load .env file at startup
    try:
        load_dotenv()
        logger.info("✅ Environment variables loaded from .env file")
    except ImportError:
        logger.info("(i) dotenv not available, using system environment variables only")

    parser = ArgumentParser(description="Structured Company Matching")

    parser.add_argument(
        "--bnetza-csv",
        type=Path,
        required=True,
        help="BNetzA CSV file path (Roll-out Quoten data)",
    )
    parser.add_argument(
        "--openrouter-api-key",
        type=str,
        help="OpenRouter API key for LLM-assisted matching",
    )
    parser.add_argument(
        "--openrouter-base-url",
        type=str,
        default="https://openrouter.ai/api/v1",
        help="OpenRouter base URL",
    )

    args = parser.parse_args()

    logger.info("🚀 VNBdigitaler - Structured Company Matching")
    logger.info("=" * 60)

    # Initialize data loader
    data_loader = DataLoader()
    matcher = StructuredCompanyMatcher(data_loader)

    try:
        # Execute all steps
        step_results = [
            await matcher.step_1_load_bnetza_companies(args.bnetza_csv),
            await matcher.step_2_load_bdew_and_match_rollout_names(),
            await matcher.step_3_match_variations(),
            await matcher.step_4_exact_matches(),
            await matcher.step_5_normalized_matches(),
        ]

        # Check if any step failed
        for i, result in enumerate(step_results, 1):
            if not result:
                return i

        # Get API credentials with debug logging
        api_key = args.openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        base_url = args.openrouter_base_url or os.getenv("OPENROUTER_BASE_URL")

        # Debug API key status
        if api_key:
            logger.info(f"🔑 API key found: {api_key[:8]}...")
        else:
            logger.info(
                "🔑 No API key found in command line args or environment variables"
            )
            logger.info(f"   Command line arg: {args.openrouter_api_key}")
            logger.info(f"   Environment var: {os.getenv('OPENROUTER_API_KEY')}")

        if not await matcher.step_6_llm_assisted_matching(api_key, base_url):
            return 6

        if not await matcher.step_7_mark_unmatched():
            return 7

        # Print final statistics
        matcher.print_final_statistics()

        logger.info("=" * 60)
        logger.info("🎉 Structured company matching completed successfully!")

        return 0

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1

    finally:
        await data_loader.close()


if __name__ == "__main__":
    asyncio.run(main())
