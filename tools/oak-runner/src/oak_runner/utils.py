#!/usr/bin/env python3
"""
Utility functions for OAK Runner

This module provides utility functions for the OAK Runner.
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional, List
import jsonpointer
import yaml

from .models import ServerConfiguration, ServerVariable

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("arazzo-runner")


def load_arazzo_doc(arazzo_path: str) -> dict:
    """
    Load and parse the Arazzo document

    Args:
        arazzo_path: Path to the Arazzo document

    Returns:
        arazzo_doc: Parsed Arazzo document
    """
    with open(arazzo_path) as f:
        content = f.read()
        if arazzo_path.endswith((".yaml", ".yml")):
            return yaml.safe_load(content)
        else:
            return json.loads(content)


def load_source_descriptions(arazzo_doc: dict, arazzo_path: str, base_path: str, http_client) -> dict[str, Any]:
    """
    Load referenced OpenAPI descriptions

    Args:
        arazzo_doc: Parsed Arazzo document
        base_path: Base path for resolving relative paths
        http_client: HTTP client to use for loading remote sources

    Returns:
        source_descriptions: Dictionary of loaded source descriptions
    """
    source_descriptions = {}
    source_descriptions_list = arazzo_doc.get("sourceDescriptions", [])

    for source in source_descriptions_list:
        source_name = source.get("name")
        source_url = source.get("url")
        source_type = source.get("type", "openapi")

        if not source_name or not source_url:
            continue

        # Handle local file references
        if not (source_url.startswith("http://") or source_url.startswith("https://")):
            # Try four approaches to finding the file path
            candidate_paths = []
            # 1. If base_path exists, use it
            if base_path:
                candidate_paths.append(os.path.join(base_path, source_url))
            # 2. Try using a path relative to the arazzo_path if available
            if arazzo_path:
                arazzo_dir = os.path.dirname(os.path.abspath(arazzo_path))
                candidate_paths.append(os.path.join(arazzo_dir, source_url))
            # 3. Try using a path relative to the current path
            current_path = os.path.abspath(os.getcwd())
            candidate_paths.append(os.path.join(current_path, source_url))
            # 4. If current path contains '/tools/oak-runner', set base_path up 2 levels
            if "/tools/oak-runner" in current_path:
                base_path_2up = os.path.abspath(os.path.join(current_path, "../.."))
                candidate_paths.append(os.path.join(base_path_2up, source_url))
            # Try each candidate path
            source_path = None
            for path in candidate_paths:
                if os.path.exists(path):
                    source_path = path
                    break
            if not source_path:
                raise FileNotFoundError(f"Could not find source file for {source_name} using any known base path candidates: {candidate_paths}")
            try:
                with open(source_path) as f:
                    content = f.read()
                    if source_path.endswith((".yaml", ".yml")):
                        source_descriptions[source_name] = yaml.safe_load(content)
                    else:
                        source_descriptions[source_name] = json.loads(content)
            except (FileNotFoundError, json.JSONDecodeError, yaml.YAMLError) as e:
                logger.error(f"Error loading source description {source_name}: {e}")
        else:
            # Handle remote URLs
            try:
                response = http_client.get(source_url)
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")

                if "yaml" in content_type or "yml" in content_type:
                    source_descriptions[source_name] = yaml.safe_load(response.text)
                else:
                    source_descriptions[source_name] = response.json()
            except Exception as e:
                logger.error(f"Error loading remote source description {source_name}: {e}")

    return source_descriptions


def dump_state(state, label: str = "Current Execution State"):
    """
    Helper method to dump the current state for debugging

    Args:
        state: Execution state to dump
        label: Optional label for the state dump
    """
    logger.debug(f"=== {label} ===")
    logger.debug(f"Workflow ID: {state.workflow_id}")
    logger.debug(f"Current Step ID: {state.current_step_id}")
    logger.debug(f"Inputs: {state.inputs}")
    logger.debug("Step Outputs:")
    for step_id, outputs in state.step_outputs.items():
        logger.debug(f"  {step_id}: {outputs}")
    logger.debug(f"Workflow Outputs: {state.workflow_outputs}")
    logger.debug(f"Status: {state.status}")


def evaluate_json_pointer(data: dict, pointer_path: str) -> Any | None:
    """
    Evaluate a JSON pointer against the provided data.

    Args:
        data: The data to evaluate the pointer against
        pointer_path: The JSON pointer path (e.g., "/products/0/name")

    Returns:
        The resolved value or None if the pointer cannot be resolved
    """
    try:
        if not pointer_path:
            return data

        # For root pointer, return the entire data
        if pointer_path == "/":
            return data

        # Create a JSON pointer resolver
        pointer = jsonpointer.JsonPointer(pointer_path)
        result = pointer.resolve(data)
        return result
    except (jsonpointer.JsonPointerException, TypeError) as e:
        logger.debug(f"Error resolving JSON pointer {pointer_path}: {e}")
        return None


def extract_json_pointer_from_expression(expression: str) -> tuple[str | None, str | None]:
    """
    Extract JSON pointer from an expression like $response.body#/path/to/value

    Args:
        expression: The expression containing a JSON pointer

    Returns:
        A tuple of (container_path, pointer_path) or (None, None) if not a valid pointer expression
    """
    if not isinstance(expression, str):
        return (None, None)

    # Handle the form $response.body#/path/to/value
    match = re.match(r"^\$([a-zA-Z0-9_.]+)#(/.*)", expression)
    if match:
        container_path, pointer_path = match.groups()
        return (container_path, pointer_path)

    # Handle expressions like $response.body.path.to.value by converting to JSON pointer
    # This supports workflows that don't explicitly use # JSON pointer syntax
    match = re.match(r"^\$([a-zA-Z0-9_]+)\.([a-zA-Z0-9_.]+)", expression)
    if match and "#" not in expression:
        container, path = match.groups()
        # Convert dot notation to JSON pointer format
        pointer_path = "/" + path.replace(".", "/")
        return (container, pointer_path)

    # Handle the standard form $response.body#/path
    match = re.match(r"^\$([a-zA-Z0-9_.]+)\.([a-zA-Z0-9_]+)#(/.*)", expression)
    if match:
        container, property_name, pointer_path = match.groups()
        return (f"{container}.{property_name}", pointer_path)

    return (None, None)


def load_openapi_file(openapi_path: str) -> dict[str, Any]:
    """Loads a single OpenAPI specification from a local file path.

    Args:
        openapi_path: The local file path of the OpenAPI specification.

    Returns:
        The parsed OpenAPI specification as a dictionary.

    Raises:
        ValueError: If the file cannot be parsed.
        FileNotFoundError: If the local file does not exist.
    """
    logger.debug(f"Loading OpenAPI specification from local path: {openapi_path}")

    try:
        if not os.path.isfile(openapi_path):
            raise FileNotFoundError(f"OpenAPI file not found: {openapi_path}")
        
        with open(openapi_path, 'r') as f:
            content = f.read()

        # Try parsing as YAML, then JSON
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError:
            try:
                return json.loads(content)
            except json.JSONDecodeError as json_err:
                logger.error(f"Failed to parse OpenAPI spec as YAML or JSON from {openapi_path}: {json_err}")
                raise ValueError(f"Failed to parse OpenAPI spec from {openapi_path}") from json_err

    except FileNotFoundError:
        logger.error(f"OpenAPI file not found: {openapi_path}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading OpenAPI spec from {openapi_path}: {e}")
        raise ValueError(f"Could not load OpenAPI spec from {openapi_path}") from e


def set_log_level(level: str):
    """
    Set the log level

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")
    logger.setLevel(numeric_level)

    # Also set for submodules
    logging.getLogger("arazzo-runner.evaluator").setLevel(numeric_level)
    logging.getLogger("arazzo-runner.executor").setLevel(numeric_level)
    logging.getLogger("arazzo-runner.http").setLevel(numeric_level)


