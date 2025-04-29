"""Tests for the JenticConfig class."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from jentic.agent_runtime.config import JenticConfig
from jentic.models import AssociatedFiles, FileEntry, FileId, GetFilesResponse, WorkflowEntry


@pytest.fixture
def mock_api_client():
    mock = MagicMock()
    # get_execution_files should be an AsyncMock for async calls
    if sys.version_info >= (3, 8):
        from unittest.mock import AsyncMock

        mock.get_execution_files = AsyncMock()
    else:
        # For Python < 3.8, fallback to MagicMock (pytest-asyncio will handle)
        mock.get_execution_files = MagicMock()
    return mock


@pytest.fixture
def mock_project_structure():
    """Create a temporary project structure for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_dir = Path(tmp_dir)

        # Create jentic.json config file (new style)
        config = {
            "workflows": {},
            "test-api": {
                "base_url": "https://test-api.example.com",
                "auth": {"api_key": "config-api-key"},
            },
        }
        with open(project_dir / "jentic.json", "w") as f:
            json.dump(config, f)

        yield project_dir / "jentic.json"


@pytest.fixture
def mock_project_with_workflows():
    """Create a temporary project structure with workflows for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        project_dir = Path(tmp_dir)

        # Create jentic.json config file with workflows (new style)
        config = {
            "workflows": {
                "workflow1": {"name": "First Workflow", "description": "Test workflow 1"},
                "workflow2": {"name": "Second Workflow", "description": "Test workflow 2"},
                "workflow3": {"name": "Third Workflow", "description": "Test workflow 3"},
            },
            "test-api": {
                "base_url": "https://test-api.example.com",
                "auth": {"api_key": "config-api-key"},
            },
        }
        with open(project_dir / "jentic.json", "w") as f:
            json.dump(config, f)

        yield project_dir / "jentic.json"


class TestJenticConfig:
    """Test suite for the JenticConfig class."""

    def test_load_project_config(self, mock_project_structure):
        """Test loading project configuration."""
        project = JenticConfig(mock_project_structure)

        assert "test-api" in project.config
        assert project.config["test-api"]["base_url"] == "https://test-api.example.com"
        assert project.config["test-api"]["auth"]["api_key"] == "config-api-key"

    def test_extract_workflows(self, mock_project_with_workflows):
        """Test extracting workflows from project configuration."""
        project = JenticConfig(mock_project_with_workflows)

        # Check that workflows were extracted correctly
        workflows = project.get_workflows()
        assert len(workflows) == 3

        # Check workflow content
        assert "workflow1" in workflows
        assert workflows["workflow1"]["name"] == "First Workflow"
        assert workflows["workflow1"]["description"] == "Test workflow 1"

        assert "workflow2" in workflows
        assert workflows["workflow2"]["name"] == "Second Workflow"

        assert "workflow3" in workflows
        assert workflows["workflow3"]["name"] == "Third Workflow"

    @pytest.mark.asyncio
    async def test_generate_config_from_uuids_workflows_only(self, mock_api_client):
        # Given
        workflow_uuids = ["wf-123", "wf-456"]
        operation_uuids = []
        mock_api_client.get_execution_files.return_value = GetFilesResponse(
            files={
                "arazzo": {
                    "arazzo-wf1": FileEntry(
                        id="arazzo-wf1",
                        filename="arazzo-wf1.json",
                        type="arazzo",
                        content={
                            "arazzo": "1.0.0",
                            "info": {"title": "Workflow Spec 1"},
                            "workflows": [{"workflowId": "wf-123", "name": "WorkflowOne"}],
                        },
                    ),
                    "arazzo-wf2": FileEntry(
                        id="arazzo-wf2",
                        filename="arazzo-wf2.json",
                        type="arazzo",
                        content={
                            "arazzo": "1.0.0",
                            "info": {"title": "Workflow Spec 2"},
                            "workflows": [{"workflowId": "wf-456", "name": "WorkflowTwo"}],
                        },
                    ),
                },
                "open_api": {
                    "openapi-wf1": FileEntry(
                        id="openapi-wf1",
                        filename="openapi-wf1.json",
                        type="open_api",
                        content={"openapi": "3.0.0", "info": {"title": "API 1"}, "paths": {}},
                    ),
                    "openapi-wf2": FileEntry(
                        id="openapi-wf2",
                        filename="openapi-wf2.json",
                        type="open_api",
                        content={"openapi": "3.0.0", "info": {"title": "API 2"}, "paths": {}},
                    ),
                },
            },
            workflows={
                "wf-123": WorkflowEntry(
                    workflow_id="wf-123",
                    workflow_uuid="wf-123",
                    name="WorkflowOne",
                    api_references=[],
                    files=AssociatedFiles(
                        arazzo=[FileId(id="arazzo-wf1")],
                        open_api=[FileId(id="openapi-wf1")],
                    ),
                ),
                "wf-456": WorkflowEntry(
                    workflow_id="wf-456",
                    workflow_uuid="wf-456",
                    name="WorkflowTwo",
                    api_references=[],
                    files=AssociatedFiles(
                        arazzo=[FileId(id="arazzo-wf2")],
                        open_api=[FileId(id="openapi-wf2")],
                    ),
                ),
            },
            workflow_file_ids={
                "wf-123": ["arazzo-wf1", "openapi-wf1"],
                "wf-456": ["arazzo-wf2", "openapi-wf2"],
            },
            operation_file_ids={},
            api_security_schemes={},
        )

        # When
        config = await JenticConfig.generate_config_from_uuids(
            mock_api_client, workflow_uuids=workflow_uuids, operation_uuids=operation_uuids
        )

        # Then
        assert "workflows" in config
        assert "wf-123" in config["workflows"]
        assert "wf-456" in config["workflows"]
        assert "operations" in config
        assert len(config["operations"]) == 0
        assert "environment_variable_mappings" in config
        mock_api_client.get_execution_files.assert_called_once_with(
            workflow_ids=workflow_uuids, operation_uuids=operation_uuids
        )
