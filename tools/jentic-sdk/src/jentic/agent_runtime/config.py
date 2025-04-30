"""Jentic project management module."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from oak_runner.auth.auth_processor import AuthProcessor
from oak_runner.auth.models import SecurityOption
from oak_runner.extractor.openapi_extractor import extract_operation_io

from jentic.api.api_hub import JenticAPIClient
from jentic.models import GetFilesResponse

logger = logging.getLogger(__name__)


def load_json_file(filepath: str | Path) -> dict[str, Any]:
    """Load a JSON file.

    Args:
        filepath: Path to the JSON file

    Returns:
        The contents of the JSON file
    """
    with open(filepath) as f:
        return json.load(f)


class JenticConfig:
    """A class that loads and manages a Jentic project."""

    def __init__(self, config_path: str = "./jentic.json") -> None:
        """Initialize the Jentic project.

        Args:
            config_path: Path to the Jentic config file
        """
        self.config_path = Path(config_path)
        logger.debug(f"Initializing JenticConfig at {self.config_path}")

        # Load project configuration
        self.config: dict[str, Any] = self._load_project_config(self.config_path)
        logger.debug(f"Loaded project configuration with {len(self.config)} entries")

        self._workflows: dict[str, dict[str, Any]] = {}
        self._operations: dict[str, Any] = {}
        self._extract_workflows()
        self._extract_operations()
        logger.debug(f"Extracted {len(self._workflows)} workflows from API specifications")
        logger.debug(f"Extracted {len(self._operations)} operations from config")

    def _load_project_config(self, config_path: str | Path) -> dict[str, Any]:
        """Load project configuration from jentic.json.

        Returns:
            Project configuration
        """
        if not config_path.exists():
            logger.warning(f"Project configuration file not found: {config_path}")
            return {}

        try:
            return load_json_file(config_path)
        except Exception as e:
            logger.error(f"Error loading project configuration: {e}")
            return {}

    def get_workflows(self) -> dict[str, dict[str, Any]]:
        """Get the workflows defined in the project.

        Returns:
            Dictionary of workflows
        """
        return self._workflows

    def _extract_workflows(self) -> None:
        """Extract workflows from the project configuration.

        This method extracts all workflows from a top-level 'workflows' key only (new style).
        """
        self._workflows = {}
        top_level_workflows = self.config.get("workflows", {})
        for workflow_id, workflow in top_level_workflows.items():
            self._workflows[workflow_id] = workflow

    def _extract_operations(self) -> None:
        """Extract top-level operations from the project configuration."""
        # Operations are any top-level key not named 'workflows'
        if self.config.get("operations"):
            self._operations = self.config["operations"]

    def get_operations(self) -> dict[str, Any]:
        """Return the extracted operations."""
        return self._operations

    @staticmethod
    def _extract_workflow_details(arazzo_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """
        Extract workflow details from an Arazzo document.

        Args:
            arazzo_doc: The Arazzo document containing workflow definitions

        Returns:
            Dictionary mapping workflow IDs to their details (inputs, outputs, description)
        """
        workflow_details = {}

        if not arazzo_doc or "workflows" not in arazzo_doc:
            return workflow_details

        for workflow in arazzo_doc.get("workflows", []):
            workflow_id = workflow.get("workflowId")

            if not workflow_id:
                continue

            # Extract the relevant details
            workflow_details[workflow_id] = {
                "description": workflow.get("description", ""),
                "summary": workflow.get("summary", ""),
                "inputs": workflow.get("inputs", {}),
                "outputs": workflow.get("outputs", {}),
            }

        return workflow_details

    @staticmethod
    def _flatten_security_requirements(security_requirements: dict) -> dict:
        """
        Converts the security_requirements dict from {source: [SecurityOption, ...]} to
        {source: [flattened dict, ...]} where each flattened dict is a SecurityRequirement as a dict
        (model_dump), with no extra 'requirements' nesting.
        """
        flattened = {}
        for k, v in security_requirements.items():
            # v is a list of SecurityOption objects (or similar)
            # Each SecurityOption has a 'requirements' field, which is a list of SecurityRequirement objects
            # We want: {k: [req.model_dump() for s in v for req in s.requirements]}
            flattened[k] = [
                req.model_dump() if hasattr(req, "model_dump") else dict(req)
                for s in v
                for req in getattr(s, "requirements", [])
            ]
        return flattened

    @staticmethod
    async def generate_config_from_uuids(
        api_hub_client: JenticAPIClient,
        workflow_uuids: Optional[List[str]],
        operation_uuids: Optional[List[str]],
    ) -> Dict[str, Any]:
        """
        Generate a runtime configuration object from a list of workflow UUIDs and/or operation UUIDs.
        """
        if not (workflow_uuids or operation_uuids):
            raise ValueError("No workflow or operation UUIDs provided.")

        logger.info(
            f"Generating config for workflow UUIDs: {workflow_uuids} and operation UUIDs: {operation_uuids}"
        )

        # Step 1: Fetch execution files for both workflows and operations
        exec_files_response = await JenticConfig._fetch_execution_files(
            api_hub_client, workflow_uuids, operation_uuids
        )

        # Step 2: Collect OpenAPI specs
        all_openapi_specs = JenticConfig._collect_openapi_specs(exec_files_response)

        # Step 3: Extract workflow details
        all_arazzo_specs, extracted_workflow_details = JenticConfig._extract_all_workflow_details(
            exec_files_response, workflow_uuids
        )

        # Step 4: Extract operation details if present
        extracted_operation_details = {}
        if operation_uuids:
            extracted_operation_details = JenticConfig._extract_all_operation_details(
                exec_files_response, operation_uuids
            )

        # Step 5: Process authentication requirements
        env_mappings = JenticConfig._process_auth(all_openapi_specs, all_arazzo_specs)

        # Step 6: Compose final config
        final_config = {
            "version": "1.0",
            "workflows": extracted_workflow_details,
            "operations": extracted_operation_details,
            "environment_variable_mappings": env_mappings,
        }
        logger.info("Successfully generated runtime configuration.")
        return final_config

    @staticmethod
    async def _fetch_execution_files(
        api_hub_client: JenticAPIClient,
        workflow_uuids: List[str],
        operation_uuids: List[str] = None,
    ):
        try:
            return await api_hub_client.get_execution_files(
                workflow_ids=workflow_uuids, operation_uuids=operation_uuids or []
            )
        except Exception as e:
            logger.error(f"Failed to fetch execution files: {e}")
            raise ValueError(f"Failed to fetch execution files: {e}") from e

    @staticmethod
    def _collect_openapi_specs(exec_files_response) -> Dict[str, dict]:
        all_openapi_specs = {}
        for openapi_file_id, openapi_file_entry in exec_files_response.files.get(
            "open_api", {}
        ).items():
            openapi_content = openapi_file_entry.content
            title = None
            if isinstance(openapi_content, dict):
                title = openapi_content.get("info", {}).get("title")
            key = title if title else openapi_file_entry.filename
            all_openapi_specs[key] = openapi_content
        return all_openapi_specs

    @staticmethod
    def _extract_all_workflow_details(
        exec_files_response: "GetFilesResponse", workflow_uuids: list[str]
    ) -> tuple[list[dict], dict[str, dict]]:
        all_arazzo_specs: list[dict] = []
        extracted_workflow_details: dict[str, dict] = {}

        for workflow_id in workflow_uuids:
            if workflow_id not in exec_files_response.workflows:
                logger.error(f"Workflow ID {workflow_id} not found in execution files response.")
                raise ValueError(
                    f"Workflow ID {workflow_id} not found in execution files response."
                )
            workflow_entry = exec_files_response.workflows[workflow_id]

            # Extract Arazzo doc
            if not workflow_entry.files.arazzo:
                logger.error(f"Missing Arazzo document for workflow_id: {workflow_id}")
                raise ValueError(f"Missing Arazzo document for workflow_id: {workflow_id}")
            arazzo_file_id = workflow_entry.files.arazzo[0].id
            arazzo_files_dict = exec_files_response.files.get("arazzo", {})
            if arazzo_file_id not in arazzo_files_dict:
                logger.error(
                    f"Arazzo file content not found for ID {arazzo_file_id} in workflow {workflow_id}."
                )
                raise ValueError(
                    f"Arazzo file content not found for ID {arazzo_file_id} in workflow {workflow_id}."
                )
            arazzo_doc = arazzo_files_dict[arazzo_file_id].content
            all_arazzo_specs.append(arazzo_doc)

            # Build source_descriptions relevant to this workflow/arazzo doc
            source_descriptions: dict[str, dict] = {}
            for openapi_ref in workflow_entry.files.open_api:
                file_id = openapi_ref.id
                openapi_files_dict = exec_files_response.files.get("open_api", {})
                if file_id in openapi_files_dict:
                    openapi_file = openapi_files_dict[file_id]
                    source_descriptions[openapi_file.filename] = openapi_file.content

            # Extract all workflows defined within this specific Arazzo document
            workflows_in_doc = JenticConfig._extract_workflow_details(arazzo_doc)
            if workflow_entry.workflow_id and workflow_entry.workflow_id in workflows_in_doc:
                workflow_details = workflows_in_doc[workflow_entry.workflow_id]
                workflow_details["workflow_uuid"] = workflow_id
                workflow_details["security_requirements"] = (
                    JenticConfig._flatten_security_requirements(
                        AuthProcessor.get_security_requirements_for_workflow(
                            workflow_id=workflow_entry.workflow_id,
                            arazzo_spec=arazzo_doc,
                            source_descriptions=source_descriptions,
                        )
                    )
                )
                extracted_workflow_details[workflow_entry.workflow_id] = workflow_details
            else:
                logger.error(
                    f"Requested workflow UUID {workflow_id} with friendly_id '{workflow_entry.workflow_id}' "
                    f"not found within its own Arazzo document's extracted details."
                )
        return all_arazzo_specs, extracted_workflow_details

    @staticmethod
    def _extract_all_operation_details(
        exec_files_response: "GetFilesResponse", operation_uuids: list[str]
    ) -> dict[str, dict]:
        extracted_operation_details: dict[str, dict] = {}
        if not hasattr(exec_files_response, "operations") or not exec_files_response.operations:
            return extracted_operation_details
        for operation_uuid in operation_uuids:
            if operation_uuid not in exec_files_response.operations:
                logger.error(
                    f"Operation ID {operation_uuid} not found in execution files response."
                )
                continue
            operation_entry = exec_files_response.operations[operation_uuid]
            # Find the first OpenAPI file associated with this operation
            openapi_spec = None
            if operation_entry.files.open_api:
                openapi_file_id = operation_entry.files.open_api[0].id
                openapi_file_entry = exec_files_response.files.get("open_api", {}).get(
                    openapi_file_id
                )
                if openapi_file_entry:
                    openapi_spec = openapi_file_entry.content
            # Extract inputs and outputs using extract_operation_io
            io_details = None
            if (
                openapi_spec
                and getattr(operation_entry, "path", None)
                and getattr(operation_entry, "method", None)
            ):
                try:
                    io_details = extract_operation_io(
                        openapi_spec,
                        operation_entry.path,
                        operation_entry.method.lower(),
                        input_max_depth=4,
                        output_max_depth=2
                    )
                except Exception as e:
                    logger.error(f"Failed to extract operation IO for {operation_uuid}: {e}")
            extracted_operation_details[operation_uuid] = {
                "operation_uuid": operation_uuid,
                "method": getattr(operation_entry, "method", None),
                "path": getattr(operation_entry, "path", None),
                "summary": getattr(operation_entry, "summary", None),
                "inputs": io_details["inputs"] if io_details and "inputs" in io_details else None,
                "outputs": (
                    io_details["outputs"] if io_details and "outputs" in io_details else None
                ),
            }
        return extracted_operation_details

    @staticmethod
    def _process_auth(all_openapi_specs, all_arazzo_specs):
        logger.debug(
            f"Processing auth for {len(all_openapi_specs)} unique OpenAPI specs and {len(all_arazzo_specs)} Arazzo docs."
        )
        auth_processor = AuthProcessor()
        try:
            auth_data = auth_processor.process_api_auth(
                openapi_specs=all_openapi_specs, arazzo_specs=all_arazzo_specs
            )
            logger.info("Auth processing completed.")
        except Exception as e:
            logger.error(f"Auth processing failed: {e}")
            raise ValueError("Auth processing failed during config generation") from e
        if auth_data.get("auth_workflows"):
            del auth_data["auth_workflows"]
        return auth_data.get("env_mappings", {})
