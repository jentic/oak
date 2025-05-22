import pytest
import os
import logging
from typing import Dict, Optional, List

from oak_runner.models import ServerConfiguration, ServerVariable
from oak_runner.executor.server_processor import ServerProcessor

# Helper to create ServerVariable instances easily for tests
def _create_server_variable(
    name: str,
    default_value: Optional[str] = None, 
    enum_values: Optional[List[str]] = None,
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


# Test Cases

def test_resolve_with_runtime_param(mock_env):
    sv_region = _create_server_variable(name="region")
    config = _create_server_config("https://{region}.api.com/v1", variables={"region": sv_region})
    resolved_url = ServerProcessor.resolve_server_base_url(config, server_runtime_params={"OAK_SERVER_REGION": "us-west"})
    assert resolved_url == "https://us-west.api.com/v1"

def test_resolve_with_env_var_no_prefix(mock_env):
    mock_env.setenv("OAK_SERVER_ENDPOINT", "prod-server")
    sv_endpoint = _create_server_variable(name="endpoint")
    config = _create_server_config("https://{endpoint}.example.com", variables={"endpoint": sv_endpoint})
    resolved_url = ServerProcessor.resolve_server_base_url(config)
    assert resolved_url == "https://prod-server.example.com"

def test_resolve_with_env_var_with_prefix(mock_env):
    mock_env.setenv("MYAPI_OAK_SERVER_INSTANCE", "customerA")
    sv_instance = _create_server_variable(name="instance")
    config = _create_server_config(
        "https://api.{instance}.com", 
        variables={"instance": sv_instance}, 
        api_title_prefix="MYAPI"
    )
    resolved_url = ServerProcessor.resolve_server_base_url(config)
    assert resolved_url == "https://api.customerA.com"

def test_resolve_with_default_value(mock_env):
    sv_version = _create_server_variable(name="version", default_value="v2.api.com")
    config = _create_server_config("{version}/api", variables={"version": sv_version})
    resolved_url = ServerProcessor.resolve_server_base_url(config)
    assert resolved_url == "v2.api.com/api"

def test_resolve_precedence_runtime_over_env_over_default(mock_env):
    mock_env.setenv("OAK_SERVER_HOST", "env-host")
    sv_host = _create_server_variable(name="host", default_value="default-host")
    config = _create_server_config(
        "{host}/data", 
        variables={"host": sv_host}
    )
    resolved_url = ServerProcessor.resolve_server_base_url(config, server_runtime_params={"OAK_SERVER_HOST": "runtime-host"})
    assert resolved_url == "runtime-host/data"

    mock_env.delenv("OAK_SERVER_HOST", raising=False) # Remove runtime to test env
    mock_env.setenv("OAK_SERVER_HOST", "env-host-only")
    resolved_url_env = ServerProcessor.resolve_server_base_url(config)
    assert resolved_url_env == "env-host-only/data"

def test_resolve_precedence_runtime_over_default(mock_env):
    sv_path = _create_server_variable(name="path", default_value="default_path")
    config = _create_server_config("/api/{path}", variables={"path": sv_path})
    resolved_url = ServerProcessor.resolve_server_base_url(config, server_runtime_params={"OAK_SERVER_PATH": "runtime_path"})
    assert resolved_url == "/api/runtime_path"

def test_resolve_precedence_env_over_default(mock_env):
    mock_env.setenv("OAK_SERVER_STAGE", "prod")
    sv_stage = _create_server_variable(name="stage", default_value="dev")
    config = _create_server_config("/{stage}/service", variables={"stage": sv_stage})
    resolved_url = ServerProcessor.resolve_server_base_url(config)
    assert resolved_url == "/prod/service"

def test_resolve_missing_required_variable_raises_value_error(mock_env):
    sv_tenant = _create_server_variable(name="tenant") # No default, no env, no runtime for this
    config = _create_server_config("https://{tenant}.company.com", variables={"tenant": sv_tenant})
    with pytest.raises(ValueError):
        ServerProcessor.resolve_server_base_url(config)

def test_resolve_missing_required_variable_with_prefix_raises_value_error(mock_env):
    sv_user = _create_server_variable(name="user")
    config = _create_server_config(
        "/{user}/profile", 
        variables={"user": sv_user}, 
        api_title_prefix="PORTAL"
    )
    with pytest.raises(ValueError):
        ServerProcessor.resolve_server_base_url(config)

def test_resolve_static_url_no_variables(mock_env):
    config = _create_server_config("https://api.example.com/fixed")
    resolved_url = ServerProcessor.resolve_server_base_url(config)
    assert resolved_url == "https://api.example.com/fixed"

def test_resolve_variable_in_url_but_not_defined_in_variables_raises_error(mock_env):
    # URL template has {undefined_var}, but 'variables' dict is empty
    config = _create_server_config("https://{undefined_var}.api.com", variables={})
    with pytest.raises(ValueError):
        ServerProcessor.resolve_server_base_url(config)

def test_resolve_variable_defined_but_not_in_url(mock_env):
    sv_unused = _create_server_variable(name="unused_var", default_value="ignore_me")
    config = _create_server_config("https://static.url.com", variables={"unused_var": sv_unused})
    resolved_url = ServerProcessor.resolve_server_base_url(config)
    assert resolved_url == "https://static.url.com"

def test_resolve_multiple_variables(mock_env):
    mock_env.setenv("OAK_SERVER_PORT", "8080")
    sv_scheme = _create_server_variable(name="scheme", default_value="http")
    sv_host = _create_server_variable(name="host") # To be provided by runtime
    sv_port = _create_server_variable(name="port") # To be provided by env
    sv_basepath = _create_server_variable(name="basepath", default_value="api")

    config = _create_server_config(
        "{scheme}://{host}:{port}/{basepath}/v1",
        variables={
            "scheme": sv_scheme,
            "host": sv_host,
            "port": sv_port,
            "basepath": sv_basepath
        }
    )
    resolved_url = ServerProcessor.resolve_server_base_url(config, server_runtime_params={"OAK_SERVER_HOST": "localhost", "OAK_SERVER_BASEPATH": "custom_api"})
    assert resolved_url == "http://localhost:8080/custom_api/v1"
