#!/usr/bin/env python3
"""
Tests for the OpenAPI Extractor module.
"""

import pytest
import logging
import sys

from oak_runner.extractor.openapi_extractor import extract_operation_io

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
    assert input_properties["X-Request-ID"] == {"type": "string", "required": False}
    
    # Check body parameter (full resolved schema within properties)
    assert "body" in input_properties
    # Manually construct expected resolved OrderInput schema
    expected_resolved_body_schema = {
        "type": "object",
        "properties": {
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
            "customer_notes": {"type": "string"}
        },
        "required": [] # UPDATED: Expect empty list because original schema has no required
    }
    assert input_properties["body"] == expected_resolved_body_schema
 
    # --- Assert Outputs (should be the full resolved 200 response schema) ---
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


def test_extract_order_post_details_simplified():
    """
    Tests extracting simplified details for the POST /orders operation.
    """
    # Call WITH simplification flag (renamed)
    extracted = extract_operation_io(TEST_SPEC, "/orders", "post", simplify=True)

    # --- Assert Inputs (Simplified) ---
    assert "inputs" in extracted
    assert isinstance(extracted["inputs"], dict)
    assert extracted["inputs"].get("type") == "object"
    assert "properties" in extracted["inputs"]
    assert isinstance(extracted["inputs"]["properties"], dict)

    input_properties = extracted["inputs"]["properties"]

    # Check non-body parameter (simplified schema within properties)
    assert "X-Request-ID" in input_properties
    assert input_properties["X-Request-ID"] == {"type": "string", "required": False} # format removed

    # Check body parameter (simplified schema)
    assert "body" in input_properties
    expected_simplified_body_schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"}, # format removed
                        "product_id": {"type": "string"},
                        "quantity": {"type": "integer"}
                    },
                    "required": ["product_id", "quantity"] # nested 'required' preserved
                }
            },
            "customer_notes": {"type": "string"}
        },
        "required": [] # Top-level required preserved
    }
    assert input_properties["body"] == expected_simplified_body_schema

    # --- Assert Outputs (Simplified) ---
    assert "outputs" in extracted
    expected_simplified_output_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"}, # format removed
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"}, # format removed
                        "product_id": {"type": "string"},
                        "quantity": {"type": "integer"}
                    },
                    "required": ["product_id", "quantity"] # nested 'required' preserved
                }
            },
            "status": {"type": "string", "enum": ["pending", "shipped", "delivered"]}
        }
        # top-level 'required' removed by the explicit 'del' operation AFTER simplification
    }
    assert extracted["outputs"] == expected_simplified_output_schema

    # --- Assert No Other Top-Level Keys ---
    assert all(key in ["inputs", "outputs"] for key in extracted.keys())
