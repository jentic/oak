#!/usr/bin/env python3
"""
Parameter Processor for OAK Runner

This module provides functionality to process parameters and request bodies.
"""

import json
import logging
import re
from typing import Any

from ..evaluator import ExpressionEvaluator
from ..models import ExecutionState

# Configure logging
logger = logging.getLogger("arazzo-runner.executor")


class ParameterProcessor:
    """
    Processes parameters and request bodies for API operations
    """

    def __init__(self, source_descriptions: dict[str, Any]):
        """
        Initialize the parameter processor

        Args:
            source_descriptions: OpenAPI source descriptions
        """
        self.source_descriptions = source_descriptions

    def prepare_parameters(self, step: dict, state: ExecutionState) -> dict[str, Any]:
        """
        Prepare parameters for an operation execution

        Args:
            step: Step definition
            state: Current execution state

        Returns:
            Dictionary of prepared parameters
        """
        parameters = {}

        # Process parameters from the step definition
        for param in step.get("parameters", []):
            name = param.get("name")
            location = param.get("in")
            value = param.get("value")

            # Process the value to resolve any expressions
            if isinstance(value, str):
                if value.startswith("$"):
                    # Try array access handler first for common patterns
                    array_value = ExpressionEvaluator.handle_array_access(value, state)
                    if array_value is not None:
                        value = array_value
                    else:
                        # Fall back to standard expression evaluation
                        value = ExpressionEvaluator.evaluate_expression(
                            value, state, self.source_descriptions
                        )
                elif "{" in value and "}" in value:
                    # Template with expressions
                    def replace_expr(match):
                        expr = match.group(1)
                        eval_value = ExpressionEvaluator.evaluate_expression(
                            expr, state, self.source_descriptions
                        )
                        return "" if eval_value is None else str(eval_value)

                    value = re.sub(r"\{([^}]+)\}", replace_expr, value)
                # Special handling for "Bearer $dependencies.x.y" format - common in authorization headers
                elif " $" in value:
                    parts = value.split(" $", 1)
                    prefix = parts[0] + " "
                    expr = "$" + parts[1]

                    # Add more debugging for dependency expressions
                    if "dependencies" in expr:
                        logger.debug(f"Processing dependency expression: {expr}")
                        logger.debug(f"Dependencies available: {state.dependency_outputs}")
                        if "." in expr:
                            parts = expr.split(".")
                            if len(parts) >= 3:
                                dep_id = parts[1]
                                output_key = parts[2]
                                logger.debug(
                                    f"Looking for dependency {dep_id}, output {output_key}"
                                )

                                if dep_id in state.dependency_outputs:
                                    logger.debug(
                                        f"Found dependency {dep_id} with outputs: {state.dependency_outputs[dep_id]}"
                                    )
                                    if output_key in state.dependency_outputs[dep_id]:
                                        logger.debug(
                                            f"Found output {output_key} with value: {state.dependency_outputs[dep_id][output_key]}"
                                        )
                                    else:
                                        logger.debug(
                                            f"Output {output_key} not found in dependency {dep_id}"
                                        )
                                else:
                                    logger.debug(
                                        f"Dependency {dep_id} not found in available dependencies"
                                    )

                    # Evaluate the expression part
                    expr_value = ExpressionEvaluator.evaluate_expression(
                        expr, state, self.source_descriptions
                    )

                    # More debugging about evaluation result
                    if "dependencies" in expr:
                        logger.debug(f"Evaluated dependency expression {expr} to: {expr_value}")

                    if expr_value is not None:
                        value = prefix + str(expr_value)
                    else:
                        logger.warning(
                            f"Expression {expr} evaluated to None - keeping original value: {value}"
                        )
            elif isinstance(value, dict):
                value = ExpressionEvaluator.process_object_expressions(
                    value, state, self.source_descriptions
                )
            elif isinstance(value, list):
                value = ExpressionEvaluator.process_array_expressions(
                    value, state, self.source_descriptions
                )

            # Log the parameter evaluation process for debugging
            logger.info(
                f"Parameter: {name}, Original value: {param.get('value')}, Evaluated value: {value}"
            )

            # Log if the value couldn't be properly evaluated
            if isinstance(value, str) and "$" in value and (value.startswith("$") or "{$" in value):
                logger.warning(
                    f"Parameter '{name}' value '{value}' still contains expression syntax after evaluation"
                )

            # Organize parameters by location
            if location == "path":
                parameters.setdefault("path", {})[name] = value
            elif location == "query":
                parameters.setdefault("query", {})[name] = value
            elif location == "header":
                parameters.setdefault("header", {})[name] = value
            elif location == "cookie":
                parameters.setdefault("cookie", {})[name] = value
            else:
                # For workflow inputs
                parameters[name] = value

        return parameters

    def prepare_request_body(self, request_body: dict, state: ExecutionState) -> dict:
        """
        Prepare request body for an operation execution

        Args:
            request_body: Request body definition
            state: Current execution state

        Returns:
            Dictionary with prepared request body
        """
        content_type = request_body.get("contentType")
        payload = request_body.get("payload")

        # Handle different payload types
        if isinstance(payload, str):
            # String payload with possible template expressions
            try:
                # First handle any template expressions in the string regardless of format
                if "{" in payload and "}" in payload:
                    # First convert any expressions like "{$inputs.value}" to their evaluated values
                    def replace_expr(match):
                        expr = match.group(1)
                        if expr.startswith("$"):
                            # It's an expression, evaluate it
                            value = ExpressionEvaluator.evaluate_expression(
                                expr, state, self.source_descriptions
                            )
                            logger.debug(f"Evaluated template expression {expr} to value: {value}")

                            # Return JSON-compatible value or string representation
                            if value is None:
                                return "null"
                            elif isinstance(value, (dict, list)):
                                # Keep actual data structure for direct inclusion in JSON
                                try:
                                    # First try to stringify to ensure it's JSON-safe
                                    json_str = json.dumps(value)
                                    # Return the original value (not the string) for use in the template
                                    return value
                                except Exception as e:
                                    logger.error(f"Cannot serialize value to JSON: {e}")
                                    # Fallback to string representation
                                    return str(value)
                            else:
                                # For primitives, return the raw value (not JSON string)
                                return value
                        else:
                            # Not an expression, return as is
                            return "{" + expr + "}"

                    # Handle expressions in the template
                    try:
                        # Special handling for payload strings that look like JSON
                        if payload.strip().startswith("{") and payload.strip().endswith("}"):
                            # Try direct JSON parsing first
                            try:
                                # Fix common JSON errors like missing commas
                                fixed_payload = re.sub(r'"\s*\n\s*"', '",\n"', payload)
                                json_data = json.loads(fixed_payload)

                                # Directly process the object expressions
                                processed_json = ExpressionEvaluator.process_object_expressions(
                                    json_data, state, self.source_descriptions
                                )

                                if content_type == "application/json":
                                    payload = processed_json  # Keep as dict for JSON
                                else:
                                    payload = json.dumps(processed_json)  # Convert back to string
                                logger.debug(
                                    "Successfully processed JSON payload with nested expressions"
                                )

                            except json.JSONDecodeError:
                                # If direct parsing fails, try traditional template substitution
                                logger.debug(
                                    "Direct JSON parsing failed, trying template replacement"
                                )

                                # Replace expressions in template string
                                templated_payload = re.sub(r"\{(\$[^}]+)\}", replace_expr, payload)
                                logger.debug(f"Template-processed payload: {templated_payload}")

                                try:
                                    # Fix common JSON issues and try parsing
                                    fixed_payload = re.sub(
                                        r'"\s*\n\s*"', '",\n"', templated_payload
                                    )
                                    json_payload = json.loads(fixed_payload)

                                    # Keep as dict if needed for JSON
                                    if content_type == "application/json":
                                        payload = json_payload
                                    else:
                                        payload = json.dumps(json_payload)
                                except json.JSONDecodeError as e:
                                    logger.warning(
                                        f"JSON decode error after template processing: {e}"
                                    )
                                    # Use the templated string as-is
                                    payload = templated_payload
                        else:
                            # Not JSON-like, process as regular template string
                            templated_payload = re.sub(r"\{(\$[^}]+)\}", replace_expr, payload)
                            payload = templated_payload
                            logger.debug(f"Processed non-JSON template: {payload}")
                    except Exception as template_error:
                        logger.error(f"Template processing error: {template_error}")
                        # Fall back to the original payload
                        logger.debug("Using original payload due to processing error")

                # If no template expressions, but looks like JSON, try to parse it
                elif payload.strip().startswith("{") and payload.strip().endswith("}"):
                    try:
                        # Fix common JSON issues
                        fixed_payload = re.sub(r'"\s*\n\s*"', '",\n"', payload)

                        # Parse the JSON
                        json_payload = json.loads(fixed_payload)

                        # Process any expressions in the parsed JSON
                        processed_payload = ExpressionEvaluator.process_object_expressions(
                            json_payload, state, self.source_descriptions
                        )

                        # Keep as object for JSON content types
                        if content_type == "application/json":
                            payload = processed_payload
                        else:
                            payload = json.dumps(processed_payload)
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON decode error in non-templated payload: {e}")
                        # Keep original as string
            except Exception as e:
                logger.error(f"Error processing payload: {e}")
                logger.error(f"Original payload: {payload}")
                # If all processing fails, use the original payload
        elif isinstance(payload, dict):
            # Process nested dictionary values, evaluating expressions
            payload = ExpressionEvaluator.process_object_expressions(
                payload, state, self.source_descriptions
            )
            logger.debug(f"Processed dict payload: {payload}")
        elif isinstance(payload, list):
            # Process nested list values, evaluating expressions
            payload = ExpressionEvaluator.process_array_expressions(
                payload, state, self.source_descriptions
            )
            logger.debug(f"Processed list payload: {payload}")
        elif isinstance(payload, str) and payload.startswith("$"):
            # Direct expression payload
            payload = ExpressionEvaluator.evaluate_expression(
                payload, state, self.source_descriptions
            )
            logger.debug(f"Processed expression payload: {payload}")

        # Handle replacements
        replacements = request_body.get("replacements", [])
        if replacements and isinstance(payload, (dict, list)):
            for replacement in replacements:
                target = replacement.get("target")
                value = replacement.get("value")

                if isinstance(value, str) and value.startswith("$"):
                    # Evaluate expression
                    value = ExpressionEvaluator.evaluate_expression(
                        value, state, self.source_descriptions
                    )

                # Apply the replacement to the payload
                try:
                    if target.startswith("/"):
                        # JSON Pointer
                        parts = target.split("/")[1:]  # Skip the first empty element

                        # Navigate to the target location
                        current = payload
                        for i, part in enumerate(parts):
                            if i == len(parts) - 1:
                                # Last part, set the value
                                current[part] = value
                            else:
                                # Navigate deeper
                                current = current[part]
                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"Error applying replacement to target {target}: {e}")

        return {"contentType": content_type, "payload": payload}

    def prepare_operation_parameters(
        self, operation_details: dict, inputs: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Prepare parameters and request body for a direct operation execution.

        This method maps raw input values to operation parameters and request body
        defined in the OpenAPI specification, without using ExecutionState or
        evaluating complex Arazzo expressions.

        Args:
            operation_details: The OpenAPI operation definition dictionary (from OperationFinder).
            inputs: The raw input dictionary provided by the user.

        Returns:
            Dictionary containing prepared parameters and body, structured as:
            {
                'path': { 'param_name': value, ... },
                'query': { 'param_name': value, ... },
                'header': { 'param_name': value, ... },
                'cookie': { 'param_name': value, ... },
                'body': request_body_value_or_object
            }

        Raises:
            ValueError: If a required parameter is missing from inputs or if the request body is required but not provided.
        """
        prepared_params = {
            "path": {},
            "query": {},
            "header": {},
            "cookie": {},
            "body": None,
        }
        used_input_keys = set()

        # 1. Process defined parameters (path, query, header, cookie)
        for param_def in operation_details.get("operation", {}).get("parameters", []):
            name = param_def.get("name")
            location = param_def.get("in")
            required = param_def.get("required", False)

            if not name or not location:
                logger.warning(f"Skipping parameter definition missing name or location: {param_def}")
                continue

            if name in inputs:
                value = inputs[name]
                if location in prepared_params:
                    prepared_params[location][name] = value
                    used_input_keys.add(name)
                    logger.debug(f"Mapped input '{name}' to {location} parameter.")
                else:
                    logger.warning(f"Unsupported parameter location '{location}' for parameter '{name}'.")
            elif required:
                logger.error(f"Required parameter '{name}' (in: {location}) missing from inputs.")
                raise ValueError(f"Required parameter '{name}' (in: {location}) is missing.")
            else:
                logger.debug(f"Optional parameter '{name}' (in: {location}) not provided in inputs.")

        # 2. Process request body
        request_body_def = operation_details.get("requestBody")
        body_keys = set(inputs.keys()) - used_input_keys
        potential_body_input = {k: inputs[k] for k in body_keys}

        if request_body_def:
            body_required = request_body_def.get("required", False)
            if potential_body_input:
                # Simple approach: assume the remaining inputs form the body.
                # A more robust implementation might check content schemas.
                prepared_params["body"] = potential_body_input
                logger.debug(f"Using remaining inputs as request body: {list(body_keys)}")
            elif body_required:
                logger.error("Request body is required but no relevant inputs were provided.")
                raise ValueError("Required request body is missing from inputs.")
            else:
                logger.debug("Optional request body not provided.")
        elif potential_body_input:
            # Inputs provided that weren't used for parameters and no body defined
            logger.warning(
                f"Inputs provided but not used for parameters or defined request body: {list(body_keys)}"
            )
            # Decide if we should error, warn, or attempt to send anyway.
            # For now, let's warn and not include it implicitly.
            # prepared_params["body"] = potential_body_input # Uncomment to send anyway

        logger.info(f"Prepared parameters for operation: {prepared_params}")
        return prepared_params

    # --- DEPRECATION NOTICE ---
    # Consider refactoring prepare_parameters or merging logic if significant overlap
    # exists after full implementation of prepare_operation_parameters.
    def prepare_parameters(self, step: dict, state: ExecutionState) -> dict[str, Any]:
        """
        Prepare parameters for an operation execution

        Args:
            step: Step definition
            state: Current execution state

        Returns:
            Dictionary of prepared parameters
        """
        parameters = {}

        # Process parameters from the step definition
        for param in step.get("parameters", []):
            name = param.get("name")
            location = param.get("in")
            value = param.get("value")

            # Process the value to resolve any expressions
            if isinstance(value, str):
                if value.startswith("$"):
                    # Try array access handler first for common patterns
                    array_value = ExpressionEvaluator.handle_array_access(value, state)
                    if array_value is not None:
                        value = array_value
                    else:
                        # Fall back to standard expression evaluation
                        value = ExpressionEvaluator.evaluate_expression(
                            value, state, self.source_descriptions
                        )
                elif "{" in value and "}" in value:
                    # Template with expressions
                    def replace_expr(match):
                        expr = match.group(1)
                        eval_value = ExpressionEvaluator.evaluate_expression(
                            expr, state, self.source_descriptions
                        )
                        return "" if eval_value is None else str(eval_value)

                    value = re.sub(r"\{([^}]+)\}", replace_expr, value)
                # Special handling for "Bearer $dependencies.x.y" format - common in authorization headers
                elif " $" in value:
                    parts = value.split(" $", 1)
                    prefix = parts[0] + " "
                    expr = "$" + parts[1]

                    # Add more debugging for dependency expressions
                    if "dependencies" in expr:
                        logger.debug(f"Processing dependency expression: {expr}")
                        logger.debug(f"Dependencies available: {state.dependency_outputs}")
                        if "." in expr:
                            parts = expr.split(".")
                            if len(parts) >= 3:
                                dep_id = parts[1]
                                output_key = parts[2]
                                logger.debug(
                                    f"Looking for dependency {dep_id}, output {output_key}"
                                )

                                if dep_id in state.dependency_outputs:
                                    logger.debug(
                                        f"Found dependency {dep_id} with outputs: {state.dependency_outputs[dep_id]}"
                                    )
                                    if output_key in state.dependency_outputs[dep_id]:
                                        logger.debug(
                                            f"Found output {output_key} with value: {state.dependency_outputs[dep_id][output_key]}"
                                        )
                                    else:
                                        logger.debug(
                                            f"Output {output_key} not found in dependency {dep_id}"
                                        )
                                else:
                                    logger.debug(
                                        f"Dependency {dep_id} not found in available dependencies"
                                    )

                    # Evaluate the expression part
                    expr_value = ExpressionEvaluator.evaluate_expression(
                        expr, state, self.source_descriptions
                    )

                    # More debugging about evaluation result
                    if "dependencies" in expr:
                        logger.debug(f"Evaluated dependency expression {expr} to: {expr_value}")

                    if expr_value is not None:
                        value = prefix + str(expr_value)
                    else:
                        logger.warning(
                            f"Expression {expr} evaluated to None - keeping original value: {value}"
                        )
            elif isinstance(value, dict):
                value = ExpressionEvaluator.process_object_expressions(
                    value, state, self.source_descriptions
                )
            elif isinstance(value, list):
                value = ExpressionEvaluator.process_array_expressions(
                    value, state, self.source_descriptions
                )

            # Log the parameter evaluation process for debugging
            logger.info(
                f"Parameter: {name}, Original value: {param.get('value')}, Evaluated value: {value}"
            )

            # Log if the value couldn't be properly evaluated
            if isinstance(value, str) and "$" in value and (value.startswith("$") or "{$" in value):
                logger.warning(
                    f"Parameter '{name}' value '{value}' still contains expression syntax after evaluation"
                )

            # Organize parameters by location
            if location == "path":
                parameters.setdefault("path", {})[name] = value
            elif location == "query":
                parameters.setdefault("query", {})[name] = value
            elif location == "header":
                parameters.setdefault("header", {})[name] = value
            elif location == "cookie":
                parameters.setdefault("cookie", {})[name] = value
            else:
                # For workflow inputs
                parameters[name] = value

        return parameters
