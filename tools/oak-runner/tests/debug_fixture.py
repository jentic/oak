#!/usr/bin/env python3
"""
Debug script for Arazzo fixtures to understand any issues
"""

import json
import logging
import os

from oak_runner import OAKRunner

from .mocks.http_client import MockHTTPExecutor

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("arazzo-debug")


def debug_login_fixture():
    """Debug the login workflow fixture"""
    # Path to fixture
    fixture_dir = os.path.join(os.path.dirname(__file__), "fixtures", "sample_login_workflow")

    # Load Arazzo spec
    arazzo_path = os.path.join(fixture_dir, "login_workflow.yaml")

    # Load OpenAPI spec
    openapi_path = os.path.join(fixture_dir, "login_api.yaml")

    # Create mock HTTP client
    http_client = MockHTTPExecutor()

    # Add direct mocks for the endpoints with full URLs
    http_client.add_static_response(
        method="post",
        url_pattern="https://api.example.com/v1/login",
        status_code=200,
        json_data={
            "token": "test-token-123",
            "user_id": "user-456",
            "expires_at": "2025-12-31T23:59:59Z",
        },
    )

    http_client.add_static_response(
        method="get",
        url_pattern="https://api.example.com/v1/profile",
        status_code=200,
        json_data={
            "user_id": "user-456",
            "name": "Test User",
            "email": "test@example.com",
            "created_at": "2023-01-01T00:00:00Z",
        },
    )

    # Display all registered matchers
    logger.debug("Registered matchers:")
    for i, (matcher, _) in enumerate(http_client.matchers):
        logger.debug(f"  {i+1}: {matcher.method} {matcher.url_pattern.pattern}")

    # Create OAK Runner
    runner = OAKRunner(arazzo_path, http_client=http_client)

    # Execute workflow
    workflow_id = "loginWorkflow"
    inputs = {"username": "testuser", "password": "password123"}

    logger.debug(f"Starting workflow execution: {workflow_id}")
    execution_id = runner.start_workflow(workflow_id, inputs)

    # Execute steps one by one
    step_count = 0
    while step_count < 10:  # Maximum of 10 steps to prevent infinite loops
        step_count += 1
        result = runner.execute_next_step(execution_id)
        logger.debug(f"Step execution result: {result}")

        # Check for completion
        if result["status"] == "workflow_complete":
            logger.debug("Workflow complete")
            break

    # Print final state
    state = runner.execution_states[execution_id]
    logger.debug(f"Step outputs: {state.step_outputs}")
    logger.debug(f"Workflow outputs: {state.workflow_outputs}")
    logger.debug(f"Step statuses: {state.status}")

    # Access workflow outputs directly from state, which should include all relevant outputs
    # without requiring special handling for specific step outputs
    workflow_outputs = state.workflow_outputs

    # For backward compatibility during debugging, let's also log the individual values
    # that we're interested in from flattened step outputs
    token_value = workflow_outputs.get("token") or state.step_outputs.get("loginStep", {}).get(
        "token"
    )
    user_id = workflow_outputs.get("userId") or state.step_outputs.get("profileStep", {}).get(
        "userId"
    )
    name = workflow_outputs.get("name") or state.step_outputs.get("profileStep", {}).get("name")
    email = workflow_outputs.get("email") or state.step_outputs.get("profileStep", {}).get("email")

    # Check what we got
    logger.debug(f"Token: {token_value}")
    logger.debug(f"User ID: {user_id}")
    logger.debug(f"Name: {name}")
    logger.debug(f"Email: {email}")

    # Print API call summary
    logger.debug("API Call Summary:")
    for i, request in enumerate(http_client.requests, 1):
        logger.debug(f"{i}. {request['method'].upper()} {request['url']}")

        if "headers" in request["kwargs"] and request["kwargs"]["headers"]:
            logger.debug(f"   Headers: {request['kwargs']['headers']}")

        if "json" in request["kwargs"] and request["kwargs"]["json"]:
            logger.debug(f"   Body: {json.dumps(request['kwargs']['json'], indent=2)}")


if __name__ == "__main__":
    debug_login_fixture()
