import unittest
from oak_runner.executor.operation_finder import OperationFinder
from oak_runner.auth.models import SecurityOption, SecurityRequirement
import pytest
from oak_runner.auth.auth_processor import AuthProcessor

# Mock OpenAPI source descriptions
MOCK_SOURCE_DESC = {
    "api_one": {
        "servers": [{"url": "http://localhost"}],
        "paths": {
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "summary": "List all users"
                },
                "post": {
                    "operationId": "createUser",
                    "summary": "Create a new user"
                }
            },
            "/users/{userId}": {
                "get": {
                    "operationId": "getUserById",
                    "summary": "Get user by ID"
                },
                "delete": {
                    "operationId": "deleteUser",
                    "summary": "Delete user by ID"
                }
            }
        }
    },
    "api_two": {
        "servers": [{"url": "http://localhost:8080"}],
        "paths": {
            "/items": {
                "get": {
                    "operationId": "listItems",
                    "summary": "List all items"
                }
            }
        }
    }
}

def make_finder_with_sources(source_descriptions):
    return OperationFinder(source_descriptions)

def test_extract_security_requirements_path_level_override():
    source_descriptions = {
        "api": {
            "security": [
                {"apiKey": []}
            ],
            "paths": {
                "/public/resource": {
                    "security": [],
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
    finder = make_finder_with_sources(source_descriptions)

    operation_info = {
        "operation": source_descriptions["api"]["paths"]["/public/resource"]["get"],
        "source": "api",
        "path": "/public/resource"
    }
    result = finder.extract_security_requirements(operation_info)
    assert result == [], "Path-level security override (empty array) should disable security requirements"

    operation_info_private = {
        "operation": source_descriptions["api"]["paths"]["/private/resource"]["get"],
        "source": "api",
        "path": "/private/resource"
    }
    result_private = finder.extract_security_requirements(operation_info_private)
    assert result_private == [SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])], "Should inherit global security when no path-level override is present"

def test_extract_security_requirements_operation_level():
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
    finder = make_finder_with_sources(source_descriptions)

    operation_info_op = {
        "operation": source_descriptions["api"]["paths"]["/resource"]["get"],
        "source": "api",
        "path": "/resource"
    }
    result_op = finder.extract_security_requirements(operation_info_op)
    assert result_op == [SecurityOption(requirements=[SecurityRequirement(scheme_name="oauth2", scopes=["read"])])], "Operation-level security should take precedence and match oauth2 scheme"

def test_extract_security_requirements_global_level():
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
    finder = make_finder_with_sources(source_descriptions)

    operation_info_global = {
        "operation": source_descriptions["api"]["paths"]["/resource"]["post"],
        "source": "api",
        "path": "/resource"
    }
    result_global = finder.extract_security_requirements(operation_info_global)
    assert result_global == [SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])], "Global security should apply and match apiKey scheme"

class TestOperationFinderHttpPath(unittest.TestCase):

    def setUp(self):
        """Set up the test case with OperationFinder instance."""
        self.finder = OperationFinder(MOCK_SOURCE_DESC)

    def test_find_exact_path_and_method_success(self):
        """Test finding an operation with exact path and method match."""
        result = self.finder.find_by_http_path_and_method("/users", "GET")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "api_one")
        self.assertEqual(result["path"], "/users")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["operationId"], "listUsers")
        self.assertEqual(result["url"], "http://localhost/users")

    def test_find_template_path_and_method_success(self):
        """Test finding an operation with a template path and method match."""
        # Note: Current implementation uses simple segment check, might need adjustment
        result = self.finder.find_by_http_path_and_method("/users/123", "DELETE")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "api_one")
        self.assertEqual(result["path"], "/users/{userId}") # Should return template path
        self.assertEqual(result["method"], "delete")
        self.assertEqual(result["operationId"], "deleteUser")
        self.assertEqual(result["url"], "http://localhost/users/{userId}")

    def test_find_case_insensitive_method_success(self):
        """Test finding an operation with a case-insensitive method match."""
        result = self.finder.find_by_http_path_and_method("/users", "post") # Lowercase 'post'
        self.assertIsNotNone(result)
        self.assertEqual(result["method"], "post")
        self.assertEqual(result["operationId"], "createUser")

    def test_find_path_exists_method_missing(self):
        """Test finding when path exists but the requested method does not."""
        result = self.finder.find_by_http_path_and_method("/users", "PUT")
        self.assertIsNone(result)

    def test_find_path_missing(self):
        """Test finding when the requested path does not exist."""
        result = self.finder.find_by_http_path_and_method("/nonexistent", "GET")
        self.assertIsNone(result)

    def test_find_in_second_api_source(self):
        """Test finding an operation defined in the second API source."""
        result = self.finder.find_by_http_path_and_method("/items", "GET")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "api_two")
        self.assertEqual(result["path"], "/items")
        self.assertEqual(result["method"], "get")
        self.assertEqual(result["operationId"], "listItems")
        self.assertEqual(result["url"], "http://localhost:8080/items")

