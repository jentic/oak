#!/usr/bin/env python3
"""
Tests for the OpenAPI Extractor module.
"""

import pytest
import logging
import sys

from oak_runner.extractor.openapi_extractor import (
    extract_operation_io,
    _limit_dict_depth 
)

# Configure specific logger for the extractor module for debug output
extractor_logger = logging.getLogger('oak_runner.extractor.openapi_extractor')
extractor_logger.setLevel(logging.DEBUG)
# Ensure handler exists to output to stderr
if not extractor_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    handler.setFormatter(formatter)
    extractor_logger.addHandler(handler)

# Example spec from task.md (simplified slightly for testing focus)
TEST_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Test API", "version": "1.0.0"},
    "servers": [{"url": "http://test.com/api"}],
    "paths": {
        "/orders": {
            "post": {
                "summary": "Create a new order",
                "operationId": "createOrder",
                "parameters": [
                    {
                        "name": "X-Request-ID",
                        "in": "header",
                        "required": False,
                        "schema": {"type": "string", "format": "uuid"}
                    }
                ],
                "requestBody": {
                    "$ref": "#/components/requestBodies/OrderRequest"
                },
                "responses": {
                    "201": {
                        "$ref": "#/components/responses/OrderCreated"
                    },
                    "400": {
                        "description": "Invalid input"
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "Order": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "items": {"type": "array", "items": {"$ref": "#/components/schemas/OrderItem"}},
                    "status": {"type": "string", "enum": ["pending", "shipped", "delivered"]}
                },
                "required": ["items"]
            },
             "OrderInput": {
                 "type": "object",
                 "properties": {
                     "items": {"type": "array", "items": {"$ref": "#/components/schemas/OrderItem"}},
                     "customer_notes": {"type": "string"}
                 }
             },
            "OrderItem": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "format": "uuid"},
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer"}
                },
                "required": ["product_id", "quantity"]
            }
        },
        "requestBodies": {
            "OrderRequest": {
                "description": "Order details",
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/OrderInput"
                        }
                    }
                }
            }
        },
        "responses": {
            "OrderCreated": {
                "description": "Order created successfully",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/Order"
                        }
                    }
                }
            }
        }
    }
}

def test_extract_order_post_details():
    """
    Tests extracting details for the POST /orders operation.
    """
    extracted = extract_operation_io(TEST_SPEC, "/orders", "post")

    # --- Assert Inputs (OpenAPI object structure) ---
    assert "inputs" in extracted
    assert isinstance(extracted["inputs"], dict)
    assert extracted["inputs"].get("type") == "object"
    assert "properties" in extracted["inputs"]
    assert isinstance(extracted["inputs"]["properties"], dict)
    
    input_properties = extracted["inputs"]["properties"]

    # Check non-body parameter (simplified schema within properties)
    assert "X-Request-ID" in input_properties
    # Check type only, required status is in the top-level list
    assert input_properties["X-Request-ID"] == {"type": "string"}
    # Check that it's NOT required in the top-level list
    assert "X-Request-ID" not in extracted["inputs"].get("required", [])

    # Check the flattened 'items' property from the body
    assert "items" in input_properties
    # Manually construct expected resolved items schema
    expected_items_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "format": "uuid"},
                "product_id": {"type": "string"},
                "quantity": {"type": "integer"}
            },
            "required": ["product_id", "quantity"]
        }
    }
    assert input_properties["items"] == expected_items_schema

    # Check the flattened 'customer_notes' property from the body
    assert "customer_notes" in input_properties
    assert input_properties["customer_notes"] == {"type": "string"}

    # Check required properties from the body are in the top-level required list
    # 'items' is NOT listed in the requestBody schema's top-level required list in TEST_SPEC
    assert "items" not in extracted["inputs"].get("required", [])
    # customer_notes was not required in the body schema
    assert "customer_notes" not in extracted["inputs"].get("required", [])

    # --- Assert Outputs (Full schema) ---
    assert "outputs" in extracted
    # Manually construct expected resolved Order schema
    expected_resolved_output_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "product_id": {"type": "string"},
                        "quantity": {"type": "integer"}
                    },
                    "required": ["product_id", "quantity"]
                }
            },
            "status": {"type": "string", "enum": ["pending", "shipped", "delivered"]}
        },
        "required": ["items"]  # Add missing required field
    }
    assert extracted["outputs"] == expected_resolved_output_schema
 
    # --- Assert No Other Top-Level Keys (like old 'parameters', 'request_body', 'responses') ---
    assert all(key in ["inputs", "outputs"] for key in extracted.keys())


