"""Workflow scanner for the Jentic ARK² MCP Plugin."""

from pathlib import Path
from typing import Any

import yaml


class WorkflowScanner:
    """Scanner for Arazzo workflow fixtures."""

    def __init__(self, fixtures_directory: str = None):
        """Initialize the workflow scanner.

        Args:
            fixtures_directory: Directory containing Arazzo workflow fixtures.
                                If None, will attempt to locate fixtures automatically.
        """
        if fixtures_directory is None:
            # Try to find the fixtures automatically
            # Check common fixture paths after the refactoring
            potential_paths = [
                # Path in jentic-runtime package
                Path("../jentic-runtime/tests/arazzo_runner/fixtures"),
                # Original path
                Path("src/tests/arazzo_runner/fixtures"),
                # Path relative to project root
                Path("tests/arazzo_runner/fixtures"),
                # Path in the same project
                Path("tests/fixtures"),
            ]

            for path in potential_paths:
                if path.exists() and path.is_dir():
                    fixtures_directory = str(path)
                    break

            if fixtures_directory is None:
                # Default to a path that doesn't exist but won't crash
                fixtures_directory = "tests/fixtures"
                print(
                    f"Warning: Could not find fixtures directory. Using default: {fixtures_directory}"
                )

        self.fixtures_directory = Path(fixtures_directory)
        print(f"Workflow scanner using fixtures from: {self.fixtures_directory.absolute()}")

    def scan_workflow_fixtures(self) -> dict[str, list[dict[str, Any]]]:
        """Scan Arazzo workflow fixtures to build a cache of workflow metadata.

        Returns:
            Dictionary mapping API IDs to lists of workflow summaries
        """
        result: dict[str, list[dict[str, Any]]] = {}

        # Scan fixture directories for Arazzo YAML files
        for fixture_dir in self.fixtures_directory.glob("*/"):
            if not fixture_dir.is_dir():
                continue

            # Look for Arazzo definition files
            arazzo_files = list(fixture_dir.glob("*.arazzo.yaml"))
            if not arazzo_files:
                continue

            for arazzo_file in arazzo_files:
                try:
                    with open(arazzo_file) as f:
                        arazzo_def = yaml.safe_load(f)

                    # Determine the API ID using the fixture directory name
                    fixture_name = fixture_dir.name.lower()

                    # Properly identify common APIs by their names
                    api_id = None
                    if "spotify" in fixture_name:
                        api_id = "spotify-v1"
                    elif "discord" in fixture_name:
                        api_id = "discord-v1"
                    elif "xkcd" in fixture_name:
                        api_id = "xkcd-v1"
                    else:
                        # Default API ID format
                        api_id = f"{fixture_name}-v1"

                    # Extract API info from source descriptions
                    source_apis = {}
                    if "sourceDescriptions" in arazzo_def:
                        for source in arazzo_def.get("sourceDescriptions", []):
                            source_name = source.get("name", "")

                            # Map known source names to proper API IDs
                            if "spotify" in source_name.lower():
                                source_apis[source_name] = "spotify-v1"
                            elif "discord" in source_name.lower():
                                source_apis[source_name] = "discord-v1"
                            elif "xkcd" in source_name.lower():
                                source_apis[source_name] = "xkcd-v1"
                            else:
                                source_apis[source_name] = api_id

                    # Extract workflow information
                    api_info = arazzo_def.get("info", {})
                    api_title = api_info.get("title", "Unknown API")

                    # Process workflows
                    for workflow in arazzo_def.get("workflows", []):
                        workflow_id = workflow.get("workflowId", "unknown")
                        summary = workflow.get("summary", "")
                        description = workflow.get("description", "")

                        # Determine the source API for this workflow
                        source_api = "unknown"
                        workflow_api_id = api_id  # Default to the file's API ID

                        # Look for operationPath or operationId to determine the source API
                        for step in workflow.get("steps", []):
                            operation_path = step.get("operationPath", "")
                            if operation_path:
                                # Format: sourceApi#/path/to/operation
                                parts = operation_path.split("#", 1)
                                if len(parts) > 0:
                                    source_api = parts[0]
                                    if source_api in source_apis:
                                        workflow_api_id = source_apis[source_api]
                                        break

                            # Also check operationId for API identification
                            operation_id = step.get("operationId", "")
                            if operation_id and not operation_path:
                                if (
                                    "spotify" in operation_id.lower()
                                    or "track" in operation_id.lower()
                                ):
                                    workflow_api_id = "spotify-v1"
                                    source_api = "spotifyApi"
                                    break
                                elif (
                                    "discord" in operation_id.lower()
                                    or "message" in operation_id.lower()
                                    or "channel" in operation_id.lower()
                                ):
                                    workflow_api_id = "discord-v1"
                                    source_api = "discordApi"
                                    break
                                elif (
                                    "xkcd" in operation_id.lower()
                                    or "comic" in operation_id.lower()
                                ):
                                    workflow_api_id = "xkcd-v1"
                                    source_api = "xkcdApi"
                                    break

                        # Try to infer API from workflow ID and descriptions if still unknown
                        if workflow_api_id == "unknown":
                            if (
                                "spotify" in workflow_id.lower()
                                or "track" in workflow_id.lower()
                                or "music" in description.lower()
                            ):
                                workflow_api_id = "spotify-v1"
                                source_api = "spotifyApi"
                            elif (
                                "discord" in workflow_id.lower()
                                or "message" in workflow_id.lower()
                                or "guild" in workflow_id.lower()
                            ):
                                workflow_api_id = "discord-v1"
                                source_api = "discordApi"
                            elif "xkcd" in workflow_id.lower() or "comic" in workflow_id.lower():
                                workflow_api_id = "xkcd-v1"
                                source_api = "xkcdApi"

                        # Create workflow summary
                        workflow_summary = {
                            "workflow_id": workflow_id,
                            "summary": summary,
                            "description": description,
                            "source_api": source_api,
                            "api_id": workflow_api_id,
                            "match_score": 0.0,
                        }

                        # Add to result dictionary
                        if workflow_api_id not in result:
                            result[workflow_api_id] = []
                        result[workflow_api_id].append(workflow_summary)

                except Exception as e:
                    print(f"Error processing Arazzo file {arazzo_file}: {e}")

        return result
