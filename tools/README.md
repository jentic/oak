# Jentic Tools

This directory contains various utilities and libraries supporting the Jentic ecosystem and the Open Agentic Knowledge (OAK) initiative.

## Jentic MCP Plugin (`jentic-mcp`)

The Jentic MCP Plugin integrates with development environments using the Model Context Protocol (MCP). It allows agents and developers to discover external APIs and workflows based on capability descriptions and generate integration code, streamlining the process of connecting applications to external services. Key tools provided include `search_apis`, `get_execution_configuration`, and `generate_code_sample`.

## Jentic SDK (`jentic-sdk`)

The Jentic SDK is a Python library designed for the discovery and execution of APIs and workflows, primarily leveraging data from the OAK repository. It facilitates the creation of agentic applications by generating LLM-compatible tool definitions (e.g., for Anthropic or OpenAI models) and providing a runtime environment (`agent_runtime`) to execute these tools, simplifying interaction with the Jentic API Knowledge Hub.

## OAK Runner (`oak-runner`)

OAK Runner is a Python-based workflow execution engine. It interprets and runs API workflows defined using the Arazzo specification and can also execute individual API operations defined in OpenAPI documents. It handles authentication based on environment variables, manages sequential or conditional step execution, and provides both a Python API and command-line interface for interacting with workflows and operations.
