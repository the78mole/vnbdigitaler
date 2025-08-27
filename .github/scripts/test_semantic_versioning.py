#!/usr/bin/env python3
"""
Test script for semantic versioning and release system.

This script simulates the commit patterns that trigger different version bumps
to help verify the semantic versioning configuration.
"""

import subprocess
from pathlib import Path


def run_git_command(cmd: list[str]) -> str:
    """Run a git command and return output."""
    result = subprocess.run(cmd, check=False, capture_output=True, text=True, cwd=".")
    if result.returncode != 0:
        print(f"Error running: {' '.join(cmd)}")
        print(f"Error: {result.stderr}")
        return ""
    return result.stdout.strip()


def test_semantic_versioning():
    """Test semantic versioning patterns."""
    print("🧪 Testing Semantic Versioning Patterns")
    print("=" * 50)

    # Get current git info
    current_branch = run_git_command(["git", "branch", "--show-current"])
    last_tag = run_git_command(["git", "describe", "--tags", "--abbrev=0"]) or "v0.0.0"

    print(f"📍 Current Branch: {current_branch}")
    print(f"🏷️ Last Tag: {last_tag}")
    print()

    # Test commit patterns
    test_patterns = [
        {
            "type": "patch",
            "pattern": "docs: update README with release information",
            "expected": "patch version bump (1.2.3 → 1.2.4)",
        },
        {
            "type": "patch",
            "pattern": "chore: update dependencies",
            "expected": "patch version bump (1.2.3 → 1.2.4)",
        },
        {
            "type": "minor",
            "pattern": "feat: add automatic semantic versioning",
            "expected": "minor version bump (1.2.3 → 1.3.0)",
        },
        {
            "type": "minor",
            "pattern": "fix: resolve release asset upload issues",
            "expected": "minor version bump (1.2.3 → 1.3.0)",
        },
        {
            "type": "minor",
            "pattern": "refactor: improve workflow error handling",
            "expected": "minor version bump (1.2.3 → 1.3.0)",
        },
        {
            "type": "major",
            "pattern": "feat!: change release artifact structure (BREAKING CHANGE)",
            "expected": "major version bump (1.2.3 → 2.0.0)",
        },
        {
            "type": "major",
            "pattern": "fix!: update database schema (BREAKING CHANGE)",
            "expected": "major version bump (1.2.3 → 2.0.0)",
        },
    ]

    print("📋 Commit Pattern Tests:")
    print()

    for i, test in enumerate(test_patterns, 1):
        print(f"{i}. **{test['type'].upper()} BUMP**")
        print(f"   Message: `{test['pattern']}`")
        print(f"   Expected: {test['expected']}")
        print()

    # Explain the versioning rules
    print("🔧 Versioning Rules:")
    print("- **Major** (BREAKING): Contains `BREAKING CHANGE`, `!:`, or `!)`")
    print("- **Minor** (Features): Starts with `feat:`, `fix:`, or `refactor:`")
    print("- **Patch** (Default): All other commit types")
    print()

    # Show current workflow configuration
    print("⚙️ Current Configuration:")
    print("- Tag Prefix: `v`")
    print("- Version Format: `${major}.${minor}.${patch}`")
    print("- Bump Each Commit: `true`")
    print("- Search Commit Body: `true`")
    print()

    # Release creation conditions
    print("📦 Release Creation Conditions:")
    print("1. ✅ BNetzA rollout update successful")
    print("2. ✅ Meaningful changes detected (new companies, updated quotas)")
    print("3. ✅ Not in dry-run or check-only mode")
    print("4. ✅ Has Excel/CSV files to include")
    print()

    print("🎯 To test the release system:")
    print("1. Make a commit with a semantic pattern:")
    print("   `git commit -m 'feat: add semantic versioning system'`")
    print("2. Trigger the central data update workflow")
    print("3. Check the releases page for new version")


def check_workflow_files():
    """Check if workflow files are properly configured."""
    print("📁 Checking Workflow Configuration:")
    print("=" * 50)

    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        print("❌ .github/workflows directory not found")
        return

    required_workflows = [
        "central-data-update.yml",
        "reusable-rollout-update.yml",
        "reusable-rollout-quota-update.yml",
        "reusable-rollout-company-update.yml",
    ]

    for workflow in required_workflows:
        workflow_path = workflows_dir / workflow
        if workflow_path.exists():
            print(f"✅ {workflow}")
        else:
            print(f"❌ {workflow}")

    print()

    # Check semantic versioning documentation
    semver_docs = Path(".github/SEMANTIC_VERSIONING.md")
    if semver_docs.exists():
        print("✅ .github/SEMANTIC_VERSIONING.md")
    else:
        print("❌ .github/SEMANTIC_VERSIONING.md")

    # Check commit template
    commit_template = Path(".gitmessage")
    if commit_template.exists():
        print("✅ .gitmessage")
    else:
        print("❌ .gitmessage")

    print()


def main():
    """Main entry point."""
    print("🚀 VNBdigitaler Semantic Versioning Test Suite")
    print("=" * 60)
    print()

    check_workflow_files()
    print()
    test_semantic_versioning()

    print("✨ Test complete! Review the output above to verify configuration.")


if __name__ == "__main__":
    main()
