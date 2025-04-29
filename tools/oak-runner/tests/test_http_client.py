#!/usr/bin/env python3
"""
Tests for the HTTP Client in OAK Runner

This file contains tests for the HTTPExecutor class in the OAK Runner library,
with a focus on authentication handling.
"""

import unittest
from oak_runner.auth.models import SecurityOption, SecurityRequirement, RequestAuthValue, AuthLocation
from oak_runner.http import HTTPExecutor


class MockAuthProvider:
    """Mock authentication provider for testing"""

    def __init__(self, api_configs=None, auth_data=None):
        self.api_configs = api_configs or {}
        self.auth_data = auth_data or {}

    def get_auth_for_api(self, api_id):
        """Return mock auth data for the given API ID"""
        return self.auth_data.get(api_id, {})
        
    def resolve_credentials(self, security_options, source_name: str | None = None):
        """
        Mock implementation of resolve_credentials
        
        Args:
            security_options: List of SecurityOption objects
            source_name: Optional source API name
            
        Returns:
            List of RequestAuthValue objects
        """
        request_auth_values = []
        
        for option in security_options:
            for requirement in option.requirements:
                scheme_name = requirement.scheme_name
                # In the mock, we'll just use the scheme name as the auth key
                # This would be more complex in the real implementation
                for api_id, api_config in self.api_configs.items():
                    # If source_name is provided, only use configs for that source
                    if source_name and api_id != source_name:
                        continue
                        
                    auth_schemes = api_config.get("auth", {}).get("security_schemes", [])
                    
                    for scheme in auth_schemes:
                        if scheme.get("name") == scheme_name:
                            auth_value = self.auth_data.get(api_id, {}).get(scheme_name)
                            if auth_value:
                                location = scheme.get("location", "header")
                                auth_location = None
                                
                                if location == "header":
                                    auth_location = AuthLocation.HEADER
                                elif location == "query":
                                    auth_location = AuthLocation.QUERY
                                elif location == "cookie":
                                    auth_location = AuthLocation.COOKIE
                                else:
                                    auth_location = AuthLocation.HEADER
                                    
                                request_auth_values.append(
                                    RequestAuthValue(
                                        name=scheme_name,
                                        location=auth_location,
                                        auth_value=auth_value
                                    )
                                )
        
        return request_auth_values


