#!/usr/bin/env python3
"""
Step Executor for OAK Runner

This module provides the main StepExecutor class that orchestrates the execution of workflow steps.
"""

import logging
import re
from typing import Any, Optional
from oak_runner.models import ExecutionState, RuntimeParams
from ..evaluator import ExpressionEvaluator
from ..http import HTTPExecutor
from .action_handler import ActionHandler
from .operation_finder import OperationFinder
from .output_extractor import OutputExtractor
from .parameter_processor import ParameterProcessor
from .success_criteria import SuccessCriteriaChecker
from .server_processor import ServerProcessor

# Configure logging
logger = logging.getLogger("arazzo-runner.executor")


class StepExecutor:
    """Executes workflow steps in Arazzo workflows"""

    def __init__(
        self,
        http_client: HTTPExecutor,
        source_descriptions: dict[str, Any],
        testing_mode: bool = False,
    ):
        """
        Initialize the step executor

        Args:
            http_client: HTTP client for executing API requests
            source_descriptions: OpenAPI source descriptions
            testing_mode: If True, enable test-specific behaviors like fallback outputs
        """
        self.http_client = http_client
        self.source_descriptions = source_descriptions
        self.testing_mode = testing_mode

        # Initialize components
        self.operation_finder = OperationFinder(source_descriptions)
        self.parameter_processor = ParameterProcessor(source_descriptions)
        self.output_extractor = OutputExtractor(source_descriptions)
        self.success_checker = SuccessCriteriaChecker(source_descriptions)
        self.action_handler = ActionHandler(source_descriptions)
        self.server_processor = ServerProcessor(source_descriptions)


    def execute_step(self, step: dict, state: ExecutionState) -> dict:
        """
        Execute a single workflow step

        Args:
            step: Step definition from the Arazzo document
            state: Current execution state

        Returns:
            result: Step execution result
        """
        step_id = step.get("stepId")

        # Determine what to execute: operation or workflow
        if "operationId" in step:
            return self._execute_operation_by_id(step, state)
        elif "operationPath" in step:
            return self._execute_operation_by_path(step, state)
        elif "workflowId" in step:
            # Nested workflows do not directly use HTTPExecutor with server configs at this level
            return self._execute_nested_workflow(step, state)
        else:
            raise ValueError(f"Step {step_id} does not specify an operation or workflow to execute")

    def _execute_operation_by_id(self, step: dict, state: ExecutionState) -> dict:
        """Execute an operation by its operationId"""
        operation_id = step.get("operationId")
        if not operation_id:
            raise ValueError("Missing operationId in step definition")

        # Find the operation in the source descriptions
        operation_info = self.operation_finder.find_by_id(operation_id)
        if not operation_info:
            raise ValueError(f"Operation {operation_id} not found in source descriptions")

        # Prepare parameters
        parameters = self.parameter_processor.prepare_parameters(step, state)

        # Prepare request body if present
        request_body = None
        if "requestBody" in step:
            request_body = self.parameter_processor.prepare_request_body(
                step.get("requestBody"), state
            )

        # Extract security requirements
        security_options = self.operation_finder.extract_security_requirements(operation_info)
        source_name = operation_info.get("source", "default")

        # Resolve final URL
        base_server_url = operation_info.get("url") # This is the relative path template
        final_url_template = self.server_processor.resolve_server_params(
            source_name=source_name,
            operation_url_template=base_server_url, # Pass it as operation_url_template
            server_runtime_params=state.runtime_params.servers if state.runtime_params else None
        )

        if not final_url_template:
            error_msg = f"Could not determine final URL for operationId '{operation_id}'"
            logger.error(error_msg)
            return {"success": False, "response": {"error": error_msg, "status_code": 0}, "outputs": {}}

        # Execute the HTTP request
        response = self.http_client.execute_request(
            method=operation_info.get("method"),
            url=final_url_template,
            parameters=parameters, 
            request_body=request_body,
            security_options=security_options,
            source_name=source_name,
        )

        # Check success criteria
        success = self.success_checker.check_success_criteria(step, response, state)

        # Extract outputs
        outputs = self.output_extractor.extract_outputs(step, response, state)

        return {"success": success, "response": response, "outputs": outputs}

    def _execute_operation_by_path(self, step: dict, state: ExecutionState) -> dict:
        """Execute an operation by its operationPath"""
        operation_path = step.get("operationPath") # This is the method:path string e.g. GET:/pets
        step_id = step.get("stepId", "unknown")

        logger.debug(f"Processing operationPath value: {operation_path} for step {step_id}")

        # Evaluate the operation path if it contains expressions
        if operation_path.startswith("{") and operation_path.endswith("}"):
            operation_path = ExpressionEvaluator.evaluate_expression(
                operation_path[1:-1], state, self.source_descriptions
            )
            logger.debug(f"Evaluated operationPath expression to: {operation_path}")

        # Parse the operation path to find the source and JSON pointer
        match = re.match(r"([^#]+)#(.+)", operation_path)
        if not match:
            error_msg = f"Invalid operation path: {operation_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        source_url, json_pointer = match.groups() # Use source_name_from_path for clarity
        logger.debug(f"Parsed operationPath - source: {source_url}, pointer: {json_pointer}")

        # Print the raw JSON pointer for debugging
        logger.debug(f"Raw JSON pointer in operationPath: {json_pointer}")

        # Try to decode it manually to see what's happening
        decoded = json_pointer.replace("~1", "/").replace("~0", "~")
        logger.debug(f"Manually decoded pointer: {decoded}")

        # Find the operation in the source descriptions
        operation_info = self.operation_finder.find_by_path(source_url, json_pointer)

        source_name = operation_info.get("source")

        if not operation_info:
            # Enhanced logging moved from original code to here for when operation_info is None
            logger.error(f"Failed to find operation for path: {operation_path}")
            for name, desc in self.source_descriptions.items():
                paths = desc.get("paths", {})
                logger.debug(f"Source '{name}' has {len(paths)} paths: {list(paths.keys())}")
                for path_key, methods in paths.items():
                    for method_key, op_details in methods.items():
                        if method_key.lower() in ["get", "post", "put", "delete", "patch"]:
                            op_id_log = op_details.get("operationId", "[No operationId]")
                            logger.debug(f"  - {method_key.upper()} {path_key} (operationId: {op_id_log})")
            raise ValueError(f"Operation not found at path {operation_path}")
        
        logger.debug(
            f"Found operation: {operation_info.get('method')} {operation_info.get('url')}"
        )

        # Prepare parameters
        parameters = self.parameter_processor.prepare_parameters(step, state)

        # Prepare request body if present
        request_body = None
        if "requestBody" in step:
            request_body = self.parameter_processor.prepare_request_body(
                step.get("requestBody"), state
            )
        
        # Extract security requirements
        security_options = self.operation_finder.extract_security_requirements(operation_info)

        # Resolve final URL
        relative_operation_path_template = operation_info.get("url") 
        final_url_template = self.server_processor.resolve_server_params(
            source_name=source_name,
            operation_url_template=relative_operation_path_template, # Pass it as operation_url_template
            server_runtime_params=state.runtime_params.servers if state.runtime_params else None
        )

        if not final_url_template:
            error_msg = f"Could not determine final URL for operationPath '{operation_path}'"
            logger.error(error_msg)
            return {"success": False, "response": {"error": error_msg, "status_code": 0}, "outputs": {}}

        # Execute the HTTP request
        response = self.http_client.execute_request(
            method=operation_info.get("method"),
            url=final_url_template,
            parameters=parameters, 
            request_body=request_body,
            security_options=security_options,
            source_name=source_name,
        )

        # Check success criteria
        success = self.success_checker.check_success_criteria(step, response, state)
        
        # Extract outputs
        outputs = self.output_extractor.extract_outputs(step, response, state)

        return {"success": success, "response": response, "outputs": outputs}

    def _execute_nested_workflow(self, step: dict, state: ExecutionState) -> dict:
        """
        Execute a nested workflow

        This is a placeholder - the actual implementation will be in the runner
        since it needs access to the runner instance to start and execute the
        nested workflow.
        """
        raise NotImplementedError("Nested workflow execution is handled by the runner")

    def determine_next_action(self, step: dict, success: bool, state: ExecutionState) -> dict:
        """
        Determine the next action based on step success/failure

        Returns:
            action: Dictionary with action type and parameters
        """
        return self.action_handler.determine_next_action(step, success, state)

    def execute_operation(
        self,
        inputs: dict[str, Any],
        operation_id: Optional[str] = None,
        operation_path: Optional[str] = None,
        runtime_params: Optional[RuntimeParams] = None,
    ) -> dict:
        """
        Execute a single API operation directly, outside of a workflow context.

        Args:
            inputs: Input parameters for the operation.
            operation_id: The operationId of the operation to execute.
            operation_path: The path and method (e.g., 'GET /users/{userId}') of the operation.
                          Provide either operation_id or operation_path, not both.
            runtime_params: Runtime parameters for execution (e.g., server variables).

        Returns:
            A dictionary containing the response status_code, headers, and body.
            Example: {'status_code': 200, 'headers': {...}, 'body': ...}

        Raises:
            ValueError: If neither or both operation_id and operation_path are provided,
                        or if the operation cannot be found, or if operation_path is invalid.
            requests.exceptions.HTTPError: If the API call results in an HTTP error status (4xx or 5xx).
        """
        # Validate inputs
        if not operation_id and not operation_path:
            raise ValueError("Either operation_id or operation_path must be provided.")
        if operation_id and operation_path:
            raise ValueError("Provide either operation_id or operation_path, not both.")

        log_identifier = f"ID='{operation_id}'" if operation_id else f"Path='{operation_path}'"
        logger.debug(f"Attempting to execute operation directly: {log_identifier}")

        # Find the operation definition
        try:
            if operation_id:
                operation_details = self.operation_finder.find_by_id(operation_id)
            else:  # operation_path must be set
                try:
                    # Restore splitting logic
                    method, path = operation_path.split(" ", 1)
                    path = path.strip()
                    method = method.strip().upper()
                    if not path or not method:
                        raise ValueError("Path and method cannot be empty after splitting.")
                    operation_details = self.operation_finder.find_by_http_path_and_method(http_path=path, http_method=method)
                except ValueError as e:
                    logger.error(f"Invalid operation_path format: '{operation_path}'. Expected 'METHOD /path'. Error: {e}")
                    raise ValueError(f"Invalid operation_path format: '{operation_path}'. Expected 'METHOD /path'.") from e

        except Exception as e:
            logger.error(f"Operation not found ({log_identifier}): {e}")
            raise ValueError(f"Operation not found: {e}") from e

        # Check if operation was found
        if not operation_details:
            log_identifier = f"ID='{operation_id}'" if operation_id else f"Path='{operation_path}'"
            logger.error(f"Operation not found: {log_identifier}")
            # Use a specific exception or re-raise appropriately
            raise ValueError(f"Operation not found: {log_identifier}")

        log_identifier = operation_details.get("operationId", f"{operation_details.get('method')} {operation_details.get('path')}")

        # Prepare Parameters and Request Body
        try:
            prepared_params = self.parameter_processor.prepare_operation_parameters(
                operation_details=operation_details,
                inputs=inputs
            )
            logger.debug(f"Prepared parameters for direct execution: {prepared_params}")
        except ValueError as e:
            logger.error(f"Error preparing parameters for {log_identifier}: {e}")
            # Reraise as ValueError, potentially add more context if needed
            raise ValueError(f"Error preparing parameters: {e}") from e

        # Handle Authentication
        security_options = self.operation_finder.extract_security_requirements(operation_details)
        logger.debug(f"Resolved security options for {log_identifier}: {security_options}")

        # Resolve final URL
        source_name = operation_details.get("source", "default") # Get source_name
        base_server_url = operation_details.get("url") # This is the relative path template

        final_url_template = self.server_processor.resolve_server_params(
            source_name=source_name,
            operation_url_template=base_server_url, # Pass it as operation_url_template
            server_runtime_params=runtime_params.servers if runtime_params else None
        )

        if not final_url_template:
            error_msg = f"Could not determine final URL for operation {log_identifier}. Operation path was '{base_server_url}' and source was '{source_name}'."
            logger.error(error_msg)
            return {"success": False, "response": {"error": error_msg, "status_code": 0}, "outputs": {}}

        # Execute Request
        method = operation_details.get("method")
        url = final_url_template # Base URL, path params handled by http_client
        request_body_payload = prepared_params.get('body') # Extract body from prepared params
        logger.debug(f"Request body payload: {request_body_payload}")

        if not method or not url:
            logger.error(f"Missing method or url in operation details for {log_identifier}")
            raise ValueError("Operation details are incomplete (missing method or url).")

        try:
            logger.debug(f"Executing direct API call: {method} {url}")
            response_data = self.http_client.execute_request(
                method=method,
                url=url,
                parameters=prepared_params, # Pass the whole structure
                request_body=request_body_payload,
                security_options=security_options
            )
            logger.debug(f"Direct operation execution completed ({log_identifier}) - Status: {response_data.get('status_code')}")
            return response_data
        except Exception as e:
            # Catch potential exceptions during HTTP execution (e.g., network errors, auth failures handled by HTTPExecutor)
            logger.error(f"Error during direct execution of {log_identifier}: {e}", exc_info=True)
            # Re-raise or handle appropriately - for now, re-raise
            # Consider wrapping in a custom exception if needed
            raise e
