"""Request handlers for the Jentic ARK² MCP Plugin."""

import logging
from typing import Any

from mcp.adapters.mcp import MCPAdapter

logger = logging.getLogger(__name__)

# The global orchestrator is only initialized when handling persistent server requests
mcp_adapter = None  # Will be initialized per request


async def handle_request(tool_name: str, request: dict[str, Any]) -> dict[str, Any]:
    """Handle a request to a specific tool.

    Args:
        tool_name: Name of the tool to invoke.
        request: Tool request parameters.

    Returns:
        Tool response.

    Raises:
        ValueError: If the tool is not recognized.
    """
    global mcp_adapter

    logger.info(f"Handling request for tool: {tool_name}")
    logger.debug(f"Request parameters: {request}")

    # Extract project directory from request if present
    project_directory = request.get("project_directory")

    # Log the project directory for debugging
    if project_directory:
        logger.info(f"Request contains project directory: {project_directory}")
    else:
        logger.warning("No project directory in request")

    # Create per-request orchestrator with project context
    mcp_adapter = MCPAdapter()

    # Define handlers with the fresh orchestrator and adapter
    tool_handlers = {
        "search_apis": mcp_adapter.search_api_capabilities,
        "get_execution_configuration": mcp_adapter.generate_runtime_config,
        "generate_code_sample": mcp_adapter.generate_code_sample,
    }

    if tool_name not in tool_handlers:
        error_msg = f"Unknown tool: {tool_name}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    try:
        handler = tool_handlers[tool_name]
        result = await handler(request)
        logger.info(f"Successfully handled request for tool: {tool_name}")
        return result
    except Exception as e:
        logger.error(f"Error handling request for tool {tool_name}: {str(e)}", exc_info=True)
        raise
