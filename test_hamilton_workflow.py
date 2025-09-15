"""
Test script for Hamilton BDEW workflow.

This script tests the Hamilton workflow execution.
"""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from workflows.hamilton_driver import create_hamilton_driver

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_hamilton_driver_creation():
    """Test that Hamilton driver can be created."""
    try:
        driver = create_hamilton_driver()
        logger.info("✅ Hamilton driver created successfully")

        # Get the list of available functions
        available_nodes = list(driver.list_available_variables())
        logger.info(f"📋 Available workflow nodes: {len(available_nodes)}")
        # Sort node names as strings to avoid HamiltonNode comparison issues
        sorted_node_names = sorted([str(node) for node in available_nodes])
        for node in sorted_node_names:
            logger.info(f"  - {node}")

        return True
    except Exception as e:
        logger.error(f"❌ Failed to create Hamilton driver: {e}")
        return False


def test_workflow_graph():
    """Test workflow graph structure."""
    try:
        driver = create_hamilton_driver()

        # Check if we can execute a simple node
        result = driver.execute(["database_config"])
        config = result["database_config"]

        logger.info("✅ Workflow graph is valid")
        logger.info(f"📋 Database config: {config}")

        return True
    except Exception as e:
        logger.error(f"❌ Workflow graph test failed: {e}")
        return False


def test_individual_functions():
    """Test individual workflow functions."""
    try:
        driver = create_hamilton_driver()

        # Test individual nodes
        test_nodes = [
            "database_config",
            "bdew_web_config",
            "sync_metadata",
        ]

        for node in test_nodes:
            try:
                result = driver.execute([node])
                logger.info(f"✅ Node '{node}' executed successfully")
                logger.info(f"   Result type: {type(result[node])}")
            except Exception as e:
                logger.error(f"❌ Node '{node}' failed: {e}")
                return False

        return True
    except Exception as e:
        logger.error(f"❌ Individual function test failed: {e}")
        return False


def test_dry_run():
    """Test workflow execution without database operations."""
    logger.info("🧪 Starting dry run of BDEW workflow...")

    try:
        driver = create_hamilton_driver()

        # Test partial execution (up to data fetching)
        result = driver.execute(
            [
                "database_config",
                "bdew_web_config",
                "sync_metadata",
            ]
        )

        logger.info("✅ Dry run completed successfully")
        logger.info(f"📋 Results: {list(result.keys())}")

        return True
    except Exception as e:
        logger.error(f"❌ Dry run failed: {e}")
        return False


def main():
    """Run all tests."""
    logger.info("🚀 Starting Hamilton BDEW Workflow Tests")
    logger.info("=" * 60)

    tests = [
        ("Driver Creation", test_hamilton_driver_creation),
        ("Workflow Graph", test_workflow_graph),
        ("Individual Functions", test_individual_functions),
        ("Dry Run", test_dry_run),
    ]

    results = {}

    for test_name, test_func in tests:
        logger.info(f"\n📝 Running test: {test_name}")
        logger.info("-" * 40)

        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 Test Results Summary")
    logger.info("=" * 60)

    passed = 0
    total = len(tests)

    for test_name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{test_name:20s} : {status}")
        if success:
            passed += 1

    logger.info("-" * 60)
    logger.info(f"Overall: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed! Hamilton workflow is ready.")
        return True
    else:
        logger.error("💥 Some tests failed. Please check the workflow.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
