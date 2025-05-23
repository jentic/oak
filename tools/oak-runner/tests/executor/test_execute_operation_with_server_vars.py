#!/usr/bin/env python3
"""
Tests for step_executor.py execute_operation function with server variables and path params
"""

import pytest
from unittest.mock import MagicMock, patch
import logging
import os
from typing import Dict, Any, Optional

from oak_runner.models import ServerConfiguration, ServerVariable, RuntimeParams
from oak_runner.executor.server_processor import ServerProcessor
from oak_runner.executor.step_executor import StepExecutor
from oak_runner.http import HTTPExecutor
from oak_runner.models import ExecutionState

# Create utility functions similar to those in test_server_processor.py
def _create_server_variable(
    name: str,
    default_value: Optional[str] = None, 
    enum_values: Optional[list[str]] = None,
    description: Optional[str] = None
) -> ServerVariable:
    kwargs = {}
    if default_value is not None:
        kwargs['default_value'] = default_value
    if enum_values is not None:
        kwargs['enum_values'] = enum_values
    if description is not None:
        kwargs['description'] = description
    return ServerVariable(**kwargs)

# Helper to create ServerConfiguration instances easily for tests
def _create_server_config(
    url_template: str, 
    variables: Optional[Dict[str, ServerVariable]] = None,
    api_title_prefix: Optional[str] = None,
    description: Optional[str] = None
) -> ServerConfiguration:
    kwargs = {'url_template': url_template}
    if variables is not None:
        kwargs['variables'] = variables
    else:
        kwargs['variables'] = {}
    if api_title_prefix is not None:
        kwargs['api_title_prefix'] = api_title_prefix
    if description is not None:
        kwargs['description'] = description
    return ServerConfiguration(**kwargs)


@pytest.fixture
def mock_env(monkeypatch):
    """Fixture to mock environment variables safely."""
    original_env = os.environ.copy()
    yield monkeypatch
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_http_client():
    """Fixture to create a mock HTTP client for testing."""
    client = MagicMock(spec=HTTPExecutor)
    # Configure the mock to return a successful response by default
    client.execute_request.return_value = {
        "status_code": 200,
        "headers": {"Content-Type": "application/json"},
        "body": {"result": "success"},
    }
    return client


@pytest.fixture
def mock_source_descriptions():
    """Fixture to create mock source descriptions with server configs for testing."""
    
    # Create a mock OpenAPI document with server variables
    api_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "MyAPI",
            "version": "1.0.0",
        },
        "servers": [
            {
                "url": "https://api.{instance}.com",
                "description": "API server with instance variable",
                "variables": {
                    "instance": {
                        "default": "default",
                        "description": "API instance name"
                    }
                }
            }
        ],
        "paths": {
            "/resource/{id}": {
                "get": {
                    "operationId": "getResource",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "result": {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/users/{username}": {
                "get": {
                    "operationId": "getUser",
                    "parameters": [
                        {
                            "name": "username",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response"
                        }
                    }
                }
            }
        }
    }
    
    return {"myapi": api_spec}


def test_execute_operation_with_server_vars_and_path_params(
    mock_http_client, mock_source_descriptions, mock_env
):
    """Test executing an operation with server variables and path parameters."""
    
    # Set up the environment variable for server instance
    mock_env.setenv("MYAPI_OAK_SERVER_INSTANCE", "customerA")
    
    # Create a StepExecutor with our mocks
    executor = StepExecutor(
        http_client=mock_http_client,
        source_descriptions=mock_source_descriptions,
        testing_mode=True,
    )
    
    # Create operation details similar to what operation_finder would return
    operation_details = {
        "method": "GET",
        "url": "/resource/{id}",
        "source": "myapi",
        "operationId": "getResource",
    }
    
    # Test executing the operation with path parameters
    response = executor.execute_operation(
        operation_id="getResource",
        inputs={"id": "12345"},
        runtime_params=RuntimeParams(servers={"MYAPI_OAK_SERVER_INSTANCE": "customerA"})
    )
    
    # Verify the HTTP client was called with the correct URL
    mock_http_client.execute_request.assert_called_once()
    call_args = mock_http_client.execute_request.call_args[1]
    
    # The URL should have the server variable resolved but keep the path parameter
    assert "https://api.customerA.com" in call_args["url"]
    assert "/resource/" in call_args["url"]
    
    # Parameters are separated by type in the API
    assert call_args["parameters"]["path"]["id"] == "12345"


def test_execute_operation_maintain_path_params(
    mock_http_client, mock_source_descriptions, mock_env
):
    """
    Test that path parameters are not replaced when they have the same name as server variables.
    This is similar to the failing test_resolve_dont_change_path_same_key_name test.
    """
    
    # Set up the environment variable for server instance
    mock_env.setenv("MYAPI_OAK_SERVER_INSTANCE", "customerA")
    
    # We need to modify the mock source descriptions to include our specific test path
    # Add a path with a parameter named "instance" (same as server variable)
    mock_source_descriptions["myapi"]["paths"]["/users/{instance}"] = {
        "get": {
            "operationId": "getUserByInstance",
            "parameters": [
                {
                    "name": "instance",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"}
                }
            ],
            "responses": {
                "200": {
                    "description": "Successful response"
                }
            }
        }
    }
    
    # Create a StepExecutor with our mocks
    executor = StepExecutor(
        http_client=mock_http_client,
        source_descriptions=mock_source_descriptions,
        testing_mode=True,
    )
    
    # Execute the operation directly
    response = executor.execute_operation(
        operation_id="getUserByInstance",
        inputs={"instance": "user123"},
        runtime_params=RuntimeParams(servers={"MYAPI_OAK_SERVER_INSTANCE": "customerA"})
    )
    
    # Verify that the HTTP client was called
    mock_http_client.execute_request.assert_called()
    
    # Get the arguments passed to the HTTP client
    call_args = mock_http_client.execute_request.call_args[1]
    
    assert call_args["parameters"]["path"]["instance"] == "user123"


def test_server_processor_direct_with_path_params(mock_env):
    """
    Direct test of the ServerProcessor to verify how it handles path parameters.
    """
    mock_env.setenv("MYAPI_OAK_SERVER_INSTANCE", "customerA")
    
    # Create a server configuration with both server variable and path parameter
    sv_instance = _create_server_variable(name="instance")
    config = _create_server_config(
        "https://api.{instance}.com/{path}",
        variables={"instance": sv_instance},
        api_title_prefix="MYAPI"
    )
    
    # Add a path variable to the server config
    path_var = _create_server_variable(name="path", default_value="default_path")
    config.variables["path"] = path_var
    
    # Now the server config has both 'instance' and 'path' variables
    resolved_url = ServerProcessor.resolve_server_base_url(config)
    
    assert resolved_url == "https://api.customerA.com/default_path"
    
    # Test same name variable
    sv_instance = _create_server_variable(name="instance")
    config = _create_server_config(
        "https://api.{instance}.com/{instance}",
        variables={"instance": sv_instance},
        api_title_prefix="MYAPI"
    )
    
    resolved_url = ServerProcessor.resolve_server_base_url(config)
    assert resolved_url == "https://api.customerA.com/customerA"