@pytest.mark.parametrize(
    "data, max_depth, expected",
    [
        # Basic dict limiting
        ({'a': {'b': {'c': 1}}}, 0, 'object'),
        ({'a': {'b': {'c': 1, 'type': 'nested_object'}}}, 0, 'object'), # Corrected expectation for max_depth=0
        ({'a': {'b': {'c': 1}}}, 1, {'a': 'object'}),
        ({'a': {'b': {'c': 1}}}, 2, {'a': {'b': 'object'}}),
        ({'a': {'b': {'c': 1}}}, 3, {'a': {'b': {'c': 1}}}),
        ({'a': {'b': {'c': 1}}}, 4, {'a': {'b': {'c': 1}}}), # Depth greater than actual
        # Basic list limiting
        ([[['a']]], 0, 'array'),
        ([[['a']]], 1, ['array']),
        ([[['a']]], 2, [['array']]),
        ([[['a']]], 3, [[['a']]]),
        ([[['a']]], 4, [[['a']]]),
        # Mixed dict/list limiting
        ({'a': [1, {'b': [2, 3]}]}, 0, 'object'),
        ({'a': [1, {'b': [2, 3]}]}, 1, {'a': 'array'}),
        ({'a': [1, {'b': [2, 3]}]}, 2, {'a': [1, 'object']}),
        ({'a': [1, {'b': [2, 3]}]}, 3, {'a': [1, {'b': 'array'}]}),
        ({'a': [1, {'b': [2, 3]}]}, 4, {'a': [1, {'b': [2, 3]}]}),
        # Other types
        ("string", 1, "string"),
        (123, 1, 123),
        (True, 1, True),
        (None, 1, None),
        ({}, 1, {}), # Empty dict
        ([], 1, []),   # Empty list
    ]
)
def test_limit_dict_depth(data, max_depth, expected):
    """Tests the _limit_dict_depth function with various inputs and depths."""
    result = _limit_dict_depth(data, max_depth)
    assert result == expected

def test_extracts_implicit_url_param():
    """
    If a path parameter is present in the URL but not declared in the spec, it should still be extracted as required.
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Minimal API", "version": "1.0.0"},
        "servers": [{"url": "http://test.com/api"}],
        "paths": {
            "/widgets/{widget_id}": {
                "get": {
                    "summary": "Get widget by ID",
                    "responses": {"200": {"description": "ok"}}
                }
            }
        }
    }
    result = extract_operation_io(spec, "/widgets/{widget_id}", "get")
    props = result["inputs"]["properties"]
    assert "widget_id" in props
    # Path params derived from URL are always required
    assert "widget_id" in result["inputs"].get("required", [])
    # Check the type (defaults to string if not specified)
    assert props["widget_id"] == {"type": "string"}

def test_extracts_explicit_url_param():
    """
    If a path parameter is specified in both the URL and the spec, it should be extracted as required and match the declared type.
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Minimal API", "version": "1.0.0"},
        "servers": [{"url": "http://test.com/api"}],
        "paths": {
            "/gadgets/{gadget_id}": {
                "get": {
                    "summary": "Get gadget by ID",
                    "parameters": [
                        {
                            "name": "gadget_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"}
                        }
                    ],
                    "responses": {"200": {"description": "ok"}}
                }
            }
        }
    }
    result = extract_operation_io(spec, "/gadgets/{gadget_id}", "get")
    props = result["inputs"]["properties"]
    assert "gadget_id" in props
    # Path params are always required
    assert "gadget_id" in result["inputs"].get("required", [])
    # Check the type matches the spec
    assert props["gadget_id"] == {"type": "integer"}


def test_extract_operation_io_depth_limits():
    """
    extract_operation_io should respect input_max_depth and output_max_depth for truncating schema depth.
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "DepthTest API", "version": "1.0.0"},
        "servers": [{"url": "http://test.com/api"}],
        "paths": {
            "/foo/{bar}": {
                "post": {
                    "parameters": [
                        {"name": "bar", "in": "path", "required": True, "schema": {"type": "string"}}
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "deep": {
                                            "type": "object",
                                            "properties": {
                                                "deeper": {"type": "object", "properties": {"val": {"type": "string"}}}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "arr": {
                                                "type": "array",
                                                "items": {"type": "object", "properties": {"x": {"type": "integer"}}}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    # Limit input to 2 levels, output to 1 level
    result = extract_operation_io(
        spec, "/foo/{bar}", "post", input_max_depth=2, output_max_depth=1
    )

    # --- Check Input Depth Limit (input_max_depth=2) ---
    assert "inputs" in result
    assert result["inputs"].get("type") == "object"
    input_props = result["inputs"].get("properties", {})

    # Path parameter 'bar' should exist and its value truncated
    assert "bar" in input_props
    # At depth=2, _limit_dict_depth returns the type string for the primitive schema
    assert input_props["bar"] == "string"

    # Body property 'deep' should be flattened and its value truncated
    assert "deep" in input_props
    # At depth=2, _limit_dict_depth returns the type of the nested object
    assert input_props["deep"] == "object"

    # Check required fields
    assert result["inputs"].get("required") == ["bar"]

    # --- Check Output Depth Limit (output_max_depth=1) ---
    assert "outputs" in result
    output_schema = result["outputs"]
    assert output_schema.get("type") == "object"
    # At depth=1, _limit_dict_depth truncates the 'properties' dict to its type
    assert output_schema.get("properties") == "object"

def test_no_params_or_body():
    """
    If an operation has no parameters or body, extract_operation_io should return an empty inputs dict.
    """
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Minimal API", "version": "1.0.0"},
        "servers": [{"url": "http://test.com/api"}],
        "paths": {
            "/widgets": {
                "get": {
                    "summary": "Get widgets",
                    "responses": {"200": {"description": "ok"}}
                }
            }
        }
    }
    result = extract_operation_io(spec, "/widgets", "get")
    assert "inputs" in result
    assert result["inputs"] == {"type": "object", "properties": {}, "required": []}
