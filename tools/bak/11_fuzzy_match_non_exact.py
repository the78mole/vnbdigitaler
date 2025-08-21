#!/usr/bin/env python3
"""
VNBdigitaler - Script 11: Fuzzy Match Non-Exact Matches

This script performs fuzzy matching between BNetzA and BDEW companies that had
no exact matches, creating:
1. A fuzzy matches CSV with confidence scores
2. Two no-match CSV files for remaining unmatched companies

Author: VNBdigitaler Project
Date: 2025-08-21
"""

import argparse
import csv
import logging
import sys
import traceback
from pathlib import Path
from typing import Any

import pandas as pd
from fuzzywuzzy import fuzz

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
MIN_FUZZY_MATCH_SCORE = 70  # Minimum score for fuzzy matching (0-100)
HIGH_CONFIDENCE_THRESHOLD = 85  # High confidence threshold
EXCELLENT_CONFIDENCE_THRESHOLD = 90  # Excellent confidence threshold
GOOD_CONFIDENCE_THRESHOLD = 80  # Good confidence threshold
MAX_LOG_MATCHES = 10  # Maximum number of matches to log for verification


class FuzzyMatchProcessor:
    """Performs fuzzy matching between BNetzA and BDEW non-exact matches."""

    def __init__(self, min_score: int = MIN_FUZZY_MATCH_SCORE):
        """Initialize the fuzzy match processor."""
        self.min_score = min_score

    def find_best_fuzzy_match(
        self, bnetza_company: dict, bdew_companies: list[dict]
    ) -> dict | None:
        """Find the best fuzzy match for a BNetzA company in BDEW companies."""
        bnetza_normalized = bnetza_company["normalized_name"]

        if not bnetza_normalized or pd.isna(bnetza_normalized):
            return None

        best_match = None
        best_score = 0

        for bdew_company in bdew_companies:
            bdew_normalized = bdew_company["normalized_name"]

            if not bdew_normalized or pd.isna(bdew_normalized):
                continue

            # Try fuzzy matching on normalized names
            score = fuzz.ratio(bnetza_normalized, bdew_normalized)

            if score > best_score and score >= self.min_score:
                best_match = {
                    "bdew_company": bdew_company,
                    "confidence": score,
                    "match_type": "fuzzy_normalized",
                }
                best_score = score

            # Also try partial ratio for better matching of substrings
            partial_score = fuzz.partial_ratio(bnetza_normalized, bdew_normalized)
            if partial_score > best_score and partial_score >= self.min_score:
                best_match = {
                    "bdew_company": bdew_company,
                    "confidence": partial_score,
                    "match_type": "fuzzy_partial",
                }
                best_score = partial_score

        return best_match

    def process_fuzzy_matches(
        self,
        bnetza_csv_path: Path,
        bdew_csv_path: Path,
        output_dir: Path,
    ) -> dict[str, Any]:
        """Process fuzzy matches and create output CSV files."""
        logger.info("🔍 VNBdigitaler - Fuzzy Match Non-Exact Matches")
        logger.info("=" * 60)

        # Load input data
        logger.info(f"📖 Reading BNetzA non-matches from: {bnetza_csv_path}")
        bnetza_df = pd.read_csv(bnetza_csv_path)
        logger.info(f"📊 Loaded {len(bnetza_df)} BNetzA non-match companies")

        logger.info(f"📖 Reading BDEW non-matches from: {bdew_csv_path}")
        bdew_df = pd.read_csv(bdew_csv_path)
        logger.info(f"📊 Loaded {len(bdew_df)} BDEW non-match companies")

        # Convert DataFrames to lists of dictionaries for easier processing
        bnetza_companies = bnetza_df.to_dict("records")
        bdew_companies = bdew_df.to_dict("records")

        # Track matched companies
        matched_bnetza_indices = set()
        matched_bdew_codes = set()
        fuzzy_matches = []

        logger.info(f"🔍 Finding fuzzy matches (min score: {self.min_score}%)...")

        # Process each BNetzA company
        for bnetza_company in bnetza_companies:
            # Skip if already matched
            if bnetza_company["bnetza_index"] in matched_bnetza_indices:
                continue

            # Find best fuzzy match
            match_result = self.find_best_fuzzy_match(bnetza_company, bdew_companies)

            if match_result:
                bdew_company = match_result["bdew_company"]

                # Skip if BDEW company already matched
                if bdew_company["bdew_code"] in matched_bdew_codes:
                    continue

                # Clean rollout_quote value
                rollout_quote = bnetza_company.get("rollout_quote", "")
                if pd.isna(rollout_quote) or rollout_quote == "nan":
                    rollout_quote = ""

                fuzzy_match = {
                    "bnetza_index": int(bnetza_company["bnetza_index"]),
                    "bdew_code": int(bdew_company["bdew_code"]),
                    "bnetza_name": bnetza_company["original_name"],
                    "bdew_name": bdew_company["original_name"],
                    "match_confidence": match_result["confidence"],
                    "rollout_quote": rollout_quote,
                    "match_type": match_result["match_type"],
                    "bdew_city": bdew_company.get("city", ""),
                }

                fuzzy_matches.append(fuzzy_match)
                matched_bnetza_indices.add(bnetza_company["bnetza_index"])
                matched_bdew_codes.add(bdew_company["bdew_code"])

                # Log first few matches for verification
                if len(fuzzy_matches) <= MAX_LOG_MATCHES:
                    confidence_icon = (
                        "🟢"
                        if match_result["confidence"] >= HIGH_CONFIDENCE_THRESHOLD
                        else "🟡"
                    )
                    logger.info(
                        f"{confidence_icon} Fuzzy match [{len(fuzzy_matches)}]: "
                        f"{bnetza_company['original_name']} -> {bdew_company['original_name']} "
                        f"({match_result['confidence']}%)"
                    )

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save fuzzy matches
        fuzzy_output_path = output_dir / "fuzzy_matches_rollout.csv"
        logger.info(
            f"💾 Saving {len(fuzzy_matches)} fuzzy matches to: {fuzzy_output_path}"
        )

        with fuzzy_output_path.open("w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "bnetza_index",
                "bdew_code",
                "bnetza_name",
                "bdew_name",
                "match_confidence",
                "rollout_quote",
                "match_type",
                "bdew_city",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(fuzzy_matches)

        # Create remaining no-matches
        bnetza_no_matches = [
            comp
            for comp in bnetza_companies
            if comp["bnetza_index"] not in matched_bnetza_indices
        ]

        bdew_no_matches = [
            comp
            for comp in bdew_companies
            if comp["bdew_code"] not in matched_bdew_codes
        ]

        # Save BNetzA no-matches
        bnetza_no_match_path = output_dir / "bnetza_no_matches.csv"
        logger.info(
            f"💾 Saving {len(bnetza_no_matches)} BNetzA no-matches to: {bnetza_no_match_path}"
        )

        with bnetza_no_match_path.open("w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "bnetza_index",
                "original_name",
                "normalized_name",
                "rollout_quote",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(bnetza_no_matches)

        # Save BDEW no-matches
        bdew_no_match_path = output_dir / "bdew_no_matches.csv"
        logger.info(
            f"💾 Saving {len(bdew_no_matches)} BDEW no-matches to: {bdew_no_match_path}"
        )

        with bdew_no_match_path.open("w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["bdew_code", "original_name", "city", "normalized_name"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(bdew_no_matches)

        # Calculate statistics
        high_confidence_matches = sum(
            1
            for m in fuzzy_matches
            if m["match_confidence"] >= HIGH_CONFIDENCE_THRESHOLD
        )

        stats = {
            "total_bnetza_non_matches": len(bnetza_companies),
            "total_bdew_non_matches": len(bdew_companies),
            "fuzzy_matches_found": len(fuzzy_matches),
            "high_confidence_fuzzy": high_confidence_matches,
            "bnetza_final_no_matches": len(bnetza_no_matches),
            "bdew_final_no_matches": len(bdew_no_matches),
            "bnetza_fuzzy_match_rate": (len(fuzzy_matches) / len(bnetza_companies))
            * 100
            if bnetza_companies
            else 0,
            "bdew_fuzzy_match_rate": (len(fuzzy_matches) / len(bdew_companies)) * 100
            if bdew_companies
            else 0,
        }

        # Print comprehensive summary
        logger.info("\n" + "=" * 60)
        logger.info("📈 FUZZY MATCH PROCESSING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"📊 Input BNetzA non-matches: {stats['total_bnetza_non_matches']}")
        logger.info(f"📊 Input BDEW non-matches: {stats['total_bdew_non_matches']}")
        logger.info("")
        logger.info(f"✅ Fuzzy matches found: {stats['fuzzy_matches_found']}")
        logger.info(
            f"🟢 High confidence (≥{HIGH_CONFIDENCE_THRESHOLD}%): {stats['high_confidence_fuzzy']}"
        )
        logger.info(
            f"🟡 Medium confidence ({self.min_score}-{HIGH_CONFIDENCE_THRESHOLD-1}%): {stats['fuzzy_matches_found'] - stats['high_confidence_fuzzy']}"
        )
        logger.info(f"💾 Output: {fuzzy_output_path}")
        logger.info("")
        logger.info(f"❌ BNetzA final no-matches: {stats['bnetza_final_no_matches']}")
        logger.info(
            f"📊 BNetzA fuzzy match rate: {stats['bnetza_fuzzy_match_rate']:.1f}%"
        )
        logger.info(f"💾 Output: {bnetza_no_match_path}")
        logger.info("")
        logger.info(f"❌ BDEW final no-matches: {stats['bdew_final_no_matches']}")
        logger.info(f"📊 BDEW fuzzy match rate: {stats['bdew_fuzzy_match_rate']:.1f}%")
        logger.info(f"💾 Output: {bdew_no_match_path}")

        # Show confidence distribution
        if fuzzy_matches:
            confidence_ranges = {
                "90-100%": sum(
                    1
                    for m in fuzzy_matches
                    if m["match_confidence"] >= EXCELLENT_CONFIDENCE_THRESHOLD
                ),
                "80-89%": sum(
                    1
                    for m in fuzzy_matches
                    if GOOD_CONFIDENCE_THRESHOLD
                    <= m["match_confidence"]
                    < EXCELLENT_CONFIDENCE_THRESHOLD
                ),
                "70-79%": sum(
                    1
                    for m in fuzzy_matches
                    if MIN_FUZZY_MATCH_SCORE
                    <= m["match_confidence"]
                    < GOOD_CONFIDENCE_THRESHOLD
                ),
            }

            logger.info("\n📊 Fuzzy Match Confidence Distribution:")
            for range_name, count in confidence_ranges.items():
                if count > 0:
                    percentage = (count / len(fuzzy_matches)) * 100
                    logger.info(f"  {range_name}: {count} matches ({percentage:.1f}%)")

        return stats


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Perform fuzzy matching on non-exact matches from BNetzA and BDEW data"
    )

    parser.add_argument(
        "--bnetza-non-matches",
        type=Path,
        default=Path("data/bnetza_non_exact_matches.csv"),
        help="Path to BNetzA non-exact matches CSV file (default: data/bnetza_non_exact_matches.csv)",
    )

    parser.add_argument(
        "--bdew-non-matches",
        type=Path,
        default=Path("data/bdew_non_exact_matches.csv"),
        help="Path to BDEW non-exact matches CSV file (default: data/bdew_non_exact_matches.csv)",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("data"),
        help="Output directory for result CSV files (default: data/)",
    )

    parser.add_argument(
        "--min-score",
        type=int,
        default=MIN_FUZZY_MATCH_SCORE,
        help=f"Minimum fuzzy match score (default: {MIN_FUZZY_MATCH_SCORE})",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    return parser.parse_args()


def main():
    """Main function."""
    args = parse_arguments()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Check input files
    required_files = [args.bnetza_non_matches, args.bdew_non_matches]
    for file_path in required_files:
        if not file_path.exists():
            logger.error(f"❌ Required file not found: {file_path}")
            sys.exit(1)

    # Initialize processor
    processor = FuzzyMatchProcessor(min_score=args.min_score)

    try:
        # Process fuzzy matches
        processor.process_fuzzy_matches(
            args.bnetza_non_matches, args.bdew_non_matches, args.output_dir
        )

        logger.info("\n🎉 Fuzzy match processing completed successfully!")

    except KeyboardInterrupt:
        logger.warning("\n⚠️ Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        if args.verbose:
            logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
