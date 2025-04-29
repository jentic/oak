"""Integration tests for the MCP functionality."""

import os
from typing import Any

import pytest
import pytest_asyncio

from mcp.adapters.mcp import MCPAdapter
from mcp.handlers import handle_request


class MockStdioTransport:
    """Mock stdio transport for testing without any side effects."""

    def __init__(self, adapter):
        """Initialize the mock stdio transport."""
        self.adapter = adapter
        self.received_messages = []
        self.sent_responses = []

    async def send_response(self, response: dict[str, Any]) -> None:
        """Record sent responses."""
        self.sent_responses.append(response)

    async def process_message(self, message: dict[str, Any]) -> None:
        """Process a mock message."""
        self.received_messages.append(message)

        tool_name = message.get("type")
        data = message.get("data", {})

        if not tool_name:
            await self.send_response({"error": "Invalid message format: missing 'type'"})
            return

        try:
            result = await handle_request(tool_name, data)
            await self.send_response(result)
        except Exception as e:
            await self.send_response({"error": str(e)})


@pytest_asyncio.fixture
async def mock_adapter():
    """Create an MCP adapter with mock components."""
    # Force mock mode on - this needs to be set before any other imports
    os.environ["MOCK_ENABLED"] = "true"

    # Create a temporary directory for test storage - explicitly use .test_output for tests
    temp_dir = os.path.join(os.getcwd(), ".test_output", "test_integration")
    os.makedirs(temp_dir, exist_ok=True)

    # Create the adapter
    adapter = MCPAdapter()

    try:
        yield adapter
    finally:
        # Reset the mock mode
        if "MOCK_ENABLED" in os.environ:
            del os.environ["MOCK_ENABLED"]


@pytest_asyncio.fixture
async def mcp_transport(mock_adapter):
    """Create a mock transport for testing."""
    transport = MockStdioTransport(adapter=mock_adapter)
    return transport


@pytest.mark.asyncio
async def test_search_api_capabilities(mcp_transport):
    """Test the search_api_capabilities MCP command."""
    # Send a search request
    await mcp_transport.process_message(
        {"type": "search_apis", "data": {"capability_description": "spotify music"}}
    )

    # Verify we got a response
    assert len(mcp_transport.sent_responses) == 1

    # Verify the response structure
    response = mcp_transport.sent_responses[0]
    assert "result" in response
    assert "matches" in response["result"]
    assert "query" in response["result"]
    assert "total_matches" in response["result"]

    # In mock mode, we should get some results


@pytest.mark.skip  # This test needs to be reworked based on the new package structure.
async def test_discord_end_to_end_workflow(mcp_transport):
    """Test a complete workflow from search to generation for Discord message API.

    This test exercises the full MCP workflow:
    1. Search for Discord message capabilities
    2. Generate a configuration from the selection
    """
    # Step 1: Search for Discord message capabilities
    await mcp_transport.process_message(
        {
            "type": "search_apis",
            "data": {
                "capability_description": "send a message to a channel on discord using a bot",
                "keywords": ["discord", "message", "channel", "bot"],
            },
        }
    )

    # Verify we got search results
    assert len(mcp_transport.sent_responses) == 1
    search_response = mcp_transport.sent_responses[0]
    assert "result" in search_response
    assert "matches" in search_response["result"]

    # Find Discord API and postChannelMessage workflow in the results
    discord_api = None
    post_channel_workflow = None

    for api in search_response["result"]["matches"]:
        if "discord" in api["api_id"].lower():
            discord_api = api
            if "workflows" in api:
                for workflow in api["workflows"]:
                    if workflow["workflow_id"] == "postChannelMessage":
                        post_channel_workflow = workflow
                        break
            break

    # Verify we found the Discord API
    assert discord_api is not None, "Discord API not found in search results"
    assert post_channel_workflow is not None, "postChannelMessage workflow not found in Discord API"

    # Print the found API and workflow for debugging
    print(f"Found Discord API: {discord_api['api_id']}")
    print(f"Found workflow: {post_channel_workflow['workflow_id']}")

    # Step 2: Generate config from the selection set
    mcp_transport.sent_responses.clear()
    await mcp_transport.process_message(
        {
            "type": "get_execution_configuration",
            "data": {
                "api_ids": [discord_api["api_id"]],
                "workflow_ids": [post_channel_workflow["workflow_id"]],
            },
        }
    )

    # Verify generation response
    assert len(mcp_transport.sent_responses) == 1
    generation_response = mcp_transport.sent_responses[0]
    assert "result" in generation_response
    print(f"Generation response: {generation_response["result"]}")

    # The response structure is different - it directly contains the API configuration
    # rather than having a nested 'config' field
    api_config = generation_response["result"]
    assert "version" in api_config
    assert "apis" in api_config
    assert len(api_config["apis"]) == 1

    # Verify the config contains the Discord API
    discord_api_config = api_config["apis"][0]
    assert "discord" in discord_api_config["api_id"].lower()
    assert "selected_workflows" in discord_api_config
    assert "postChannelMessage" in discord_api_config["selected_workflows"]
    assert "workflows" in discord_api_config
    assert "postChannelMessage" in discord_api_config["workflows"]