def test_get_security_requirements_for_workflow_basic():
    arazzo_spec = {
        "workflows": [
            {
                "workflowId": "wf1",
                "steps": [
                    {"operationId": "op1"}
                ]
            }
        ]
    }
    source_descriptions = {
        "src": {
            "servers": [{"url": "http://dummy.com"}],
            "paths": {
                "/foo": {
                    "get": {
                        "operationId": "op1",
                        "security": [{"apiKey": []}]
                    }
                }
            },
            "security": [{"apiKey": []}],
            "components": {"securitySchemes": {"apiKey": {"type": "apiKey"}}}
        }
    }
    processor = AuthProcessor()
    result = processor.get_security_requirements_for_workflow("wf1", arazzo_spec, source_descriptions)
    assert list(result.keys()) == ["src"]
    assert result["src"] == [SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])]

def test_get_security_requirements_for_workflow_multiple_sources():
    arazzo_spec = {
        "workflows": [
            {
                "workflowId": "wf2",
                "steps": [
                    {"operationId": "op1"},
                    {"operationId": "op2"}
                ]
            }
        ]
    }
    source_descriptions = {
        "src1": {
            "servers": [{"url": "http://dummy1.com"}],
            "paths": {
                "/foo": {
                    "get": {
                        "operationId": "op1",
                        "security": [{"apiKey": []}]
                    }
                }
            },
            "security": [{"apiKey": []}],
            "components": {"securitySchemes": {"apiKey": {"type": "apiKey"}}}
        },
        "src2": {
            "servers": [{"url": "http://dummy2.com"}],
            "paths": {
                "/bar": {
                    "post": {
                        "operationId": "op2",
                        "security": [{"oauth2": ["read"]}]
                    }
                }
            },
            "security": [{"oauth2": ["read"]}],
            "components": {"securitySchemes": {"oauth2": {"type": "oauth2"}}}
        }
    }
    processor = AuthProcessor()
    result = processor.get_security_requirements_for_workflow("wf2", arazzo_spec, source_descriptions)
    assert set(result.keys()) == {"src1", "src2"}
    assert SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])]) in result["src1"]
    assert SecurityOption(requirements=[SecurityRequirement(scheme_name="oauth2", scopes=["read"])]) in result["src2"]
    assert len(result["src1"]) == 1
    assert len(result["src2"]) == 1

def test_get_security_requirements_for_workflow_deduplication():
    arazzo_spec = {
        "workflows": [
            {
                "workflowId": "wf3",
                "steps": [
                    {"operationId": "op1"},
                    {"operationId": "op2"}
                ]
            }
        ]
    }
    source_descriptions = {
        "src": {
            "servers": [{"url": "http://dummy.com"}],
            "paths": {
                "/foo": {
                    "get": {
                        "operationId": "op1",
                        "security": [{"apiKey": []}]
                    }
                },
                "/bar": {
                    "post": {
                        "operationId": "op2",
                        "security": [{"apiKey": []}]
                    }
                }
            },
            "security": [{"apiKey": []}],
            "components": {"securitySchemes": {"apiKey": {"type": "apiKey"}}}
        }
    }
    processor = AuthProcessor()
    result = processor.get_security_requirements_for_workflow("wf3", arazzo_spec, source_descriptions)
    assert list(result.keys()) == ["src"]
    assert result["src"] == [SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])]

