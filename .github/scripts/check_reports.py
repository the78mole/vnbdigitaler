#!/usr/bin/env python3
"""
GitHub Actions Check Reports Script

This script checks for new BNetzA rollout reports and sets GitHub Actions outputs.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_check() -> bool:
    """
    Check for new BNetzA rollout reports.

    Returns:
        bool: True if updates are available, False otherwise
    """
    try:
        # Check for new reports
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "src/bnetza/rollout_report_updater.py",
                "--check-update",
                "--verbose",
            ],
            capture_output=True,
            text=True,
            cwd=".",
            check=False,
        )

        output = result.stdout + result.stderr
        print("=== CHECK REPORT OUTPUT ===")
        print(output)
        print("=== END OUTPUT ===")

        # Determine if updates are available based on exit code and output
        has_updates = (
            result.returncode == 0 and "no new reports available" not in output.lower()
        )

        # Set GitHub Actions output
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            output_clean = output.replace("\n", " ")
            with Path(github_output).open("a") as f:
                f.write(f"has_updates={str(has_updates).lower()}\n")
                f.write(f"check_output={output_clean}\n")

        return has_updates

    except Exception as e:
        print(f"Error checking reports: {e}")
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with Path(github_output).open("a") as f:
                f.write("has_updates=false\n")
                f.write(f"check_output=Error: {e}\n")
        return False


def main():
    """Main entry point."""
    run_check()
    sys.exit(0)


if __name__ == "__main__":
    main()
