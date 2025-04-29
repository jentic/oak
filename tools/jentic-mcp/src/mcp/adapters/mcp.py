"""MCP adapter for the Jentic MCP Plugin."""

import logging
from typing import Any

from jentic import Jentic
from jentic.models import ApiCapabilitySearchRequest, APISearchResults

from mcp.core.generators.code_generator import generate_code_sample


class MCPAdapter:
    """Model Configuration Protocol adapter for the Jentic MCP Plugin."""

    def __init__(self):
        """Initialize the MCP adapter."""
        self.jentic = Jentic()

    async def search_api_capabilities(self, request: dict[str, Any]) -> dict[str, Any]:
        """MCP endpoint for searching API capabilities.

        Args:
            request: MCP tool request parameters.

        Returns:
            MCP tool response.
        """
        request = ApiCapabilitySearchRequest(
            capability_description=request["capability_description"],
            keywords=request.get("keywords"),
            max_results=request.get("max_results", 5),
        )

        results: APISearchResults = await self.jentic.search_api_capabilities(request=request)

        return {
            "result": {
                "matches": results.model_dump(),
                "query": request.capability_description,
                "total_matches": len(results.workflows) + len(results.operations),
            }
        }

    async def generate_runtime_config(self, request: dict[str, Any]) -> dict[str, Any]:
        """MCP endpoint for generating a configuration file from a selection set.

        Args:
            request: MCP tool request parameters.

        Returns:
            MCP tool response.
        """
        workflow_uuids = request.get("workflow_uuids")
        operation_uuids = request.get("operation_uuids")

        # Log the project directory for debugging
        logger = logging.getLogger(__name__)
        logger.info(
            f"Generating config with workflow_uuids: {workflow_uuids}, operation_uuids: {operation_uuids}"
        )

        try:
            # Generate configuration from the selection set
            result = await self.jentic.get_execution_configuration(
                workflow_uuids=workflow_uuids, operation_uuids=operation_uuids
            )

            return {"result": result}

        except ValueError as e:
            logger.error(f"Error generating config: {str(e)}")
            return {
                "result": {
                    "success": False,
                    "operation_uuids": operation_uuids,
                    "workflow_uuids": workflow_uuids,
                    "message": str(e),
                    "config": {},
                }
            }

    async def generate_code_sample(self, request: dict[str, Any]) -> dict[str, Any]:
        """MCP endpoint for generating code samples.

        Args:
            request: MCP tool request parameters.

        Returns:
            MCP tool response with generated code sample.
        """
        format_name = request.get("format")
        language = request.get("language")

        logger = logging.getLogger(__name__)
        logger.debug(f"Generating code sample for format: {format_name}, language: {language}")

        try:
            # Generate the code sample
            code = generate_code_sample(format=format_name, language=language)

            return {"result": {"success": True, "code": code}}
        except Exception as e:
            logger.error(f"Error generating code sample: {str(e)}")
            return {"result": {"success": False, "message": str(e)}}
