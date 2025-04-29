import unittest
from unittest.mock import MagicMock
from oak_runner.executor.parameter_processor import ParameterProcessor

# Mock operation details structures
MOCK_OP_DETAILS_PARAMS = {
    "source": "testApi",
    "path": "/items/{itemId}",
    "method": "get",
    "url": "https://api.test.com/items/{itemId}",
    "operation": {
        "summary": "Get item with query",
        "operationId": "getItem",
        "parameters": [
            {"in": "path", "name": "itemId", "required": True, "schema": {"type": "integer"}},
            {"in": "query", "name": "filter", "required": False, "schema": {"type": "string"}},
            {"in": "header", "name": "X-Request-ID", "required": False, "schema": {"type": "string"}}
            # Cookie parameters are less common, skipping for brevity but could be added
        ]
    }
}

MOCK_OP_DETAILS_BODY_REQUIRED = {
    "source": "testApi",
    "path": "/items",
    "method": "post",
    "url": "https://api.test.com/items",
    "operation": {
        "summary": "Create item",
        "operationId": "createItem",
        "parameters": []
    },
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "number"}
                    },
                    "required": ["name"]
                }
            }
        }
    }
}

MOCK_OP_DETAILS_BODY_OPTIONAL = {
    "source": "testApi",
    "path": "/items/{itemId}",
    "method": "patch",
    "url": "https://api.test.com/items/{itemId}",
    "operation": {
        "summary": "Update item",
        "operationId": "updateItem",
        "parameters": [
             {"in": "path", "name": "itemId", "required": True, "schema": {"type": "integer"}}
        ]
    },
    "requestBody": {
        "required": False, # Optional body
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"}
                    }
                }
            }
        }
    }
}

# Mock for Form URL Encoded Content Type
MOCK_OP_DETAILS_BODY_FORM = {
    "source": "testApi",
    "path": "/submit",
    "method": "post",
    "url": "https://api.test.com/submit",
    "operation": {
        "summary": "Submit form",
        "operationId": "submitForm",
    },
    "requestBody": {
        "required": True,
        "content": {
            "application/x-www-form-urlencoded": { # Different content type
                "schema": {
                    "type": "object",
                    "properties": {
                        "field1": {"type": "string"},
                        "field2": {"type": "integer"}
                    },
                    "required": ["field1"]
                }
            }
        }
    }
}

# Mock for Multiple Content Types (JSON first)
MOCK_OP_DETAILS_BODY_MULTI_CONTENT_JSON_FIRST = {
    "source": "testApi",
    "path": "/data",
    "method": "post",
    "url": "https://api.test.com/data",
    "operation": {"operationId": "postDataMultiJsonFirst"},
    "requestBody": {
        "required": True,
        "content": {
            "application/xml": {"schema": {"type": "string"}}, # XML listed first
            "application/json": {"schema": {"type": "object"}}, # JSON listed second
            "text/plain": {"schema": {"type": "string"}}
        }
    }
}

# Mock for Multiple Content Types (No JSON)
MOCK_OP_DETAILS_BODY_MULTI_CONTENT_NO_JSON = {
    "source": "testApi",
    "path": "/data",
    "method": "post",
    "url": "https://api.test.com/data",
    "operation": {"operationId": "postDataMultiNoJson"},
    "requestBody": {
        "required": True,
        "content": {
            "application/xml": {"schema": {"type": "string"}}, # XML listed first
            "text/plain": {"schema": {"type": "string"}} # Plain text second
        }
    }
}

# Mock for Operation with no requestBody spec
MOCK_OP_DETAILS_NO_BODY_SPEC = {
    "source": "testApi",
    "path": "/action",
    "method": "post",
    "url": "https://api.test.com/action",
    "operation": {
        "summary": "Action without defined body",
        "operationId": "doActionNoBody",
        "parameters": []
        # No requestBody defined at all
    }
}

