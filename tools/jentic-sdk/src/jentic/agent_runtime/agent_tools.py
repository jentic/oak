"""Agent tool manager for integrating Jentic workflows with agent frameworks."""

import logging
from pathlib import Path
from typing import Any

from .config import JenticConfig
from .tool_execution import TaskExecutor
from .tool_specs import LLMToolSpecManager

logger = logging.getLogger(__name__)


class AgentToolManager:
    """Manager for converting Jentic workflows into agent-compatible tools."""

    def __init__(
        self,
        config_path: str = "./jentic.json",
        format: str = "anthropic",
        config_overrides: dict[str, Any] | None = None,
        api_hub_client=None,
    ) -> None:
        """Initialize the agent tool manager.

        Args:
            config_path: Path to the Jentic project
            format: Tool format ("anthropic" or "openai")
            config_overrides: Optional configuration overrides
            api_hub_client: Optional API hub client for TaskExecutor
        """
        self.project = JenticConfig(config_path)
        self.format = format.lower()
        self.config_overrides = config_overrides or {}

        # Create combined configuration
        self.config = self._create_config()

        # Setup tool specification manager
        self.tool_spec_manager = LLMToolSpecManager()
        self.tool_spec_manager.load_from_jentic_config(self.project)

        # Setup tool executor
        from jentic.api.api_hub import JenticAPIClient

        self.tool_executor = TaskExecutor(api_hub_client or JenticAPIClient())

    def _create_config(self) -> dict[str, Any]:
        """Create a merged configuration from the project and overrides.

        Returns:
            Merged configuration
        """
        # Start with project config
        config = dict(self.project.config)

        # Apply overrides
        for key, value in self.config_overrides.items():
            if isinstance(value, dict) and key in config and isinstance(config[key], dict):
                # Merge dictionaries
                config[key].update(value)
            else:
                # Replace value
                config[key] = value

        return config

    def generate_tool_definitions(self) -> list[dict[str, Any]]:
        """Get tool definitions for the specified format.

        Returns:
            List of tool definitions
        """
        # Get tool specifications
        specs = self.tool_spec_manager.get_tool_specs(self.format)

        # Return just the tools list
        return specs["tools"]

    async def execute_tool(self, tool_name: str, inputs: dict[str, Any] = None) -> dict[str, Any]:
        """Execute a tool.

        Args:
            tool_name: Name of the tool (workflow or operation) to execute
            inputs: inputs for the tool

        Returns:
            Tool execution result
        """
        if inputs is None:
            inputs = {}

        try:
            # Determine the type of tool
            tool_type = self.tool_spec_manager.get_tool_type(tool_name)

            if tool_type == "workflow":
                logger.info(f"Executing tool '{tool_name}' as a workflow.")
                workflow_uuid = self.tool_spec_manager.get_workflow_uuid(tool_name)
                if not workflow_uuid:
                    # This case should ideally not happen if get_tool_type returned 'workflow'
                    # but adding a fallback check for robustness.
                    logger.error(
                        f"Could not find UUID for workflow tool name {tool_name} despite type being 'workflow'."
                    )
                    return {
                        "success": False,
                        "error": f"Could not find UUID for workflow tool name {tool_name}",
                    }

                result = await self.tool_executor.execute_workflow(workflow_uuid, inputs)

            elif tool_type == "operation":
                logger.info(f"Executing tool '{tool_name}' as an operation.")
                operation_uuid = self.tool_spec_manager.get_operation_uuid(tool_name)
                if not operation_uuid:
                    return {
                        "success": False,
                        "error": f"Could not find UUID for operation tool name {tool_name}",
                    }

                result = await self.tool_executor.execute_operation(operation_uuid, inputs)

            else:  # tool_type == "unknown"
                logger.error(f"Cannot execute unknown tool type for tool name: {tool_name}")
                return {"success": False, "error": f"Tool '{tool_name}' not found or type unknown."}

            return result  # Assuming both execute methods return compatible dicts
        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
