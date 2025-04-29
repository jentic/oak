from typing import Any, Dict, List, Optional

import pytest
from pydantic import BaseModel

from jentic.api.api_hub import JenticAPIClient

# Assuming models are accessible via the path below
# Split imports to potentially resolve import errors
from jentic.models import AssociatedFiles, FileEntry, FileId, WorkflowEntry


# Minimal mock models for testing
class MockAssociatedFiles(AssociatedFiles):
    arazzo: List[FileId] = []  # Use FileId
    open_api: List[FileId] = []  # Use FileId


class MockFileEntry(FileEntry):
    pass


class MockWorkflowEntry(WorkflowEntry):
    # Override fields that expect complex types if not needed directly
    api_references: List[Any] = []  # Keep it simple for this test
    files: MockAssociatedFiles = MockAssociatedFiles()  # Use updated mock with defaults


@pytest.fixture
def api_client() -> JenticAPIClient:
    """Fixture to create a JenticAPIClient instance for testing."""
    # No need for real URLs or API keys for testing this method
    return JenticAPIClient()


# --- Test Cases --- #


def test_build_source_descriptions_happy_path(api_client):
    """Test the new logic: first Arazzo OpenAPI source maps to first available OpenAPI file."""
    workflow_entry = MockWorkflowEntry(
        workflow_id="wf1",
        workflow_uuid="uuid1",
        name="Test Workflow",
        files=MockAssociatedFiles(open_api=[FileId(id="file1_id"), FileId(id="file2_id")]),
        api_references=[],
    )
    # Content for the first available file (file1_id)
    content1 = {"openapi": "3.0", "info": {"title": "API One - First File"}}
    # Content for the second file (file2_id) - should NOT be used
    content2 = {"openapi": "3.0", "info": {"title": "API Two - Second File"}}
    all_openapi_files = {
        "file1_id": MockFileEntry(
            id="file1_id", type="open_api", filename="./api_one.json", content=content1
        ),
        "file2_id": MockFileEntry(
            id="file2_id", type="open_api", filename="./api_two.yaml", content=content2
        ),
    }
    # First source name - should be used
    first_source_name = "ApiOneSourceFirst"
    # Second source name - should NOT be used
    second_source_name = "ApiTwoSourceSecond"
    arazzo_doc = {
        "sourceDescriptions": [
            {"name": first_source_name, "url": "./specs/api_one.json", "type": "openapi"},
            {"name": second_source_name, "url": "./specs/api_two.yaml", "type": "openapi"},
        ]
    }

    result = api_client._build_source_descriptions(
        workflow_entry=workflow_entry,
        all_openapi_files=all_openapi_files,
        arazzo_doc=arazzo_doc,
    )

    # Should map the *first* name to the *first* file content
    assert len(result) == 1
    assert first_source_name in result
    assert result[first_source_name] == content1
    assert second_source_name not in result  # Verify second name wasn't used


def test_build_source_descriptions_no_arazzo_sources(api_client):
    """Test when Arazzo doc has no sourceDescriptions. Should return empty dict."""
    workflow_entry = MockWorkflowEntry(
        workflow_id="wf1",
        workflow_uuid="uuid1",
        name="Test",
        files=MockAssociatedFiles(open_api=[FileId(id="file1_id")]),
    )
    all_openapi_files = {
        "file1_id": MockFileEntry(id="file1_id", type="open_api", filename="./api.json", content={})
    }
    arazzo_doc = {}  # No sourceDescriptions

    result = api_client._build_source_descriptions(workflow_entry, all_openapi_files, arazzo_doc)
    assert result == {}


def test_build_source_descriptions_empty_arazzo_sources(api_client):
    """Test when Arazzo doc has empty sourceDescriptions list. Should return empty dict."""
    workflow_entry = MockWorkflowEntry(
        workflow_id="wf1",
        workflow_uuid="uuid1",
        name="Test",
        files=MockAssociatedFiles(open_api=[FileId(id="file1_id")]),
    )
    all_openapi_files = {
        "file1_id": MockFileEntry(id="file1_id", type="open_api", filename="./api.json", content={})
    }
    arazzo_doc = {"sourceDescriptions": []}

    result = api_client._build_source_descriptions(workflow_entry, all_openapi_files, arazzo_doc)
    assert result == {}


def test_build_source_descriptions_missing_file_in_response(api_client):
    """Test when the first referenced OpenAPI file ID is not in the response files.
    Should use the content of the *next* available referenced file.
    """
    # Workflow references 'missing_id' first, then 'file2_id'
    workflow_entry = MockWorkflowEntry(
        workflow_id="wf1",
        workflow_uuid="uuid1",
        name="Test",
        files=MockAssociatedFiles(open_api=[FileId(id="missing_id"), FileId(id="file2_id")]),
    )
    # Only the second file's content is available in the response
    content2 = {"info": "API Two - Content"}
    all_openapi_files = {
        "file2_id": MockFileEntry(
            id="file2_id", type="open_api", filename="./api_two.json", content=content2
        )
        # 'missing_id' is not present here
    }
    # Arazzo still defines a source name
    arazzo_source_name = "ApiSource"
    arazzo_doc = {
        "sourceDescriptions": [
            {"name": arazzo_source_name, "type": "openapi"}  # No URL needed for new logic
        ]
    }

    result = api_client._build_source_descriptions(
        workflow_entry=workflow_entry,
        all_openapi_files=all_openapi_files,
        arazzo_doc=arazzo_doc,
    )

    # Should map the first (and only) Arazzo name to the content of the *second* (first available) file
    assert len(result) == 1
    assert arazzo_source_name in result
    assert result[arazzo_source_name] == content2
