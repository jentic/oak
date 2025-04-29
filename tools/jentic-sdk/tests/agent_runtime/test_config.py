import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jentic.agent_runtime.config import JenticConfig


@pytest.mark.asyncio
async def test_generate_config_from_uuids():
    # Prepare mock api_hub_client
    mock_api_hub_client = MagicMock()
    # Fake workflow UUID and details
    workflow_uuid = "uuid-1234"
    fake_arazzo_doc = {"workflows": {"friendly-id": {"name": "Test Workflow"}}}
    fake_details = MagicMock()
    fake_details.arazzo_doc = fake_arazzo_doc
    fake_details.friendly_workflow_id = "friendly-id"
    fake_details.source_descriptions = {"openapi": {"info": "fake"}}

    # get_execution_details_for_workflow returns a single details object
    mock_api_hub_client.get_execution_details_for_workflow = AsyncMock(return_value=fake_details)

    # get_execution_files must also be AsyncMock if used in new code
    fake_files_response = MagicMock()
    fake_files_response.files = {
        "open_api": {},
        "arazzo": {"arazzo-id": MagicMock(content=fake_arazzo_doc)},
    }
    fake_files_response.workflows = {
        workflow_uuid: MagicMock(
            workflow_id="friendly-id",
            files=MagicMock(arazzo=[MagicMock(id="arazzo-id")], open_api=[]),
        )
    }
    fake_files_response.operations = None
    mock_api_hub_client.get_execution_files = AsyncMock(return_value=fake_files_response)

    # Patch AuthProcessor.process_api_auth and JenticConfig._extract_workflow_details
    with (
        patch("jentic.agent_runtime.config.AuthProcessor") as MockAuthProcessor,
        patch.object(
            JenticConfig,
            "_extract_workflow_details",
            return_value={"friendly-id": {"name": "Test Workflow"}},
        ),
    ):
        mock_auth_processor = MockAuthProcessor.return_value

        config = await JenticConfig.generate_config_from_uuids(
            mock_api_hub_client, [workflow_uuid], []
        )

    assert config["version"] == "1.0"
    assert "workflows" in config
    assert "friendly-id" in config["workflows"]
    assert config["workflows"]["friendly-id"]["name"] == "Test Workflow"
    assert config["workflows"]["friendly-id"]["workflow_uuid"] == workflow_uuid


@pytest.mark.asyncio
async def test_generate_config_from_uuids_empty():
    mock_api_hub_client = MagicMock()
    with pytest.raises(ValueError):
        await JenticConfig.generate_config_from_uuids(mock_api_hub_client, [], [])


@pytest.mark.asyncio
async def test_generate_config_security_requirements():
    """Test that per-workflow security_requirements are outputted correctly."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from jentic.agent_runtime.config import JenticConfig

    mock_api_hub_client = MagicMock()
    workflow_uuid = "uuid-9999"
    fake_arazzo_doc = {"workflows": {"friendly-id": {"name": "Test Workflow"}}}
    fake_details = MagicMock()
    fake_details.arazzo_doc = fake_arazzo_doc
    fake_details.friendly_workflow_id = "friendly-id"
    fake_details.source_descriptions = {"openapi.json": {"info": "fake"}}
    mock_api_hub_client.get_execution_details_for_workflow = AsyncMock(return_value=fake_details)

    fake_files_response = MagicMock()
    fake_files_response.files = {
        "open_api": {},
        "arazzo": {"arazzo-id": MagicMock(content=fake_arazzo_doc)},
    }
    fake_files_response.workflows = {
        workflow_uuid: MagicMock(
            workflow_id="friendly-id",
            files=MagicMock(arazzo=[MagicMock(id="arazzo-id")], open_api=[]),
        )
    }
    fake_files_response.operations = None
    mock_api_hub_client.get_execution_files = AsyncMock(return_value=fake_files_response)

    # Patch AuthProcessor.get_security_requirements_for_workflow to return a known structure
    fake_security_option = MagicMock()
    fake_security_option.requirements = [
        MagicMock(model_dump=MagicMock(return_value={"scheme_name": "BotToken", "scopes": []})),
        MagicMock(
            model_dump=MagicMock(return_value={"scheme_name": "OAuth2", "scopes": ["identify"]})
        ),
    ]
    fake_security_requirements = {"openapi.json": [fake_security_option]}

    with (
        patch("jentic.agent_runtime.config.AuthProcessor") as MockAuthProcessor,
        patch.object(
            JenticConfig,
            "_extract_workflow_details",
            return_value={"friendly-id": {"name": "Test Workflow"}},
        ),
    ):
        # Patch get_security_requirements_for_workflow on the *class*, not the instance
        MockAuthProcessor.get_security_requirements_for_workflow.return_value = (
            fake_security_requirements
        )

        config = await JenticConfig.generate_config_from_uuids(
            mock_api_hub_client, [workflow_uuid], []
        )

    # Check the per-workflow security_requirements
    assert "workflows" in config
    assert "friendly-id" in config["workflows"]
    workflow = config["workflows"]["friendly-id"]
    assert "security_requirements" in workflow
    assert workflow["security_requirements"] == {
        "openapi.json": [
            {"scheme_name": "BotToken", "scopes": []},
            {"scheme_name": "OAuth2", "scopes": ["identify"]},
        ]
    }


def test_extract_operations_and_get_operations():
    """Test _extract_operations and get_operations methods of JenticConfig."""
    import json
    import os
    import tempfile

    from jentic.agent_runtime.config import JenticConfig

    # Case 1: config with operations
    config_with_ops = {"operations": {"op1": {"desc": "Operation 1"}}, "workflows": {}}
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        json.dump(config_with_ops, f)
        f.flush()
        cfg_path = f.name
    try:
        jc = JenticConfig(cfg_path)
        assert jc.get_operations() == {"op1": {"desc": "Operation 1"}}
    finally:
        os.remove(cfg_path)

    # Case 2: config without operations
    config_without_ops = {"workflows": {}}
    with tempfile.NamedTemporaryFile("w", delete=False) as f:
        json.dump(config_without_ops, f)
        f.flush()
        cfg_path = f.name
    try:
        jc = JenticConfig(cfg_path)
        assert jc.get_operations() == {}  # Should be empty
    finally:
        os.remove(cfg_path)