def resolve_server_base_url(server_config: ServerConfiguration, runtime_params: Optional[Dict[str, str]] = None) -> str:
    """
    Resolves the templated server URL using provided parameters, environment variables,
    or default values for a given ServerConfiguration.

    Args:
        server_config: The ServerConfiguration object.
        runtime_params: A dictionary of runtime parameters to substitute.

    Returns:
        The resolved server base URL as a string.

    Raises:
        ValueError: If a required variable in the template cannot be resolved.
    """
    resolved_url = server_config.url_template
    if runtime_params is None:
        runtime_params = {}

    # Find all variable placeholders like {var_name} in the URL template
    template_vars_in_url = set(re.findall(r"{(.*?)}", server_config.url_template))

    for var_name in template_vars_in_url:
        server_var_details = server_config.variables.get(var_name)

        if not server_var_details:
            # This implies a mismatch: a variable placeholder in the URL template
            # does not have a corresponding definition in the 'variables' section.
            # OpenAPI spec dictates that all variables in the URL template MUST be defined.
            raise ValueError(
                f"Variable '{var_name}' in URL template '{server_config.url_template}' has no corresponding "
                f"definition in server variables. This may indicate an invalid OpenAPI document."
            )

        resolved_value: Optional[str] = None

        if resolved_value is None:
            env_var_name_base = f"OAK_SERVER_{var_name.upper()}"
            env_var_name = (
                f"{server_config.api_title_prefix}_{env_var_name_base}"
                if server_config.api_title_prefix
                else env_var_name_base
            )
            env_var_name = re.sub(r'[^A-Z0-9_]+', '_', env_var_name)
            
             # 1. Use value from runtime_params if provided
            env_value = runtime_params.get(env_var_name)

            # 2. Else, try to use value from environment variable
            if not env_value:
                env_value = os.getenv(env_var_name)
                
            if env_value is not None:
                resolved_value = env_value
                logger.debug(f"Server variable '{var_name}': resolved from env var '{env_var_name}'.")

        # 3. Else, use ServerVariable.default_value
        if resolved_value is None and server_var_details.default_value is not None:
            resolved_value = server_var_details.default_value
            logger.debug(f"Server variable '{var_name}': resolved from default_value.")

        # 4. If still unresolved, this variable is mandatory and no value was found
        if resolved_value is None:
            raise ValueError(
                f"Required server variable '{var_name}' could not be resolved for URL template "
                f"'{server_config.url_template}'. No runtime parameter, environment variable (tried: '{env_var_name}'), "
                f"or default value found."
            )

        # 5. If ServerVariable.enum_values is set, log a warning if the resolved value is not in the enum
        if server_var_details.enum_values and resolved_value not in server_var_details.enum_values:
            logger.warning(
                f"Value '{resolved_value}' for server variable '{var_name}' is not in its defined "
                f"enum values: {server_var_details.enum_values}. URL: '{server_config.url_template}'"
            )

        # Substitute the resolved value into the URL string
        resolved_url = resolved_url.replace(f"{{{var_name}}}", resolved_value)

    return resolved_url


