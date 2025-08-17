#!/usr/bin/env python3
"""
BNetzA Roll-Out Report Finder

This script uses AI (OpenRouter) to analyze found Excel URLs and identify
which one contains the Smart Meter Roll-Out Quoten (quarterly reports).

Usage:
    uv run python tools/02_find_roll_out_report.py [--metadata-file PATH] [--verbose] [--dry-run]
"""

import argparse
import json
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    Environment = None
    FileSystemLoader = None


# Load environment variables from .env file if available
def load_env_file():
    """Load environment variables from .env file in project root."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with env_file.open("r", encoding="utf-8") as f:
            for raw_line in f:
                env_line = raw_line.strip()
                if env_line and not env_line.startswith("#") and "=" in env_line:
                    key, value = env_line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if (
                        value and key not in os.environ
                    ):  # Don't override existing env vars
                        os.environ[key] = value


# Load .env before importing other modules
load_env_file()


# Constants
DEFAULT_MODEL = os.getenv(
    "ROLL_OUT_REPORT_FIND_MODEL", "NousResearch/Hermes-2-Pro-Llama-3-8B"
)
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
USER_AGENT = (
    "vnbdigitaler/1.0 (AI URL Classifier; https://github.com/the78mole/vnbdigitaler)"
)
REQUEST_TIMEOUT = 30
SIMULATED_ROLLOUT_INDEX = 3  # Index for dry-run simulation


class RollOutReportFinder:
    """Uses AI to identify Roll-Out Report URLs from BNetzA Excel files."""

    def __init__(
        self,
        verbose: bool = False,
        dry_run: bool = False,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.verbose = verbose
        self.dry_run = dry_run
        self.override_api_key = api_key
        self.model = model or DEFAULT_MODEL

        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

        # Initialize OpenRouter client
        self.api_key = self._get_api_key()

        # For free models, we might not need an API key
        if not self.dry_run:
            if not self.api_key and not self._is_free_model():
                raise ValueError(
                    "OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable."
                )

            self.client = OpenAI(
                base_url=OPENROUTER_BASE_URL,
                api_key=self.api_key or "dummy-key-for-free-models",
                default_headers={
                    "HTTP-Referer": "https://github.com/the78mole/vnbdigitaler",
                    "X-Title": "VNBdigitaler Roll-Out Report Finder",
                },
            )
        else:
            self.client = None

    def _get_api_key(self) -> str | None:
        """Get OpenRouter API key from environment or config."""
        # Use override API key first (from command line)
        if self.override_api_key:
            return self.override_api_key

        # Try environment variable
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            return api_key

        # Try from config file if available
        try:
            from src.config import settings

            return getattr(settings, "openrouter_api_key", None)
        except ImportError:
            pass

        return None

    def _is_free_model(self) -> bool:
        """Check if the current model is a free model that doesn't require an API key."""
        free_models = [
            "meta-llama/llama-3.2-3b-instruct:free",
            "microsoft/phi-3.5-mini-128k-instruct:free",
            # Note: google/gemma-3n-e2b-it:free has issues with system messages
            # Note: meta-llama/llama-3.2-1b-instruct:free not available
        ]
        return self.model in free_models

    def create_jinja_prompt(self, excel_urls: list[str]) -> str:
        """Create AI prompt using Jinja2 template."""
        if Environment is None or FileSystemLoader is None:
            self.logger.warning("Jinja2 not available, falling back to simple prompt")
            return self.create_analysis_prompt(excel_urls)

        try:
            # Setup Jinja2 environment with autoescape for security
            template_dir = Path(__file__).parent / "templates"
            env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=True,  # Enable autoescape to prevent XSS vulnerabilities
            )

            # Add custom date filter
            def date_filter(value, format_string):
                if isinstance(value, datetime):
                    return value.strftime(format_string)
                return value

            env.filters["date"] = date_filter

            # Choose template based on model
            if "hermes" in self.model.lower():
                template_name = "find_report_prompt_hermes.md.j2"
                self.logger.debug("Using Hermes-2-Pro native template")
            else:
                template_name = "find_report_prompt.md.j2"
                self.logger.debug("Using standard Jinja2 template")

            # Load and render template
            template = env.get_template(template_name)
            prompt = template.render(urls=excel_urls, now=datetime.now())

            self.logger.debug(f"Successfully rendered Jinja2 template: {template_name}")
            return prompt

        except Exception as e:
            self.logger.warning(
                f"Failed to render Jinja2 template: {e}, falling back to simple prompt"
            )
            return self.create_analysis_prompt(excel_urls)

    def load_metadata(self, metadata_file: Path) -> dict[str, Any]:
        """Load metadata from previous download step."""
        self.logger.info(f"Loading metadata from: {metadata_file}")

        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")

        with metadata_file.open("r", encoding="utf-8") as f:
            metadata = json.load(f)

        self.logger.info(
            f"Loaded metadata with {metadata['excel_files']['count']} Excel URLs"
        )
        return metadata

    def create_analysis_prompt(self, excel_urls: list[str]) -> str:
        """Create a focused prompt for AI analysis."""
        urls_text = "\n".join(f"{i+1}. {url}" for i, url in enumerate(excel_urls))

        prompt = f"""Analysiere diese Excel-Datei URLs von der Bundesnetzagentur (BNetzA) und identifiziere welche die Smart Meter Roll-Out Quoten (quartalsweise Berichte) enthält:

{urls_text}

Die URLs enthalten folgende Dateitypen:
- Roll-Out-Quoten: Quartalsberichte mit Statistiken zum Smart Meter Rollout
- Fragebogen: Erhebungsbögen für Messstellenbetreiber
- Standard/Sonder: Verschiedene Kategorien von Erhebungen

Antworte NUR mit der Nummer (1-{len(excel_urls)}) der URL, die die Roll-Out-Quoten enthält.
Falls mehrere URLs Roll-Out-Quoten enthalten könnten, wähle die aktuellste.
Falls keine eindeutige Roll-Out-Quoten URL identifiziert werden kann, antworte mit "0".

Antwort:"""

        return prompt

    def analyze_urls_with_ai(self, excel_urls: list[str]) -> dict[str, Any]:
        """Use AI to analyze and classify Excel URLs."""
        if self.dry_run:
            self.logger.info("DRY RUN: Would analyze URLs with AI")
            return {
                "selected_index": SIMULATED_ROLLOUT_INDEX,
                "selected_url": excel_urls[SIMULATED_ROLLOUT_INDEX]
                if len(excel_urls) > SIMULATED_ROLLOUT_INDEX
                else excel_urls[0],
                "confidence": "high (simulated)",
                "reasoning": "DRY RUN: Simulated selection of Roll-out-Quoten file",
            }

        self.logger.info(
            f"Analyzing {len(excel_urls)} URLs with AI model: {self.model}"
        )

        # Use appropriate Jinja2 template based on model
        prompt = self.create_jinja_prompt(excel_urls)

        # For Hermes-2-Pro native format, send as single user message
        if "hermes" in self.model.lower():
            messages = [{"role": "user", "content": prompt}]
        else:
            # Use system + user message for other models
            messages = [
                {
                    "role": "system",
                    "content": "Du bist ein Experte für deutsche Behördendokumente und Smart Meter Rollout-Berichte. Analysiere URLs präzise und objektiv.",
                },
                {"role": "user", "content": prompt},
            ]

        try:
            if not self.client:
                raise ValueError("AI client not available (dry_run mode or no API key)")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
                max_tokens=200,  # Increased for JSON response from template
                temperature=0.1,  # Low temperature for consistent results
                timeout=REQUEST_TIMEOUT,
            )

            ai_response = response.choices[0].message.content
            ai_response = ai_response.strip() if ai_response else ""
            self.logger.debug(f"AI response: {ai_response}")

            # Parse AI response
            try:
                # Try to parse as JSON first (from Jinja2 template)
                try:
                    json_text = ai_response
                    # Extract JSON from code blocks if present
                    if "```json" in ai_response:
                        start = ai_response.find("```json") + 7
                        end = ai_response.find("```", start)
                        if end != -1:
                            json_text = ai_response[start:end].strip()
                    elif "```" in ai_response:
                        start = ai_response.find("```") + 3
                        end = ai_response.find("```", start)
                        if end != -1:
                            json_text = ai_response[start:end].strip()

                    ai_json = json.loads(json_text)
                    if isinstance(ai_json, dict):
                        selected_index = None
                        selected_url_from_ai = ai_json.get("selected_url")

                        # Method 1: Use selected_url if provided and validate
                        if selected_url_from_ai:
                            # Find index of URL in our list
                            for i, url in enumerate(excel_urls):
                                if url == selected_url_from_ai:
                                    selected_index = i
                                    self.logger.info(
                                        f"AI provided valid selected_url, matched to index {i}"
                                    )
                                    break

                            if selected_index is None:
                                self.logger.warning(
                                    f"AI provided selected_url not in list: {selected_url_from_ai}"
                                )
                                # Fall back to selected_index if URL doesn't match
                                if "selected_index" in ai_json:
                                    selected_index = ai_json["selected_index"]

                        # Method 2: Use selected_index with validation and correction
                        elif "selected_index" in ai_json:
                            selected_index = ai_json["selected_index"]

                        if selected_index is None:
                            raise ValueError(
                                "AI JSON response missing both selected_url and selected_index"
                            )

                        # Validate and correct index (be forgiving with 1-based counting)
                        original_index = selected_index
                        if selected_index < 0:
                            raise ValueError(
                                f"AI returned negative index: {selected_index}"
                            )
                        elif selected_index >= len(excel_urls):
                            # Check if AI used 1-based indexing instead of 0-based
                            if (
                                selected_index - 1 < len(excel_urls)
                                and selected_index - 1 >= 0
                            ):
                                self.logger.warning(
                                    f"AI used 1-based indexing ({selected_index}), correcting to 0-based ({selected_index - 1})"
                                )
                                selected_index = selected_index - 1
                            else:
                                raise ValueError(
                                    f"AI returned invalid index: {selected_index} (max: {len(excel_urls) - 1})"
                                )

                        # Validate against selected_url if both provided
                        if (
                            selected_url_from_ai
                            and excel_urls[selected_index] != selected_url_from_ai
                        ):
                            self.logger.warning(
                                f"Mismatch between selected_index ({selected_index}) and selected_url. "
                                f"Index points to: {excel_urls[selected_index][:100]}... "
                                f"But AI provided: {selected_url_from_ai[:100]}..."
                            )
                            # Trust the URL over the index
                            for i, url in enumerate(excel_urls):
                                if url == selected_url_from_ai:
                                    selected_index = i
                                    self.logger.info(
                                        f"Using URL-based selection, corrected index to {i}"
                                    )
                                    break

                        # Extract additional fields from JSON response
                        confidence = ai_json.get("confidence", "high")
                        reasoning = ai_json.get(
                            "reasoning",
                            f"AI selected URL {selected_index + 1} as Roll-Out report",
                        )
                        quarter = ai_json.get("quarter", "unknown")
                        year = ai_json.get("year", "unknown")

                        result = {
                            "selected_index": selected_index,
                            "selected_url": excel_urls[selected_index],
                            "confidence": confidence,
                            "reasoning": reasoning,
                            "quarter": quarter,
                            "year": year,
                            "ai_response": ai_response,
                            "model_used": self.model,
                            "tokens_used": response.usage.total_tokens
                            if response.usage
                            else 0,
                        }

                        # Log any index corrections for debugging
                        if original_index != selected_index:
                            result["index_corrected"] = True
                            result["original_index"] = original_index
                            self.logger.info(
                                f"Index corrected from {original_index} to {selected_index}"
                            )

                        self.logger.info(
                            f"AI selected URL {selected_index + 1}: {Path(excel_urls[selected_index]).name}"
                        )
                        return result

                except json.JSONDecodeError:
                    # Fallback: try to parse as simple number (legacy format)
                    selected_index = int(ai_response) - 1  # Convert to 0-based index
                    if selected_index < 0 or selected_index >= len(excel_urls):
                        raise ValueError(f"AI returned invalid index: {ai_response}")

                    result = {
                        "selected_index": selected_index,
                        "selected_url": excel_urls[selected_index],
                        "confidence": "high",
                        "reasoning": f"AI selected URL {selected_index + 1} as Roll-Out report",
                        "ai_response": ai_response,
                        "model_used": self.model,
                        "tokens_used": response.usage.total_tokens
                        if response.usage
                        else 0,
                    }

                    self.logger.info(
                        f"AI selected URL {selected_index + 1}: {Path(excel_urls[selected_index]).name}"
                    )
                    return result

            except ValueError as e:
                self.logger.warning(f"Could not parse AI response '{ai_response}': {e}")
                # Fallback: look for Roll-out pattern in URLs
                return self._fallback_pattern_matching(excel_urls)

        except Exception as e:
            self.logger.error(f"AI analysis failed: {e}")
            # Fallback to pattern matching
            return self._fallback_pattern_matching(excel_urls)

    def _fallback_pattern_matching(self, excel_urls: list[str]) -> dict[str, Any]:
        """Fallback method using pattern matching for Roll-Out URLs."""
        self.logger.info("Using fallback pattern matching for URL selection")

        rollout_patterns = ["roll-out", "rollout", "quoten", "quote"]

        for i, url in enumerate(excel_urls):
            url_lower = url.lower()
            # Prefer quarterly reports (Q1, Q2, etc.) over forms
            if any(pattern in url_lower for pattern in rollout_patterns) and any(
                quarter in url_lower for quarter in ["_q1_", "_q2_", "_q3_", "_q4_"]
            ):
                self.logger.info(
                    f"Pattern matching selected URL {i + 1}: {Path(url).name}"
                )
                return {
                    "selected_index": i,
                    "selected_url": url,
                    "confidence": "medium",
                    "reasoning": "Pattern matching: found roll-out with quarterly identifier",
                    "method": "fallback_pattern",
                }

        # If no clear quarterly report, take the first roll-out URL
        for i, url in enumerate(excel_urls):
            if any(pattern in url.lower() for pattern in rollout_patterns):
                self.logger.info(
                    f"Pattern matching selected URL {i + 1}: {Path(url).name}"
                )
                return {
                    "selected_index": i,
                    "selected_url": url,
                    "confidence": "low",
                    "reasoning": "Pattern matching: found roll-out URL but no clear quarterly identifier",
                    "method": "fallback_pattern",
                }

        # No roll-out URL found
        self.logger.warning("No Roll-Out URL identified")
        return {
            "selected_index": -1,
            "selected_url": None,
            "confidence": "none",
            "reasoning": "No Roll-Out URL pattern found",
            "method": "fallback_pattern",
        }

    def save_results(
        self,
        metadata: dict[str, Any],
        analysis_result: dict[str, Any],
        output_file: Path,
    ):
        """Save analysis results to file."""
        results = {
            "analysis_session": {
                "timestamp": datetime.now().isoformat(),
                "script_version": "1.0",
                "dry_run": self.dry_run,
            },
            "input_metadata": {
                "source_file": str(
                    metadata.get("download_session", {}).get(
                        "temp_directory", "unknown"
                    )
                ),
                "total_urls": metadata["excel_files"]["count"],
                "download_timestamp": metadata.get("download_session", {}).get(
                    "timestamp"
                ),
            },
            "ai_analysis": analysis_result,
            "selected_report": {
                "url": analysis_result.get("selected_url"),
                "filename": Path(analysis_result["selected_url"]).name.split("?")[0]
                if analysis_result.get("selected_url")
                else None,
                "confidence": analysis_result.get("confidence"),
                "method": analysis_result.get("method", "ai_analysis"),
            },
            "all_urls": metadata["excel_files"]["found_urls"],
        }

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Results saved to: {output_file}")

    def run(
        self, metadata_file: Path, output_file: Path | None = None
    ) -> dict[str, Any]:
        """Run the complete analysis process."""
        self.logger.info("Starting Roll-Out Report analysis...")

        try:
            # Load metadata from previous step
            metadata = self.load_metadata(metadata_file)

            excel_urls = metadata["excel_files"]["found_urls"]
            if not excel_urls:
                raise ValueError("No Excel URLs found in metadata")

            # Analyze URLs with AI
            analysis_result = self.analyze_urls_with_ai(excel_urls)

            # Determine output file
            if not output_file:
                base_dir = metadata_file.parent
                output_file = base_dir / "roll_out_analysis.json"

            # Save results
            self.save_results(metadata, analysis_result, output_file)

            self.logger.info("Analysis completed successfully!")
            return analysis_result

        except Exception as e:
            self.logger.error(f"Analysis process failed: {e}")
            raise


