"""Tests for the AgentToolManager class."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from jentic.agent_runtime.agent_tools import AgentToolManager


@pytest.fixture
def mock_project_structure():
    """Create a temporary project structure for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_dir = Path(tmp_dir)

        # Create jentic.json config file with workflows (not nested under 'apis')
        config = {
            "workflows": {
                "testWorkflow": {
                    "workflow_uuid": "test-workflow-uuid",
                    "name": "Test Workflow",
                    "description": "A test workflow",
                    "inputs": {
                        "properties": {"query": {"type": "string", "description": "Test query"}},
                        "required": ["query"],
                    },
                    "steps": [
                        {
                            "id": "step1",
                            "operation": {"path": "/test", "method": "GET"},
                            "parameters": {"q": "$inputs.query"},
                        }
                    ],
                    "output": "$steps.step1",
                }
            },
            "test-api": {
                "base_url": "https://test-api.example.com",
                "auth": {"api_key": "config-api-key"},
            },
        }
        config_path = project_dir / "jentic.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        yield config_path


@pytest.fixture
def mock_api_hub_client():
    return MagicMock()


@pytest.fixture
def agent_tool_manager(mock_project_structure, mock_api_hub_client):
    """Create a mocked AgentToolManager for testing."""
    # Then patch the TaskExecutor.execute_workflow method
    with patch(
        "jentic.agent_runtime.tool_execution.TaskExecutor.execute_workflow"
    ) as mock_execute_workflow:
        # Configure the mock workflow execution response
        mock_execute_workflow.return_value = {
            "success": True,
            "result": {"data": "test result"},
        }

        # Create manager
        manager = AgentToolManager(
            mock_project_structure, format="anthropic", api_hub_client=mock_api_hub_client
        )

        # Mock the project's get_workflow_api_id method
        manager.project.get_workflow_api_id = MagicMock(return_value="test-api")

        yield manager


class TestAgentToolManager:
    """Test suite for the AgentToolManager class."""

    def test_initialization(self, mock_project_structure):
        """Test AgentToolManager initialization."""
        manager = AgentToolManager(mock_project_structure)

        assert manager.format == "anthropic"  # Default format
        assert manager.project is not None
        assert manager.tool_spec_manager is not None
        assert manager.tool_executor is not None

    def test_generate_tool_definitions_anthropic(self, mock_project_structure):
        """Test getting Anthropic tool definitions."""
        manager = AgentToolManager(mock_project_structure, format="anthropic")
        tools = manager.generate_tool_definitions()

        assert len(tools) > 0
        assert "name" in tools[0]
        assert "input_schema" in tools[0]
        assert tools[0]["name"] == "testWorkflow"

    def test_generate_tool_definitions_openai(self, mock_project_structure):
        """Test getting OpenAI tool definitions."""
        manager = AgentToolManager(mock_project_structure, format="openai")
        tools = manager.generate_tool_definitions()

        assert len(tools) > 0
        assert "type" in tools[0]
        assert "function" in tools[0]
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "testWorkflow"

    @pytest.mark.asyncio
    async def test_execute_tool(self, agent_tool_manager):
        """Test executing a tool."""
        # Execute the test workflow
        result = await agent_tool_manager.execute_tool("testWorkflow", {"query": "test"})

        # Verify the result
        assert result["success"] is True
        assert result["result"]["data"] == "test result"

        # Verify the tool executor was called correctly
        agent_tool_manager.tool_executor.execute_workflow.assert_called_once_with(
            "test-workflow-uuid", {"query": "test"}
        )

    @pytest.mark.asyncio
    async def test_execute_tool_error(self, agent_tool_manager):
        """Test executing a tool with an error."""
        # Configure the mock to raise an exception
        agent_tool_manager.tool_executor.execute_workflow.side_effect = Exception("Test error")

        # Execute the test workflow
        result = await agent_tool_manager.execute_tool("testWorkflow", {"query": "test"})

        # Verify the result
        assert result["success"] is False
        assert "Test error" in result["error"]
