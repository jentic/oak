"""MCP Plugin implementation for Jentic ARK²."""

import os
from typing import Any

from mcp import __version__
from mcp.tools import get_all_tool_definitions


def get_plugin_manifest() -> dict[str, Any]:
    """Generate the MCP plugin manifest.

    Returns:
        Dict[str, Any]: The MCP plugin manifest.
    """
    base_url = os.environ.get("MCP_BASE_URL", "http://localhost:8000")

    return {
        "schema_version": "v1",
        "name_for_model": "jentic_mcp",
        "name_for_human": "Jentic MCP",
        "description_for_model": (
            "Jentic MCP is an Agentic API Reference and Runtime Knowledge Kit that enables "
            "developers to discover, select, and integrate external APIs into agent workflows. "
            "Use this plugin for ANY task related to finding APIs, getting API details, "
            "generating code for API integration, or creating prompts with API knowledge."
        ),
        "description_for_human": "Find and integrate APIs into your agents with Jentic's MCP.",
        "auth": {"type": "none"},
        "api": {"type": "openapi", "url": f"{base_url}/openapi.json"},
        "logo_url": f"{base_url}/logo.png",
        "contact_email": "support@jenticlabs.com",
        "legal_info_url": "https://jenticlabs.com/legal",
        "version": __version__,
    }


def generate_openapi_spec(config: Any) -> dict[str, Any]:
    """Generate the OpenAPI specification for the MCP plugin.

    Args:
        config: Configuration object with MCP settings.

    Returns:
        Dict[str, Any]: The OpenAPI specification.
    """
    base_url = config.mcp.base_url
    tools = get_all_tool_definitions()

    paths: dict[str, Any] = {}
    components: dict[str, Any] = {"schemas": {}}

    # Add each tool as an endpoint
    for tool in tools:
        tool_name = tool["name"]
        path = f"/api/{tool_name}"

        # Add request and response schemas
        request_schema_name = f"{tool_name}Request"
        response_schema_name = f"{tool_name}Response"

        components["schemas"][request_schema_name] = {
            "type": "object",
            "properties": tool["parameters"]["properties"],
            "required": tool["parameters"].get("required", []),
        }

        components["schemas"][response_schema_name] = {
            "type": "object",
            "properties": {
                "result": {"type": "object", "description": f"Result of the {tool_name} operation"}
            },
        }

        # Add path
        paths[path] = {
            "post": {
                "operationId": tool_name,
                "summary": tool["description"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{request_schema_name}"}
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{response_schema_name}"}
                            }
                        },
                    }
                },
            }
        }

    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Jentic ARK² MCP Plugin API",
            "description": (
                "API for Jentic ARK² MCP Plugin, enabling developers to discover, "
                "select, and integrate external APIs into agent workflows."
            ),
            "version": __version__,
        },
        "servers": [{"url": base_url}],
        "paths": paths,
        "components": components,
    }


def get_openapi_spec() -> dict[str, Any]:
    """Generate the OpenAPI specification for the MCP plugin.

    Returns:
        Dict[str, Any]: The OpenAPI specification.
    """
    base_url = os.environ.get("MCP_BASE_URL", "http://localhost:8000")
    tools = get_all_tool_definitions()

    paths: dict[str, Any] = {}
    components: dict[str, Any] = {"schemas": {}}

    # Add each tool as an endpoint
    for tool in tools:
        tool_name = tool["name"]
        path = f"/{tool_name}"

        # Add request and response schemas
        request_schema_name = f"{tool_name}Request"
        response_schema_name = f"{tool_name}Response"

        components["schemas"][request_schema_name] = {
            "type": "object",
            "properties": tool["parameters"]["properties"],
            "required": tool["parameters"].get("required", []),
        }

        components["schemas"][response_schema_name] = {
            "type": "object",
            "properties": {
                "result": {"type": "object", "description": f"Result of the {tool_name} operation"}
            },
        }

        # Add path
        paths[path] = {
            "post": {
                "operationId": tool_name,
                "summary": tool["description"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{request_schema_name}"}
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{response_schema_name}"}
                            }
                        },
                    }
                },
            }
        }

    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Jentic ARK² MCP Plugin API",
            "description": (
                "API for Jentic ARK² MCP Plugin, enabling developers to discover, "
                "select, and integrate external APIs into agent workflows."
            ),
            "version": __version__,
        },
        "servers": [{"url": base_url}],
        "paths": paths,
        "components": components,
    }


def serve_plugin(host: str = "127.0.0.1", port: int = 8010) -> None:
    """Serve the MCP plugin.

    Args:
        host: Host to bind the server to.
        port: Port to serve the MCP plugin on.
    """
    import logging

    import uvicorn
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    from mcp.config import load_config
    from mcp.handlers import handle_request

    config = load_config()
    mock_mode = "ENABLED" if config.mock.enabled else "DISABLED"

    print(f"Starting ARK² MCP Plugin server at http://{host}:{port}")
    print(f"Mock mode: {mock_mode}")

    # Create FastAPI app
    app = FastAPI(
        title="Jentic ARK² MCP Plugin",
        description="MCP Plugin for Jentic's API Knowledge Hub",
        version=__version__,
    )

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("ark2_mcp")

    # Manifest endpoint
    @app.get("/.well-known/ai-plugin.json")
    async def get_manifest_endpoint():
        return get_plugin_manifest()

    # OpenAPI spec endpoint
    @app.get("/openapi.json")
    async def get_openapi_spec_endpoint():
        return get_openapi_spec()

    # Dynamic tool endpoints based on tool definitions
    for tool in get_all_tool_definitions():
        tool_name = tool["name"]

        # Create a closure to capture the tool_name
        async def create_tool_endpoint(request: Request, tool_name=tool_name):
            data = await request.json()
            result = await handle_request(tool_name, data)
            return result

        # Add the endpoint
        endpoint = create_tool_endpoint
        endpoint.__name__ = f"handle_{tool_name}"
        app.post(f"/{tool_name}", response_model=None)(endpoint)

        logger.info(f"Registered endpoint for tool: {tool_name}")

    # Error handler
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Error processing request: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )

    # Start the server
    uvicorn.run(app, host=host, port=port, log_level=config.logging.level.lower())
