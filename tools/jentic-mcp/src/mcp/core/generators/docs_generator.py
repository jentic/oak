"""Documentation generator for Jentic MCP Plugin."""

import logging
from typing import Any

# Import the auth parser from jentic-runtime
from mcp.core.api_hub import ApiHubClient
from mcp.core.generators.auth_processor import AuthProcessor

logger = logging.getLogger(__name__)


class DocumentationGenerator:
    """Generates documentation for selected APIs and workflows."""

    def __init__(self, api_spec_cache: dict[str, Any]):
        """Initialize the documentation generator.

        Args:
            api_spec_cache: Cache of API specifications.
        """
        self.api_spec_cache = api_spec_cache

    async def generate_documentation(
        self, config_filename: str, api_ids: list[str], api_hub_client: ApiHubClient
    ) -> str:
        """Generate documentation on how to use the workflows from the config.

        Args:
            config_filename: The name of the config file
            api_ids: List of API IDs included in the configuration
            api_hub_client: Client for the Jentic API Knowledge Hub

        Returns:
            Documentation content as a string
        """
        # Get API details for all requested APIs
        api_details_request = {"api_ids": api_ids}

        # Fetch API details
        api_details = await api_hub_client.get_api_details(api_details_request)

        # Extract API names from the details
        api_names = []
        for api_id in api_ids:
            if api_id in api_details and api_details[api_id]:
                api_name = api_details[api_id].get("name", api_id)
                api_names.append(f"{api_name} ({api_id})")
            else:
                logger.warning(f"API details not found for {api_id}")
                api_names.append(f"Unknown API ({api_id})")

        # Start building the documentation
        docs = []
        docs.append("# Jentic API Integration Guide")
        docs.append("")
        docs.append("## Overview")
        docs.append("")
        docs.append("This guide explains the authentication requirements for the following APIs:")
        docs.append("")
        for api_name in api_names:
            docs.append(f"- {api_name}")
        docs.append("")
        docs.append(f"Configuration file: `{config_filename}`")
        docs.append("")

        # Agent Integration section
        docs.append("## Agent Integration")
        docs.append("")
        docs.append("### Installing the Jentic Runtime Agent Framework")
        docs.append("")
        docs.append("First, install the jentic-runtime package:")
        docs.append("")
        docs.append("```bash")
        docs.append("pip install jentic-runtime")
        docs.append("```")
        docs.append("")
        docs.append("### Using the Jentic Runtime Agent Framework")
        docs.append("")
        docs.append(
            "Jentic provides a runtime library to easily integrate your workflows with AI agent frameworks."
        )
        docs.append(
            "The following examples show how to use the Jentic Runtime with Claude and OpenAI:"
        )
        docs.append("")
        docs.append("```python")
        docs.append("# Claude Agent Example")
        docs.append("import anthropic")
        docs.append("from jentic.agent_runtime.agent_tools import AgentToolManager")
        docs.append("")
        docs.append("# Initialize the tool manager with your project directory")
        docs.append('tool_manager = AgentToolManager("./", format="anthropic")')
        docs.append("")
        docs.append("# Get tool definitions for Claude")
        docs.append("tool_definitions = tool_manager.get_tool_definitions()")
        docs.append("")
        docs.append("# Initialize Claude client")
        docs.append('client = anthropic.Anthropic(api_key="your_api_key")')
        docs.append("")
        docs.append("# Create a conversation with the tools")
        docs.append("response = client.messages.create(")
        docs.append('    model="claude-3-opus-20240229",')
        docs.append("    max_tokens=1024,")
        docs.append("    tools=tool_definitions,")
        docs.append("    messages=[")
        docs.append('        {"role": "user", "content": "Can you help me with these APIs?"}')
        docs.append("    ]")
        docs.append(")")
        docs.append("")
        docs.append("# Handle tool calls")
        docs.append('if response.content[0].type == "tool_calls":')
        docs.append("    for tool_call in response.content[0].tool_calls:")
        docs.append("        result = await tool_manager.execute_tool(")
        docs.append("            tool_call.name,")
        docs.append("            tool_call.parameters")
        docs.append("        )")
        docs.append("        # Send result back to Claude...")
        docs.append("```")
        docs.append("")
        docs.append("```python")
        docs.append("# OpenAI Agent Example")
        docs.append("from openai import AsyncOpenAI")
        docs.append("from jentic.agent_runtime.agent_tools import AgentToolManager")
        docs.append("")
        docs.append("# Initialize the tool manager with your project directory")
        docs.append('tool_manager = AgentToolManager("./", format="openai")')
        docs.append("")
        docs.append("# Get tool definitions for OpenAI")
        docs.append("tool_definitions = tool_manager.get_tool_definitions()")
        docs.append("")
        docs.append("# Initialize OpenAI client")
        docs.append('client = AsyncOpenAI(api_key="your_api_key")')
        docs.append("")
        docs.append("# Create a conversation with the tools")
        docs.append("response = await client.chat.completions.create(")
        docs.append('    model="gpt-4o",')
        docs.append("    tools=tool_definitions,")
        docs.append("    messages=[")
        docs.append('        {"role": "user", "content": "Can you help me with these APIs?"}')
        docs.append("    ]")
        docs.append(")")
        docs.append("")
        docs.append("# Handle tool calls")
        docs.append("if response.choices[0].message.tool_calls:")
        docs.append("    for tool_call in response.choices[0].message.tool_calls:")
        docs.append("        # Parse the JSON arguments")
        docs.append("        import json")
        docs.append("        arguments = json.loads(tool_call.function.arguments)")
        docs.append("        ")
        docs.append("        result = await tool_manager.execute_tool(")
        docs.append("            tool_call.function.name,")
        docs.append("            arguments")
        docs.append("        )")
        docs.append("        # Send result back to OpenAI...")
        docs.append("```")
        docs.append("")
        docs.append(
            "For more advanced integration options, see the full examples in the jentic-runtime package."
        )
        docs.append("")
        docs.append("### For LLM Agent Developers")
        docs.append("")
        docs.append(
            "**Important:** After running the `generate_config` function, your LLM agent should:"
        )
        docs.append("")
        docs.append("1. Parse this `JENTIC.md` file from the project's root directory")
        docs.append(
            "2. Use the instructions herein to coordinate LLM tool specification and execution"
        )
        docs.append("3. Properly handle authentication requirements listed in this file")
        docs.append("4. Set up the AgentToolManager using the provided examples")
        docs.append("5. Execute all external workflows using the Jentic runtime framework")
        docs.append("")
        docs.append(
            "When developing AI agents that will use these Jentic tools, ensure your agent implementation:"
        )
        docs.append("")
        docs.append("- Checks for, reads, and follows the instructions in `JENTIC.md`")
        docs.append("- Leverages the AgentToolManager for proper workflow dependency handling")
        docs.append("- Handles authentication according to the specifications in this document")
        docs.append("- Manages workflow execution state between related API calls")
        docs.append("- Properly propagates authentication tokens between dependent workflows")
        docs.append("")
        docs.append("### Advanced Agent Integration")
        docs.append("")
        docs.append(
            "The Jentic Agent Runtime provides more advanced features for building robust agent applications:"
        )
        docs.append("")
        docs.append("#### Complete Agent Implementation")
        docs.append("")
        docs.append("```python")
        docs.append("# Complete Claude Agent Pattern")
        docs.append("from jentic.agent_runtime.agent_tools import AgentToolManager")
        docs.append("import anthropic")
        docs.append("import asyncio")
        docs.append("import os")
        docs.append("")
        docs.append("class JenticAgent:")
        docs.append("    def __init__(self, project_path):")
        docs.append("        # Initialize with your project")
        docs.append(
            '        self.tool_manager = AgentToolManager(project_path, format="anthropic")'
        )
        docs.append("        self.tools = self.tool_manager.get_tool_definitions()")
        docs.append(
            '        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))'
        )
        docs.append("")
        docs.append("    async def process_message(self, user_message, conversation_history=None):")
        docs.append("        if conversation_history is None:")
        docs.append("            conversation_history = []")
        docs.append("            ")
        docs.append("        # Add the user message")
        docs.append("        messages = conversation_history + [")
        docs.append('            {"role": "user", "content": user_message}')
        docs.append("        ]")
        docs.append("        ")
        docs.append("        # Get initial response")
        docs.append("        response = self.client.messages.create(")
        docs.append('            model="claude-3-opus-20240229",')
        docs.append("            messages=messages,")
        docs.append("            tools=self.tools,")
        docs.append("            max_tokens=1024")
        docs.append("        )")
        docs.append("        ")
        docs.append("        # Handle tool calls recursively until we get a text response")
        docs.append('        while response.content[0].type == "tool_calls":')
        docs.append("            # Add assistant response with tool calls")
        docs.append("            messages.append({")
        docs.append('                "role": "assistant", ')
        docs.append('                "content": response.content')
        docs.append("            })")
        docs.append("            ")
        docs.append("            # Process each tool call")
        docs.append("            tool_results = []")
        docs.append("            for tool_call in response.content[0].tool_calls:")
        docs.append("                # Execute the tool")
        docs.append("                result = await self.tool_manager.execute_tool(")
        docs.append("                    tool_call.name,")
        docs.append("                    tool_call.parameters")
        docs.append("                )")
        docs.append("                ")
        docs.append("                # Add to results")
        docs.append("                tool_results.append({")
        docs.append('                    "tool_call_id": tool_call.id,')
        docs.append('                    "output": result')
        docs.append("                })")
        docs.append("            ")
        docs.append("            # Add tool results to conversation")
        docs.append("            messages.append({")
        docs.append('                "role": "user",')
        docs.append(
            '                "content": [{"type": "tool_result", "tool_results": tool_results}]'
        )
        docs.append("            })")
        docs.append("            ")
        docs.append("            # Get follow-up response")
        docs.append("            response = self.client.messages.create(")
        docs.append('                model="claude-3-opus-20240229",')
        docs.append("                messages=messages,")
        docs.append("                tools=self.tools,")
        docs.append("                max_tokens=1024")
        docs.append("            )")
        docs.append("        ")
        docs.append("        # Return the final text response")
        docs.append("        return response.content[0].text")
        docs.append("```")
        docs.append("")
        docs.append("#### Configuration and Authentication")
        docs.append("")
        docs.append("The `AgentToolManager` handles API authentication automatically:")
        docs.append("")
        docs.append("- Uses environment variables for API credentials")
        docs.append("- Supports OAuth2, API keys, and basic authentication")
        docs.append("- Automatically refreshes tokens when needed")
        docs.append(
            "- Manages workflow dependencies (a workflow that requires an auth token will automatically execute the auth workflow first)"
        )
        docs.append("")
        docs.append("You can provide configuration overrides when initializing the tool manager:")
        docs.append("")
        docs.append("```python")
        docs.append("# Override specific configuration values")
        docs.append("config_overrides = {")
        docs.append('    "api_name": {')
        docs.append('        "base_url": "https://custom-endpoint.example.com"')
        docs.append("    }")
        docs.append("}")
        docs.append('tool_manager = AgentToolManager("./", config_overrides=config_overrides)')
        docs.append("```")
        docs.append("")

        # Authentication section
        docs.append("## Authentication")
        docs.append("")
        docs.append(
            "Set the following environment variables to authenticate with the configured APIs:"
        )
        docs.append("")

        # Create the auth processor for better auth information
        auth_processor = AuthProcessor()

        # Process each API to extract auth requirements
        for api_id in api_ids:
            # Skip if API details not found
            if api_id not in api_details or not api_details[api_id]:
                logger.warning(f"API details not found for {api_id}")
                continue

            api_detail = api_details[api_id]
            api_name = api_detail.get("name", api_id)

            docs.append(f"### {api_name}")
            docs.append("")

            # Process the files to find Arazzo workflow and OpenAPI specs
            if "files" not in api_detail:
                logger.warning(f"No files found in API details for {api_id}")
                docs.append(
                    "API specification not available. Authentication information cannot be displayed."
                )
                docs.append("")
                continue

            # Use ApiHubClient's split_files_by_type method
            try:
                arazzo_doc, openapi_specs = api_hub_client.split_files_by_type(
                    api_detail["files"], api_id
                )

                if not arazzo_doc:
                    logger.warning(f"No Arazzo workflow specification found for API {api_id}")
                    docs.append(
                        "Arazzo workflow specification not available. Authentication information cannot be displayed."
                    )
                    docs.append("")
                    continue

                # Extract Arazzo specs for selected workflows
                arazzo_specs = []
                if arazzo_doc:
                    arazzo_specs.append(arazzo_doc)

                # Use the auth processor for better information
                auth_data = auth_processor.process_api_auth(
                    api_id, list(openapi_specs.values()), arazzo_specs, api_name=api_name
                )

                # Directly show environment variables without the detailed auth sections
                if auth_data["requirements"]:
                    # Just show a simple summary of auth types
                    auth_types = set()
                    for req_dict in auth_data["requirements"]:
                        auth_types.add(req_dict.get("type", "custom"))

                    if auth_types:
                        auth_types_str = ", ".join(auth_types)
                        docs.append(f"Authentication Type: {auth_types_str}")
                        docs.append("")

                    # Add environment variable information, grouped by auth type
                    if "grouped_env_mappings" in auth_data and auth_data["grouped_env_mappings"]:
                        # Use the new grouped format
                        for auth_type, env_vars in auth_data["grouped_env_mappings"].items():
                            if env_vars:  # Skip empty auth types
                                # Format auth type nicely
                                auth_type_display = auth_type.replace("_", " ").title()

                                # Special case for oauth2 types
                                if auth_type == "oauth2_web":
                                    auth_type_display = "OAuth2 (Web Flow)"
                                elif auth_type == "oauth2_client_credentials":
                                    auth_type_display = "OAuth2 (Client Credentials)"
                                elif auth_type == "oauth2_password":
                                    auth_type_display = "OAuth2 (Password Flow)"
                                elif auth_type == "oauth2":
                                    auth_type_display = "OAuth2"
                                elif auth_type == "apikey":
                                    auth_type_display = "API Key"

                                docs.append(f"**{auth_type_display}**")
                                docs.append("")

                                # List environment variables for this auth type
                                for cred_key, env_var in env_vars.items():
                                    docs.append(f"- `{env_var}`: {cred_key}")
                                docs.append("")
                    # Fallback to flat list if grouped mappings not available
                    elif auth_data["env_mappings"]:
                        for cred_key, env_var in auth_data["env_mappings"].items():
                            docs.append(f"- `{env_var}`: {cred_key}")
                        docs.append("")
                    else:
                        docs.append("No specific environment variables identified.")
                        docs.append("")

                    # Add auth workflow information if any
                    if auth_data["auth_workflows"]:
                        docs.append("Authentication Workflows:")
                        docs.append("")

                        for auth_workflow in auth_data["auth_workflows"]:
                            workflow_id = auth_workflow.get("workflow_id", "")
                            token_output = auth_workflow.get("token_output")

                            docs.append(f"- **{workflow_id}**")
                            if token_output:
                                docs.append(f"  - Token output: `{token_output}`")

                        docs.append("")
                else:
                    docs.append("No authentication requirements found in the API specification.")
                    docs.append("")
            except Exception as e:
                logger.error(f"Error processing API specifications for {api_id}: {str(e)}")
                docs.append(
                    "Error processing API specifications. Authentication information cannot be displayed."
                )
                docs.append("")
                continue

        return "\n".join(docs)