def find_latest_metadata_file() -> Path | None:
    """Find the most recent metadata file from download script."""
    # Use workspace tmp directory instead of system temp
    workspace_root = Path(__file__).parent.parent
    temp_dir = workspace_root / "tmp"

    if not temp_dir.exists():
        return None

    # Look for BNetzA download directories
    bnetza_dirs = list(temp_dir.glob("bnetza_download_*"))
    if not bnetza_dirs:
        return None

    # Find the most recent one with metadata
    latest_metadata = None
    latest_time = 0

    for dir_path in bnetza_dirs:
        metadata_file = dir_path / "download_metadata.json"
        if metadata_file.exists():
            mtime = metadata_file.stat().st_mtime
            if mtime > latest_time:
                latest_time = mtime
                latest_metadata = metadata_file

    return latest_metadata


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Find Roll-Out Report URL using AI analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--metadata-file",
        type=Path,
        help="Path to metadata JSON file from download script (default: auto-detect latest)",
    )

    parser.add_argument(
        "--output-file",
        type=Path,
        help="Output file for analysis results (default: auto-generated)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate analysis without calling AI API",
    )

    parser.add_argument(
        "--api-key",
        type=str,
        help="OpenRouter API key (overrides environment variable)",
    )

    parser.add_argument(
        "--model",
        type=str,
        help="AI model to use (overrides ROLL_OUT_REPORT_FIND_MODEL environment variable)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Find metadata file if not specified
    if not args.metadata_file:
        args.metadata_file = find_latest_metadata_file()
        if not args.metadata_file:
            print("❌ No metadata file found. Run 01_download_bnetza_data.py first.")
            sys.exit(1)
        print(f"📁 Using metadata file: {args.metadata_file}")

    # Create analyzer
    try:
        analyzer = RollOutReportFinder(
            verbose=args.verbose,
            dry_run=args.dry_run,
            api_key=args.api_key,
            model=args.model,
        )

        # Run analysis
        result = analyzer.run(
            metadata_file=args.metadata_file, output_file=args.output_file
        )

        # Show results
        if result["selected_url"]:
            print("\n✅ Roll-Out Report identified!")
            print(f"📊 Selected: {Path(result['selected_url']).name.split('?')[0]}")
            print(f"🎯 Confidence: {result['confidence']}")
            print(f"💭 Method: {result.get('method', 'ai_analysis')}")
            if not args.dry_run and "tokens_used" in result:
                print(f"🔢 AI Tokens used: {result['tokens_used']}")
        else:
            print("\n⚠️  No Roll-Out Report identified")
            print(f"💭 Reason: {result.get('reasoning', 'Unknown')}")

    except KeyboardInterrupt:
        print("\n❌ Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
