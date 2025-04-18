#!/usr/bin/env python3
"""
Output Extractor for OAK Runner

This module provides functionality to extract outputs from API responses.
"""

import logging
from typing import Any

from ..evaluator import ExpressionEvaluator
from ..models import ExecutionState
from ..utils import evaluate_json_pointer, extract_json_pointer_from_expression

# Configure logging
logger = logging.getLogger("arazzo-runner.executor")


class OutputExtractor:
    """Extracts outputs from API responses"""

    def __init__(self, source_descriptions: dict[str, Any]):
        """
        Initialize the output extractor

        Args:
            source_descriptions: OpenAPI source descriptions
        """
        self.source_descriptions = source_descriptions

    def extract_outputs(self, step: dict, response: dict, state: ExecutionState) -> dict[str, Any]:
        """
        Extract outputs from the response based on step definitions

        Args:
            step: Step definition
            response: API response
            state: Current execution state

        Returns:
            Dictionary of extracted outputs
        """
        outputs = {}

        # Detailed logging of response structure for troubleshooting
        logger.info(f"Response status code: {response.get('status_code')}")
        logger.debug(f"Response headers: {response.get('headers')}")
        logger.debug(f"Response body: {response.get('body')}")

        # Cache direct ID values from response for potential future use
        # We extract these first but don't add them to outputs yet - we'll only add
        # them if they're actually needed based on workflow definitions
        cached_ids = {}
        if isinstance(response.get("body"), dict):
            body = response.get("body", {})
            # Extract IDs from response body
            for key, value in body.items():
                if key.endswith("Id") and isinstance(value, str):
                    cached_ids[key] = value

            # Also extract IDs from resource URLs in response
            for key, value in body.items():
                if (
                    (key == "self" or key.endswith("Url") or key.endswith("Uri"))
                    and isinstance(value, str)
                    and "/" in value
                ):
                    # Get base type name from URL path
                    path_parts = value.rstrip("/").split("/")
                    if len(path_parts) >= 2:
                        # Try to determine the resource type from the path
                        resource_type = path_parts[
                            -2
                        ]  # e.g., "customers" from "/customers/CUST123"
                        if resource_type.endswith("s"):  # Handle plural form
                            resource_type = resource_type[:-1]  # Remove trailing 's'

                        id_key = f"{resource_type}Id"
                        cached_ids[id_key] = path_parts[-1]

        # Special handling for JSON pointer expressions in outputs
        for output_name, output_expr in step.get("outputs", {}).items():
            value = None

            # Check if this is a JSON pointer expression
            if isinstance(output_expr, str) and "#/" in output_expr:
                container_path, pointer_path = extract_json_pointer_from_expression(output_expr)

                if container_path and pointer_path:
                    # Handle response.body#/path case
                    if container_path == "response.body":
                        body = response.get("body", {})
                        value = evaluate_json_pointer(body, pointer_path)
                        logger.debug(f"JSON Pointer extracted output {output_name}: {value}")
                        outputs[output_name] = value
                        continue  # Skip normal evaluation for this output

            # Handle dot notation by converting to JSON pointer
            if (
                isinstance(output_expr, str)
                and output_expr.startswith("$response.body.")
                and "#" not in output_expr
            ):
                # Convert dot notation to JSON pointer
                path = output_expr.replace("$response.body.", "")
                pointer_path = "/" + path.replace(".", "/")

                body = response.get("body", {})
                value = evaluate_json_pointer(body, pointer_path)
                if value is not None:
                    logger.debug(
                        f"Dot notation converted to JSON pointer for {output_name}: {value}"
                    )
                    outputs[output_name] = value
                    continue

            # If the expression is requesting an ID we've cached, use that
            if output_name in cached_ids:
                outputs[output_name] = cached_ids[output_name]
                logger.debug(f"Using cached ID for {output_name}: {cached_ids[output_name]}")
                continue

            # Normal expression evaluation
            value = ExpressionEvaluator.evaluate_expression(
                output_expr,
                state,
                self.source_descriptions,
                {
                    "statusCode": response["status_code"],
                    "response": response,
                    "headers": response["headers"],
                    "body": response["body"],
                },
            )

            if value is not None:
                outputs[output_name] = value
                logger.debug(f"Extracted output {output_name}: {value}")

        # Log if no outputs were extracted
        if not outputs:
            logger.warning(f"No outputs were successfully extracted for step {step.get('stepId')}")

        return outputs
