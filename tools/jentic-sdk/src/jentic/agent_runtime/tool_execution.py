"""Tool execution library for Agent Runtime."""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from oak_runner import OAKRunner

from jentic import api
from jentic.api import JenticAPIClient
from jentic.api.api_hub import JenticAPIClient
from jentic.models import WorkflowExecutionDetails


# Define a WorkflowResult class to standardize results
@dataclass
class WorkflowResult:
    """Result of a workflow execution."""

    success: bool
    output: dict[str, Any] | None = None
    error: str | None = None
    step_results: dict[str, Any] | None = None


# Setup logging
logger = logging.getLogger(__name__)


class TaskExecutor:
    """Executor for AI tool calls to Arazzo workflows."""

    def __init__(self, api_hub_client: Optional[JenticAPIClient] = None):
        """Initialize the tool executor.

        Args:
            config: Configuration dictionary for the project.
        """

        # Initialize API Hub client
        self.api_hub_client = api_hub_client or JenticAPIClient()

    async def execute_workflow(self, workflow_uuid: str, inputs: Dict[str, Any]) -> WorkflowResult:
        """Executes a specified workflow using OAK runner.

        Args:
            workflow_uuid: The UUID of the workflow to execute.
            inputs: The input parameters for the workflow execution.

        Returns:
            The result of the workflow execution.
        """
        logger.info(f"Fetching execution files for workflow UUID: {workflow_uuid}")
        try:
            # Call the modified method with a single workflow ID
            exec_details: WorkflowExecutionDetails = (
                await self.api_hub_client.get_execution_details_for_workflow(workflow_uuid)
            )

            if exec_details is None:
                logger.error(
                    f"Execution details could not be retrieved for workflow_uuid: {workflow_uuid}."
                )
                return WorkflowResult(
                    success=False,
                    output=None,
                    error=f"Execution details not found for workflow {workflow_uuid}",
                )

            arazzo_doc = exec_details.arazzo_doc
            source_descriptions = exec_details.source_descriptions
            friendly_workflow_id = exec_details.friendly_workflow_id  # Use the internal ID

            if not arazzo_doc or not friendly_workflow_id:
                logger.error(
                    f"Missing Arazzo document or internal workflow ID for workflow_uuid: {workflow_uuid}."
                )
                return WorkflowResult(
                    success=False,
                    output=None,
                    error=f"Arazzo document or internal workflow ID missing for {workflow_uuid}",
                )

            # 4. Instantiate OAKRunner
            logger.debug(
                f"Instantiating OAKRunner for internal workflow ID: {friendly_workflow_id}"
            )
            runner = OAKRunner(
                arazzo_doc=arazzo_doc,
                source_descriptions=source_descriptions,
            )

            # 5. Execute the workflow using the INTERNAL workflow ID
            logger.debug(
                f"Running workflow {friendly_workflow_id} via OAKRunner with UUID {workflow_uuid}."
            )
            # Removed await as runner.execute_workflow seems synchronous based on TypeError
            execution_output = runner.execute_workflow(
                workflow_id=friendly_workflow_id, inputs=inputs
            )

            # 6. Process result and return WorkflowResult
            if execution_output.get("status") == "completed":
                return WorkflowResult(
                    success=True,
                    output=execution_output.get("outputs"),
                    step_results=execution_output.get("steps"),
                )
            else:
                return WorkflowResult(
                    success=False,
                    error=execution_output.get("error", "Workflow execution failed."),
                    step_results=execution_output.get("steps"),
                )

        except Exception as e:
            logger.exception(f"Error executing workflow {workflow_uuid}: {e}")
            return WorkflowResult(success=False, error=f"An unexpected error occurred: {e}")

    async def execute_operation(
        self,
        operation_uuid: str,
        inputs: Dict[str, Any],
    ) -> dict:
        """
        Executes a specified API operation using OAKRunner after fetching required files from the API.

        Args:
            operation_uuid: The UUID of the operation to execute.
            inputs: Input parameters for the operation.
        Returns:
            A dictionary containing the response status_code, headers, and body.
        """
        logger.info(f"Fetching execution files for operation UUID: {operation_uuid}")
        try:
            # Fetch operation execution files from the API
            exec_files_response = await self.api_hub_client.get_execution_files(
                operation_uuids=[operation_uuid]
            )
            if (
                not exec_files_response.operations
                or operation_uuid not in exec_files_response.operations
            ):
                logger.error(
                    f"Operation ID {operation_uuid} not found in execution files response."
                )
                return {
                    "success": False,
                    "error": f"Operation ID {operation_uuid} not found in execution files response.",
                }
            operation_entry = exec_files_response.operations[operation_uuid]

            # Prepare OpenAPI spec for OAKRunner
            openapi_content = None
            openapi_files = exec_files_response.files.get("open_api", {})
            if operation_entry.files.open_api:
                openapi_file_id = operation_entry.files.open_api[0].id
                if openapi_file_id in openapi_files:
                    openapi_content = openapi_files[openapi_file_id].content
            if not openapi_content:
                logger.error(f"OpenAPI spec not found for operation {operation_uuid}")
                return {
                    "success": False,
                    "error": f"OpenAPI spec not found for operation {operation_uuid}",
                }
            source_descriptions = {"default": openapi_content}

            # Prepare OAKRunner and execute the operation
            runner = OAKRunner(source_descriptions=source_descriptions)
            # Pass operation_uuid, path, and method from the operation_entry
            result = runner.execute_operation(
                inputs=inputs, operation_path=f"{operation_entry.method} {operation_entry.path}"
            )
            logger.debug(f"Operation execution result: {result}")
            # Return body if present, else return the full result
            return result.get("body") if isinstance(result, dict) and "body" in result else result
        except Exception as e:
            logger.exception(f"Error executing operation {operation_uuid}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def _format_workflow_result(self, result: WorkflowResult) -> dict[str, Any]:
        """Format a workflow result for tool output.

        Args:
            result: Workflow execution result.

        Returns:
            Formatted result.
        """
        if not result.success:
            return {
                "success": False,
                "error": result.error or "Unknown error",
            }

        # Format a successful result
        output = {
            "success": True,
            "result": result.output,
        }

        # Add step information if available
        if result.step_results:
            output["steps"] = {}
            for step_id, step_result in result.step_results.items():
                # Handle step_result being a dict (raw step result from runner)
                # instead of a WorkflowResult object
                if isinstance(step_result, dict):
                    step_success = step_result.get("success", False)
                    step_output = step_result.get("outputs", {})
                    step_error = step_result.get("error", "")

                    output["steps"][step_id] = {"success": step_success, "output": step_output}

                    if not step_success and step_error:
                        output["steps"][step_id]["error"] = step_error
                else:
                    # Original code for WorkflowResult objects
                    output["steps"][step_id] = {
                        "success": step_result.success,
                        "output": step_result.output,
                    }
                    if not step_result.success:
                        output["steps"][step_id]["error"] = step_result.error

        return output