def format_server_config_details(config: ServerConfiguration) -> str:
    """
    Formats the details of a ServerConfiguration for user-friendly display.

    This includes the URL template, its description, and for each variable:
    its name, description, default value, possible enum values, and the
    exact environment variable name that can be used to set it.

    Args:
        config: The ServerConfiguration object to format.

    Returns:
        A string containing the formatted details.
    """
    details = []

    details.append(f"Server URL Template: {config.url_template}")
    if config.description:
        details.append(f"  Description: {config.description}")
    
    if config.api_title_prefix:
        details.append(f"  (Associated API Title Prefix for ENV VARS: {config.api_title_prefix})")

    if not config.variables:
        details.append("  This server URL has no dynamic variables.")
    else:
        details.append("  Variables:")
        for var_name, var_details in config.variables.items():
            details.append(f"    - Variable: '{var_name}'")
            if var_details.description:
                details.append(f"      Description: {var_details.description}")
            
            env_var_name_base = f"OAK_SERVER_{var_name.upper()}"
            env_var_name = (
                f"{config.api_title_prefix}_{env_var_name_base}"
                if config.api_title_prefix
                else env_var_name_base
            )
            details.append(f"      Set via ENV: {env_var_name}")

            if var_details.default_value is not None:
                details.append(f"      Default: '{var_details.default_value}'")
            else:
                details.append(f"      Default: (none)")

            if var_details.enum_values:
                details.append(f"      Possible Values: {', '.join(var_details.enum_values)}")
            else:
                details.append(f"      Possible Values: (any)")
    
    return "\n".join(details)
