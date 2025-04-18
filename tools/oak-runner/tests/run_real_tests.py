#!/usr/bin/env python3
"""
Run Real HTTP Tests for OAK Runner

This script runs Arazzo tests in real HTTP mode, making actual API calls
instead of using mocks.
"""

import argparse
import logging
import os
import sys
import unittest

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("arazzo-real-test")

# Add project directory to path so we can import the test modules
project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_dir)


# Main function
def main():
    parser = argparse.ArgumentParser(description="Run Arazzo tests with real HTTP calls")
    parser.add_argument("--fixture", type=str, help="Specific fixture to run (e.g., pet_coupons)")
    parser.add_argument(
        "--workflow", type=str, help="Specific workflow ID to run (e.g., getUserInfoAndSendMessage)"
    )
    parser.add_argument(
        "--list", action="store_true", help="List available real test fixtures and workflows"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--debug", "-d", action="store_true", help="Debug level logging")

    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("arazzo-test").setLevel(logging.DEBUG)
        logging.getLogger("arazzo-runner").setLevel(logging.DEBUG)

    # Import the test discovery module - use relative import since we're in the same package
    from .test_fixture_discovery import fixtures

    # Find ALL fixtures with their workflows - we'll run them in real mode
    # regardless of the 'enabled' flag when explicitly requested
    real_fixtures = {}
    for fixture in fixtures:
        # Get workflows for each fixture
        workflows = []
        for workflow_config in fixture["config"].get("workflows", []):
            workflows.append(workflow_config["id"])
        real_fixtures[fixture["name"]] = workflows

    # List available fixtures and workflows if requested
    if args.list:
        print("Available real-mode test fixtures and workflows:")
        for fixture_name, workflows in real_fixtures.items():
            print(f"  - {fixture_name}")
            for workflow in workflows:
                print(f"    • {workflow}")
        return

    # If a specific fixture was specified
    if args.fixture:
        if args.fixture not in real_fixtures:
            logger.error(
                f"Fixture '{args.fixture}' is not available in real mode or does not exist"
            )
            logger.error(f"Available real-mode fixtures: {', '.join(real_fixtures.keys())}")
            return

        pattern = f"Test_{args.fixture}_Real"

        # If a specific workflow was specified, set it as a global environment variable
        # The test framework will check for this and only run the specified workflow
        if args.workflow:
            if not real_fixtures[args.fixture] or args.workflow not in real_fixtures[args.fixture]:
                logger.error(f"Workflow '{args.workflow}' not found in fixture '{args.fixture}'")
                logger.error(f"Available workflows: {', '.join(real_fixtures[args.fixture])}")
                return

            # Set the environment variable for the test framework to pick up
            os.environ["ARAZZO_TEST_WORKFLOW"] = args.workflow
            logger.info(f"Running only workflow '{args.workflow}' in fixture '{args.fixture}'")
    else:
        # Run all real tests
        pattern = "*_Real"

        # Clear any workflow filter
        if "ARAZZO_TEST_WORKFLOW" in os.environ:
            del os.environ["ARAZZO_TEST_WORKFLOW"]

    # Create test suite with real mode tests
    test_suite = unittest.defaultTestLoader.loadTestsFromName(
        f"tests.oak_runner.test_fixture_discovery.{pattern}"
    )

    # Set environment variable to tell test classes they should run in real mode
    os.environ["ARAZZO_RUN_REAL_TESTS"] = "1"

    try:
        # Run tests
        runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
        runner.run(test_suite)
    finally:
        # Clean up environment variable
        if "ARAZZO_RUN_REAL_TESTS" in os.environ:
            del os.environ["ARAZZO_RUN_REAL_TESTS"]


if __name__ == "__main__":
    main()
