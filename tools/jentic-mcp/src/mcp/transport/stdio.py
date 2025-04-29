"""Standard IO transport for the ARK² MCP Plugin according to MCP spec."""

import asyncio
import json
import logging
import signal
import sys
from typing import Any

from mcp.adapters.mcp import MCPAdapter
from mcp.transport.base import BaseTransport

logger = logging.getLogger(__name__)


class StdioTransport(BaseTransport):
    """Stdio transport implementation for MCP protocol.

    This transport reads JSON requests from stdin and writes JSON responses to stdout,
    following the Model Configuration Protocol (MCP) specification.
    """

    def __init__(self, adapter: MCPAdapter, debug_stdio: bool = False):
        """Initialize the stdio transport.

        Args:
            adapter: MCP adapter to handle requests.
            debug_stdio: Whether to log stdio communication for debugging.
        """
        self.adapter = adapter
        self._running = False
        self._task = None
        self._debug_stdio = debug_stdio

        # Map request types to handler methods
        self._handlers = {
            "search_apis": self._handle_search_api_capabilities,
            "get_execution_configuration": self._handle_generate_runtime_from_selection_set,
            "generate_code_sample": self._handle_generate_code_sample,
        }

        # Log available tools
        tool_names = list(self._handlers.keys())
        logger.info(
            f"StdioTransport initialized with {len(tool_names)} available tools: {', '.join(tool_names)}"
        )

    async def _handle_search_api_capabilities(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle search_apis request.

        Args:
            data: Request data.

        Returns:
            Response data.
        """
        try:
            return await self.adapter.search_api_capabilities(data)
        except Exception as e:
            logger.error(f"Error in search_api_capabilities: {str(e)}")
            return {
                "result": {
                    "matches": [],
                    "query": data.get("capability_description", ""),
                    "total_matches": 0,
                    "error": f"Error in search: {str(e)}",
                }
            }

    async def _handle_create_selection_set(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle create_selection_set request.

        Args:
            data: Request data.

        Returns:
            Response data.
        """
        return await self.adapter.create_selection_set(data)

    async def _handle_get_selection_set(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle get_selection_set request.

        Args:
            data: Request data.

        Returns:
            Response data.
        """
        return await self.adapter.get_selection_set(data)

    async def _handle_update_selection_set(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle update_selection_set request.

        Args:
            data: Request data.

        Returns:
            Response data.
        """
        return await self.adapter.update_selection_set(data)

    async def _handle_generate_runtime_from_selection_set(
        self, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle generate_runtime_config request.

        Args:
            data: Request data.

        Returns:
            Response data.
        """
        return await self.adapter.generate_runtime_config(data)

    async def _handle_generate_code_sample(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle generate_code_sample request.

        Args:
            data: Request data.

        Returns:
            Response data.
        """
        return await self.adapter.generate_code_sample(data)

    async def _handle_jsonrpc_initialize(
        self, params: dict[str, Any], request_id: Any
    ) -> dict[str, Any]:
        """Handle JSON-RPC initialize request.

        This is called when using the server with clients that follow JSON-RPC protocol,
        like Windsurf.

        Args:
            params: Request parameters.
            request_id: Request ID.

        Returns:
            Response data in JSON-RPC format.
        """
        logger.info(f"Handling JSON-RPC initialize request (id: {request_id})")

        # Get a list of our available tools with their full schemas
        from mcp.tools import get_all_tool_definitions

        tool_definitions = get_all_tool_definitions()

        tool_list = []
        for tool in tool_definitions:
            # Convert our tool definition to exact MCP format per the schema in mcp_schema.ts
            tool_schema = {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": tool["parameters"]["properties"],
                    "required": tool["parameters"].get("required", []),
                },
            }
            tool_list.append(tool_schema)

        logger.info(f"Returning {len(tool_list)} tool definitions in initialize response")

        # Get protocol version from params or use latest
        protocol_version = params.get("protocolVersion", "2024-11-05")

        # Respond with our capabilities according to MCP schema
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": protocol_version,
                "capabilities": {
                    "tools": {}  # Empty object indicates we support tools but don't need special capabilities
                },
                "serverInfo": {"name": "jentic-ark2-mcp", "version": "0.1.0"},
            },
        }

    async def _handle_jsonrpc_shutdown(
        self, params: dict[str, Any], request_id: Any
    ) -> dict[str, Any]:
        """Handle JSON-RPC shutdown request.

        Args:
            params: Request parameters.
            request_id: Request ID.

        Returns:
            Response data in JSON-RPC format.
        """
        logger.info(f"Handling JSON-RPC shutdown request (id: {request_id})")

        # Schedule shutdown
        asyncio.create_task(self.stop())

        return {"jsonrpc": "2.0", "id": request_id, "result": None}

    async def _handle_jsonrpc_list_tools(
        self, params: dict[str, Any], request_id: Any
    ) -> dict[str, Any]:
        """Handle JSON-RPC tools/list request.

        Args:
            params: Request parameters.
            request_id: Request ID.

        Returns:
            Response data in JSON-RPC format.
        """
        logger.info(f"Handling JSON-RPC tools/list (id: {request_id})")

        # Get a list of our available tools with their full schemas
        from mcp.tools import get_all_tool_definitions

        tool_definitions = get_all_tool_definitions()

        tool_list = []
        for tool in tool_definitions:
            # Convert our tool definition to exact MCP format per the schema in mcp_schema.ts
            tool_schema = {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": tool["parameters"]["properties"],
                    "required": tool["parameters"].get("required", []),
                },
            }
            tool_list.append(tool_schema)

        logger.info(f"Returning {len(tool_list)} tool definitions in tools/list response")

        # Respond according to MCP schema
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tool_list}}

    async def _handle_jsonrpc_toolcall(
        self, params: dict[str, Any], request_id: Any
    ) -> dict[str, Any]:
        """Handle JSON-RPC toolcall request.

        Args:
            params: Request parameters.
            request_id: Request ID.

        Returns:
            Response data in JSON-RPC format.
        """
        tool_name = params.get("name")

        # Per MCP spec, params may be in "arguments" field (used by Windsurf)
        # or "params" field (used by some implementations)
        tool_params = params.get("arguments", params.get("params", {}))

        logger.info(f"Handling JSON-RPC toolcall for {tool_name} (id: {request_id})")
        logger.debug(f"Tool parameters: {json.dumps(tool_params)}")

        if not tool_name:
            logger.error("No tool name provided in toolcall request")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32602, "message": "Invalid params: missing tool name"},
            }

        if tool_name not in self._handlers:
            logger.error(f"Unknown tool: {tool_name}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: unknown tool '{tool_name}'",
                },
            }

        # Process the request using our existing handlers
        try:
            handler = self._handlers[tool_name]
            response_data = await handler(tool_params)
            logger.info(f"Handler for {tool_name} completed successfully")

            # Shape the response according to CallToolResult in MCP spec
            # Wrap the result in a content array with TextContent format
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(response_data.get("result", {}))}
                    ],
                    "isError": False,
                },
            }

        except Exception as e:
            logger.exception(f"Error in handler for {tool_name}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True,
                },
            }

    async def _process_stdin(self) -> None:
        """Process stdin in a loop.

        Reads JSON requests from stdin, processes them, and writes responses to stdout.
        Supports both MCP and JSON-RPC protocol formats.
        """
        loop = asyncio.get_running_loop()

        while self._running:
            try:
                # Use loop.run_in_executor to read from stdin without blocking
                line = await loop.run_in_executor(None, sys.stdin.readline)

                if not line:
                    # EOF, exit the loop
                    logger.info("Received EOF, stopping stdio transport")
                    self._running = False
                    break

                # Parse the JSON request
                try:
                    if not line.strip():
                        logger.warning("Received empty line from stdin")
                        continue

                    logger.info(
                        f"Received raw input: {line[:100]}{'...' if len(line) > 100 else ''}"
                    )

                    try:
                        request = json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON: {e}")
                        logger.error(f"Raw input was: {line}")
                        error_response = {"error": f"Invalid JSON: {str(e)}"}
                        print(json.dumps(error_response), flush=True)
                        continue

                    if self._debug_stdio:
                        logger.debug(f"Received request: {json.dumps(request)}")

                    # Detect protocol format (MCP vs JSON-RPC)
                    if "jsonrpc" in request:
                        # JSON-RPC format
                        logger.info("Detected JSON-RPC protocol request")

                        request_id = request.get("id")
                        method = request.get("method")
                        params = request.get("params", {})

                        if not method:
                            logger.error("No method specified in JSON-RPC request")
                            error_response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {
                                    "code": -32600,
                                    "message": "Invalid Request: missing method",
                                },
                            }
                            print(json.dumps(error_response), flush=True)
                            continue

                        logger.info(f"Processing JSON-RPC method: {method}, id: {request_id}")

                        # Check if this is a notification (has no ID or starts with notifications/)
                        if request_id is None or method.startswith("notifications/"):
                            # This is a notification, we don't send a response
                            logger.info(f"Received notification: {method}")
                            # Handle specific notifications if needed
                            if method == "notifications/initialized":
                                logger.info("Client has completed initialization")
                            elif method == "notifications/cancelled":
                                logger.info(f"Client cancelled request: {params.get('requestId')}")
                            # Don't send a response for notifications
                            continue

                        # Handle different JSON-RPC methods
                        if method == "initialize":
                            response = await self._handle_jsonrpc_initialize(params, request_id)
                        elif method == "shutdown":
                            response = await self._handle_jsonrpc_shutdown(params, request_id)
                        elif method == "tools/list":
                            response = await self._handle_jsonrpc_list_tools(params, request_id)
                        elif method == "tools/call":
                            response = await self._handle_jsonrpc_toolcall(params, request_id)
                        elif method == "toolcall":  # Backward compatibility
                            response = await self._handle_jsonrpc_toolcall(params, request_id)
                        else:
                            logger.error(f"Unknown JSON-RPC method: {method}")
                            response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {"code": -32601, "message": f"Method not found: {method}"},
                            }

                        # Log and send the response
                        if self._debug_stdio:
                            logger.debug(f"Sending JSON-RPC response: {json.dumps(response)}")
                        else:
                            logger.info(f"Sending JSON-RPC response for {method}, id: {request_id}")

                        print(json.dumps(response), flush=True)

                    elif "type" in request and "data" in request:
                        # MCP format
                        logger.info("Detected MCP protocol request")
                        request_type = request["type"]
                        request_data = request["data"]
                        request_id = request.get("id")

                        logger.info(
                            f"Processing MCP request type: {request_type}, id: {request_id}"
                        )

                        # Check if we have a handler for this request type
                        if request_type not in self._handlers:
                            logger.error(f"Unknown request type: {request_type}")
                            error_response = {"error": f"Unknown request type: {request_type}"}
                            if request_id:
                                error_response["id"] = request_id
                            print(json.dumps(error_response), flush=True)
                            continue

                        # Process the request
                        logger.info(f"Calling handler for {request_type}")
                        handler = self._handlers[request_type]

                        try:
                            response_data = await handler(request_data)
                            logger.info(f"Handler for {request_type} completed successfully")
                        except Exception as e:
                            logger.exception(f"Error in handler for {request_type}: {e}")
                            error_response = {"error": f"Error processing {request_type}: {str(e)}"}
                            if request_id:
                                error_response["id"] = request_id
                            print(json.dumps(error_response), flush=True)
                            continue

                        # Build the response
                        response = {
                            "result": response_data.get("result", {}),
                        }

                        # Include request ID if provided
                        if request_id:
                            response["id"] = request_id

                        # Log the response
                        if self._debug_stdio:
                            logger.debug(f"Sending MCP response: {json.dumps(response)}")
                        else:
                            logger.info(
                                f"Sending MCP response for {request_type}, id: {request_id}"
                            )

                        # Write the response to stdout
                        print(json.dumps(response), flush=True)

                    else:
                        # Unknown format
                        logger.error(f"Unknown request format: {request}")
                        error_response = {
                            "error": "Invalid request format, expected MCP or JSON-RPC format"
                        }
                        print(json.dumps(error_response), flush=True)

                except Exception as e:
                    logger.exception(f"Error processing request: {e}")
                    error_response = {"error": f"Error processing request: {str(e)}"}
                    print(json.dumps(error_response), flush=True)

            except asyncio.CancelledError:
                logger.info("Stdio processing task cancelled")
                break

            except Exception as e:
                logger.exception(f"Unexpected error in stdin processing: {e}")
                # Continue to try to process the next request

    async def start(self) -> None:
        """Start the stdio transport."""
        self._running = True

        # Handle termination gracefully
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handle_exit)

        # Start processing stdin
        logger.info("Starting stdio transport")
        self._task = asyncio.create_task(self._process_stdin())

        try:
            # Wait for the stdin processing task to complete
            await self._task
        except asyncio.CancelledError:
            logger.info("Stdio transport stopped")
        finally:
            self._running = False

    def _handle_exit(self, sig, frame):
        """Handle termination signals."""
        if self._running:
            logger.info("Shutting down stdio transport...")
            asyncio.create_task(self.stop())

    async def stop(self) -> None:
        """Stop the stdio transport."""
        if self._running:
            self._running = False

            # Cancel the stdin processing task
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

            logger.info("Stdio transport stopped")

    @property
    def is_running(self) -> bool:
        """Check if the stdio transport is running."""
        return self._running
