"""HTTP transport implementation for the ARK² MCP Plugin."""

import asyncio
import logging
import signal

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from mcp.adapters.mcp import MCPAdapter
from mcp.config import load_config
from mcp.plugin import generate_openapi_spec
from mcp.transport.base import BaseTransport

logger = logging.getLogger(__name__)


class HTTPTransport(BaseTransport):
    """HTTP transport using FastAPI."""

    def __init__(
        self,
        adapter: MCPAdapter,
        host: str = "127.0.0.1",
        port: int = 8010,
    ):
        """Initialize the HTTP transport.

        Args:
            adapter: MCP adapter to handle requests.
            host: Host to bind the server to.
            port: Port to serve on.
        """
        self.adapter = adapter
        self.host = host
        self.port = port
        self.config = load_config()
        self._app = FastAPI(title="Jentic ARK² MCP Plugin")
        self._server = None
        self._running = False
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up the FastAPI routes."""

        @self._app.get("/openapi.json")
        async def get_openapi():
            """Generate the OpenAPI specification."""
            spec = generate_openapi_spec(self.config)
            return JSONResponse(spec)

        @self._app.get("/.well-known/ai-plugin.json")
        async def get_plugin_manifest():
            """Serve the plugin manifest."""
            mock_status = "ENABLED" if self.config.mock.enabled else "DISABLED"
            manifest = {
                "schema_version": "v1",
                "name_for_human": "Jentic ARK² API Knowledge Hub",
                "name_for_model": "jentic_api_knowledge_hub",
                "description_for_human": "Connect to the Jentic API Knowledge Hub to discover and integrate APIs.",
                "description_for_model": "This plugin helps discover, explore, and integrate with APIs that match specific capability needs.",
                "auth": {"type": "none"},
                "api": {
                    "type": "openapi",
                    "url": f"{self.config.mcp.base_url}/openapi.json",
                    "has_user_authentication": False,
                },
                "logo_url": f"{self.config.mcp.base_url}/logo.png",
                "contact_email": "info@jenticlabs.com",
                "legal_info_url": "https://jenticlabs.com/legal",
                "mock_status": mock_status,
            }
            return JSONResponse(manifest)

        @self._app.post("/api/search_apis")
        async def search_api_capabilities(request: Request):
            """MCP endpoint for searching API capabilities."""
            data = await request.json()
            result = await self.adapter.search_api_capabilities(data)
            return JSONResponse(result)

        @self._app.post("/api/create_selection_set")
        async def create_selection_set(request: Request):
            """MCP endpoint for creating a selection set."""
            data = await request.json()
            result = await self.adapter.create_selection_set(data)
            return JSONResponse(result)

        @self._app.post("/api/get_selection_set")
        async def get_selection_set(request: Request):
            """MCP endpoint for retrieving a selection set."""
            data = await request.json()
            result = await self.adapter.get_selection_set(data)
            return JSONResponse(result)

        @self._app.post("/api/update_selection_set")
        async def update_selection_set(request: Request):
            """MCP endpoint for updating a selection set."""
            data = await request.json()
            result = await self.adapter.update_selection_set(data)
            return JSONResponse(result)

        @self._app.post("/api/generate_config")
        async def generate_config(request: Request):
            """MCP endpoint for generating a configuration file from a selection set."""
            data = await request.json()
            result = await self.adapter.generate_runtime_config(data)
            return JSONResponse(result)

        # Keep for backwards compatibility
        @self._app.post("/api/generate_runtime_config")
        async def generate_runtime_config(request: Request):
            """Legacy endpoint (renamed to generate_config)."""
            data = await request.json()
            result = await self.adapter.generate_runtime_config(data)
            return JSONResponse(result)

    async def start(self) -> None:
        """Start the HTTP server."""
        config = uvicorn.Config(app=self._app, host=self.host, port=self.port, log_level="info")
        self._server = uvicorn.Server(config)
        self._running = True

        # Handle termination gracefully
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._handle_exit)

        logger.info(f"Starting HTTP server on {self.host}:{self.port}")
        await self._server.serve()

    def _handle_exit(self, sig, frame):
        """Handle termination signals."""
        if self._running:
            logger.info("Shutting down HTTP server...")
            asyncio.create_task(self.stop())

    async def stop(self) -> None:
        """Stop the HTTP server."""
        if self._server and self._running:
            self._running = False
            if hasattr(self._server, "should_exit"):
                self._server.should_exit = True
            logger.info("HTTP server stopped")

    @property
    def is_running(self) -> bool:
        """Check if the HTTP server is running."""
        return self._running
