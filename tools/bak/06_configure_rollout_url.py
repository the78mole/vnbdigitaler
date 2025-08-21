#!/usr/bin/env python3
"""
VNBdigitaler - Script 06: BNetzA Roll-Out URL Discovery

This script extracts Excel URLs from the BNetzA iMSys article page
and uses AI to identify which Excel file contains the Smart Meter Roll-Out Quoten.
No files are stored locally - only the final identification result.

Author: VNBdigitaler Project
Date: 2025-08-21
"""

import argparse
import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Constants
BNETZA_ARTICLE_URL = "https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/NetzzugangMesswesen/Mess-undZaehlwesen/iMSys/artikel.html"
USER_AGENT = (
    "vnbdigitaler/1.0 (Data Collection Bot; https://github.com/the78mole/vnbdigitaler)"
)
REQUEST_TIMEOUT = 30
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2

# AI Models (prioritized by speed and reliability)
AI_MODELS = [
    "anthropic/claude-3-haiku-20240307",  # Fast and reliable
    "openai/gpt-4o-mini",  # Good fallback
    "google/gemini-flash-1.5",  # Alternative
    "meta-llama/llama-3.1-8b-instruct",  # Open source option
]

# Roll-Out URL configurations
DEFAULT_QUARTER = "Q1_2025"

ROLLOUT_URLS = {
    "Q1_2025": {
        "quarter": "Q1",
        "year": "2025",
        "description": "Roll-out-Quoten Q1 2025",
        "filename": "Roll-out-Quoten_Q1_2025.xlsx",
        "url": "https://www.bundesnetzagentur.de/SharedDocs/Downloads/DE/Sachgebiete/ElektrizitaetundGas/Unternehmen_Institutionen/NetzanschlussErzeugungsanlagen/iMSys/Roll-out-Quoten_Q1_2025.xlsx",
    }
}

# Logging setup
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BNetzARollOutURLProvider:
    """Provides direct URLs for BNetzA Roll-Out Quoten data."""

    def __init__(self, data_dir: Path | None = None, verbose: bool = False):
        # Use workspace data directory
        if data_dir is None:
            workspace_root = Path(__file__).parent.parent
            data_dir = workspace_root / "data"

        self.data_dir = data_dir
        self.verbose = verbose

        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)

        if self.verbose:
            logger.setLevel(logging.DEBUG)

        logger.info("🔧 BNetzA Roll-Out URL Provider initialized")
        logger.info(f"📁 Data directory: {self.data_dir}")

    def list_available_quarters(self) -> dict[str, dict]:
        """List all available quarters."""
        return ROLLOUT_URLS

    def get_url_for_quarter(self, quarter: str) -> dict | None:
        """Get URL information for a specific quarter."""
        return ROLLOUT_URLS.get(quarter)

    def get_latest_quarter(self) -> dict:
        """Get the latest available quarter data."""
        return ROLLOUT_URLS[DEFAULT_QUARTER]

    def create_identification_file(self, quarter: str | None = None) -> Path:
        """Create the identification JSON file for the specified quarter."""
        if quarter is None:
            quarter = DEFAULT_QUARTER

        quarter_data = self.get_url_for_quarter(quarter)
        if not quarter_data:
            raise ValueError(
                f"Quarter '{quarter}' not available. Available quarters: {list(ROLLOUT_URLS.keys())}"
            )

        # Create identification data in the same format as the AI-based approach
        identification_data = {
            "identification_timestamp": datetime.now().isoformat(),
            "method_used": "direct_url",
            "quarter_requested": quarter,
            "identified_file": {
                "number": 1,  # Always 1 since we're selecting directly
                "filename": quarter_data["filename"],
                "url": quarter_data["url"],
                "confidence": 100,  # 100% confidence since we know the URL
                "reasoning": f"Direct URL for {quarter_data['description']} - manually verified and configured",
            },
            "quarter_info": {
                "quarter": quarter_data["quarter"],
                "year": quarter_data["year"],
                "description": quarter_data["description"],
            },
        }

        # Save to data directory
        output_file = self.data_dir / "bnetza_rollout_identification.json"
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(identification_data, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Identification file created: {output_file}")
        return output_file

    def run(self, quarter: str | None = None, dry_run: bool = False) -> dict:
        """Run the URL provider process."""
        if dry_run:
            logger.info("🔍 DRY RUN - No files will be created")
            return {"dry_run": True}

        try:
            # Use default quarter if not specified
            if quarter is None:
                quarter = DEFAULT_QUARTER
                logger.info(f"📅 Using default quarter: {quarter}")
            else:
                logger.info(f"📅 Using requested quarter: {quarter}")

            # Validate quarter exists
            quarter_data = self.get_url_for_quarter(quarter)
            if not quarter_data:
                available = ", ".join(ROLLOUT_URLS.keys())
                logger.error(
                    f"❌ Quarter '{quarter}' not available. Available: {available}"
                )
                return {"error": f"Quarter '{quarter}' not available"}

            # Create identification file
            output_file = self.create_identification_file(quarter)

            logger.info("🎯 Roll-Out URL Configuration Summary:")
            logger.info(f"📊 Quarter: {quarter_data['quarter']} {quarter_data['year']}")
            logger.info(f"✅ File: {quarter_data['filename']}")
            logger.info("🎯 Confidence: 100% (Direct URL)")
            logger.info(f"💡 Description: {quarter_data['description']}")
            logger.info(f"📁 Saved to: {output_file}")

            return {
                "success": True,
                "quarter": quarter,
                "quarter_data": quarter_data,
                "output_file": str(output_file),
                "data_directory": str(self.data_dir),
            }

        except Exception as e:
            logger.error(f"❌ URL configuration failed: {e}")
            if self.verbose:
                logger.error(traceback.format_exc())
            return {"error": str(e)}


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Configure BNetzA Roll-Out Quoten URL (direct approach)"
    )

    parser.add_argument(
        "--quarter",
        "-q",
        type=str,
        help=f"Quarter to use (default: {DEFAULT_QUARTER}). Available: {', '.join(ROLLOUT_URLS.keys())}",
    )

    parser.add_argument(
        "--data-dir", type=Path, help="Custom data directory (default: workspace data/)"
    )

    parser.add_argument(
        "--list-quarters",
        "-l",
        action="store_true",
        help="List all available quarters and exit",
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Perform dry run without creating files"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()

    try:
        provider = BNetzARollOutURLProvider(
            data_dir=args.data_dir, verbose=args.verbose
        )

        # Handle list quarters command
        if args.list_quarters:
            logger.info("📅 Available quarters:")
            for quarter_id, quarter_data in provider.list_available_quarters().items():
                logger.info(f"  {quarter_id}: {quarter_data['description']}")
                if args.verbose:
                    logger.info(f"    File: {quarter_data['filename']}")
                    logger.info(f"    URL: {quarter_data['url']}")
            sys.exit(0)

        # Run the main process
        result = provider.run(quarter=args.quarter, dry_run=args.dry_run)

        if result.get("success"):
            logger.info("🎉 Roll-Out URL configuration completed successfully!")
            sys.exit(0)
        else:
            logger.error("💥 Roll-Out URL configuration failed")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("🛑 Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        if args.verbose:
            logger.error(traceback.format_exc())

            logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
