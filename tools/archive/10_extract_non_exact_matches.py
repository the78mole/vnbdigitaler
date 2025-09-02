#!/usr/bin/env python3
"""
VNBdigitaler - Script 10: Extract Non-Exact Matches

This script analyzes the exact matches CSV and creates two new CSV files:
1. BNetzA companies without exact matches in BDEW database
2. BDEW companies without exact matches in BNetzA Roll-Out data

This helps identify missing matches for further analysis and manual matching.

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

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NonExactMatchExtractor:
    """Extracts non-exact matches from BNetzA and BDEW data."""

    def __init__(self):
        """Initialize the non-exact match extractor."""
        pass

    def extract_non_matches(
        self,
        bnetza_csv_path: Path,
        bdew_csv_path: Path,
        exact_matches_csv_path: Path,
        output_dir: Path,
    ) -> dict[str, Any]:
        """Extract non-exact matches and create two CSV files."""
        logger.info("🔍 VNBdigitaler - Non-Exact Match Extraction")
        logger.info("=" * 60)

        # Load input data
        logger.info(f"📖 Reading BNetzA data from: {bnetza_csv_path}")
        bnetza_df = pd.read_csv(bnetza_csv_path)
        logger.info(f"📊 Loaded {len(bnetza_df)} BNetzA companies")

        logger.info(f"📖 Reading BDEW data from: {bdew_csv_path}")
        bdew_df = pd.read_csv(bdew_csv_path)
        logger.info(f"📊 Loaded {len(bdew_df)} BDEW companies")

        logger.info(f"📖 Reading exact matches from: {exact_matches_csv_path}")
        exact_matches_df = pd.read_csv(exact_matches_csv_path)
        logger.info(f"📊 Loaded {len(exact_matches_df)} exact matches")

        # Get sets of matched indices/codes
        matched_bnetza_indices = set(exact_matches_df["bnetza_index"])
        matched_bdew_codes = set(exact_matches_df["bdew_code"])

        logger.info("🔍 Finding non-matched entries...")

        # Find BNetzA companies without exact matches
        bnetza_non_matches = []
        for index, row in bnetza_df.iterrows():
            if index not in matched_bnetza_indices:
                bnetza_non_matches.append(
                    {
                        "bnetza_index": index,
                        "original_name": row["original_name"],
                        "normalized_name": row["normalized_name"],
                        "rollout_quote": row.get("ausstattungsquote", ""),
                    }
                )

        # Find BDEW companies without exact matches
        bdew_non_matches = []
        for _, row in bdew_df.iterrows():
            if row["bdew_code"] not in matched_bdew_codes:
                bdew_non_matches.append(
                    {
                        "bdew_code": row["bdew_code"],
                        "original_name": row["original_name"],
                        "city": row.get("city", ""),
                        "normalized_name": row["normalized_name"],
                    }
                )

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save BNetzA non-matches
        bnetza_output_path = output_dir / "bnetza_non_exact_matches.csv"
        logger.info(
            f"💾 Saving {len(bnetza_non_matches)} BNetzA non-matches to: {bnetza_output_path}"
        )

        with bnetza_output_path.open("w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "bnetza_index",
                "original_name",
                "normalized_name",
                "rollout_quote",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(bnetza_non_matches)

        # Save BDEW non-matches
        bdew_output_path = output_dir / "bdew_non_exact_matches.csv"
        logger.info(
            f"💾 Saving {len(bdew_non_matches)} BDEW non-matches to: {bdew_output_path}"
        )

        with bdew_output_path.open("w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["bdew_code", "original_name", "city", "normalized_name"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(bdew_non_matches)

        # Calculate statistics
        stats = {
            "total_bnetza_companies": len(bnetza_df),
            "total_bdew_companies": len(bdew_df),
            "exact_matches": len(exact_matches_df),
            "bnetza_non_matches": len(bnetza_non_matches),
            "bdew_non_matches": len(bdew_non_matches),
            "bnetza_match_rate": (
                (len(bnetza_df) - len(bnetza_non_matches)) / len(bnetza_df)
            )
            * 100,
            "bdew_match_rate": ((len(bdew_df) - len(bdew_non_matches)) / len(bdew_df))
            * 100,
        }

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("📈 NON-EXACT MATCH EXTRACTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"📊 Total BNetzA companies: {stats['total_bnetza_companies']}")
        logger.info(f"📊 Total BDEW companies: {stats['total_bdew_companies']}")
        logger.info(f"✅ Exact matches found: {stats['exact_matches']}")
        logger.info("")
        logger.info(f"❌ BNetzA non-matches: {stats['bnetza_non_matches']}")
        logger.info(f"📊 BNetzA match rate: {stats['bnetza_match_rate']:.1f}%")
        logger.info(f"💾 Output: {bnetza_output_path}")
        logger.info("")
        logger.info(f"❌ BDEW non-matches: {stats['bdew_non_matches']}")
        logger.info(f"📊 BDEW match rate: {stats['bdew_match_rate']:.1f}%")
        logger.info(f"💾 Output: {bdew_output_path}")

        # Show first few non-matches for verification
        if bnetza_non_matches:
            logger.info("\n📋 First 5 BNetzA non-matches:")
            for i, company in enumerate(bnetza_non_matches[:5]):
                logger.info(
                    f"  {i+1}. [{company['bnetza_index']}] {company['original_name']}"
                )

        if bdew_non_matches:
            logger.info("\n📋 First 5 BDEW non-matches:")
            for i, company in enumerate(bdew_non_matches[:5]):
                logger.info(
                    f"  {i+1}. [{company['bdew_code']}] {company['original_name']} ({company['city']})"
                )

        return stats


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract non-exact matches from BNetzA and BDEW data"
    )

    parser.add_argument(
        "--bnetza-csv",
        type=Path,
        default=Path("data/debug_bnetza_rollout_companies.csv"),
        help="Path to BNetzA debug CSV file (default: data/debug_bnetza_rollout_companies.csv)",
    )

    parser.add_argument(
        "--bdew-csv",
        type=Path,
        default=Path("data/debug_bdew_companies.csv"),
        help="Path to BDEW debug CSV file (default: data/debug_bdew_companies.csv)",
    )

    parser.add_argument(
        "--exact-matches-csv",
        type=Path,
        default=Path("data/exact_matches_rollout.csv"),
        help="Path to exact matches CSV file (default: data/exact_matches_rollout.csv)",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=Path("data"),
        help="Output directory for non-match CSV files (default: data/)",
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
    required_files = [args.bnetza_csv, args.bdew_csv, args.exact_matches_csv]
    for file_path in required_files:
        if not file_path.exists():
            logger.error(f"❌ Required file not found: {file_path}")
            sys.exit(1)

    # Initialize extractor
    extractor = NonExactMatchExtractor()

    try:
        # Extract non-matches
        extractor.extract_non_matches(
            args.bnetza_csv, args.bdew_csv, args.exact_matches_csv, args.output_dir
        )

        logger.info("\n🎉 Non-exact match extraction completed successfully!")

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
