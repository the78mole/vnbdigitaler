#!/usr/bin/env python3
"""
VNBdigitaler Company Matching Script - Step 1: Load and Analyze Data

This script loads BNetzA and BDEW companies and provides basic statistics.
"""

import asyncio
import csv
import json
import logging
import os
import sys
import time
from argparse import ArgumentParser
from pathlib import Path

import pandas as pd
from fuzzywuzzy import fuzz
from jinja2 import Environment, FileSystemLoader
from openai import OpenAI

# Add src to path for imports
_src_path = str(Path(__file__).parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

from src.company_matcher import CompanyMatcher  # noqa: E402
from src.data_loader import DataLoader  # noqa: E402
from src.matching_models import BDEWCompany, BNetzACompany, CompanyMatch  # noqa: E402

# Constants
STEP_STATISTICS = 1
STEP_MATCHING = 2
STEP_EXTRACT_SINGLE_EXACT = 3
STEP_FUZZY_WITH_LOCATION = 4
STEP_LLM_ASSISTED_MATCHING = 5

# Fuzzy matching constants
MIN_FUZZY_THRESHOLD = 70
MAX_ITERATIONS = 100
LOCATION_BOOST_POINTS = 10

# LLM constants
LLM_MODEL = "gpt-4o-mini"  # Cost-effective model for classification tasks
LLM_MAX_CANDIDATES = 5  # Maximum number of fuzzy candidates to send to LLM
LLM_MIN_CONFIDENCE = 0.7  # Minimum confidence threshold for LLM matches

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class LLMCompanyMatcher:
    """LLM-assisted company matching using OpenAI."""

    def __init__(self, api_key: str | None = None):
        """Initialize LLM matcher with OpenAI client."""
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

        # Setup Jinja2 template environment
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir), autoescape=True
        )
        self.template = self.jinja_env.get_template("llm_company_matching.j2")

    def get_fuzzy_candidates(
        self, bnetza_company: BNetzACompany, bdew_companies: list[BDEWCompany]
    ) -> list[CompanyMatch]:
        """Get fuzzy match candidates for LLM evaluation."""
        # Use the existing fuzzy matching logic
        matcher = CompanyMatcher(bdew_companies)

        # Get fuzzy matches (but not exact matches since those are already processed)
        fuzzy_matches = matcher.find_fuzzy_matches(bnetza_company)

        # Limit to top candidates for LLM efficiency
        return fuzzy_matches[:LLM_MAX_CANDIDATES]

    def ask_llm_for_match(
        self, bnetza_company: BNetzACompany, candidates: list[CompanyMatch]
    ) -> dict:
        """Ask LLM to evaluate fuzzy candidates and return best match."""
        try:
            # Render the prompt template
            prompt = self.template.render(
                bnetza_company=bnetza_company, candidates=candidates
            )

            logger.debug(f"LLM Prompt for {bnetza_company.original_name}:\n{prompt}")

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Du bist ein Experte für deutsche Energieversorgungsunternehmen. Antworte ausschließlich mit gültigem JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # Low temperature for consistent results
                max_tokens=500,
            )

            # Parse JSON response
            response_content = response.choices[0].message.content
            if not response_content:
                raise ValueError("Empty response from LLM")

            response_text = response_content.strip()
            logger.debug(f"LLM Response: {response_text}")

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result = json.loads(response_text)

            # Validate response format
            required_keys = ["match_found", "confidence", "reasoning"]
            if not all(key in result for key in required_keys):
                raise ValueError(f"Invalid LLM response format: {result}")

            if result["match_found"] and "bdew_code" not in result:
                raise ValueError("LLM found match but didn't provide bdew_code")

            return result

        except Exception as e:
            logger.error(f"LLM API error for {bnetza_company.original_name}: {e}")
            return {
                "match_found": False,
                "confidence": 0.0,
                "reasoning": f"LLM API error: {e!s}",
            }

    def process_company(
        self, bnetza_company: BNetzACompany, bdew_companies: list[BDEWCompany]
    ) -> CompanyMatch | None:
        """Process a single BNetzA company with LLM assistance."""
        # Get fuzzy candidates
        candidates = self.get_fuzzy_candidates(bnetza_company, bdew_companies)

        if not candidates:
            logger.info(
                f"No fuzzy candidates found for: {bnetza_company.original_name}"
            )
            return None

        # Ask LLM for evaluation
        llm_result = self.ask_llm_for_match(bnetza_company, candidates)

        # Check if LLM found a confident match
        if llm_result["match_found"] and llm_result["confidence"] >= LLM_MIN_CONFIDENCE:
            # Find the corresponding candidate
            bdew_code = llm_result["bdew_code"]
            matching_candidate = None

            for candidate in candidates:
                if candidate.bdew_company.bdew_code == bdew_code:
                    matching_candidate = candidate
                    break

            if matching_candidate:
                # Create enhanced match with LLM information
                llm_match = CompanyMatch(
                    bnetza_company=bnetza_company,
                    bdew_company=matching_candidate.bdew_company,
                    match_score=llm_result["confidence"] * 100,  # Convert to percentage
                    match_type=f"llm_assisted (confidence: {llm_result['confidence']:.2f})",
                )

                logger.info(
                    f"✅ LLM Match: {bnetza_company.original_name} → {matching_candidate.bdew_company.name}"
                )
                logger.info(f"   Confidence: {llm_result['confidence']:.2f}")
                logger.info(f"   Reasoning: {llm_result['reasoning']}")

                return llm_match
            else:
                logger.warning(
                    f"LLM suggested BDEW code {bdew_code} not found in candidates"
                )

        else:
            logger.info(f"❌ LLM No Match: {bnetza_company.original_name}")
            logger.info(f"   Confidence: {llm_result['confidence']:.2f}")
            logger.info(f"   Reasoning: {llm_result['reasoning']}")

        return None


