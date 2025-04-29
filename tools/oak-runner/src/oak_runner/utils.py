#!/usr/bin/env python3
"""
Utility functions for OAK Runner

This module provides utility functions for the OAK Runner.
"""

import json
import logging
import os
import re
from typing import Any
import jsonpointer
import yaml

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