class TestHTTPExecutor(unittest.TestCase):
    """Test the HTTP Client functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.http_client = HTTPExecutor()

    def test_init(self):
        """Test that the HTTP client initializes correctly"""
        self.assertIsNotNone(self.http_client)
        self.assertIsNone(self.http_client.auth_provider)

    def test_apply_auth_no_provider(self):
        """Test that auth application is skipped when no auth provider is available"""
        headers = {}
        query_params = {}
        cookies = {}

        # No auth provider set
        self.http_client._apply_auth_to_request(
            "https://example.com", headers, query_params, cookies
        )

        # Should not modify any of the dictionaries
        self.assertEqual(headers, {})
        self.assertEqual(query_params, {})
        self.assertEqual(cookies, {})

    def test_apply_auth_query_parameter(self):
        """Test applying auth as query parameters"""
        # Create mock auth provider with query parameter auth
        api_id = "test-api"
        auth_provider = MockAuthProvider(
            api_configs={
                api_id: {
                    "auth": {
                        "security_schemes": [
                            {
                                "type": "apiKey",
                                "name": "api-key",
                                "required": True,
                                "location": "query",
                            }
                        ]
                    }
                }
            },
            auth_data={api_id: {"api-key": "test-api-key-12345"}},
        )

        self.http_client.auth_provider = auth_provider

        headers = {}
        query_params = {}
        cookies = {}

        # Create security options
        security_options = [
            SecurityOption(
                requirements=[
                    SecurityRequirement(scheme_name="api-key", scopes=[])
                ]
            )
        ]

        # Apply auth
        self.http_client._apply_auth_to_request(
            "https://example.com", headers, query_params, cookies, security_options
        )

        # Check that query parameters were updated correctly
        self.assertEqual(query_params, {"api-key": "test-api-key-12345"})
        # Headers and cookies should remain empty
        self.assertEqual(headers, {})
        self.assertEqual(cookies, {})

    def test_apply_auth_header(self):
        """Test applying auth as headers"""
        # Create mock auth provider with header auth
        api_id = "test-api"
        auth_provider = MockAuthProvider(
            api_configs={
                api_id: {
                    "auth": {
                        "security_schemes": [
                            {
                                "type": "apiKey",
                                "name": "X-Api-Key",
                                "required": True,
                                "location": "header",
                            }
                        ]
                    }
                }
            },
            auth_data={api_id: {"X-Api-Key": "test-api-key-12345"}},
        )

        self.http_client.auth_provider = auth_provider

        headers = {}
        query_params = {}
        cookies = {}

        # Create security options
        security_options = [
            SecurityOption(
                requirements=[
                    SecurityRequirement(scheme_name="X-Api-Key", scopes=[])
                ]
            )
        ]

        # Apply auth
        self.http_client._apply_auth_to_request(
            "https://example.com", headers, query_params, cookies, security_options
        )

        # Check that headers were updated correctly
        self.assertEqual(headers, {"X-Api-Key": "test-api-key-12345"})
        # Query params and cookies should remain empty
        self.assertEqual(query_params, {})
        self.assertEqual(cookies, {})

    def test_apply_auth_cookie(self):
        """Test applying auth as cookies"""
        # Create mock auth provider with cookie auth
        api_id = "test-api"
        auth_provider = MockAuthProvider(
            api_configs={
                api_id: {
                    "auth": {
                        "security_schemes": [
                            {
                                "type": "apiKey",
                                "name": "session",
                                "required": True,
                                "location": "cookie",
                            }
                        ]
                    }
                }
            },
            auth_data={api_id: {"session": "test-session-id-12345"}},
        )

        self.http_client.auth_provider = auth_provider

        headers = {}
        query_params = {}
        cookies = {}

        # Create security options
        security_options = [
            SecurityOption(
                requirements=[
                    SecurityRequirement(scheme_name="session", scopes=[])
                ]
            )
        ]

        # Apply auth
        self.http_client._apply_auth_to_request(
            "https://example.com", headers, query_params, cookies, security_options
        )

        # Check that cookies were updated correctly
        self.assertEqual(cookies, {"session": "test-session-id-12345"})
        # Headers and query params should remain empty
        self.assertEqual(headers, {})
        self.assertEqual(query_params, {})

    def test_apply_auth_multiple_requirements(self):
        """Test applying auth with multiple requirements in different locations"""
        # Create mock auth provider with multiple auth requirements
        api_id = "test-api"
        auth_provider = MockAuthProvider(
            api_configs={
                api_id: {
                    "auth": {
                        "security_schemes": [
                            {
                                "type": "apiKey",
                                "name": "api-key",
                                "required": True,
                                "location": "query",
                            },
                            {
                                "type": "apiKey",
                                "name": "X-Client-Id",
                                "required": True,
                                "location": "header",
                            },
                            {
                                "type": "apiKey",
                                "name": "session",
                                "required": True,
                                "location": "cookie",
                            },
                        ]
                    }
                }
            },
            auth_data={
                api_id: {
                    "api-key": "test-api-key-12345",
                    "X-Client-Id": "client-12345",
                    "session": "test-session-id-12345",
                }
            },
        )

        self.http_client.auth_provider = auth_provider

        headers = {}
        query_params = {}
        cookies = {}

        # Create security options
        security_options = [
            SecurityOption(
                requirements=[
                    SecurityRequirement(scheme_name="api-key", scopes=[]),
                    SecurityRequirement(scheme_name="X-Client-Id", scopes=[]),
                    SecurityRequirement(scheme_name="session", scopes=[]),
                ]
            )
        ]

        # Apply auth
        self.http_client._apply_auth_to_request(
            "https://example.com", headers, query_params, cookies, security_options
        )

        # Check that all parameters were updated correctly
        self.assertEqual(query_params, {"api-key": "test-api-key-12345"})
        self.assertEqual(headers, {"X-Client-Id": "client-12345"})
        self.assertEqual(cookies, {"session": "test-session-id-12345"})

    def test_apply_auth_missing_value(self):
        """Test handling of missing auth values"""
        # Create mock auth provider with auth requirement but missing value
        api_id = "test-api"
        auth_provider = MockAuthProvider(
            api_configs={
                api_id: {
                    "auth": {
                        "security_schemes": [
                            {
                                "type": "apiKey",
                                "name": "api-key",
                                "required": True,
                                "location": "query",
                            }
                        ]
                    }
                }
            },
            auth_data={
                api_id: {
                    # Missing "api-key"
                    "other-key": "value"
                }
            },
        )

        self.http_client.auth_provider = auth_provider

        headers = {}
        query_params = {}
        cookies = {}

        # Create security options
        security_options = [
            SecurityOption(
                requirements=[
                    SecurityRequirement(scheme_name="api-key", scopes=[])
                ]
            )
        ]

        # Apply auth
        self.http_client._apply_auth_to_request(
            "https://example.com", headers, query_params, cookies, security_options
        )

        # All dictionaries should remain empty
        self.assertEqual(headers, {})
        self.assertEqual(query_params, {})
        self.assertEqual(cookies, {})

    def test_apply_auth_unknown_location(self):
        """Test handling of unknown auth location (should default to header)"""
        # Create mock auth provider with unknown auth location
        api_id = "test-api"
        auth_provider = MockAuthProvider(
            api_configs={
                api_id: {
                    "auth": {
                        "security_schemes": [
                            {
                                "type": "apiKey",
                                "name": "api-key",
                                "required": True,
                                "location": "unknown",  # Unknown location
                            }
                        ]
                    }
                }
            },
            auth_data={api_id: {"api-key": "test-api-key-12345"}},
        )

        self.http_client.auth_provider = auth_provider

        headers = {}
        query_params = {}
        cookies = {}

        # Create security options
        security_options = [
            SecurityOption(
                requirements=[
                    SecurityRequirement(scheme_name="api-key", scopes=[])
                ]
            )
        ]

        # Apply auth
        self.http_client._apply_auth_to_request(
            "https://example.com", headers, query_params, cookies, security_options
        )

        # Should default to header
        self.assertEqual(headers, {"api-key": "test-api-key-12345"})
        self.assertEqual(query_params, {})
        self.assertEqual(cookies, {})

    def test_apply_auth_multiple_apis(self):
        """Test applying auth from multiple APIs"""
        # Create mock auth provider with multiple APIs
        auth_provider = MockAuthProvider(
            api_configs={
                "api1": {
                    "auth": {
                        "security_schemes": [
                            {
                                "type": "apiKey",
                                "name": "api1-key",
                                "required": True,
                                "location": "query",
                            }
                        ]
                    }
                },
                "api2": {
                    "auth": {
                        "security_schemes": [
                            {
                                "type": "apiKey",
                                "name": "api2-key",
                                "required": True,
                                "location": "header",
                            }
                        ]
                    }
                },
            },
            auth_data={
                "api1": {"api1-key": "api1-key-value"},
                "api2": {"api2-key": "api2-key-value"},
            },
        )

        self.http_client.auth_provider = auth_provider

        headers = {}
        query_params = {}
        cookies = {}

        # Create security options
        security_options = [
            SecurityOption(
                requirements=[
                    SecurityRequirement(scheme_name="api1-key", scopes=[]),
                    SecurityRequirement(scheme_name="api2-key", scopes=[]),
                ]
            )
        ]

        # Apply auth
        self.http_client._apply_auth_to_request(
            "https://example.com", headers, query_params, cookies, security_options
        )

        # Both APIs' auth should be applied
        self.assertEqual(query_params, {"api1-key": "api1-key-value"})
        self.assertEqual(headers, {"api2-key": "api2-key-value"})
        self.assertEqual(cookies, {})


if __name__ == "__main__":
    unittest.main()
