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
        """Test that extra inputs not defined as parameters are ignored."""
        inputs = {"itemId": 789, "filter": "all", "extraKey": "ignoreMe"}
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_PARAMS, inputs)
        self.assertEqual(result['path'], {"itemId": 789})
        self.assertEqual(result['query'], {"filter": "all"})
        self.assertEqual(result['header'], {})
        # Check that 'extraKey' was not processed
        self.assertNotIn("extraKey", result['path'])
        self.assertNotIn("extraKey", result['query'])
        self.assertNotIn("extraKey", result['header'])

    def test_prepare_required_body_success(self):
        """Test preparing a required request body successfully."""
        inputs = {"name": "newItem", "value": 99.9}
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_BODY_REQUIRED, inputs)
        self.assertEqual(result['path'], {})
        self.assertEqual(result['query'], {})
        self.assertEqual(result['header'], {})
        # The entire input dict should become the body for application/json
        self.assertEqual(result['body'], {"name": "newItem", "value": 99.9})

    def test_prepare_required_body_missing_error(self):
        """Test error when required request body input is missing."""
        inputs = {} # No body provided
        with self.assertRaisesRegex(ValueError, "Required request body is missing from inputs"):
            self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_BODY_REQUIRED, inputs)

    def test_prepare_optional_body_present(self):
        """Test preparing when an optional body is provided."""
        inputs = {"itemId": 555, "description": "updated desc"}
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_BODY_OPTIONAL, inputs)
        self.assertEqual(result['path'], {"itemId": 555})
        self.assertEqual(result['query'], {})
        self.assertEqual(result['header'], {})
        # Only the 'description' should be in the body, not itemId
        self.assertEqual(result['body'], {"description": "updated desc"})

    def test_prepare_optional_body_missing(self):
        """Test preparing when an optional body is not provided."""
        inputs = {"itemId": 666} # Only path param, no optional body
        result = self.processor.prepare_operation_parameters(MOCK_OP_DETAILS_BODY_OPTIONAL, inputs)
        self.assertEqual(result['path'], {"itemId": 666})
        self.assertEqual(result['query'], {})
        self.assertEqual(result['header'], {})
        self.assertIsNone(result['body'])


if __name__ == '__main__':
    unittest.main()
