"""Mock providers for the Jentic MCP Plugin."""

import json
import os
from pathlib import Path
from typing import Any

from mcp.config import load_config
from mcp.core.models import ApiCapabilitySearchRequest
from mcp.mock.mock_data_generator import MockDataGenerator
from mcp.mock.search_matcher import SearchMatcher
from mcp.mock.workflow_scanner import WorkflowScanner


class MockAPIHubProvider:
    """Mock provider for the API Hub client."""

    def __init__(self, mock_directory: str = None, fixtures_directory: str = None):
        """Initialize the mock provider.

        Args:
            mock_directory: Directory containing mock response data. If None, will be determined based on environment.
            fixtures_directory: Directory containing Arazzo workflow fixtures. If None, it will be auto-detected.
        """
        # Determine the appropriate directory based on whether we're in a test environment
        if mock_directory is None:
            from mcp.config import is_test_environment

            base_dir = ".test_output" if is_test_environment() else ".jentic"
            mock_directory = os.path.join(os.getcwd(), base_dir, "mock_data")
        self.mock_directory = Path(mock_directory)

        # Initialize helper classes
        self.data_generator = MockDataGenerator()
        self.workflow_scanner = WorkflowScanner(fixtures_directory)
        self.search_matcher = SearchMatcher()

        # Ensure mock data exists
        self.data_generator.ensure_mock_data_exists(mock_directory)

        # Scan and cache workflows
        self.workflow_cache = self.workflow_scanner.scan_workflow_fixtures()

        # Print workflow cache for debugging
        print(f"Loaded workflows for {len(self.workflow_cache)} APIs:")
        for api_id, workflows in self.workflow_cache.items():
            workflow_ids = [w["workflow_id"] for w in workflows]
            print(f"  - {api_id}: {len(workflows)} workflows: {', '.join(workflow_ids)}")

    async def search_api_capabilities(
        self, request: ApiCapabilitySearchRequest
    ) -> list[dict[str, Any]]:
        """Mock implementation of search_api_capabilities.

        Args:
            request: Search request parameters.

        Returns:
            List of matching API capabilities.
        """
        print(f"Search query: '{request.capability_description}', keywords: {request.keywords}")

        search_response_path = self.mock_directory / "search_api_capabilities.json"

        with open(search_response_path) as f:
            mock_data = json.load(f)

        # Enhance APIs with workflows from our cache
        for api_result in mock_data:
            api_id = api_result["api_id"]
            if api_id in self.workflow_cache:
                # Calculate match scores for workflows
                matched_workflows = self.search_matcher.calculate_match_scores(
                    self.workflow_cache[api_id], request.capability_description, request.keywords
                )

                if matched_workflows:
                    api_result["workflows"] = matched_workflows

        # Also look for direct workflow matches that might not be in our canned APIs
        for api_id, workflows in self.workflow_cache.items():
            # Skip APIs that are already in our canned results
            if any(api["api_id"] == api_id for api in mock_data):
                continue

            # Calculate match scores for workflows
            matched_workflows = self.search_matcher.calculate_match_scores(
                workflows, request.capability_description, request.keywords
            )

            # If we have any workflow matches, add the API to results
            if matched_workflows:
                # Construct an API result from the fixture info
                max_score = max(w["match_score"] for w in matched_workflows)

                # Apply API-specific boosting based on query
                max_score = self.search_matcher.boost_api_score(
                    api_id, request.capability_description
                )

                # Adjust the match score based on keyword matches
                if any(kw.lower() in api_id.lower() for kw in (request.keywords or [])):
                    max_score = 0.97  # Make it appear before non-exact matches

                # Get API display details
                api_details = self.search_matcher.get_api_details(api_id)

                new_api_result = {
                    "api_id": api_id,
                    "api_name": f"{api_details['display_name']} API",
                    "api_description": api_details["description"],
                    "version": "1.0",
                    "capability_match_score": max_score,
                    "auth_methods": ["api_key"],
                    "categories": api_details["categories"],
                    "workflows": matched_workflows,
                }

                mock_data.append(new_api_result)

        # Sort by match score
        mock_data.sort(key=lambda x: x["capability_match_score"], reverse=True)

        # Filter results based on max_results
        return mock_data[: request.max_results]

    async def get_api_details(self, request: dict[str, Any]) -> dict[str, Any]:
        """Mock implementation of get_api_details.

        Args:
            request: Dictionary containing API details request parameters:
                - api_ids: List of API IDs to fetch

        Returns:
            Dictionary mapping API IDs to their detailed specifications.
        """
        details_response_path = self.mock_directory / "get_api_details.json"
        api_ids = request["api_ids"]

        with open(details_response_path) as f:
            mock_data = json.load(f)

        # Filter results to only include requested APIs
        filtered_data = {api_id: mock_data.get(api_id, {}) for api_id in api_ids}
        return filtered_data

    def get_mock_runtime(self, project_directory: str) -> dict[str, str]:
        """Get mock runtime code.

        Args:
            project_directory: The current working project directory associated with the agent.

        Returns:
            Dictionary mapping file paths to generated code.
        """
        runtime_response_path = self.mock_directory / "generate_runtime.json"

        with open(runtime_response_path) as f:
            mock_data = json.load(f)

        # Use the project directory in the file paths, if needed
        result = {}
        for file_path, content in mock_data.items():
            # If you need to use project_directory, you can modify paths here
            result[file_path] = content

        return result

    def get_mock_prompt_library(self) -> dict[str, str]:
        """Get mock prompt library.

        Returns:
            Dictionary mapping prompt types to generated prompts.
        """
        prompt_response_path = self.mock_directory / "generate_prompt_library.json"

        with open(prompt_response_path) as f:
            mock_data = json.load(f)

        return mock_data


def get_mock_provider() -> MockAPIHubProvider | None:
    """Get the mock provider if mock mode is enabled.

    Returns:
        MockAPIHubProvider if mock mode is enabled, None otherwise.
    """
    config = load_config()

    if config.mock.enabled:
        return MockAPIHubProvider(mock_directory=config.mock.mock_directory)

    return None
