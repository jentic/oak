"""API Hub client for Jentic Runtime."""

import logging
import os
from typing import Any, Optional

import httpx

from jentic.models import (
    ApiCapabilitySearchRequest,
    APISearchResults,
    FileEntry,
    GetFilesResponse,
    OperationSearchResult,
    WorkflowEntry,
    WorkflowExecutionDetails,
    WorkflowSearchResult,
)

from .api_cache import api_cache

logger = logging.getLogger(__name__)


class JenticAPIClient:
    """Client for interacting with the Jentic API Knowledge Hub."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        """Initialize the API Hub client.

        Args:
            base_url: Base URL for the Jentic API Knowledge Hub.
            api_key: API key for authentication.
        """
        # Set the base URL with default fallback
        self.base_url = base_url or os.environ.get(
            "JENTIC_API_URL", "https://directory-api.qa1.eu-west-1.jenticdev.net"
        )

        self.base_url = self.base_url.rstrip("/")

        # Set the API key
        self.api_key = api_key or os.environ.get("JENTIC_API_KEY", "")

        logger.info(f"Initialized API Hub client with base_url: {self.base_url}")

        # Set up headers
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

    async def get_execution_files(
        self, workflow_ids: list[str] = [], operation_uuids: list[str] = []
    ) -> GetFilesResponse:
        """Retrieve files for execution from the real API."""
        logger.info(
            f"Fetching execution files from API for workflows: {workflow_ids}, operations: {operation_uuids}"
        )
        params = {}
        if workflow_ids:
            params["workflow_uuids"] = ",".join(workflow_ids)
        if operation_uuids:
            params["operation_uuids"] = ",".join(operation_uuids)
        url = f"{self.base_url}/api/v1/files"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                response_model = GetFilesResponse.model_validate(data)
                return response_model
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error fetching execution files: {e.response.status_code} {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Error fetching execution files: {e}")
            raise

    def _build_source_descriptions(
        self,
        workflow_entry: WorkflowEntry,
        all_openapi_files: dict[str, FileEntry],
        arazzo_doc: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """Build the source_descriptions dict mapping Arazzo name to OpenAPI content.

        Assumes a primary OpenAPI source in Arazzo and maps it to the first
        available OpenAPI file content from the API response for the workflow.
        """
        source_descriptions = {}
        arazzo_openapi_source_name = None
        openapi_content = None

        # 1. Find the name of the first Arazzo sourceDescription with type 'openapi'
        try:
            arazzo_sources = arazzo_doc.get("sourceDescriptions", [])
            if not isinstance(arazzo_sources, list):
                logger.warning("Arazzo 'sourceDescriptions' is not a list.")
                arazzo_sources = []

            for source in arazzo_sources:
                if isinstance(source, dict) and source.get("type") == "openapi":
                    name = source.get("name")
                    if name:
                        arazzo_openapi_source_name = name
                        logger.debug(
                            f"Found Arazzo OpenAPI source name: {arazzo_openapi_source_name}"
                        )
                        break  # Use the first one found
                    else:
                        logger.warning(
                            f"Skipping Arazzo OpenAPI sourceDescription missing name: {source}"
                        )

            if not arazzo_openapi_source_name:
                logger.warning(
                    f"No Arazzo sourceDescription with type 'openapi' and a 'name' found for workflow {workflow_entry.workflow_id}"
                )

        except Exception as e:
            logger.error(f"Error parsing Arazzo sourceDescriptions: {e}")

        # 2. Find the content of the first available OpenAPI file associated with the workflow
        if workflow_entry.files.open_api and all_openapi_files:
            for openapi_file_id_obj in workflow_entry.files.open_api:
                openapi_file_id = openapi_file_id_obj.id
                if openapi_file_id in all_openapi_files:
                    openapi_content = all_openapi_files[openapi_file_id].content
                    logger.debug(f"Found OpenAPI content for file ID: {openapi_file_id}")
                    break  # Use the first one found
                else:
                    logger.warning(
                        f"OpenAPI file content not found for ID {openapi_file_id} in workflow {workflow_entry.workflow_id} (referenced but not in main files dict)."
                    )

            if not openapi_content:
                logger.warning(
                    f"No available OpenAPI file content found for workflow {workflow_entry.workflow_id} despite references."
                )
        elif not all_openapi_files:
            logger.warning(
                "No OpenAPI files were provided in the main 'files' dictionary of the response."
            )
        else:
            logger.debug(
                f"Workflow {workflow_entry.workflow_id} does not reference any OpenAPI files."
            )

        # 3. If both name and content were found, create the mapping
        if arazzo_openapi_source_name and openapi_content:
            source_descriptions[arazzo_openapi_source_name] = openapi_content
            logger.info(
                f"Successfully mapped Arazzo source '{arazzo_openapi_source_name}' to OpenAPI content."
            )
        else:
            logger.warning(
                f"Could not create source description mapping for workflow {workflow_entry.workflow_id}. "
                f"Arazzo source name found: {bool(arazzo_openapi_source_name)}, OpenAPI content found: {bool(openapi_content)}"
            )

        return source_descriptions

    async def get_execution_details_for_workflow(
        self, workflow_id: str
    ) -> Optional[WorkflowExecutionDetails]:
        """Fetch Arazzo doc, OpenAPI specs, and internal ID for a single workflow UUID.

        Args:
            workflow_id: The UUID of the workflow.

        Returns:
            The WorkflowExecutionDetails object for the given workflow UUID, or None if not found.
        """
        logger.debug(f"Fetching execution details for workflow UUID: {workflow_id}")

        if not workflow_id:
            return None  # Return None if no ID requested

        try:
            # Call get_execution_files for the requested workflow ID
            exec_files_response: GetFilesResponse = await self.get_execution_files(
                workflow_ids=[workflow_id]
            )

            if workflow_id not in exec_files_response.workflows:
                logger.warning(f"Workflow ID {workflow_id} not found in API response.")
                return None

            workflow_entry = exec_files_response.workflows[workflow_id]

            # Extract Arazzo document content
            if not workflow_entry.files.arazzo:
                logger.warning(
                    f"No Arazzo file reference found for workflow {workflow_id}. Skipping."
                )
                return None
            if len(workflow_entry.files.arazzo) > 1:
                logger.warning(
                    f"Multiple Arazzo file references found for workflow {workflow_id}. Using first."
                )
            arazzo_file_id_obj = workflow_entry.files.arazzo[0]
            arazzo_file_id = arazzo_file_id_obj.id
            arazzo_files_dict = exec_files_response.files.get("arazzo")
            if not arazzo_files_dict or arazzo_file_id not in arazzo_files_dict:
                logger.warning(
                    f"Arazzo file content not found for ID {arazzo_file_id} in workflow {workflow_id}. Skipping."
                )
                return None
            arazzo_doc = arazzo_files_dict[arazzo_file_id].content

            # Build source_descriptions using the helper method
            source_descriptions = self._build_source_descriptions(
                workflow_entry=workflow_entry,
                all_openapi_files=exec_files_response.files.get("open_api", {}),
                arazzo_doc=arazzo_doc,
            )

            # Store the details in the results dictionary
            return WorkflowExecutionDetails(
                arazzo_doc=arazzo_doc,
                source_descriptions=source_descriptions,
                friendly_workflow_id=workflow_entry.workflow_id,  # Use the workflow_id from the entry
            )
        except Exception as e:
            logger.error(f"Failed to fetch execution details for workflow {workflow_id}: {e}")
            return None

    async def search_api_capabilities(
        self, request: ApiCapabilitySearchRequest
    ) -> APISearchResults:
        """Search for API capabilities that match specific requirements.

        Args:
            request: Search request parameters.

        Returns:
            SearchResults object containing matching APIs, workflows, and operations.
        """

        # Real API call - using new search server API
        # Use the unified search endpoint to get a comprehensive view
        logger.info(
            f"Searching for API capabilities using unified search: {request.capability_description}"
        )
        search_results = await self._search_all(request)

        # Parse API, workflow, and operation results from search_results
        workflow_summaries: list[WorkflowSearchResult] = []
        for wf in search_results.get("workflows", []):
            try:
                workflow_summaries.append(
                    WorkflowSearchResult(
                        workflow_id=wf.get("id", ""),
                        summary=wf.get("name", wf.get("workflow_id", "")),
                        description=wf.get("description", ""),
                        match_score=wf.get("distance", 0.0),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse workflow summary: {e}")
        logger.info(
            f"Found {len(workflow_summaries)} workflows matching '{request.capability_description}'"
        )

        operation_summaries: list[OperationSearchResult] = []
        for op in search_results.get("operations", []):
            try:
                operation_summaries.append(
                    OperationSearchResult(
                        operation_uuid=op.get("id", ""),
                        summary=op.get("summary", ""),
                        description=op.get("description", ""),
                        path=op.get("path", ""),
                        method=op.get("method", ""),
                        match_score=op.get("distance", 0.0),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse operation summary: {e}")
        logger.info(
            f"Found {len(operation_summaries)} operations matching '{request.capability_description}'"
        )

        # Return as a SearchResults object for high-level structure
        return APISearchResults(workflows=workflow_summaries, operations=operation_summaries)

    async def _search_all(self, request: ApiCapabilitySearchRequest) -> dict[str, Any]:
        """Search across all entity types for the capability description.

        Args:
            request: The capability search request.

        Returns:
            Search response with all entity types.
        """
        # Prepare the search request for the all endpoint
        search_request = {
            "query": request.capability_description,
            "limit": request.max_results
            * 2,  # Get more results to ensure we have enough after filtering
            "entity_types": ["api", "workflow", "operation"],
        }

        if request.keywords:
            # Add keywords to the query
            keyword_str = " ".join(request.keywords)
            search_request["query"] = f"{search_request['query']} {keyword_str}"

        logger.info(f"Searching all entities with query: {search_request['query']}")

        # Log the URL we're connecting to for debugging
        search_url = f"{self.base_url}/api/v1/search/all"
        logger.info(f"Connecting to search URL: {search_url}")

        # Make the search request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                search_url,
                json=search_request,
                headers=self.headers,
            )
            response.raise_for_status()

            search_response = response.json()
            api_count = len(search_response.get("apis", []))
            workflow_count = len(search_response.get("workflows", []))
            operation_count = len(search_response.get("operations", []))

            logger.info(
                f"Found {api_count} APIs, {workflow_count} workflows, {operation_count} operations"
            )

            return search_response

    async def _search_workflows(self, request: ApiCapabilitySearchRequest) -> list[dict[str, Any]]:
        """Search for workflows that match the capability description.

        Args:
            request: The capability search request.

        Returns:
            List of workflow search results.
        """
        # Prepare the search request for the workflows endpoint
        search_request = {
            "query": request.capability_description,
            "limit": request.max_results
            * 2,  # Get more workflows to ensure we have enough after grouping
        }

        if request.keywords:
            # Add keywords to the query
            keyword_str = " ".join(request.keywords)
            search_request["query"] = f"{search_request['query']} {keyword_str}"

        logger.info(f"Searching workflows with query: {search_request['query']}")

        # Make the search request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/search/workflows",
                json=search_request,
                headers=self.headers,
            )
            response.raise_for_status()

            search_response = response.json()
            logger.info(f"Found {len(search_response.get('workflows', []))} workflows")

            return search_response.get("workflows", [])
