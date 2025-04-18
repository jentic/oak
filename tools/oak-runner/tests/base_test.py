#!/usr/bin/env python3
"""
Base Test Utilities for OAK Runner

This module provides a base test class and utilities for testing Arazzo workflows.
"""

import json
import logging
import os
import tempfile
import unittest
from collections.abc import Callable
from typing import Any, Literal

import yaml

from oak_runner import OAKRunner, StepStatus

from .mocks import MockHTTPExecutor, OpenAPIMocker
from .mocks.real_http_client import RealHTTPExecutor

# Configure logging
logger = logging.getLogger("arazzo-test")


class ArazzoTestCase(unittest.TestCase):
    """
    Base test case for OAK Runner tests

    This class provides methods for loading and executing Arazzo workflows
    with either mock or real API responses.
    """

    def setUp(self, mode: Literal["mock", "real"] = "mock"):
        """
        Set up test fixtures

        Args:
            mode: Test mode - either 'mock' or 'real'
        """
        # Create temporary directory for test files
        self.temp_dir = tempfile.TemporaryDirectory()

        # Store the test mode
        self.mode = mode

        # Initialize appropriate HTTP client based on mode
        if mode == "mock":
            # Initialize mock HTTP client
            self.http_client = MockHTTPExecutor()

            # Initialize OpenAPI mocker
            self.openapi_mocker = OpenAPIMocker(self.http_client)
        else:  # real mode
            # Initialize real HTTP client
            self.http_client = RealHTTPExecutor()

            # No OpenAPI mocker for real mode
            self.openapi_mocker = None

        # List to keep track of created files for cleanup
        self.created_files = []

    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up temporary directory
        self.temp_dir.cleanup()

    def create_openapi_spec(self, spec_content: dict[str, Any], name: str = "test_api") -> str:
        """
        Create an OpenAPI spec file with the given content

        Args:
            spec_content: OpenAPI specification dictionary
            name: Name of the spec file (without extension)

        Returns:
            Path to the created OpenAPI spec file
        """
        file_path = os.path.join(self.temp_dir.name, f"{name}.yaml")

        with open(file_path, "w") as f:
            yaml.dump(spec_content, f)

        self.created_files.append(file_path)
        return file_path

    def create_arazzo_spec(
        self, spec_content: dict[str, Any], name: str = "test_workflow"
    ) -> dict[str, Any]:
        """
        Create an Arazzo workflow spec with the given content

        Args:
            spec_content: Arazzo workflow specification dictionary
            name: Name for reference (not used for file creation)

        Returns:
            The Arazzo spec content
        """
        # Return the spec content directly
        return spec_content

    def load_test_openapi_spec(self, file_path: str, name: str | None = None) -> str:
        """
        Load an OpenAPI spec for testing

        Args:
            file_path: Path to the OpenAPI spec file
            name: Optional name for the spec, defaults to filename without extension

        Returns:
            Name of the loaded spec
        """
        if self.mode == "mock" and self.openapi_mocker:
            return self.openapi_mocker.load_spec(file_path, name)

        # In real mode, we don't load the spec into a mocker
        # Just return the name for reference
        if not name:
            name = os.path.splitext(os.path.basename(file_path))[0]

        logger.info(f"Real mode: OpenAPI spec '{name}' from {file_path} (not loaded into mocker)")
        return name

    def mock_all_api_operations(
        self, spec_name: str, base_url: str | None = None, success_rate: float = 1.0
    ) -> None:
        """
        Configure mock responses for all operations in a spec

        Args:
            spec_name: Name of the previously loaded spec
            base_url: Base URL to use for the API
            success_rate: Probability of returning a success response (vs. error)
        """
        if self.mode == "mock" and self.openapi_mocker:
            self.openapi_mocker.mock_all_operations(
                spec_name=spec_name, base_url=base_url, success_rate=success_rate
            )
        else:
            # In real mode, we store the base URL for the client to use
            if isinstance(self.http_client, RealHTTPExecutor) and base_url:
                self.http_client.base_urls[spec_name] = base_url
                logger.info(f"Real mode: Setting base URL for {spec_name} to {base_url}")

    def mock_api_operation(
        self,
        spec_name: str,
        path: str,
        method: str,
        base_url: str | None = None,
        operation_id: str | None = None,
        success_rate: float = 1.0,
        custom_response_generator: Callable | None = None,
    ) -> None:
        """
        Configure a mock response for a specific operation

        Args:
            spec_name: Name of the previously loaded spec
            path: API path (e.g., "/pets")
            method: HTTP method (e.g., "get", "post")
            base_url: Base URL to use
            operation_id: If provided, matches the operationId instead of path/method
            success_rate: Probability of returning a success response (vs. error)
            custom_response_generator: Optional function to generate a custom response

        Notes:
            In real mode, this only sets the base URL if provided.
        """
        if self.mode == "mock" and self.openapi_mocker:
            self.openapi_mocker.mock_operation(
                spec_name=spec_name,
                path=path,
                method=method,
                base_url=base_url,
                operation_id=operation_id,
                success_rate=success_rate,
                custom_response_generator=custom_response_generator,
            )
        else:
            # In real mode, we store the base URL for the client to use
            if isinstance(self.http_client, RealHTTPExecutor) and base_url:
                self.http_client.base_urls[spec_name] = base_url
                logger.info(
                    f"Real mode: Setting base URL for operation {method} {path} to {base_url}"
                )

    def create_oak_runner(
        self, arazzo_doc: dict[str, Any], source_descriptions: dict[str, Any]
    ) -> OAKRunner:
        """
        Create an OAK Runner instance for a specific workflow

        Args:
            arazzo_doc: Parsed Arazzo document
            source_descriptions: Dictionary of Open API Specs

        Returns:
            Configured OAKRunner instance
        """
        print("SOOURCEDESC", source_descriptions)
        return OAKRunner(arazzo_doc, source_descriptions, http_client=self.http_client)

    def execute_workflow(
        self,
        runner: OAKRunner,
        workflow_id: str,
        inputs: dict[str, Any],
        expect_success: bool = True,
        max_steps: int = 100,
    ) -> dict[str, Any]:
        """
        Execute a workflow from start to finish

        Args:
            runner: OAKRunner instance
            workflow_id: ID of the workflow to execute
            inputs: Input parameters for the workflow
            expect_success: Whether to expect successful completion
            max_steps: Maximum number of steps to execute (to prevent infinite loops)

        Returns:
            Dictionary with workflow outputs or error information
        """
        # Start the workflow
        execution_id = runner.start_workflow(workflow_id, inputs)

        # Keep track of executed steps
        executed_steps = []
        final_result = None

        logger.debug(f"Starting workflow execution: {workflow_id}")

        # Execute steps until completion or error
        step_count = 0
        while step_count < max_steps:
            step_count += 1
            result = runner.execute_next_step(execution_id)

            logger.debug(f"Step execution result: {result}")

            # Record step execution
            if result["status"] == "step_complete":
                step_success = result.get("success", False)
                executed_steps.append({"step_id": result["step_id"], "success": step_success})
                logger.debug(f"Completed step: {result['step_id']}, success: {step_success}")

            # Check for workflow completion
            if result["status"] == "workflow_complete":
                final_result = result
                logger.debug(f"Workflow complete. Final result: {result}")
                break

            # Check for error
            if result["status"] == "step_error":
                logger.debug(f"Step error: {result.get('error')}")
                if expect_success:
                    self.fail(f"Workflow execution failed: {result.get('error')}")

                return {
                    "status": "error",
                    "error": result.get("error", "A step failed"),
                    "executed_steps": executed_steps,
                }

            # Check for too many steps (potential infinite loop)
            if step_count >= max_steps:
                self.fail(f"Workflow execution exceeded maximum number of steps ({max_steps})")

        # We should have a final result now
        if not final_result:
            self.fail("Workflow execution ended without a final result")

        # Get the execution state to check step statuses
        state = runner.execution_states[execution_id]

        logger.debug(f"Execution state: {state.step_outputs}")
        logger.debug(f"Workflow outputs: {state.workflow_outputs}")

        # Determine if any steps failed
        step_statuses = list(state.status.values())
        any_step_failed = any(status == StepStatus.FAILURE for status in step_statuses)

        # Validate expectations
        if expect_success and any_step_failed:
            self.fail(f"Expected all steps to succeed but some failed: {state.status}")
        elif not expect_success and not any_step_failed:
            self.fail("Expected workflow to fail but all steps succeeded")

        # Use the workflow outputs from execution state directly
        # This avoids hardcoding specific output paths for different workflows
        workflow_outputs = state.workflow_outputs.copy()

        # If workflow outputs are empty but we have step outputs, let's include them
        # in a generic way that works for any workflow
        if not workflow_outputs and state.step_outputs:
            logger.debug("No workflow outputs found in state, using step outputs")
            # Flatten step outputs in a structured way
            for step_id, outputs in state.step_outputs.items():
                if isinstance(outputs, dict):
                    for key, value in outputs.items():
                        workflow_outputs[f"{step_id}.{key}"] = value

        return {
            "status": "success" if not any_step_failed else "error",
            "outputs": workflow_outputs,  # Use our manually constructed workflow outputs
            "executed_steps": executed_steps,
            "step_statuses": {k: str(v) for k, v in state.status.items()},
        }

    def _load_arazzo_spec(self, spec_path: str) -> dict[str, Any]:
        """
        Load an Arazzo spec file

        Args:
            spec_path: Path to the Arazzo spec file

        Returns:
            Arazzo spec as a dictionary
        """
        with open(spec_path) as f:
            if spec_path.endswith(".json"):
                return json.load(f)
            else:
                return yaml.safe_load(f)

    def validate_api_calls(self, expected_call_count: int | None = None) -> None:
        """
        Validate that the expected API calls were made

        Args:
            expected_call_count: Optional count of expected API calls
        """
        if expected_call_count is not None:
            self.assertEqual(
                self.http_client.get_request_count(),
                expected_call_count,
                f"Expected {expected_call_count} API calls, but got {self.http_client.get_request_count()}",
            )

    def get_api_calls(self) -> list[dict[str, Any]]:
        """Get all API calls that were made during the test"""
        return self.http_client.requests

    def print_api_call_summary(self) -> None:
        """Print a summary of all API calls made during the test"""
        print("\nAPI Call Summary:")
        print("-----------------")

        for i, request in enumerate(self.http_client.requests, 1):
            print(f"{i}. {request['method'].upper()} {request['url']}")

            # Show query params if present
            if "params" in request["kwargs"] and request["kwargs"]["params"]:
                print(f"   Query params: {request['kwargs']['params']}")

            # Show headers if present (excluding common ones)
            if "headers" in request["kwargs"] and request["kwargs"]["headers"]:
                headers = {
                    k: v
                    for k, v in request["kwargs"]["headers"].items()
                    if k.lower() not in ["user-agent", "accept", "connection"]
                }
                if headers:
                    print(f"   Headers: {headers}")

            # Show body if present
            if "json" in request["kwargs"] and request["kwargs"]["json"]:
                print(f"   Body: {json.dumps(request['kwargs']['json'], indent=2)[:200]}...")
            elif "data" in request["kwargs"] and request["kwargs"]["data"]:
                data = request["kwargs"]["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                print(f"   Data: {data[:200]}...")

        print("-----------------")
