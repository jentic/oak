#!/usr/bin/env python3
"""
Success Criteria Checker for OAK Runner

This module provides functionality to check if API responses meet success criteria.
"""

import logging
import re
from typing import Any

import jsonpath_ng.ext as jsonpath

from ..evaluator import ExpressionEvaluator
from ..models import ExecutionState

# Configure logging
logger = logging.getLogger("arazzo-runner.executor")


class SuccessCriteriaChecker:
    """Checks if API responses meet success criteria"""

    def __init__(self, source_descriptions: dict[str, Any]):
        """
        Initialize the success criteria checker

        Args:
            source_descriptions: OpenAPI source descriptions
        """
        self.source_descriptions = source_descriptions

    def check_success_criteria(self, step: dict, response: dict, state: ExecutionState) -> bool:
        """
        Check if the response meets the success criteria

        Args:
            step: Step definition
            response: Response to check
            state: Current execution state

        Returns:
            True if success criteria are met, False otherwise
        """
        criteria = step.get("successCriteria", [])

        if not criteria:
            # Default success criterion: status code 2xx
            return 200 <= response["status_code"] < 300

        # Log all success criteria for debugging
        logger.debug(f"Checking success criteria: {criteria}")

        # Context for evaluating expressions
        context = {
            "statusCode": response["status_code"],
            "response": response,
            "headers": response["headers"],
            "body": response["body"],
        }

        # Check all criteria
        for criterion in criteria:
            condition = criterion.get("condition")
            criterion_type = criterion.get("type", "simple")
            criterion_context = None

            logger.debug(f"Evaluating criterion: {condition} (type: {criterion_type})")

            # Special handling for conditions that use JSON pointer syntax
            if (
                criterion_type == "simple"
                and isinstance(condition, str)
                and condition.startswith("$response.body#/")
            ):
                try:
                    # Handle patterns like $response.body#/path/to/value == value
                    import jsonpointer

                    # Parse left and right sides of the comparison
                    match = re.match(r"^\$response\.body#(/.*?)\s*([=!<>]+)\s*(.*)$", condition)
                    if match:
                        pointer_path, operator, right_value = match.groups()
                        body = response.get("body", {})

                        # Get the value from the response using the JSON pointer
                        pointer = jsonpointer.JsonPointer(pointer_path)
                        left_value = pointer.resolve(body)

                        # Eval the right side if it looks like a variable
                        if right_value.startswith("$"):
                            right_value = ExpressionEvaluator.evaluate_expression(
                                right_value, state, self.source_descriptions, context
                            )
                        else:
                            # Try to evaluate literals (booleans, numbers, etc.)
                            try:
                                right_value = eval(right_value)
                            except:
                                # If it's not a valid Python expression, treat as string
                                right_value = right_value.strip("\"'")

                        # Perform the comparison
                        logger.debug(
                            f"JSON Pointer comparison: {left_value} {operator} {right_value}"
                        )
                        if operator == "==":
                            result = left_value == right_value
                        elif operator == "!=":
                            result = left_value != right_value
                        elif operator == ">":
                            result = left_value > right_value
                        elif operator == "<":
                            result = left_value < right_value
                        elif operator == ">=":
                            result = left_value >= right_value
                        elif operator == "<=":
                            result = left_value <= right_value
                        else:
                            logger.warning(
                                f"Unsupported operator in JSON pointer condition: {operator}"
                            )
                            result = False

                        if not result:
                            logger.debug(f"Criterion failed: {condition}")
                            return False

                        # Skip the normal evaluation since we handled it manually
                        continue
                except Exception as e:
                    logger.error(f"Error evaluating JSON pointer condition {condition}: {e}")

            if "context" in criterion:
                context_expr = criterion.get("context")
                criterion_context = ExpressionEvaluator.evaluate_expression(
                    context_expr, state, self.source_descriptions, context
                )
            else:
                criterion_context = context

            if criterion_type == "simple":
                # Evaluate the condition as a simple expression
                result = ExpressionEvaluator.evaluate_simple_condition(
                    condition, state, self.source_descriptions, context
                )
                if not result:
                    logger.debug(f"Simple criterion failed: {condition}")
                    return False
            elif criterion_type == "regex":
                # Evaluate the condition as a regex pattern
                if not criterion_context or not condition:
                    return False

                # Convert context to string if needed
                ctx_str = str(criterion_context)

                # Check if the regex pattern matches
                match = re.search(condition, ctx_str)
                if not match:
                    return False
            elif criterion_type == "jsonpath":
                # Evaluate the condition as a JSONPath expression
                if not criterion_context or not condition:
                    logger.warning("JSONPath condition failed: empty context or condition")
                    return False

                # Handle jsonpath condition
                result = self._evaluate_jsonpath_condition(condition, criterion_context)
                if not result:
                    return False
            elif criterion_type == "xpath":
                # Evaluate the condition as an XPath expression
                # This would require an XML parser like lxml
                logger.warning("XPath evaluation not implemented")
                return False

        # All criteria passed
        return True

    def _evaluate_jsonpath_condition(self, condition: str, context: Any) -> bool:
        """
        Evaluate a JSONPath condition

        Args:
            condition: JSONPath condition to evaluate
            context: Context to evaluate against

        Returns:
            True if condition is met, False otherwise
        """
        try:
            logger.info(f"Evaluating JSONPath condition: {condition}")
            logger.info(f"Context type: {type(context)}, Content: {context}")

            # Special handling for count expressions that JSONPath library might have trouble with
            if condition.startswith("$[?count(@.") and ")" in condition:
                # Parse count expression like $[?count(@.products) > 0]
                match = re.match(
                    r"\$\[\?count\(\@\.([a-zA-Z0-9_]+)\) *([<>=!]+) *(\d+)\]", condition
                )
                if match:
                    property_name, operator, value_str = match.groups()
                    value = int(value_str)

                    # Get property value
                    array_value = None
                    if isinstance(context, dict) and property_name in context:
                        array_value = context[property_name]

                    # Count items if it's a list
                    if isinstance(array_value, list):
                        count = len(array_value)
                    elif array_value is not None:
                        # If not a list but not None, treat as 1 item
                        count = 1
                    else:
                        # If property doesn't exist or is None, count is 0
                        count = 0

                    logger.info(
                        f"Count expression: property={property_name}, count={count}, op={operator}, value={value}"
                    )

                    # Evaluate the comparison
                    if operator == "==":
                        result = count == value
                    elif operator == "!=":
                        result = count != value
                    elif operator == ">":
                        result = count > value
                    elif operator == "<":
                        result = count < value
                    elif operator == ">=":
                        result = count >= value
                    elif operator == "<=":
                        result = count <= value
                    else:
                        logger.warning(f"Unsupported operator in count expression: {operator}")
                        return False

                    if not result:
                        logger.warning(f"Count comparison failed: {count} {operator} {value}")
                        return False

                    logger.info(f"Count comparison succeeded: {count} {operator} {value}")
                    return True

            # If not a special case, use standard JSONPath library
            jsonpath_expr = jsonpath.parse(condition)
            matches = [match.value for match in jsonpath_expr.find(context)]

            logger.info(f"JSONPath matches: {matches}")

            if not matches:
                logger.warning(f"JSONPath condition returned no matches: {condition}")
                return False

            logger.info(f"JSONPath condition succeeded: {condition}")
            return True
        except Exception as e:
            logger.error(f"Error evaluating JSONPath expression {condition}: {e}")
            logger.error(f"Context was: {context}")
            # For debugging, try simple approach if standard fails
            try:
                if condition == "$[?count(@.products) > 0]" and isinstance(context, dict):
                    products = context.get("products", [])
                    count = len(products) if isinstance(products, list) else 0
                    logger.info(f"Fallback count check: {count} > 0 = {count > 0}")
                    return count > 0
            except Exception as fallback_err:
                logger.error(f"Fallback approach also failed: {fallback_err}")
            return False
