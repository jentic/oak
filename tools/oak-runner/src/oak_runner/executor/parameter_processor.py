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

    @staticmethod
    def _resolve_ref(ref: str, root: dict) -> dict:
        """
        Resolve a JSON reference (e.g., '#/components/parameters/foo') in an OpenAPI document.
        Args:
            ref: The $ref string.
            root: The OpenAPI root document.
        Returns:
            The referenced object.
        """
        if not ref.startswith('#/'):
            raise ValueError(f"Only local refs are supported, got: {ref}")
        parts = ref.lstrip('#/').split('/')
        obj = root
        for part in parts:
            obj = obj[part]
        # Recursively resolve nested $ref
        if isinstance(obj, dict) and '$ref' in obj:
            return ParameterProcessor._resolve_ref(obj['$ref'], root)
        return obj

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
            logger.debug(
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
        logger.debug("Preparing operation parameters...")
        logger.debug(f"Operation details: {operation_details}")
        logger.debug(f"Inputs: {inputs}")
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
        prepared_params: dict[str, Any] = {
            "path": {},
            "query": {},
            "header": {},
            "cookie": {},
            "body": None,
        }
        used_input_keys = set()

        # 1. Merge parameters from path-item and operation level, operation-level wins
        op_params = operation_details.get("operation", {}).get("parameters", [])
        path_params = operation_details.get("parameters", [])
        param_map = {}
        all_params = path_params + op_params
        for param in all_params:
            # --- $ref resolution ---
            if isinstance(param, dict) and "$ref" in param:
                source_name = operation_details.get("source")
                if not source_name or source_name not in self.source_descriptions:
                    raise ValueError(f"Cannot resolve $ref: source '{source_name}' not found in source_descriptions.")
                param = self._resolve_ref(param["$ref"], self.source_descriptions[source_name])
            key = (param.get("name"), param.get("in"))
            param_map[key] = param
        merged_params = list(param_map.values())

        # 2. Parse path template for {param} tokens and ensure all are present as required path params
        path_template = operation_details.get("path", "")
        path_param_names = set(re.findall(r"{([^}]+)}", path_template))
        for param_name in path_param_names:
            key = (param_name, "path")
            if key not in param_map:
                param_map[key] = {
                    "name": param_name,
                    "in": "path",
                    "required": True,
                }
        merged_params = list(param_map.values())

        # 3. Process all parameters (path, query, header, cookie)
        for param_def in merged_params:
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

        # 4. Process request body
        operation = operation_details.get("operation")  # Get operation dict or None
        request_body_ref = None
        if operation and isinstance(operation, dict):
            request_body_ref = operation.get("requestBody")

        # If not found in operation (or operation doesn't exist), check the top level
        if not request_body_ref:
            request_body_ref = operation_details.get("requestBody")

        request_body_def = None
        if request_body_ref:
            logger.debug(f"Found request body reference: {request_body_ref}")
            # Resolve $ref if necessary (simplified back to original for now, assuming source handled elsewhere if needed)
            if isinstance(request_body_ref, dict) and "$ref" in request_body_ref:
                ref_path = request_body_ref["$ref"]
                try:
                    # Assuming _resolve_ref can find the source description if needed,
                    # or that refs are local within the current file.
                    request_body_def = self._resolve_ref(ref_path)
                    logger.debug(f"Resolved requestBody $ref '{ref_path}' to: {request_body_def}")
                except ValueError as e:
                    logger.error(f"Failed to resolve requestBody $ref '{ref_path}': {e}")
                    request_body_def = None
                except Exception as e:
                    logger.error(f"Unexpected error resolving requestBody $ref '{ref_path}': {e}")
                    request_body_def = None
            elif isinstance(request_body_ref, dict):
                request_body_def = request_body_ref
                logger.debug(f"Using inline requestBody definition: {request_body_def}")
            else:
                logger.warning(f"Unexpected format for requestBody reference: {request_body_ref}")

        # Determine potential body keys (inputs not used for path/query/header/cookie)
        potential_body_keys = set(inputs.keys()) - used_input_keys
        payload_dict = None
        determined_content_type = None
        body_required = False

        # Only process body if the spec defines one
        if request_body_def and isinstance(request_body_def, dict):
            body_required = request_body_def.get("required", False)

            if potential_body_keys:
                payload_dict = {k: inputs[k] for k in potential_body_keys}
                logger.debug(f"Identified potential request body payload from unused inputs: {list(potential_body_keys)}")
                used_input_keys.update(potential_body_keys) # Mark these inputs as used

                # Determine content type based on the spec's definition
                content_schema = request_body_def.get("content", {})
                if content_schema and isinstance(content_schema, dict):
                     # Prioritize application/json, otherwise take the first key
                    if "application/json" in content_schema:
                        determined_content_type = "application/json"
                    elif content_schema:
                        determined_content_type = next(iter(content_schema.keys()), None)

                    if determined_content_type:
                        logger.debug(f"Determined request body content type: {determined_content_type}")
                    else:
                         logger.warning("Could not determine content type from requestBody definition, even though payload was identified.")
                else:
                    logger.warning("requestBody definition found, but 'content' map is missing or invalid.")

                # Store payload and content type (only if payload was identified)
                prepared_params["body"] = {
                    "payload": payload_dict,
                    "contentType": determined_content_type
                }
            # Check requirement if spec defines a body but no payload was found
            elif body_required:
                 logger.error("Required request body is missing from inputs (spec defines body, but no unused inputs found).")
                 raise ValueError("Required request body is missing.")
            else: # Optional body defined in spec, but no payload provided
                 logger.debug("Optional request body defined in spec, but not provided or identified in inputs.")

        # If spec does NOT define a request body, but we HAVE potential body keys -> Log warning
        elif potential_body_keys:
             logger.warning(
                 f"Inputs provided but not used for parameters and no requestBody defined in spec: {list(potential_body_keys)}. These inputs are being ignored."
             )
             # Body remains None in prepared_params

        # Final check for requirement (redundant if logic above is correct, but safe)
        if body_required and prepared_params.get("body") is None:
             # This case should theoretically be caught above, but acts as a safeguard
            logger.error("Consistency check failed: Required body specified, but no body was prepared.")
            raise ValueError("Required request body was specified but could not be prepared from inputs.")

        logger.debug(f"Prepared parameters: {prepared_params}")
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
            logger.debug(
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
