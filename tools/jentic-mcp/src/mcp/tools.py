"""Tool definitions for the Jentic MCP Plugin.

This module defines the tools available through the Model Configuration Protocol (MCP).
The tools follow a specific workflow for API integration:

1. SEARCH: Use search_apis to find relevant APIs based on the developer's needs. ALWAYS keep track of 'api_id's and 'workflow_id's in search results.
2. VERIFY: Confirm with the developer which APIs and workflows they want to use.
3. GENERATE: Only when ready and with developer permission, use get_execution_configuration to create
   configuration and documentation files for the selected APIs and workflows.
4. CODE SAMPLE [Optional]: Generate a code sample to quickly allow a coding agent to integrate a codebase with Jentic tools. The sample code will never include any API specific code and you will not need to implement any API specific code. You will NOT need to implement API specific environment variable logic for auth. Make as few changes as possible to integrate the sample code with the codebase.

Note: Authentication configuration is handled manually after configuration generation, not through these tools.

Always maintain this workflow order and get explicit permission before generating configuration.
Always show the user the steps you are taking.
"""

from typing import Any

# Tool definitions based on the MCP_agent_prompt.md specification
SEARCH_API_CAPABILITIES_TOOL = {
    "name": "search_apis",
    "description": "Search for API and workflow capabilities that match specific requirements. Always use this tool FIRST when a developer needs to find or work with external APIs or services. The results from this search will help build a configuration for generating integration code. Once you find relevant APIs, recommend creating a configuration file to proceed with the integration.",
    "parameters": {
        "type": "object",
        "properties": {
            "capability_description": {
                "type": "string",
                "description": "Natural language description of the API capabilities needed (e.g., 'send emails', 'weather forecasting', 'natural language processing')",
            },
            "keywords": {
                "type": "array",
                "description": "Optional list of specific keywords to help narrow down the search",
                "items": {"type": "string"},
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of API capabilities to return",
                "default": 5,
            },
        },
        "required": ["capability_description"],
    },
}

LOAD_CONFIG_TOOL = {
    "name": "get_execution_configuration",
    "description": "Load a configuration based on the user's chosen API IDs and Workflow IDs. This JSON configuration the information needed for all APIs, workflows, and settings. ALWAYS ask the user if they would like to write this configuration to the root of their project, in a file called jentic.json, so that it can be used in their AI agent. NEVER modify the content of the output of this tool.",
    "parameters": {
        "type": "object",
        "properties": {
            "workflow_uuids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The UUIDs of the workflows to include in the configuration files.",
            },
            "operation_uuids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The UUIDs of the operations to include in the configuration files.",
            },
        },
        "required": ["workflow_uuids", "operation_uuids"],
    },
}

CODE_SAMPLE_TOOL = {
    "name": "generate_code_sample",
    "description": "Generate a code sample for using the Jentic agent runtime with a specific AI model format and programming language. Provides templates for integrating Jentic tools with various AI models without writing API specific code. The sample code will never include any API specific code and you will not need to implement any API specific code. You will NOT need to implement API specific environment variable logic for auth. Make as few changes as possible to integrate the sample code with the codebase.",
    "parameters": {
        "type": "object",
        "properties": {
            "format": {
                "type": "string",
                "description": "The AI model format to use (e.g., 'claude', 'chatgpt')",
            },
            "language": {
                "type": "string",
                "description": "The programming language for the code sample (e.g., 'python')",
            },
        },
        "required": ["format", "language"],
    },
}

# Tool definitions complete


def get_all_tool_definitions() -> list[dict[str, Any]]:
    """Get all tool definitions for the Jentic MCP Plugin.

    Returns:
        List[Dict[str, Any]]: All tool definitions.
    """
    return [
        SEARCH_API_CAPABILITIES_TOOL,
        LOAD_CONFIG_TOOL,
        CODE_SAMPLE_TOOL,
    ]
