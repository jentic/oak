import pytest
from oak_runner.executor.step_executor import StepExecutor
from oak_runner.auth.models import SecurityOption, SecurityRequirement

class DummyHTTPClient:
    pass

def make_executor_with_sources(source_descriptions):
    return StepExecutor(
        http_client=DummyHTTPClient(),
        source_descriptions=source_descriptions,
        testing_mode=True,
    )

def test_extract_security_requirements_path_level_override():
    # OpenAPI-like structure with global, path, and operation-level security
    source_descriptions = {
        "api": {
            "security": [
                {"apiKey": []}
            ],
            "paths": {
                "/public/resource": {
                    "security": [],  # Path-level override disables security
                    "get": {
                        "responses": {
                            "200": {"description": "ok"}
                        }
                    }
                },
                "/private/resource": {
                    "get": {
                        "responses": {"200": {"description": "ok"}}
                    }
                }
            },
            "components": {
                "securitySchemes": {
                    "apiKey": {"type": "apiKey", "in": "header", "name": "X-API-KEY"}
                }
            }
        }
    }
    executor = make_executor_with_sources(source_descriptions)

    # Path-level override: should return empty (no security)
    operation_info = {
        "operation": source_descriptions["api"]["paths"]["/public/resource"]["get"],
        "source": "api",
        "path": "/public/resource"
    }
    result = executor._extract_security_requirements(operation_info)
    assert result == [], "Path-level security override (empty array) should disable security requirements"

    # Path without override: should inherit global security
    operation_info_private = {
        "operation": source_descriptions["api"]["paths"]["/private/resource"]["get"],
        "source": "api",
        "path": "/private/resource"
    }
    result_private = executor._extract_security_requirements(operation_info_private)
    assert result_private == [SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])], "Should inherit global security when no path-level override is present"

def test_extract_security_requirements_operation_level():
    # OpenAPI-like structure with operation-level security
    source_descriptions = {
        "api": {
            "security": [
                {"apiKey": []}
            ],
            "paths": {
                "/resource": {
                    "get": {
                        "security": [
                            {"oauth2": ["read"]}
                        ],
                        "responses": {"200": {"description": "ok"}}
                    },
                    "post": {
                        "responses": {"200": {"description": "ok"}}
                    }
                }
            },
            "components": {
                "securitySchemes": {
                    "apiKey": {"type": "apiKey", "in": "header", "name": "X-API-KEY"},
                    "oauth2": {"type": "oauth2", "flows": {"implicit": {"authorizationUrl": "https://example.com", "scopes": {"read": "Read access"}}}}
                }
            }
        }
    }
    executor = make_executor_with_sources(source_descriptions)

    # Operation-level security: should use operation security
    operation_info_op = {
        "operation": source_descriptions["api"]["paths"]["/resource"]["get"],
        "source": "api",
        "path": "/resource"
    }
    result_op = executor._extract_security_requirements(operation_info_op)
    # Should match the operation-level security
    assert result_op == [SecurityOption(requirements=[SecurityRequirement(scheme_name="oauth2", scopes=["read"])])], "Operation-level security should take precedence and match oauth2 scheme"

def test_extract_security_requirements_global_level():
    # OpenAPI-like structure with global security only
    source_descriptions = {
        "api": {
            "security": [
                {"apiKey": []}
            ],
            "paths": {
                "/resource": {
                    "post": {
                        "responses": {"200": {"description": "ok"}}
                    }
                }
            },
            "components": {
                "securitySchemes": {
                    "apiKey": {"type": "apiKey", "in": "header", "name": "X-API-KEY"}
                }
            }
        }
    }
    executor = make_executor_with_sources(source_descriptions)

    # No operation-level security: should use global
    operation_info_global = {
        "operation": source_descriptions["api"]["paths"]["/resource"]["post"],
        "source": "api",
        "path": "/resource"
    }
    result_global = executor._extract_security_requirements(operation_info_global)
    assert result_global == [SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])], "Global security should apply and match apiKey scheme"
