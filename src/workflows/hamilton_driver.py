"""
Hamilton Driver for BDEW Code Update Workflow.

This module orchestrates the BDEW code update workflow using Hamilton.
"""

import logging
from datetime import datetime

from hamilton import driver

from . import bdew_update_workflow_normalized as workflow

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_hamilton_driver():
    """Create and configure the Hamilton driver."""
    config = {}  # No specific config needed for now

    dr = driver.Driver(
        config,
        workflow,
    )
    return dr


def run_bdew_sync():
    """Execute the complete BDEW synchronization workflow."""
    logger.info("Starting BDEW Code synchronization workflow")

    try:
        # Create Hamilton driver
        dr = create_hamilton_driver()

        # Execute the workflow
        result = dr.execute(
            ["workflow_summary"],  # Final output node
            inputs={},  # No external inputs needed
        )

        summary = result["workflow_summary"]

        logger.info("BDEW synchronization workflow completed")
        logger.info(f"Workflow ID: {summary['workflow_id']}")
        logger.info(f"Duration: {summary['duration_seconds']} seconds")
        logger.info(f"Success: {summary['overall_success']}")
        logger.info(f"Records inserted: {summary['records_inserted']}")
        logger.info(f"Records updated: {summary['records_updated']}")
        logger.info(f"Records failed: {summary['records_failed']}")

        return summary

    except Exception as e:
        logger.error(f"BDEW synchronization workflow failed: {e}")
        raise


def visualize_workflow():
    """Generate a visualization of the Hamilton workflow DAG."""
    try:
        from hamilton import graph  # noqa: PLC0415

        dr = create_hamilton_driver()

        # Generate the DAG visualization
        # Get all nodes from the driver
        nodes = set(dr.list_available_variables())

        dot_graph = graph.create_graphviz_graph(
            nodes,
            comment="BDEW Code Update Workflow",
            graphviz_kwargs={},
            node_modifiers={},
            strictly_display_only_nodes_passed_in=False,
        )

        # Save to file
        output_file = f"bdew_workflow_dag_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        dot_graph.render(output_file, format="png", cleanup=True)

        logger.info(f"Workflow DAG visualization saved as {output_file}.png")
        return f"{output_file}.png"

    except ImportError:
        logger.warning("Graphviz not available for workflow visualization")
        return None
    except Exception as e:
        logger.error(f"Failed to generate workflow visualization: {e}")
        return None


if __name__ == "__main__":
    # Run the workflow
    summary = run_bdew_sync()

    # Optionally generate visualization
    visualize_workflow()
