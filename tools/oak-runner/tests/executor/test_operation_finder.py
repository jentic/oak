import unittest
from oak_runner.executor.operation_finder import OperationFinder

# Mock OpenAPI source descriptions
MOCK_SOURCE_DESC = {
    "api_one": {
        "servers": [{"url": "https://api.example.com/v1"}],
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
        self.assertEqual(result["url"], "https://api.example.com/v1/users")

    def test_find_template_path_and_method_success(self):
        """Test finding an operation with a template path and method match."""
        # Note: Current implementation uses simple segment check, might need adjustment
        result = self.finder.find_by_http_path_and_method("/users/123", "DELETE")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "api_one")
        self.assertEqual(result["path"], "/users/{userId}") # Should return template path
        self.assertEqual(result["method"], "delete")
        self.assertEqual(result["operationId"], "deleteUser")
        self.assertEqual(result["url"], "https://api.example.com/v1/users/{userId}")

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

if __name__ == '__main__':
    unittest.main()
