"""Tests for the security requirements extraction functionality."""

import pytest
from oak_runner.auth.auth_parser import extract_security_requirements
from oak_runner.auth.models import SecurityOption, SecurityRequirement


class TestSecurityRequirements:
    """Tests for security requirements extraction from OpenAPI specs."""

    def test_api_key_only(self):
        """Test extraction of API key only security."""
        # OpenAPI spec with a single API key security requirement
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "API Key Only Example",
                "version": "1.0.0"
            },
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "getItems",
                        "summary": "Get all items",
                        "responses": {
                            "200": {
                                "description": "Successful response"
                            }
                        }
                    }
                }
            },
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-KEY"
                    }
                }
            },
            "security": [
                {"ApiKeyAuth": []}
            ]
        }

        # Extract security requirements
        security_requirements = extract_security_requirements(openapi_spec)

        # Verify global security requirements
        assert security_requirements.global_requirements is not None
        assert len(security_requirements.global_requirements.options) == 1
        
        option = security_requirements.global_requirements.options[0]
        assert len(option.requirements) == 1
        assert option.requirements[0].scheme_name == "ApiKeyAuth"
        assert option.requirements[0].scopes == []

        # Verify no operation-specific requirements
        assert len(security_requirements.operation_requirements) == 0

    def test_oauth2_only(self):
        """Test extraction of OAuth2 only security."""
        # OpenAPI spec with OAuth2 security
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "OAuth2 Only Example",
                "version": "1.0.0"
            },
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "getItems",
                        "summary": "Get all items",
                        "responses": {
                            "200": {
                                "description": "Successful response"
                            }
                        }
                    }
                }
            },
            "components": {
                "securitySchemes": {
                    "OAuth2": {
                        "type": "oauth2",
                        "flows": {
                            "implicit": {
                                "authorizationUrl": "https://example.com/oauth/authorize",
                                "scopes": {
                                    "read:items": "Read items",
                                    "write:items": "Write items"
                                }
                            }
                        }
                    }
                }
            },
            "security": [
                {"OAuth2": ["read:items", "write:items"]}
            ]
        }

        # Extract security requirements
        security_requirements = extract_security_requirements(openapi_spec)

        # Verify global security requirements
        assert security_requirements.global_requirements is not None
        assert len(security_requirements.global_requirements.options) == 1
        
        option = security_requirements.global_requirements.options[0]
        assert len(option.requirements) == 1
        assert option.requirements[0].scheme_name == "OAuth2"
        assert option.requirements[0].scopes == ["read:items", "write:items"]

    def test_multiple_options(self):
        """Test extraction of multiple security options (OR relationship)."""
        # OpenAPI spec with multiple security options
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Multiple Options Example",
                "version": "1.0.0"
            },
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "getItems",
                        "summary": "Get all items",
                        "responses": {
                            "200": {
                                "description": "Successful response"
                            }
                        }
                    }
                }
            },
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-KEY"
                    },
                    "OAuth2": {
                        "type": "oauth2",
                        "flows": {
                            "implicit": {
                                "authorizationUrl": "https://example.com/oauth/authorize",
                                "scopes": {
                                    "read:items": "Read items"
                                }
                            }
                        }
                    }
                }
            },
            "security": [
                {"ApiKeyAuth": []},  # Option 1: API Key
                {"OAuth2": ["read:items"]}  # Option 2: OAuth2
            ]
        }

        # Extract security requirements
        security_requirements = extract_security_requirements(openapi_spec)

        # Verify global security requirements
        assert security_requirements.global_requirements is not None
        assert len(security_requirements.global_requirements.options) == 2
        
        # Option 1: API Key
        option1 = security_requirements.global_requirements.options[0]
        assert len(option1.requirements) == 1
        assert option1.requirements[0].scheme_name == "ApiKeyAuth"
        assert option1.requirements[0].scopes == []
        
        # Option 2: OAuth2
        option2 = security_requirements.global_requirements.options[1]
        assert len(option2.requirements) == 1
        assert option2.requirements[0].scheme_name == "OAuth2"
        assert option2.requirements[0].scopes == ["read:items"]

    def test_combined_requirements(self):
        """Test extraction of combined security requirements (AND relationship)."""
        # OpenAPI spec with combined security requirements
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Combined Requirements Example",
                "version": "1.0.0"
            },
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "getItems",
                        "summary": "Get all items",
                        "responses": {
                            "200": {
                                "description": "Successful response"
                            }
                        }
                    }
                }
            },
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-KEY"
                    },
                    "OAuth2": {
                        "type": "oauth2",
                        "flows": {
                            "implicit": {
                                "authorizationUrl": "https://example.com/oauth/authorize",
                                "scopes": {
                                    "read:items": "Read items"
                                }
                            }
                        }
                    }
                }
            },
            "security": [
                {
                    "ApiKeyAuth": [],
                    "OAuth2": ["read:items"]
                }  # Requires BOTH API Key AND OAuth2
            ]
        }

        # Extract security requirements
        security_requirements = extract_security_requirements(openapi_spec)

        # Verify global security requirements
        assert security_requirements.global_requirements is not None
        assert len(security_requirements.global_requirements.options) == 1
        
        # Single option with multiple requirements
        option = security_requirements.global_requirements.options[0]
        assert len(option.requirements) == 2
        
        # Check both requirements are present
        scheme_names = [req.scheme_name for req in option.requirements]
        assert "ApiKeyAuth" in scheme_names
        assert "OAuth2" in scheme_names
        
        # Find OAuth2 requirement and check scopes
        oauth2_req = next(req for req in option.requirements if req.scheme_name == "OAuth2")
        assert oauth2_req.scopes == ["read:items"]

    def test_operation_level_security(self):
        """Test extraction of operation-level security requirements."""
        # OpenAPI spec with operation-level security
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Operation Level Security Example",
                "version": "1.0.0"
            },
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "getItems",
                        "summary": "Get all items",
                        "security": [
                            {"ApiKeyAuth": []}
                        ],
                        "responses": {
                            "200": {
                                "description": "Successful response"
                            }
                        }
                    },
                    "post": {
                        "operationId": "createItem",
                        "summary": "Create an item",
                        "security": [
                            {"OAuth2": ["write:items"]}
                        ],
                        "responses": {
                            "201": {
                                "description": "Item created"
                            }
                        }
                    }
                }
            },
            "components": {
                "securitySchemes": {
                    "ApiKeyAuth": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-API-KEY"
                    },
                    "OAuth2": {
                        "type": "oauth2",
                        "flows": {
                            "implicit": {
                                "authorizationUrl": "https://example.com/oauth/authorize",
                                "scopes": {
                                    "read:items": "Read items",
                                    "write:items": "Write items"
                                }
                            }
                        }
                    }
                }
            },
            "security": [
                {"OAuth2": ["read:items"]}  # Default global security
            ]
        }

        # Extract security requirements
        security_requirements = extract_security_requirements(openapi_spec)

        # Verify global security requirements
        assert security_requirements.global_requirements is not None
        assert len(security_requirements.global_requirements.options) == 1
        
        # Verify operation-level requirements
        assert len(security_requirements.operation_requirements) == 2
        
        # Find operations by ID
        get_items_op = next(op for op in security_requirements.operation_requirements 
                           if op.operation_id == "getItems")
        create_item_op = next(op for op in security_requirements.operation_requirements 
                             if op.operation_id == "createItem")
        
        # Check getItems operation
        assert get_items_op.path == "/items"
        assert get_items_op.method == "get"
        assert len(get_items_op.options) == 1
        assert get_items_op.options[0].requirements[0].scheme_name == "ApiKeyAuth"
        
        # Check createItem operation
        assert create_item_op.path == "/items"
        assert create_item_op.method == "post"
        assert len(create_item_op.options) == 1
        assert create_item_op.options[0].requirements[0].scheme_name == "OAuth2"
        assert create_item_op.options[0].requirements[0].scopes == ["write:items"]

    def test_empty_security(self):
        """Test extraction with no security requirements."""
        # OpenAPI spec with no security requirements
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "No Security Example",
                "version": "1.0.0"
            },
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "getItems",
                        "summary": "Get all items",
                        "responses": {
                            "200": {
                                "description": "Successful response"
                            }
                        }
                    }
                }
            }
        }

        # Extract security requirements
        security_requirements = extract_security_requirements(openapi_spec)

        # Verify no security requirements
        assert security_requirements.global_requirements is not None
        assert len(security_requirements.global_requirements.options) == 0
        assert len(security_requirements.operation_requirements) == 0
