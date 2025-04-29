#!/usr/bin/env python3
"""
Expression Evaluator for OAK Runner

This module provides functions for evaluating runtime expressions used in Arazzo workflows.
"""

import logging
import re
from typing import Any

from .models import ExecutionState

# Configure logging
logger = logging.getLogger("arazzo-runner.evaluator")


class ExpressionEvaluator:
    """Evaluates runtime expressions in Arazzo workflows"""

    @staticmethod
    def handle_array_access(expression: str, state: ExecutionState) -> Any | None:
        """
        Special handler for array access expressions like $steps.findPetsStep.outputs.availablePets[0].id
        Returns None if the expression doesn't match the expected pattern or value can't be found
        """
        # Check if this looks like an array access pattern
        if not (expression.startswith("$") and "[" in expression and "]" in expression):
            return None

        # Match the common pattern: $steps.{stepId}.outputs.{array}[{index}].{field}
        match = re.match(
            r"^\$steps\.([a-zA-Z0-9_]+)\.outputs\.([a-zA-Z0-9_]+)\[(\d+)\]\.([a-zA-Z0-9_]+)$",
            expression,
        )
        if match:
            step_id, array_name, index_str, field_name = match.groups()
            index = int(index_str)

            logger.info(
                f"Array access - Step: {step_id}, Array: {array_name}, Index: {index}, Field: {field_name}"
            )

            # Check if step exists
            if step_id not in state.step_outputs:
                logger.info(f"Step {step_id} not found in outputs")
                return None

            step_output = state.step_outputs[step_id]

            # Check if array exists in step outputs
            if array_name not in step_output:
                logger.info(f"Array {array_name} not found in step {step_id} outputs")
                return None

            array = step_output[array_name]

            # Check if array is a list and index is valid
            if not isinstance(array, list):
                logger.info(f"{array_name} is not a list: {type(array)}")
                return None

            if not (0 <= index < len(array)):
                logger.info(f"Index {index} out of range for array of length {len(array)}")
                return None

            item = array[index]

            # Check if item is a dict and has the field
            if not isinstance(item, dict):
                logger.info(f"Array item is not a dict: {type(item)}")
                return None

            if field_name not in item:
                logger.info(f"Field {field_name} not found in item: {list(item.keys())}")
                return None

            # Found the value!
            value = item[field_name]
            logger.info(f"Successfully extracted array value: {value}")
            return value

        # Try direct array index access: $steps.{stepId}.outputs.{array}[{index}]
        match = re.match(
            r"^\$steps\.([a-zA-Z0-9_]+)\.outputs\.([a-zA-Z0-9_]+)\[(\d+)\]$", expression
        )
        if match:
            step_id, array_name, index_str = match.groups()
            index = int(index_str)

            logger.info(
                f"Direct array access - Step: {step_id}, Array: {array_name}, Index: {index}"
            )

            # Check if step exists
            if step_id not in state.step_outputs:
                logger.info(f"Step {step_id} not found in outputs")
                return None

            step_output = state.step_outputs[step_id]

            # Check if array exists in step outputs
            if array_name not in step_output:
                logger.info(f"Array {array_name} not found in step {step_id} outputs")
                return None

            array = step_output[array_name]

            # Check if array is a list and index is valid
            if not isinstance(array, list):
                logger.info(f"{array_name} is not a list: {type(array)}")
                return None

            if not (0 <= index < len(array)):
                logger.info(f"Index {index} out of range for array of length {len(array)}")
                return None

            # Found the value!
            value = array[index]
            logger.info(f"Successfully extracted array item: {value}")
            return value

        # Try direct input array access: $inputs.{array}[{index}]
        match = re.match(r"^\$inputs\.([a-zA-Z0-9_]+)\[(\d+)\]$", expression)
        if match:
            array_name, index_str = match.groups()
            index = int(index_str)

            logger.info(f"Input array access - Array: {array_name}, Index: {index}")

            # Check if array exists in inputs
            if array_name not in state.inputs:
                logger.info(f"Array {array_name} not found in inputs")
                return None

            array = state.inputs[array_name]

            # Check if array is a list and index is valid
            if not isinstance(array, list):
                logger.info(f"{array_name} is not a list: {type(array)}")
                return None

            if not (0 <= index < len(array)):
                logger.info(f"Index {index} out of range for array of length {len(array)}")
                return None

            # Found the value!
            value = array[index]
            logger.info(f"Successfully extracted input array item: {value}")
            return value

        return None

    @staticmethod
    def evaluate_expression(
        expression: str,
        state: ExecutionState,
        source_descriptions: dict[str, Any] = None,
        additional_context: dict[str, Any] = None,
    ) -> Any:
        """
        Evaluate a runtime expression in the context of the current state.

        This evaluator supports:
        - Dot notation for object properties (e.g., $steps.loginStep.outputs.token)
        - Array indexing with brackets (e.g., $steps.findPetsStep.outputs.availablePets[0].id)
        - Nested object access
        - JSON Pointers (e.g., $response.body#/data/items)
        """
        if not isinstance(expression, str):
            return expression

        if not expression.startswith("$"):
            return expression

        # Build evaluation context
        context = {
            "inputs": state.inputs,
            "steps": state.step_outputs,
            "outputs": state.workflow_outputs,
            "dependencies": state.dependency_outputs,
            "sourceDescriptions": source_descriptions or {},
            "statusCode": additional_context.get("statusCode") if additional_context else None,
            "response": additional_context.get("response") if additional_context else None,
        }

        # Add additional context if provided
        if additional_context:
            for key, value in additional_context.items():
                if key not in context:  # Don't overwrite core context variables
                    context[key] = value

        try:
            # Save the original for error messages
            original_expression = expression

            # Handle special case: if the expression is a direct reference to a context variable
            if expression == "$statusCode" and "statusCode" in context:
                return context["statusCode"]
            if expression == "$response" and "response" in context:
                return context["response"]

            # Handle JSON Pointer syntax in expressions
            # Check for patterns like $response.body#/path/to/value
            json_pointer_match = re.match(r"^\$([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)#(/.*)$", expression)
            if json_pointer_match:
                import jsonpointer

                container, property_name, pointer_path = json_pointer_match.groups()

                # Get the container object
                if container not in context:
                    logger.debug(
                        f"JSON Pointer evaluation failed: container '{container}' not found in context"
                    )
                    return None

                container_obj = context[container]

                # Get the property from the container
                if not isinstance(container_obj, dict) or property_name not in container_obj:
                    logger.debug(
                        f"JSON Pointer evaluation failed: property '{property_name}' not found in container"
                    )
                    return None

                property_value = container_obj[property_name]

                # Use jsonpointer to resolve the path
                try:
                    # For empty pointer or root, return the entire object
                    if pointer_path == "/":
                        return property_value

                    # Create a JSON pointer resolver
                    pointer = jsonpointer.JsonPointer(pointer_path)
                    result = pointer.resolve(property_value)
                    logger.debug(f"JSON Pointer evaluation: Found value for {expression}")
                    return result
                except (jsonpointer.JsonPointerException, TypeError) as e:
                    logger.debug(f"JSON Pointer evaluation failed: {e}")
                    return None

            # Try array access handler first
            array_value = ExpressionEvaluator.handle_array_access(expression, state)
            if array_value is not None:
                return array_value

            # For direct access to array elements like $steps.findPetsStep.outputs.availablePets[0].id
            # First check if this is a simple array access pattern we can handle directly
            array_access_pattern = r"^\$([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\[(\d+)\]\.([a-zA-Z0-9_]+)$"
            array_match = re.match(array_access_pattern, expression)

            if array_match:
                # This is a direct array access, let's handle it explicitly
                container, item, property1, property2, idx, field = array_match.groups()
                idx = int(idx)

                # Build the access path step by step
                if container in context:
                    container_obj = context[container]
                    if item in container_obj:
                        item_obj = container_obj[item]
                        if property1 in item_obj:
                            prop1_obj = item_obj[property1]
                            if property2 in prop1_obj:
                                prop2_obj = prop1_obj[property2]
                                if isinstance(prop2_obj, list) and 0 <= idx < len(prop2_obj):
                                    array_item = prop2_obj[idx]
                                    if isinstance(array_item, dict) and field in array_item:
                                        logger.debug(
                                            f"Direct array access: Found value {array_item[field]} at {expression}"
                                        )
                                        return array_item[field]

            # If direct pattern matching fails, fall back to general expression parsing
            # Handle array indexing with brackets
            array_indices = []
            # Extract bracketed indices
            bracket_pattern = r"\[(\d+)\]"

            # Find all array indices in the expression
            for match in re.finditer(bracket_pattern, expression):
                idx = int(match.group(1))
                array_indices.append((match.start(), match.end(), idx))

            # Replace brackets with placeholders that won't be split by dots
            # Using a format that won't appear in normal expressions
            modified_expression = expression
            adjustment = 0
            for start, end, idx in array_indices:
                adjusted_start = start + adjustment
                adjusted_end = end + adjustment
                placeholder = f"__ARRAY_INDEX_{idx}__"
                modified_expression = (
                    modified_expression[:adjusted_start]
                    + placeholder
                    + modified_expression[adjusted_end:]
                )
                # Adjust for length difference between original and replacement
                adjustment += len(placeholder) - (end - start)

            # Strip the leading $ and handle an **optional** extra dot after it.
            # Example necessity:
            #   Expression: $.steps.myStep.statusCode
            #   Without this fix → split produces ["", "steps", ...] and lookup of '' fails.
            #   With the fix     → path_parts becomes ["steps", "myStep", "statusCode"].
            path_str = modified_expression[1:]
            if path_str.startswith("."):
                # Remove redundant root dot so we don't get an empty token
                path_str = path_str[1:]

            path_parts = path_str.split(".")

            # Restore array indices in path parts
            for i, part in enumerate(path_parts):
                if part.startswith("__ARRAY_INDEX_") and part.endswith("__"):
                    try:
                        # Extract the index
                        idx = int(part[len("__ARRAY_INDEX_") : -2])
                        path_parts[i] = str(idx)
                    except (ValueError, IndexError):
                        pass

            # Navigate through the structure
            current = context
            path_so_far = "$"

            # Debug log the context and path parts for easier troubleshooting
            logger.debug(f"Evaluating expression: {original_expression}")
            logger.debug(f"Path parts: {path_parts}")
            logger.debug(f"Context keys: {list(context.keys())}")

            for i, part in enumerate(path_parts):
                path_so_far += f".{part}"

                if current is None:
                    logger.debug(f"Expression evaluation failed at {path_so_far}: parent is None")
                    return None

                if isinstance(current, dict):
                    # Handle dictionary access
                    if part == "outputs" and part not in current:
                        continue
                    if part in current:
                        current = current[part]
                    else:
                        logger.debug(
                            f"Expression evaluation failed at {path_so_far}: key '{part}' not found in dict {list(current.keys())}"
                        )
                        return None
                elif isinstance(current, list):
                    # Handle list indexing
                    if part.isdigit():
                        idx = int(part)
                        if 0 <= idx < len(current):
                            current = current[idx]
                        else:
                            logger.debug(
                                f"Expression evaluation failed at {path_so_far}: index {idx} out of range for list of length {len(current)}"
                            )
                            return None
                    else:
                        # Try to access the attribute for all items in the list
                        # This is useful for filtering lists
                        try:
                            current = [
                                item.get(part) if isinstance(item, dict) else getattr(item, part)
                                for item in current
                            ]
                        except (AttributeError, KeyError):
                            logger.debug(
                                f"Expression evaluation failed at {path_so_far}: cannot access '{part}' on list items"
                            )
                            return None
                elif hasattr(current, part):
                    # Handle object attribute access
                    current = getattr(current, part)
                else:
                    logger.debug(
                        f"Expression evaluation failed at {path_so_far}: cannot navigate further with '{part}'"
                    )
                    return None

            return current

        except Exception as e:
            logger.error(f"Error evaluating expression '{original_expression}': {e}")
            return None

    @staticmethod
    def evaluate_simple_condition(
        condition: str,
        state: ExecutionState,
        source_descriptions: dict[str, Any] = None,
        additional_context: dict[str, Any] = None,
    ) -> bool:
        """Evaluate a simple condition expression"""
        logger.debug(f"Evaluating condition: {condition}")

        # Special case handling for common patterns
        if (
            "==" in condition
            or "!=" in condition
            or "<" in condition
            or ">" in condition
            or "<=" in condition
            or ">=" in condition
        ):
            # Handle comparisons with JavaScript-style true/false literals
            condition = condition.replace(" == true", " == True").replace(" == false", " == False")
            condition = condition.replace(" != true", " != True").replace(" != false", " != False")

            # Handle null comparisons (null is None in Python)
            condition = condition.replace(" == null", " == None").replace(" != null", " != None")

            # Handle JavaScript-style OR operator
            condition = condition.replace("||", " or ")

            # Handle JavaScript-style AND operator
            condition = condition.replace("&&", " and ")

            logger.debug(f"Processed condition: {condition}")

            # Simple parsing for common comparison patterns
            left_right_match = re.match(r"^\s*([^<>=!]+)\s*([<>=!]+)\s*([^<>=!]+)\s*$", condition)
            if left_right_match:
                left_expr, operator, right_expr = left_right_match.groups()

                # Evaluate left side
                if left_expr.strip().startswith("$"):
                    left_value = ExpressionEvaluator.evaluate_expression(
                        left_expr.strip(), state, source_descriptions, additional_context
                    )
                else:
                    # Handle literals
                    if left_expr.strip() == "true":
                        left_value = True
                    elif left_expr.strip() == "false":
                        left_value = False
                    elif left_expr.strip() == "null":
                        left_value = None
                    else:
                        try:
                            left_value = eval(left_expr.strip())
                        except:
                            left_value = left_expr.strip()

                # Evaluate right side
                if right_expr.strip().startswith("$"):
                    right_value = ExpressionEvaluator.evaluate_expression(
                        right_expr.strip(), state, source_descriptions, additional_context
                    )
                else:
                    # Handle literals
                    if right_expr.strip() == "true":
                        right_value = True
                    elif right_expr.strip() == "false":
                        right_value = False
                    elif right_expr.strip() == "null":
                        right_value = None
                    else:
                        try:
                            right_value = eval(right_expr.strip())
                        except:
                            right_value = right_expr.strip()

                logger.debug(f"Comparison: {left_value} {operator} {right_value}")

                # Perform comparison
                if operator == "==":
                    return left_value == right_value
                elif operator == "!=":
                    return left_value != right_value
                elif operator == ">":
                    return left_value > right_value
                elif operator == "<":
                    return left_value < right_value
                elif operator == ">=":
                    return left_value >= right_value
                elif operator == "<=":
                    return left_value <= right_value

        # For complex conditions or if simple parsing fails, try the more general approach
        try:
            # Replace expressions with their values
            def replace_expr(match):
                expr = match.group(0)
                value = ExpressionEvaluator.evaluate_expression(
                    expr, state, source_descriptions, additional_context
                )
                if value is True:
                    return "True"
                elif value is False:
                    return "False"
                elif value is None:
                    return "None"
                else:
                    return repr(value)

            # Replace all expressions that start with $
            condition_with_values = re.sub(r"\$[a-zA-Z0-9_.]+", replace_expr, condition)

            # Replace JavaScript-style syntax with Python syntax
            condition_with_values = condition_with_values.replace("||", " or ").replace(
                "&&", " and "
            )
            condition_with_values = condition_with_values.replace(" == null", " == None").replace(
                " != null", " != None"
            )
            condition_with_values = condition_with_values.replace(" == true", " == True").replace(
                " == false", " == False"
            )
            condition_with_values = condition_with_values.replace(" != true", " != True").replace(
                " != false", " != False"
            )

            logger.debug(f"Processed condition for eval: {condition_with_values}")

            # Evaluate the condition
            result = eval(condition_with_values)
            return bool(result)
        except Exception as e:
            logger.error(f"Error evaluating condition {condition}: {e}")
            logger.error(
                f"Processed condition was: {condition_with_values if 'condition_with_values' in locals() else 'N/A'}"
            )
            return False

    @staticmethod
    def process_object_expressions(
        obj: dict, state: ExecutionState, source_descriptions: dict[str, Any] = None
    ) -> dict:
        """Process dictionary values, evaluating any expressions"""
        if not isinstance(obj, dict):
            return obj

        result = {}
        for key, value in obj.items():
            if isinstance(value, str) and value.startswith("$"):
                # Evaluate expression
                result[key] = ExpressionEvaluator.evaluate_expression(
                    value, state, source_descriptions
                )
            elif isinstance(value, dict):
                # Process nested dictionary
                result[key] = ExpressionEvaluator.process_object_expressions(
                    value, state, source_descriptions
                )
            elif isinstance(value, list):
                # Process nested list
                result[key] = ExpressionEvaluator.process_array_expressions(
                    value, state, source_descriptions
                )
            else:
                result[key] = value
        return result

    @staticmethod
    def process_array_expressions(
        arr: list, state: ExecutionState, source_descriptions: dict[str, Any] = None
    ) -> list:
        """Process list values, evaluating any expressions"""
        if not isinstance(arr, list):
            return arr

        result = []
        for item in arr:
            if isinstance(item, str) and item.startswith("$"):
                # Evaluate expression
                result.append(
                    ExpressionEvaluator.evaluate_expression(item, state, source_descriptions)
                )
            elif isinstance(item, dict):
                # Process nested dictionary
                result.append(
                    ExpressionEvaluator.process_object_expressions(item, state, source_descriptions)
                )
            elif isinstance(item, list):
                # Process nested list
                result.append(
                    ExpressionEvaluator.process_array_expressions(item, state, source_descriptions)
                )
            else:
                result.append(item)
        return result
