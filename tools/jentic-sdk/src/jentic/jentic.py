from typing import Any, Dict, List, Optional

from jentic.agent_runtime.agent_tools import AgentToolManager
from jentic.agent_runtime.config import JenticConfig
from jentic.agent_runtime.tool_execution import TaskExecutor, WorkflowResult
from jentic.api.api_hub import JenticAPIClient
from jentic.models import ApiCapabilitySearchRequest, APISearchResults


class Jentic:
    """Main class for Jentic.

    This class provides the primary interface for interacting with the Jentic SDK.
    It allows users to search for API capabilities and execute operations or workflows.
    It can also generate tool definitions for agent tools and execute those tools.

    """

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        """
        Initialize the Jentic agent runtime.

        Args:
            base_url (str | None): Optional base URL for the API hub.
            api_key (str | None): Optional API key for authentication.
        """
        self._agent_tool_manager: AgentToolManager | None = None
        self._api_hub_client = JenticAPIClient(base_url=base_url, api_key=api_key)
        self._task_executor = TaskExecutor(self._api_hub_client)

    async def search_api_capabilities(
        self, request: ApiCapabilitySearchRequest
    ) -> APISearchResults:
        """
        Search for API capabilities using the API client.

        Args:
            request (ApiCapabilitySearchRequest): The search request parameters.
        Returns:
            APISearchResults: The results of the API capability search.
        """
        return await self._api_hub_client.search_api_capabilities(request)

    def generate_llm_tool_definitions(
        self, format: str, config_path: Optional[str] = "./jentic.json"
    ) -> List[Dict[str, Any]]:
        """
        Generate tool definitions for the agent based on the specified format and configuration.

        Args:
            format (str): The format to generate tool definitions for (e.g., 'anthropic', 'openai').
            config_path (Optional[str]): Path to the configuration file. Defaults to './jentic.json'.
        Returns:
            List[Dict[str, Any]]: A list of tool definitions.
        """
        if not format:
            raise ValueError("format must be specified. E.g. 'anthropic' or 'openai'.")
        self._agent_tool_manager = AgentToolManager(config_path, format)
        return self._agent_tool_manager.generate_tool_definitions()

    async def run_llm_tool(self, tool_name: str, inputs: dict = {}):
        """
        Run a specific tool by name with the given parameters.

        Args:
            tool_name (str): The name of the tool to execute.
            inputs (dict, optional): Parameters for the tool execution.
        Returns:
            dict: The result of the tool execution, including success status and any errors.
        """
        if self._agent_tool_manager is None:
            return {
                "success": False,
                "error": "No tools found. Call generate_llm_tool_definitions first.",
            }
        return await self._agent_tool_manager.execute_tool(tool_name=tool_name, inputs=inputs)

    async def get_execution_configuration(
        self, workflow_uuids: Optional[List[str]], operation_uuids: Optional[List[str]]
    ):
        """
        Get the execution configuration for the specified workflow and operation UUIDs.
        This configuration is used to understand expected inputs and outputs for the specified tasks.

        Args:
            workflow_uuids (Optional[List[str]]): List of workflow UUIDs.
            operation_uuids (Optional[List[str]]): List of operation UUIDs.
        Returns:
            dict: The generated execution configuration.
        """
        return await JenticConfig.generate_config_from_uuids(
            workflow_uuids=workflow_uuids,
            operation_uuids=operation_uuids,
            api_hub_client=self._api_hub_client,
        )

    async def execute_operation(self, operation_uuid: str, inputs: dict) -> Dict[str, Any]:
        """
        Execute a specific operation by UUID with the provided inputs.

        Args:
            operation_uuid (str): The UUID of the operation to execute.
            inputs (dict): Input parameters for the operation.
        Returns:
            Dict[str, Any]: The result of the operation execution.
        """
        return await self._task_executor.execute_operation(operation_uuid, inputs)

    async def execute_workflow(self, workflow_uuid: str, inputs: dict) -> WorkflowResult:
        """
        Execute a workflow by UUID with the provided inputs.

        Args:
            workflow_uuid (str): The UUID of the workflow to execute.
            inputs (dict): Input parameters for the workflow.
        Returns:
            WorkflowResult: The result of the workflow execution.
        """
        return await self._task_executor.execute_workflow(workflow_uuid, inputs)