def test_get_security_requirements_for_workflow_duplicate_names_different_sources():
    arazzo_spec = {
        "workflows": [
            {
                "workflowId": "wf4",
                "steps": [
                    {"operationId": "op1"},
                    {"operationId": "op2"}
                ]
            }
        ]
    }
    source_descriptions = {
        "src1": {
            "servers": [{"url": "http://dummy1.com"}],
            "paths": {
                "/foo": {
                    "get": {
                        "operationId": "op1",
                        "security": [{"apiKey": []}]
                    }
                }
            },
            "security": [{"apiKey": []}],
            "components": {"securitySchemes": {"apiKey": {"type": "apiKey", "x-issuer": "src1"}}}
        },
        "src2": {
            "servers": [{"url": "http://dummy2.com"}],
            "paths": {
                "/bar": {
                    "post": {
                        "operationId": "op2",
                        "security": [{"apiKey": []}] # Same scheme name, different source
                    }
                }
            },
            "security": [{"apiKey": []}],
            "components": {"securitySchemes": {"apiKey": {"type": "apiKey", "x-issuer": "src2"}}}
        }
    }
    processor = AuthProcessor()
    result = processor.get_security_requirements_for_workflow("wf4", arazzo_spec, source_descriptions)
    assert set(result.keys()) == {"src1", "src2"}
    assert SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])]) in result["src1"]
    assert SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])]) in result["src2"]
    assert len(result["src1"]) == 1
    assert len(result["src2"]) == 1

def test_get_security_requirements_for_workflow_scope_merging():
    """
    If two operations in the same workflow have SecurityOptions with the same scheme name but different scopes,
    the merged SecurityOption should contain all unique scopes for that scheme.
    """
    arazzo_spec = {
        "workflows": [
            {
                "workflowId": "wf_scope_merge",
                "steps": [
                    {"operationId": "op1"},
                    {"operationId": "op2"}
                ]
            }
        ]
    }
    source_descriptions = {
        "src": {
            "servers": [{"url": "http://dummy.com"}],
            "paths": {
                "/foo": {
                    "get": {
                        "operationId": "op1",
                        "security": [{"oauth2": ["read"]}]
                    }
                },
                "/bar": {
                    "post": {
                        "operationId": "op2",
                        "security": [{"oauth2": ["write"]}] 
                    }
                }
            },
            "security": [{"oauth2": ["read", "write"]}],
            "components": {"securitySchemes": {"oauth2": {"type": "oauth2"}}}
        }
    }
    processor = AuthProcessor()
    result = processor.get_security_requirements_for_workflow("wf_scope_merge", arazzo_spec, source_descriptions)
    assert list(result.keys()) == ["src"]
    # The merged SecurityOption should have both scopes for oauth2
    merged_option = SecurityOption(requirements=[SecurityRequirement(scheme_name="oauth2", scopes=["read", "write"])])
    # Allow for scopes to be in any order
    assert len(result["src"]) == 1
    req = result["src"][0].requirements[0]
    assert req.scheme_name == "oauth2"
    assert set(req.scopes) == {"read", "write"}

def test_get_security_requirements_for_openapi_operation_basic():
    openapi_spec = {
        "servers": [{"url": "http://dummy.com"}],
        "paths": {
            "/foo": {
                "get": {
                    "operationId": "op1",
                    "security": [{"apiKey": []}]
                }
            }
        },
        "security": [{"apiKey": []}],
        "components": {"securitySchemes": {"apiKey": {"type": "apiKey"}}}
    }
    processor = AuthProcessor()
    result = processor.get_security_requirements_for_openapi_operation(openapi_spec, "get", "/foo")
    assert result == [SecurityOption(requirements=[SecurityRequirement(scheme_name="apiKey", scopes=[])])]

if __name__ == '__main__':
    unittest.main()
