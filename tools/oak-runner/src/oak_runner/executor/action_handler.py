#!/usr/bin/env python3
"""
Action Handler for OAK Runner

This module provides functionality to determine the next action after a step execution.
"""

import logging
import re
from typing import Any

import jsonpath_ng.ext as jsonpath

from ..evaluator import ExpressionEvaluator
from ..models import ActionType, ExecutionState

# Configure logging
logger = logging.getLogger("arazzo-runner.executor")


class ActionHandler:
    """Determines the next action after a step execution"""

    def __init__(self, source_descriptions: dict[str, Any]):
        """
        Initialize the action handler

        Args:
            source_descriptions: OpenAPI source descriptions
        """
        self.source_descriptions = source_descriptions

    def determine_next_action(self, step: dict, success: bool, state: ExecutionState) -> dict:
        """
        Determine the next action based on step success/failure

        Args:
            step: Step definition
            success: Whether the step succeeded
            state: Current execution state

        Returns:
            Dictionary with action type and parameters
        """
        step_id = step.get("stepId", "unknown")
        logger.debug(f"Determining next action for step {step_id}, success={success}")

        if success:
            # Check onSuccess actions
            actions = step.get("onSuccess", [])
            logger.info(f"Step {step_id} has {len(actions)} onSuccess actions")

            for i, action in enumerate(actions):
                action_name = action.get("name", f"action_{i}")
                action_type = action.get("type", "unknown")
                logger.info(f"Checking action {action_name} of type {action_type}")

                # Check if action has criteria
                if "criteria" in action:
                    criteria = action.get("criteria", [])
                    logger.info(f"Action {action_name} has {len(criteria)} criteria")
                    criteria_met = self._check_action_criteria(criteria, state)

                    if not criteria_met:
                        logger.info(f"Action {action_name} criteria not met, skipping")
                        continue
                    else:
                        logger.info(f"Action {action_name} criteria met, executing")

                # Process the action
                action_type = action.get("type")
                if action_type == "end":
                    logger.info(f"Action {action_name} ends the workflow")
                    return {"type": ActionType.END}
                elif action_type == "goto":
                    if "workflowId" in action:
                        target = action.get("workflowId")
                        logger.info(f"Action {action_name} goes to workflow {target}")
                        return {"type": ActionType.GOTO, "workflow_id": target}
                    elif "stepId" in action:
                        target = action.get("stepId")
                        logger.info(f"Action {action_name} goes to step {target}")
                        return {"type": ActionType.GOTO, "step_id": target}

            # No matching action, continue to next step
            logger.info(f"No matching action for step {step_id}, continuing to next step")
            return {"type": ActionType.CONTINUE}
        else:
            # Check onFailure actions
            actions = step.get("onFailure", [])
            logger.debug(f"Step {step_id} has {len(actions)} onFailure actions")

            for i, action in enumerate(actions):
                action_name = action.get("name", f"failure_action_{i}")
                action_type = action.get("type", "unknown")
                logger.info(f"Checking failure action {action_name} of type {action_type}")

                # Check if action has criteria
                if "criteria" in action:
                    criteria = action.get("criteria", [])
                    logger.info(f"Failure action {action_name} has {len(criteria)} criteria")
                    criteria_met = self._check_action_criteria(criteria, state)

                    if not criteria_met:
                        logger.info(f"Failure action {action_name} criteria not met, skipping")
                        continue
                    else:
                        logger.info(f"Failure action {action_name} criteria met, executing")

                # Process the action
                action_type = action.get("type")
                if action_type == "end":
                    logger.info(f"Failure action {action_name} ends the workflow")
                    return {"type": ActionType.END}
                elif action_type == "goto":
                    if "workflowId" in action:
                        target = action.get("workflowId")
                        logger.info(f"Failure action {action_name} goes to workflow {target}")
                        return {"type": ActionType.GOTO, "workflow_id": target}
                    elif "stepId" in action:
                        target = action.get("stepId")
                        logger.info(f"Failure action {action_name} goes to step {target}")
                        return {"type": ActionType.GOTO, "step_id": target}
                elif action_type == "retry":
                    retry_after = action.get("retryAfter", 0)
                    retry_limit = action.get("retryLimit", 1)
                    logger.info(
                        f"Failure action {action_name} retries (after={retry_after}, limit={retry_limit})"
                    )

                    result = {
                        "type": ActionType.RETRY,
                        "retry_after": retry_after,
                        "retry_limit": retry_limit,
                    }

                    if "workflowId" in action:
                        target = action.get("workflowId")
                        logger.info(f"Retry action targets workflow {target}")
                        result["workflow_id"] = target
                    elif "stepId" in action:
                        target = action.get("stepId")
                        logger.info(f"Retry action targets step {target}")
                        result["step_id"] = target

                    return result

            # No matching action, end the workflow with failure
            logger.warning(
                f"No matching failure action for step {step_id}, ending workflow with failure"
            )
            return {"type": ActionType.END}

    def _check_action_criteria(self, criteria: list[dict], state: ExecutionState) -> bool:
        """
        Check if action criteria are met

        Args:
            criteria: List of criteria to check
            state: Current execution state

        Returns:
            True if all criteria are met, False otherwise
        """
        logger.info(f"Checking {len(criteria)} action criteria")

        # Context for evaluating criteria
        context = {}

        # Check each criterion
        for i, criterion in enumerate(criteria):
            condition = criterion.get("condition")
            criterion_type = criterion.get("type", "simple")

            logger.info(f"Criterion {i+1}: type={criterion_type}, condition={condition}")

            # Evaluate context if specified
            if "context" in criterion:
                context_expr = criterion.get("context")
                context_value = ExpressionEvaluator.evaluate_expression(
                    context_expr, state, self.source_descriptions, context
                )
                logger.info(f"Context expression {context_expr} evaluated to: {context_value}")
                if context_value is None:
                    logger.warning(f"Context expression {context_expr} evaluated to None")
                    return False
                local_context = context_value
            else:
                # Use default context for current action
                local_context = context

            # Check criterion based on type
            if criterion_type == "simple":
                result = ExpressionEvaluator.evaluate_simple_condition(
                    condition, state, self.source_descriptions, context
                )
                if not result:
                    logger.warning(f"Simple condition failed: {condition}")
                    return False
                logger.info(f"Simple condition passed: {condition}")

            elif criterion_type == "jsonpath":
                if not local_context or not condition:
                    logger.warning("JSONPath condition failed: empty context or condition")
                    return False

                try:
                    logger.info(f"Evaluating JSONPath condition: {condition}")
                    logger.info(f"Context type: {type(local_context)}, Content: {local_context}")

                    # Special handling for count expressions (common in workflows)
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
                            if isinstance(local_context, dict) and property_name in local_context:
                                array_value = local_context[property_name]

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
                                f"Count evaluation: property={property_name}, count={count}, op={operator}, value={value}"
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
                                logger.warning(f"Unsupported operator: {operator}")
                                return False

                            if not result:
                                logger.warning(
                                    f"Count comparison failed: {count} {operator} {value}"
                                )
                                return False

                            logger.info(f"Count comparison succeeded: {count} {operator} {value}")
                            continue

                    # Standard JSONPath evaluation
                    jsonpath_expr = jsonpath.parse(condition)
                    matches = [match.value for match in jsonpath_expr.find(local_context)]

                    logger.info(f"JSONPath matches: {matches}")

                    if not matches:
                        logger.warning(f"JSONPath condition failed: no matches for {condition}")
                        return False

                    logger.info(f"JSONPath condition passed: {condition}")
                except Exception as e:
                    logger.error(f"Error evaluating JSONPath expression: {e}")
                    return False

            elif criterion_type == "regex":
                if not local_context or not condition:
                    logger.warning("Regex condition failed: empty context or condition")
                    return False

                # Convert context to string if needed
                ctx_str = str(local_context)

                # Check if the regex pattern matches
                match = re.search(condition, ctx_str)
                if not match:
                    logger.warning(f"Regex condition failed: {condition} did not match {ctx_str}")
                    return False

                logger.info(f"Regex condition passed: {condition}")

            else:
                logger.warning(f"Unsupported criterion type: {criterion_type}")
                return False

        # All criteria passed
        logger.info("All criteria passed")
        return True