def print_statistics_table(bnetza_companies, bdew_companies):
    """Print a two-column statistics table."""
    print("\n" + "=" * 60)
    print("📊 DATENSTATISTIK")
    print("=" * 60)
    print(f"{'Kategorie':<30} {'BNetzA':<15} {'BDEW':<15}")
    print("-" * 60)
    print(
        f"{'Anzahl Unternehmen':<30} {len(bnetza_companies):<15} {len(bdew_companies):<15}"
    )

    # Analyze BNetzA companies
    bnetza_with_quote = sum(1 for c in bnetza_companies if c.rollout_quote is not None)
    bnetza_normalized = sum(
        1 for c in bnetza_companies if c.normalized_name and c.normalized_name.strip()
    )

    # Analyze BDEW companies
    bdew_with_city = sum(1 for c in bdew_companies if c.city)
    bdew_normalized = sum(
        1 for c in bdew_companies if c.normalized_name and c.normalized_name.strip()
    )

    print(f"{'Mit Rollout-Quote':<30} {bnetza_with_quote:<15} {'-':<15}")
    print(f"{'Mit Stadt/Ort':<30} {'-':<15} {bdew_with_city:<15}")
    print(f"{'Normalisierte Namen':<30} {bnetza_normalized:<15} {bdew_normalized:<15}")

    # Sample data
    print("-" * 60)
    print("📋 BEISPIELDATEN")
    print("-" * 60)

    print("\nBNetzA (erste 3 Einträge):")
    for i, company in enumerate(bnetza_companies[:3]):
        quote_str = (
            f"{company.rollout_quote:.6f}"
            if company.rollout_quote is not None
            else "N/A"
        )
        print(f"  {i+1}. {company.original_name} (Quote: {quote_str})")

    print("\nBDEW (erste 3 Einträge):")
    for i, company in enumerate(bdew_companies[:3]):
        city_str = company.city or "N/A"
        print(f"  {i+1}. {company.name} ({company.bdew_code}) - {city_str}")

    print("=" * 60)


