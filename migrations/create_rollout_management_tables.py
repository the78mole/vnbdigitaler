#!/usr/bin/env python3
"""
Database Migration: Create Rollout Tables

Creates the new, clean rollout management tables:
- rollout_companies: Companies from BNetzA rollout reports
- rollout_quotas: Smart meter rollout quotas
- rollout_reports: Processed report tracking
- workflow_executions: Workflow execution monitoring

This migration implements the correct rollout-focused approach,
not the old BDEW-matching approach.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from config import get_config
from rollout_models import (
    Base,
    RolloutCompany,
    RolloutQuota,
    RolloutReport,
    WorkflowExecution,
)

from database import get_engine


def create_rollout_tables():
    """Create all rollout management tables."""
    print("🏗️  Creating rollout management tables...")

    config = get_config()
    engine = get_engine()

    try:
        # Create all tables defined in rollout_models
        Base.metadata.create_all(engine)

        print("✅ Successfully created rollout tables:")
        print("   - rollout_companies")
        print("   - rollout_quotas")
        print("   - rollout_reports")
        print("   - workflow_executions")

        print("\n📊 Table Details:")
        print("   🏢 rollout_companies: BNetzA rollout report companies")
        print("   📈 rollout_quotas: Smart meter rollout quotas by quarter")
        print("   📄 rollout_reports: Processed report tracking")
        print("   ⚙️  workflow_executions: Workflow execution monitoring")

        return True

    except Exception as e:
        print(f"❌ Failed to create rollout tables: {e}")
        return False


if __name__ == "__main__":
    success = create_rollout_tables()
    sys.exit(0 if success else 1)