# Mock for $ref request body
MOCK_COMPONENTS = {
    "requestBodies": {
        "UserBody": {
            "required": True,
            "content": {
                "application/json": {
                     "schema": {
                         "type": "object",
                         "properties": {"username": {"type": "string"}, "email": {"type": "string"}}
                     }
                }
            }
        }
    }
}

MOCK_OP_DETAILS_BODY_REF = {
    "source": "refApi",
    "path": "/users",
    "method": "post",
    "url": "https://api.ref.com/users",
    "operation": {
        "summary": "Create user via ref",
        "operationId": "createUserRef",
        "requestBody": {
            "$ref": "#/components/requestBodies/UserBody" # Reference
        }
    }
}

# Additional mock for operation_details with only path param in path string (not in parameters)
MOCK_OP_DETAILS_PATH_ONLY = {
    "source": "testApi",
    "path": "/widgets/{widget_id}/do",
    "method": "post",
    "url": "https://api.test.com/widgets/{widget_id}/do",
    "operation": {
        "summary": "Do something with widget",
        "operationId": "doWidgetAction",
        # No parameters field here
    }
}


class TestParameterProcessorOperation(unittest.TestCase):

    def setUp(self):
        """Set up the test case with ParameterProcessor instance."""
        self.processor = ParameterProcessor(source_descriptions={})

    def test_prepare_params_success(self):
        """Test preparing path, query, header params successfully."""
        inputs = {"itemId": 123, "filter": "active", "X-Request-ID": "req-1"}
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_PARAMS, inputs)
        self.assertEqual(result['path'], {"itemId": 123})
        self.assertEqual(result['query'], {"filter": "active"})
        self.assertEqual(result['header'], {"X-Request-ID": "req-1"})
        self.assertIsNone(result['body'])

    def test_prepare_params_optional_missing(self):
        """Test when optional parameters are missing from input."""
        inputs = {"itemId": 456} # Missing optional filter and X-Request-ID
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_PARAMS, inputs)
        self.assertEqual(result['path'], {"itemId": 456})
        self.assertEqual(result['query'], {})
        self.assertEqual(result['header'], {})
        self.assertIsNone(result['body'])

    def test_prepare_params_required_missing_error(self):
        """Test error when a required path parameter is missing."""
        inputs = {"filter": "inactive"} # Missing required itemId
        # Update the expected regex to match the actual error message
        with self.assertRaisesRegex(ValueError, r"Required parameter 'itemId' \(in: path\) is missing."):
            self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_PARAMS, inputs)

    def test_prepare_params_extra_input_ignored(self):
        """Test that extra inputs not defined as parameters are ignored when no requestBody is specified."""
        inputs = {"itemId": 789, "filter": "all", "extraKey": "ignoreMe"}
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_PARAMS, inputs)
        self.assertEqual(result['path'], {"itemId": 789})
        self.assertEqual(result['query'], {"filter": "all"})
        self.assertEqual(result['header'], {})
        # Check that 'extraKey' was ignored and body is None (matching stricter logic)
        self.assertIsNone(result['body'])
        # Optional: Check logs for warning if logging is captured/assertable

    def test_prepare_required_body_success_json(self):
        """Test preparing a required JSON request body successfully."""
        inputs = {"name": "newItem", "value": 99.9}
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_BODY_REQUIRED, inputs)
        self.assertEqual(result['path'], {})
        self.assertEqual(result['query'], {})
        self.assertEqual(result['header'], {})
        # Assert the new structure: payload and contentType
        expected_body = {
            "payload": {"name": "newItem", "value": 99.9},
            "contentType": "application/json" # Determined from spec
        }
        self.assertEqual(result['body'], expected_body)

    def test_prepare_required_body_missing_error(self):
        """Test error when required request body input is missing."""
        inputs = {} # No body provided
        # Regex updated to match the new error message wording if it changed
        with self.assertRaisesRegex(ValueError, "Required request body is missing."):
            self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_BODY_REQUIRED, inputs)

    def test_prepare_optional_body_present_json(self):
        """Test preparing when an optional JSON body is provided."""
        inputs = {"itemId": 555, "description": "updated desc"} # itemId is path param
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_BODY_OPTIONAL, inputs)
        self.assertEqual(result['path'], {"itemId": 555})
        self.assertEqual(result['query'], {})
        self.assertEqual(result['header'], {})
        # Assert the new structure: payload and contentType
        expected_body = {
            "payload": {"description": "updated desc"}, # Only unused input key
            "contentType": "application/json" # Determined from spec
        }
        self.assertEqual(result['body'], expected_body)

    def test_prepare_optional_body_missing(self):
        """Test preparing when an optional body is not provided."""
        inputs = {"itemId": 666} # Only path param, no optional body
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_BODY_OPTIONAL, inputs)
        self.assertEqual(result['path'], {"itemId": 666})
        self.assertEqual(result['query'], {})
        self.assertEqual(result['header'], {})
        self.assertIsNone(result['body'])

    def test_prepare_required_body_success_form(self):
        """Test preparing a required form request body successfully."""
        inputs = {"field1": "value1", "field2": 123}
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_BODY_FORM, inputs)
        self.assertEqual(result['path'], {})
        self.assertEqual(result['query'], {})
        self.assertEqual(result['header'], {})
        # Assert the new structure: payload and contentType
        expected_body = {
            "payload": {"field1": "value1", "field2": 123},
            "contentType": "application/x-www-form-urlencoded" # Determined from spec
        }
        self.assertEqual(result['body'], expected_body)

    def test_prepare_body_multi_content_json_priority(self):
        """Test content type selection prioritizes application/json."""
        inputs = {"key": "value"}
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_BODY_MULTI_CONTENT_JSON_FIRST, inputs)
        expected_body = {
            "payload": {"key": "value"},
            "contentType": "application/json" # Should prioritize JSON
        }
        self.assertEqual(result['body'], expected_body)

    def test_prepare_body_multi_content_first_priority(self):
        """Test content type selection picks the first listed when JSON is absent."""
        inputs = {"raw_xml": "<data>hello</data>"}
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_BODY_MULTI_CONTENT_NO_JSON, inputs)
        expected_body = {
            "payload": {"raw_xml": "<data>hello</data>"},
            "contentType": "application/xml" # Should pick the first one (XML)
        }
        self.assertEqual(result['body'], expected_body)

    def test_prepare_body_provided_but_no_spec(self):
        """Test providing body input when spec has no requestBody definition."""
        inputs = {"unexpected": "data"}
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_NO_BODY_SPEC, inputs)
        # With stricter logic, unused inputs are ignored if no requestBody defined.
        self.assertIsNone(result['body'])

    def test_prepare_body_with_ref(self):
        """Test preparing request body defined by a $ref."""
        # Mock the _resolve_ref method for this test
        # In a real scenario with multiple source_descriptions, might need more setup
        self.processor._resolve_ref = MagicMock(return_value=MOCK_COMPONENTS["requestBodies"]["UserBody"])

        inputs = {"username": "testuser", "email": "test@example.com"}
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_BODY_REF, inputs)

        expected_body = {
            "payload": {"username": "testuser", "email": "test@example.com"},
            "contentType": "application/json"
        }
        self.assertEqual(result['body'], expected_body)
        # Verify _resolve_ref was called correctly (assuming simple ref path)
        self.processor._resolve_ref.assert_called_once_with("#/components/requestBodies/UserBody")
        # Clean up mock if it affects other tests
        del self.processor._resolve_ref

    def test_path_param_from_path_string_only(self):
        """Test that a path param present only in the path string is enforced as required."""
        # Should succeed when widget_id is present
        inputs = {"widget_id": "abc123"}
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_PATH_ONLY, inputs)
        self.assertEqual(result['path'], {"widget_id": "abc123"})
        self.assertEqual(result['query'], {})
        self.assertEqual(result['header'], {})
        self.assertIsNone(result['body'])
        # Should fail when widget_id is missing
        with self.assertRaisesRegex(ValueError, r"Required parameter 'widget_id' \(in: path\) is missing."):
            self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_PATH_ONLY, {})


if __name__ == '__main__':
    unittest.main()