async def main():
    """Main data loading and analysis workflow."""
    parser = ArgumentParser(description="VNBdigitaler Data Analysis")
    parser.add_argument(
        "--bnetza-csv",
        type=Path,
        default=Path("data/rollout_companies.csv"),
        help="BNetzA CSV file path",
    )
    parser.add_argument(
        "--use-db",
        action="store_true",
        help="Load BDEW companies from database instead of CSV",
    )
    parser.add_argument(
        "--bdew-csv",
        type=Path,
        help="BDEW CSV file path (if not using database)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of BDEW companies to process (for testing)",
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=[
            STEP_STATISTICS,
            STEP_MATCHING,
            STEP_EXTRACT_SINGLE_EXACT,
            STEP_FUZZY_WITH_LOCATION,
            STEP_LLM_ASSISTED_MATCHING,
        ],
        default=STEP_STATISTICS,
        help="Step to execute (1: statistics, 2: matching, 3: extract single exact matches, 4: fuzzy matching with location, 5: LLM-assisted matching)",
    )
    parser.add_argument(
        "--openai-api-key",
        type=str,
        help="OpenAI API key for LLM-assisted matching (can also be set via OPENAI_API_KEY env var)",
    )

    args = parser.parse_args()

    logger.info(f"🚀 VNBdigitaler Data Analysis - Step {args.step}")
    logger.info("=" * 50)

    # Initialize data loader only if needed for database
    data_loader = None
    if args.use_db:
        data_loader = DataLoader()

    try:
        # Load BNetzA companies
        logger.info(f"📖 Loading BNetzA companies from: {args.bnetza_csv}")
        if not args.bnetza_csv.exists():
            logger.error(f"❌ BNetzA CSV file not found: {args.bnetza_csv}")
            return 1

        # Create a simple CSV loader for BNetzA
        if data_loader:
            bnetza_companies = data_loader.load_bnetza_companies_from_csv(
                args.bnetza_csv
            )
        else:
            # Simple CSV loading without database dependency
            df = pd.read_csv(args.bnetza_csv)
            bnetza_companies = []

            for idx, row in enumerate(df.iterrows()):
                _, row_data = row
                # Try different column name variations
                original_name = ""
                rollout_quote = None

                if "original_name" in row_data:
                    original_name = row_data["original_name"]
                elif "company_name" in row_data:
                    original_name = row_data["company_name"]
                elif "name" in row_data:
                    original_name = row_data["name"]
                else:
                    # Use the first string column as name
                    for col in df.columns:
                        if df[col].dtype == "object" and pd.notna(row_data[col]):
                            original_name = str(row_data[col])
                            break

                # Try to get rollout quote
                if "Ausstattungsquote zum 31. März 2025" in row_data:
                    quote_val = row_data["Ausstattungsquote zum 31. März 2025"]
                    if pd.notna(quote_val) and quote_val != "":
                        try:
                            rollout_quote = float(quote_val)
                        except (ValueError, TypeError):
                            rollout_quote = None
                elif "ausstattungsquote" in row_data:
                    quote_val = row_data["ausstattungsquote"]
                    if pd.notna(quote_val) and quote_val != "":
                        try:
                            rollout_quote = float(quote_val)
                        except (ValueError, TypeError):
                            rollout_quote = None
                elif "rollout_quote" in row_data:
                    quote_val = row_data["rollout_quote"]
                    if pd.notna(quote_val) and quote_val != "":
                        try:
                            rollout_quote = float(quote_val)
                        except (ValueError, TypeError):
                            rollout_quote = None

                if original_name.strip():
                    company = BNetzACompany(
                        index=idx,
                        original_name=original_name.strip(),
                        rollout_quote=rollout_quote,
                    )
                    bnetza_companies.append(company)

        logger.info(f"✅ Loaded {len(bnetza_companies)} BNetzA companies")

        # Load BDEW companies
        if args.use_db:
            if not data_loader:
                logger.error("❌ Database loader not initialized")
                return 1
            logger.info("📖 Loading BDEW companies from database...")
            bdew_companies = await data_loader.load_bdew_companies_from_db()
        else:
            if not args.bdew_csv:
                logger.error("❌ Either --use-db or --bdew-csv must be specified")
                return 1

            logger.info(f"📖 Loading BDEW companies from: {args.bdew_csv}")
            if not args.bdew_csv.exists():
                logger.error(f"❌ BDEW CSV file not found: {args.bdew_csv}")
                return 1

            # Simple CSV loading for BDEW without database dependency
            df = pd.read_csv(args.bdew_csv)
            bdew_companies = []

            for _index, row in df.iterrows():
                bdew_code = ""
                name = ""
                city = None

                # Try to get BDEW code
                if "bdew_code" in row:
                    bdew_code = str(row["bdew_code"])
                elif "code" in row:
                    bdew_code = str(row["code"])
                elif "id" in row:
                    bdew_code = str(row["id"])

                # Try to get company name
                if "original_name" in row:
                    name = row["original_name"]
                elif "name" in row:
                    name = row["name"]
                elif "company_name" in row:
                    name = row["company_name"]
                elif "bdew_name" in row:
                    name = row["bdew_name"]

                # Try to get city
                if "city" in row and pd.notna(row["city"]):
                    city = row["city"]
                elif "bdew_city" in row and pd.notna(row["bdew_city"]):
                    city = row["bdew_city"]

                if bdew_code and name:
                    company = BDEWCompany(
                        bdew_code=bdew_code,
                        name=name.strip(),
                        city=city.strip() if city else None,
                    )
                    bdew_companies.append(company)

        logger.info(f"✅ Loaded {len(bdew_companies)} BDEW companies")

        # Print statistics table for Step 1
        if args.step == STEP_STATISTICS:
            print_statistics_table(bnetza_companies, bdew_companies)
            logger.info("\n🎉 Step 1 completed successfully!")
            return 0

        # Step 2: Company matching
        if args.step == STEP_MATCHING:
            print_statistics_table(bnetza_companies, bdew_companies)
            logger.info("\n" + "=" * 50)
            logger.info("🔍 Step 2: Company Matching Analysis")
            logger.info("=" * 50)

            # Initialize the matching engine
            matcher = CompanyMatcher(bdew_companies)

            # Determine how many BDEW companies to process
            companies_to_process = bdew_companies
            if args.limit is not None:
                companies_to_process = bdew_companies[: args.limit]
                logger.info(
                    f"📝 Processing first {len(companies_to_process)} "
                    f"BDEW companies (limited by --limit {args.limit})"
                )
            else:
                logger.info(
                    f"📝 Processing all {len(companies_to_process)} BDEW companies"
                )

            # Process each BDEW company
            total_matches = 0
            for i, bdew_company in enumerate(companies_to_process, 1):
                logger.info(f"\n--- BDEW Company {i}/{len(companies_to_process)} ---")
                logger.info(f"BDEW Code: {bdew_company.bdew_code}")
                logger.info(f"Name: {bdew_company.name}")
                logger.info(f"City: {bdew_company.city}")

                # Find all BNetzA companies that match this BDEW company
                matches = []
                for bnetza_company in bnetza_companies:
                    company_matches = matcher.find_all_matches(bnetza_company)
                    # Filter for matches that correspond to our current BDEW company
                    for match in company_matches:
                        if match.bdew_company.bdew_code == bdew_company.bdew_code:
                            matches.append(match)

                if matches:
                    logger.info(f"✅ Found {len(matches)} match(es):")
                    for j, match in enumerate(matches, 1):
                        logger.info(
                            f"  {j}. BNetzA: {match.bnetza_company.original_name}"
                        )
                        logger.info(f"     Score: {match.match_score:.1f}")
                        logger.info(f"     Type: {match.match_type}")
                        if match.bnetza_company.rollout_quote is not None:
                            logger.info(
                                f"     Quote: {match.bnetza_company.rollout_quote:.1f}%"
                            )
                    total_matches += len(matches)
                else:
                    logger.info("❌ No matches found")

            logger.info("\n📊 Matching Summary:")
            logger.info(f"   Processed: {len(companies_to_process)} BDEW companies")
            logger.info(f"   Total matches: {total_matches}")
            logger.info(
                f"   Average matches per company: "
                f"{total_matches / len(companies_to_process):.2f}"
            )

        # Step 3: Extract single exact matches and update lists
        if args.step == STEP_EXTRACT_SINGLE_EXACT:
            print_statistics_table(bnetza_companies, bdew_companies)
            logger.info("\n" + "=" * 50)
            logger.info("📋 Step 3: Extract Single Exact Matches")
            logger.info("=" * 50)

            # Initialize the matching engine
            matcher = CompanyMatcher(bdew_companies)

            # Extract single exact matches
            (
                single_matches,
                remaining_bnetza,
                remaining_bdew,
            ) = matcher.extract_single_exact_matches(bnetza_companies)

            logger.info(f"\n📋 Single Exact Matches Found: {len(single_matches)}")
            logger.info("-" * 50)

            # Display the extracted matches
            for i, match in enumerate(single_matches, 1):
                logger.info(
                    f"{i:3d}. BDEW: {match.bdew_company.name} ({match.bdew_company.bdew_code})"
                )
                logger.info(f"     BNetzA: {match.bnetza_company.original_name}")
                logger.info(
                    f"     Score: {match.match_score:.1f} | Type: {match.match_type}"
                )
                if match.bdew_company.city:
                    logger.info(f"     City: {match.bdew_company.city}")
                if match.bnetza_company.rollout_quote is not None:
                    logger.info(
                        f"     Quote: {match.bnetza_company.rollout_quote:.1f}%"
                    )
                logger.info("")

            logger.info("\n📊 Updated Statistics:")
            logger.info(f"   Original BNetzA companies: {len(bnetza_companies)}")
            logger.info(f"   Remaining BNetzA companies: {len(remaining_bnetza)}")
            logger.info(f"   Original BDEW companies: {len(bdew_companies)}")
            logger.info(f"   Remaining BDEW companies: {len(remaining_bdew)}")
            logger.info(f"   Single exact matches extracted: {len(single_matches)}")

            # Optionally save the results to files
            logger.info("\n💾 Saving results...")

            # Save single exact matches to CSV
            if single_matches:
                single_matches_file = Path("data") / "single_exact_matches.csv"
                with single_matches_file.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=[
                            "bnetza_index",
                            "bdew_code",
                            "bnetza_name",
                            "bdew_name",
                            "bdew_city",
                            "match_score",
                            "match_type",
                            "confidence_level",
                            "rollout_quote",
                        ],
                    )
                    writer.writeheader()
                    for match in single_matches:
                        writer.writerow(match.to_dict())
                logger.info(f"   Single exact matches saved to: {single_matches_file}")

            # Save remaining companies for further processing
            remaining_bnetza_file = Path("data") / "remaining_bnetza_companies.csv"
            remaining_bdew_file = Path("data") / "remaining_bdew_companies.csv"

            # Save remaining BNetzA companies
            with remaining_bnetza_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["index", "original_name", "rollout_quote"]
                )
                writer.writeheader()
                for company in remaining_bnetza:
                    writer.writerow(
                        {
                            "index": company.index,
                            "original_name": company.original_name,
                            "rollout_quote": company.rollout_quote or "",
                        }
                    )
            logger.info(
                f"   Remaining BNetzA companies saved to: {remaining_bnetza_file}"
            )

            # Save remaining BDEW companies
            with remaining_bdew_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["bdew_code", "name", "city"])
                writer.writeheader()
                for company in remaining_bdew:
                    writer.writerow(
                        {
                            "bdew_code": company.bdew_code,
                            "name": company.name,
                            "city": company.city or "",
                        }
                    )
            logger.info(f"   Remaining BDEW companies saved to: {remaining_bdew_file}")

        # Step 4: Fuzzy matching with location enhancement
        if args.step == STEP_FUZZY_WITH_LOCATION:
            print_statistics_table(bnetza_companies, bdew_companies)
            logger.info("\n" + "=" * 50)
            logger.info("🌍 Step 4: Fuzzy Matching with Location Enhancement")
            logger.info("=" * 50)

            # Initialize the matching engine
            matcher = CompanyMatcher(bdew_companies)

            # Load remaining companies from Step 3 if they exist
            remaining_bnetza_file = Path("data") / "remaining_bnetza_companies.csv"
            remaining_bdew_file = Path("data") / "remaining_bdew_companies.csv"
            existing_matches_file = Path("data") / "single_exact_matches.csv"

            working_bnetza = bnetza_companies
            working_bdew = bdew_companies
            all_confirmed_matches = []

            # Check if we have saved data from Step 3
            if remaining_bnetza_file.exists() and remaining_bdew_file.exists():
                logger.info("📂 Loading remaining companies from Step 3...")

                # Load remaining BNetzA companies
                bnetza_df = pd.read_csv(remaining_bnetza_file)
                working_bnetza = []
                for _, row in bnetza_df.iterrows():
                    company = BNetzACompany(
                        index=row["index"],
                        original_name=row["original_name"],
                        rollout_quote=(
                            row["rollout_quote"]
                            if pd.notna(row["rollout_quote"])
                            and row["rollout_quote"] != ""
                            else None
                        ),
                    )
                    working_bnetza.append(company)

                # Load remaining BDEW companies
                bdew_df = pd.read_csv(remaining_bdew_file)
                working_bdew = []
                for _, row in bdew_df.iterrows():
                    company = BDEWCompany(
                        bdew_code=row["bdew_code"],
                        name=row["name"],
                        city=(
                            row["city"]
                            if pd.notna(row["city"]) and row["city"] != ""
                            else None
                        ),
                    )
                    working_bdew.append(company)

                # Update matcher with remaining BDEW companies
                matcher = CompanyMatcher(working_bdew)

                # Load existing matches if available
                if existing_matches_file.exists():
                    logger.info("📂 Loading existing exact matches from Step 3...")
                    matches_df = pd.read_csv(existing_matches_file)
                    for _, row in matches_df.iterrows():
                        # Reconstruct match objects for reference
                        bnetza_match = BNetzACompany(
                            index=row["bnetza_index"],
                            original_name=row["bnetza_name"],
                            rollout_quote=(
                                row["rollout_quote"]
                                if pd.notna(row["rollout_quote"])
                                and row["rollout_quote"] != ""
                                else None
                            ),
                        )
                        bdew_match = BDEWCompany(
                            bdew_code=row["bdew_code"],
                            name=row["bdew_name"],
                            city=(
                                row["bdew_city"]
                                if pd.notna(row["bdew_city"]) and row["bdew_city"] != ""
                                else None
                            ),
                        )
                        match = CompanyMatch(
                            bnetza_company=bnetza_match,
                            bdew_company=bdew_match,
                            match_score=row["match_score"],
                            match_type=row["match_type"],
                        )
                        all_confirmed_matches.append(match)

                logger.info(
                    f"✅ Loaded {len(working_bnetza)} remaining BNetzA companies"
                )
                logger.info(f"✅ Loaded {len(working_bdew)} remaining BDEW companies")
                logger.info(
                    f"✅ Loaded {len(all_confirmed_matches)} existing exact matches"
                )
            else:
                logger.info("📋 Using original company lists (Step 3 data not found)")

            # Implement iterative fuzzy matching with location enhancement
            logger.info("\n🔄 Starting iterative fuzzy matching process...")
            logger.info("=" * 50)

            iteration = 1
            new_matches_this_round = []

            while working_bnetza and working_bdew:
                logger.info(f"\n--- Iteration {iteration} ---")
                logger.info(
                    f"Working with {len(working_bnetza)} BNetzA and {len(working_bdew)} BDEW companies"
                )

                # Create enhanced search names for BDEW companies (Name + City)
                enhanced_bdew_search_names = []
                for bdew_company in working_bdew:
                    base_name = bdew_company.name
                    if bdew_company.city:
                        enhanced_name = f"{base_name} {bdew_company.city}"
                    else:
                        enhanced_name = base_name
                    enhanced_bdew_search_names.append((enhanced_name, bdew_company))

                logger.info(
                    f"Created {len(enhanced_bdew_search_names)} enhanced search names"
                )

                # Find best matches for this iteration
                iteration_candidates = []

                for bnetza_company in working_bnetza:
                    # Get normalized and original names for BNetzA company
                    search_terms = []
                    if bnetza_company.normalized_name:
                        search_terms.append(bnetza_company.normalized_name)
                    search_terms.append(bnetza_company.original_name)

                    best_score = 0
                    best_match_info = None

                    # Test against all enhanced BDEW names
                    for search_term in search_terms:
                        for enhanced_name, bdew_company in enhanced_bdew_search_names:
                            # Calculate fuzzy match score
                            score = fuzz.ratio(
                                search_term.lower(), enhanced_name.lower()
                            )

                            # Apply location boost if location keywords overlap
                            bnetza_keywords = bnetza_company.get_location_keywords()
                            bdew_keywords = bdew_company.get_location_keywords()

                            if bnetza_keywords & bdew_keywords:
                                score = min(
                                    100, score + LOCATION_BOOST_POINTS
                                )  # Location boost
                                match_type = "fuzzy_enhanced_with_location"
                            else:
                                match_type = "fuzzy_enhanced"

                            if (
                                score > best_score and score >= MIN_FUZZY_THRESHOLD
                            ):  # Minimum threshold
                                best_score = score
                                best_match_info = {
                                    "bnetza_company": bnetza_company,
                                    "bdew_company": bdew_company,
                                    "score": score,
                                    "match_type": match_type,
                                    "search_term": search_term,
                                    "enhanced_name": enhanced_name,
                                }

                    if best_match_info:
                        iteration_candidates.append(best_match_info)

                if not iteration_candidates:
                    logger.info("❌ No more viable matches found - stopping iterations")
                    break

                # Sort candidates by score (highest first)
                iteration_candidates.sort(key=lambda x: x["score"], reverse=True)

                logger.info(f"Found {len(iteration_candidates)} potential matches")

                # Find the best unique match for this iteration
                best_match = iteration_candidates[0]

                logger.info(f"\n🎯 Best match for iteration {iteration}:")
                logger.info(f"   BNetzA: {best_match['bnetza_company'].original_name}")
                logger.info(
                    f"   BDEW: {best_match['bdew_company'].name} ({best_match['bdew_company'].bdew_code})"
                )
                if best_match["bdew_company"].city:
                    logger.info(f"   City: {best_match['bdew_company'].city}")
                logger.info(f"   Enhanced search: {best_match['enhanced_name']}")
                logger.info(f"   Score: {best_match['score']:.1f}")
                logger.info(f"   Type: {best_match['match_type']}")

                # Create CompanyMatch object
                company_match = CompanyMatch(
                    bnetza_company=best_match["bnetza_company"],
                    bdew_company=best_match["bdew_company"],
                    match_score=best_match["score"],
                    match_type=best_match["match_type"],
                )

                # Add to confirmed matches
                all_confirmed_matches.append(company_match)
                new_matches_this_round.append(company_match)

                # Remove matched companies from working lists
                working_bnetza = [
                    c
                    for c in working_bnetza
                    if c.index != best_match["bnetza_company"].index
                ]
                working_bdew = [
                    c
                    for c in working_bdew
                    if c.bdew_code != best_match["bdew_company"].bdew_code
                ]

                logger.info(
                    "✅ Match confirmed and companies removed from working lists"
                )
                logger.info(
                    f"   Remaining: {len(working_bnetza)} BNetzA, {len(working_bdew)} BDEW"
                )

                iteration += 1

                # Safety break to prevent infinite loops
                if iteration > MAX_ITERATIONS:
                    logger.warning(
                        f"⚠️  Reached maximum iterations ({MAX_ITERATIONS}) - stopping"
                    )
                    break

            # Summary of fuzzy matching results
            logger.info("\n📊 Fuzzy Matching with Location Enhancement - Summary:")
            logger.info("=" * 60)
            logger.info(f"   New fuzzy matches found: {len(new_matches_this_round)}")
            logger.info(f"   Total confirmed matches: {len(all_confirmed_matches)}")
            logger.info(f"   Remaining BNetzA companies: {len(working_bnetza)}")
            logger.info(f"   Remaining BDEW companies: {len(working_bdew)}")

            # Display new fuzzy matches
            if new_matches_this_round:
                logger.info("\n🎯 New Fuzzy Matches Found:")
                logger.info("-" * 50)
                for i, match in enumerate(new_matches_this_round, 1):
                    logger.info(f"{i:3d}. BNetzA: {match.bnetza_company.original_name}")
                    logger.info(
                        f"     BDEW: {match.bdew_company.name} ({match.bdew_company.bdew_code})"
                    )
                    if match.bdew_company.city:
                        logger.info(f"     City: {match.bdew_company.city}")
                    logger.info(
                        f"     Score: {match.match_score:.1f} | Type: {match.match_type}"
                    )
                    if match.bnetza_company.rollout_quote is not None:
                        logger.info(
                            f"     Quote: {match.bnetza_company.rollout_quote:.1f}%"
                        )
                    logger.info("")

            # Save updated results
            logger.info("\n💾 Saving enhanced matching results...")

            # Save all confirmed matches (exact + fuzzy)
            all_matches_file = Path("data") / "all_confirmed_matches.csv"
            with all_matches_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "bnetza_index",
                        "bdew_code",
                        "bnetza_name",
                        "bdew_name",
                        "bdew_city",
                        "match_score",
                        "match_type",
                        "confidence_level",
                        "rollout_quote",
                    ],
                )
                writer.writeheader()
                for match in all_confirmed_matches:
                    writer.writerow(match.to_dict())
            logger.info(f"   All confirmed matches saved to: {all_matches_file}")

            # Save new fuzzy matches separately
            if new_matches_this_round:
                fuzzy_matches_file = Path("data") / "fuzzy_matches_with_location.csv"
                with fuzzy_matches_file.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=[
                            "bnetza_index",
                            "bdew_code",
                            "bnetza_name",
                            "bdew_name",
                            "bdew_city",
                            "match_score",
                            "match_type",
                            "confidence_level",
                            "rollout_quote",
                        ],
                    )
                    writer.writeheader()
                    for match in new_matches_this_round:
                        writer.writerow(match.to_dict())
                logger.info(f"   New fuzzy matches saved to: {fuzzy_matches_file}")

            # Save final remaining companies
            final_remaining_bnetza_file = (
                Path("data") / "final_remaining_bnetza_companies.csv"
            )
            final_remaining_bdew_file = (
                Path("data") / "final_remaining_bdew_companies.csv"
            )

            # Save remaining BNetzA companies
            with final_remaining_bnetza_file.open(
                "w", newline="", encoding="utf-8"
            ) as f:
                writer = csv.DictWriter(
                    f, fieldnames=["index", "original_name", "rollout_quote"]
                )
                writer.writeheader()
                for company in working_bnetza:
                    writer.writerow(
                        {
                            "index": company.index,
                            "original_name": company.original_name,
                            "rollout_quote": company.rollout_quote or "",
                        }
                    )
            logger.info(
                f"   Final remaining BNetzA companies saved to: {final_remaining_bnetza_file}"
            )

            # Save remaining BDEW companies
            with final_remaining_bdew_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["bdew_code", "name", "city"])
                writer.writeheader()
                for company in working_bdew:
                    writer.writerow(
                        {
                            "bdew_code": company.bdew_code,
                            "name": company.name,
                            "city": company.city or "",
                        }
                    )
            logger.info(
                f"   Final remaining BDEW companies saved to: {final_remaining_bdew_file}"
            )

        # Step 5: LLM-assisted matching for remaining companies
        if args.step == STEP_LLM_ASSISTED_MATCHING:
            print_statistics_table(bnetza_companies, bdew_companies)
            logger.info("\n" + "=" * 50)
            logger.info("🤖 Step 5: LLM-Assisted Matching")
            logger.info("=" * 50)

            # Check if OpenAI API key is available
            api_key = args.openai_api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("❌ OpenAI API key required for LLM-assisted matching")
                logger.info(
                    "Set OPENAI_API_KEY environment variable or use --openai-api-key"
                )
                return 1

            # Load remaining companies from previous steps
            remaining_bnetza_file = (
                Path("data") / "final_remaining_bnetza_companies.csv"
            )
            remaining_bdew_file = Path("data") / "final_remaining_bdew_companies.csv"
            existing_matches_file = Path("data") / "all_confirmed_matches.csv"

            working_bnetza = bnetza_companies
            working_bdew = bdew_companies
            all_confirmed_matches = []

            # Check if we have saved data from previous steps
            if remaining_bnetza_file.exists() and remaining_bdew_file.exists():
                logger.info("📂 Loading remaining companies from previous steps...")

                # Load remaining BNetzA companies
                bnetza_df = pd.read_csv(remaining_bnetza_file)
                working_bnetza = []
                for _, row in bnetza_df.iterrows():
                    company = BNetzACompany(
                        index=row["index"],
                        original_name=row["original_name"],
                        rollout_quote=(
                            row["rollout_quote"]
                            if pd.notna(row["rollout_quote"])
                            and row["rollout_quote"] != ""
                            else None
                        ),
                    )
                    working_bnetza.append(company)

                # Load remaining BDEW companies
                bdew_df = pd.read_csv(remaining_bdew_file)
                working_bdew = []
                for _, row in bdew_df.iterrows():
                    company = BDEWCompany(
                        bdew_code=row["bdew_code"],
                        name=row["name"],
                        city=(
                            row["city"]
                            if pd.notna(row["city"]) and row["city"] != ""
                            else None
                        ),
                    )
                    working_bdew.append(company)

                # Load existing matches if available
                if existing_matches_file.exists():
                    logger.info("📂 Loading existing matches from previous steps...")
                    matches_df = pd.read_csv(existing_matches_file)
                    for _, row in matches_df.iterrows():
                        # Reconstruct match objects for reference
                        bnetza_match = BNetzACompany(
                            index=row["bnetza_index"],
                            original_name=row["bnetza_name"],
                            rollout_quote=(
                                row["rollout_quote"]
                                if pd.notna(row["rollout_quote"])
                                and row["rollout_quote"] != ""
                                else None
                            ),
                        )
                        bdew_match = BDEWCompany(
                            bdew_code=row["bdew_code"],
                            name=row["bdew_name"],
                            city=(
                                row["bdew_city"]
                                if pd.notna(row["bdew_city"]) and row["bdew_city"] != ""
                                else None
                            ),
                        )
                        match = CompanyMatch(
                            bnetza_company=bnetza_match,
                            bdew_company=bdew_match,
                            match_score=row["match_score"],
                            match_type=row["match_type"],
                        )
                        all_confirmed_matches.append(match)

                logger.info(
                    f"✅ Loaded {len(working_bnetza)} remaining BNetzA companies"
                )
                logger.info(f"✅ Loaded {len(working_bdew)} remaining BDEW companies")
                logger.info(f"✅ Loaded {len(all_confirmed_matches)} existing matches")
            else:
                logger.info(
                    "📋 Using original company lists (previous step data not found)"
                )

            # Initialize LLM matcher
            logger.info(f"🤖 Initializing LLM matcher (model: {LLM_MODEL})")
            llm_matcher = LLMCompanyMatcher(api_key=api_key)

            # Process remaining BNetzA companies with LLM assistance
            logger.info("\n🔄 Starting LLM-assisted matching process...")
            logger.info("=" * 50)

            llm_matches = []
            processed_count = 0

            for i, bnetza_company in enumerate(working_bnetza, 1):
                logger.info(
                    f"\n--- Processing {i}/{len(working_bnetza)}: {bnetza_company.original_name} ---"
                )

                try:
                    # Get LLM evaluation
                    llm_match = llm_matcher.process_company(
                        bnetza_company, working_bdew
                    )

                    if llm_match:
                        llm_matches.append(llm_match)
                        all_confirmed_matches.append(llm_match)

                        # Remove matched BDEW company from working list to avoid duplicates
                        working_bdew = [
                            c
                            for c in working_bdew
                            if c.bdew_code != llm_match.bdew_company.bdew_code
                        ]

                        logger.info(
                            f"📊 Updated working lists: {len(working_bdew)} BDEW companies remaining"
                        )

                    processed_count += 1

                    # Add small delay to respect API rate limits
                    if processed_count % 10 == 0:
                        logger.info(
                            f"⏸️  Processed {processed_count} companies, pausing briefly..."
                        )
                        time.sleep(1)

                except Exception as e:
                    logger.error(
                        f"❌ Error processing {bnetza_company.original_name}: {e}"
                    )
                    continue

            # Summary of LLM matching results
            logger.info("\n📊 LLM-Assisted Matching - Summary:")
            logger.info("=" * 60)
            logger.info(f"   Companies processed: {processed_count}")
            logger.info(f"   New LLM matches found: {len(llm_matches)}")
            logger.info(f"   Total confirmed matches: {len(all_confirmed_matches)}")
            logger.info(
                f"   Remaining BNetzA companies: {len(working_bnetza) - len(llm_matches)}"
            )
            logger.info(f"   Remaining BDEW companies: {len(working_bdew)}")

            # Display LLM matches
            if llm_matches:
                logger.info("\n🎯 New LLM-Assisted Matches Found:")
                logger.info("-" * 50)
                for i, match in enumerate(llm_matches, 1):
                    logger.info(f"{i:3d}. BNetzA: {match.bnetza_company.original_name}")
                    logger.info(
                        f"     BDEW: {match.bdew_company.name} ({match.bdew_company.bdew_code})"
                    )
                    if match.bdew_company.city:
                        logger.info(f"     City: {match.bdew_company.city}")
                    logger.info(
                        f"     Score: {match.match_score:.1f} | Type: {match.match_type}"
                    )
                    if match.bnetza_company.rollout_quote is not None:
                        logger.info(
                            f"     Quote: {match.bnetza_company.rollout_quote:.1f}%"
                        )
                    logger.info("")

            # Save updated results
            logger.info("\n💾 Saving LLM-enhanced matching results...")

            # Save all confirmed matches (exact + fuzzy + LLM)
            final_matches_file = Path("data") / "final_all_matches.csv"
            with final_matches_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "bnetza_index",
                        "bdew_code",
                        "bnetza_name",
                        "bdew_name",
                        "bdew_city",
                        "match_score",
                        "match_type",
                        "confidence_level",
                        "rollout_quote",
                    ],
                )
                writer.writeheader()
                for match in all_confirmed_matches:
                    writer.writerow(match.to_dict())
            logger.info(f"   Final all matches saved to: {final_matches_file}")

            # Save LLM matches separately
            if llm_matches:
                llm_matches_file = Path("data") / "llm_assisted_matches.csv"
                with llm_matches_file.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=[
                            "bnetza_index",
                            "bdew_code",
                            "bnetza_name",
                            "bdew_name",
                            "bdew_city",
                            "match_score",
                            "match_type",
                            "confidence_level",
                            "rollout_quote",
                        ],
                    )
                    writer.writeheader()
                    for match in llm_matches:
                        writer.writerow(match.to_dict())
                logger.info(f"   LLM matches saved to: {llm_matches_file}")

            # Save final unmatched companies
            final_unmatched_bnetza = [
                c
                for c in working_bnetza
                if not any(m.bnetza_company.index == c.index for m in llm_matches)
            ]

            unmatched_bnetza_file = (
                Path("data") / "final_unmatched_bnetza_companies.csv"
            )
            with unmatched_bnetza_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["index", "original_name", "rollout_quote"]
                )
                writer.writeheader()
                for company in final_unmatched_bnetza:
                    writer.writerow(
                        {
                            "index": company.index,
                            "original_name": company.original_name,
                            "rollout_quote": company.rollout_quote or "",
                        }
                    )
            logger.info(
                f"   Final unmatched BNetzA companies saved to: {unmatched_bnetza_file}"
            )

            unmatched_bdew_file = Path("data") / "final_unmatched_bdew_companies.csv"
            with unmatched_bdew_file.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["bdew_code", "name", "city"])
                writer.writeheader()
                for company in working_bdew:
                    writer.writerow(
                        {
                            "bdew_code": company.bdew_code,
                            "name": company.name,
                            "city": company.city or "",
                        }
                    )
            logger.info(
                f"   Final unmatched BDEW companies saved to: {unmatched_bdew_file}"
            )

        logger.info("\n🎉 Data analysis completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"❌ Error during data loading: {e}")
        return 1

    finally:
        if data_loader:
            await data_loader.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
