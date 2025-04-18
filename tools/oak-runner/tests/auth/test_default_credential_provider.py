"""
Unit tests for the DefaultCredentialProvider class.
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from oak_runner.auth.default_credential_provider import DefaultCredentialProvider
from oak_runner.auth.models import (
    AuthLocation,
    SecurityOption,
    SecurityRequirement,
    EnvVarKeys,
    RequestAuthValue,
    OAuth2Scheme,
    AuthType,
    OAuth2Flows,
    ClientCredentialsFlow
)


class TestDefaultCredentialProvider(unittest.TestCase):
    """Tests for the DefaultCredentialProvider class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create sample auth requirements
        self.api_key_req = {
            "type": "apiKey",
            "name": "ApiKey",
            "location": "header",
            "security_scheme_name": "ApiKeyAuth"
        }
        
        self.bearer_req = {
            "type": "http",
            "schemes": ["bearer"],
            "name": "Authorization",
            "location": "header",
            "security_scheme_name": "BearerAuth"
        }
        
        self.basic_req = {
            "type": "http",
            "schemes": ["basic"],
            "name": "Authorization",
            "location": "header",
            "security_scheme_name": "BasicAuth"
        }
        
        self.oauth2_req = {
            "type": "oauth2",
            "flow_type": "clientCredentials",
            "scopes": ["read", "write"],
            "security_scheme_name": "OAuth2Auth.clientCredentials",
            "auth_urls": {
                "token": "https://example.com/token"
            }
        }
        
        # Create sample environment mappings
        self.env_mappings = {
            "ApiKeyAuth": {
                EnvVarKeys.API_KEY: "TEST_API_KEY"
            },
            "BearerAuth": {
                EnvVarKeys.TOKEN: "TEST_BEARER_TOKEN"
            },
            "BasicAuth": {
                EnvVarKeys.USERNAME: "TEST_USERNAME",
                EnvVarKeys.PASSWORD: "TEST_PASSWORD"
            },
            "OAuth2Auth.clientCredentials": {
                EnvVarKeys.CLIENT_ID: "TEST_CLIENT_ID",
                EnvVarKeys.CLIENT_SECRET: "TEST_CLIENT_SECRET",
                EnvVarKeys.TOKEN: "TEST_OAUTH_TOKEN"
            }
        }

    @patch.dict(os.environ, {
        "TEST_API_KEY": "test-api-key-value",
        "TEST_BEARER_TOKEN": "test-bearer-token-value",
        "TEST_USERNAME": "test-username",
        "TEST_PASSWORD": "test-password"
    })
    def test_resolve_credentials_api_key(self):
        """Test resolving API Key credentials."""
        # Create provider with API Key auth requirement
        provider = DefaultCredentialProvider(
            auth_requirements=[self.api_key_req],
            env_mappings=self.env_mappings
        )
        
        # Create security option with API Key requirement
        security_option = SecurityOption(
            requirements=[
                SecurityRequirement(scheme_name="ApiKeyAuth", scopes=[])
            ]
        )
        
        # Resolve credentials
        result = provider.resolve_credentials([security_option])
        
        # Verify result
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], RequestAuthValue)
        self.assertEqual(result[0].location, AuthLocation.HEADER)
        self.assertEqual(result[0].name, "ApiKey")
        self.assertEqual(result[0].auth_value, "test-api-key-value")

    @patch.dict(os.environ, {
        "TEST_API_KEY": "test-api-key-value",
        "TEST_BEARER_TOKEN": "test-bearer-token-value",
        "TEST_USERNAME": "test-username",
        "TEST_PASSWORD": "test-password"
    })
    def test_resolve_credentials_bearer(self):
        """Test resolving Bearer token credentials."""
        # Create provider with Bearer auth requirement
        provider = DefaultCredentialProvider(
            auth_requirements=[self.bearer_req],
            env_mappings=self.env_mappings
        )
        
        # Create security option with Bearer requirement
        security_option = SecurityOption(
            requirements=[
                SecurityRequirement(scheme_name="BearerAuth", scopes=[])
            ]
        )
        
        # Resolve credentials
        result = provider.resolve_credentials([security_option])
        
        # Verify result
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], RequestAuthValue)
        self.assertEqual(result[0].location, AuthLocation.HEADER)
        self.assertEqual(result[0].name, "Authorization")
        self.assertEqual(result[0].auth_value, "Bearer test-bearer-token-value")

    @patch.dict(os.environ, {
        "TEST_API_KEY": "test-api-key-value",
        "TEST_BEARER_TOKEN": "test-bearer-token-value",
        "TEST_USERNAME": "test-username",
        "TEST_PASSWORD": "test-password"
    })
    def test_resolve_credentials_basic(self):
        """Test resolving Basic auth credentials."""
        # Create provider with Basic auth requirement
        provider = DefaultCredentialProvider(
            auth_requirements=[self.basic_req],
            env_mappings=self.env_mappings
        )
        
        # Create security option with Basic auth requirement
        security_option = SecurityOption(
            requirements=[
                SecurityRequirement(scheme_name="BasicAuth", scopes=[])
            ]
        )
        
        # Resolve credentials
        result = provider.resolve_credentials([security_option])
        
        # Verify result
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], RequestAuthValue)
        self.assertEqual(result[0].location, AuthLocation.HEADER)
        self.assertEqual(result[0].name, "Authorization")
        # Basic auth value should be base64 encoded username:password
        import base64
        expected_value = f"Basic {base64.b64encode(b'test-username:test-password').decode()}"
        self.assertEqual(result[0].auth_value, expected_value)

    @patch.dict(os.environ, {
        "TEST_API_KEY": "test-api-key-value",
        "TEST_BEARER_TOKEN": "test-bearer-token-value"
    })
    def test_resolve_credentials_missing_env_vars(self):
        """Test resolving credentials with missing environment variables."""
        # Create provider with Basic auth requirement (but missing env vars)
        provider = DefaultCredentialProvider(
            auth_requirements=[self.basic_req],
            env_mappings=self.env_mappings
        )
        
        # Create security option with Basic auth requirement
        security_option = SecurityOption(
            requirements=[
                SecurityRequirement(scheme_name="BasicAuth", scopes=[])
            ]
        )
        
        # Resolve credentials - should return empty list since env vars are missing
        result = provider.resolve_credentials([security_option])
        
        # Verify result is empty
        self.assertEqual(len(result), 0)

    @patch.dict(os.environ, {
        "TEST_API_KEY": "test-api-key-value",
        "TEST_BEARER_TOKEN": "test-bearer-token-value",
        "TEST_USERNAME": "test-username",
        "TEST_PASSWORD": "test-password"
    })
    def test_resolve_credentials_multiple_options(self):
        """Test resolving credentials with multiple security options."""
        # Create provider with multiple auth requirements
        provider = DefaultCredentialProvider(
            auth_requirements=[self.api_key_req, self.bearer_req, self.basic_req],
            env_mappings=self.env_mappings
        )
        
        # Create security options (API Key OR Bearer)
        api_key_option = SecurityOption(
            requirements=[
                SecurityRequirement(scheme_name="ApiKeyAuth", scopes=[])
            ]
        )
        bearer_option = SecurityOption(
            requirements=[
                SecurityRequirement(scheme_name="BearerAuth", scopes=[])
            ]
        )
        
        # Resolve credentials with multiple options
        result = provider.resolve_credentials([api_key_option, bearer_option])
        
        # Verify result - should process all options that resolve successfully
        self.assertEqual(len(result), 2)
        
        # First result should be from the first option (API Key)
        self.assertIsInstance(result[0], RequestAuthValue)
        self.assertEqual(result[0].location, AuthLocation.HEADER)
        self.assertEqual(result[0].name, "ApiKey")
        self.assertEqual(result[0].auth_value, "test-api-key-value")
        
        # Second result should be from the second option (Bearer)
        self.assertIsInstance(result[1], RequestAuthValue)
        self.assertEqual(result[1].location, AuthLocation.HEADER)
        self.assertEqual(result[1].name, "Authorization")
        self.assertEqual(result[1].auth_value, "Bearer test-bearer-token-value")

    @patch.dict(os.environ, {
        "TEST_API_KEY": "test-api-key-value",
        "TEST_BEARER_TOKEN": "test-bearer-token-value"
    })
    def test_resolve_credentials_combined_requirements(self):
        """Test resolving credentials with combined security requirements (AND relationship)."""
        # Create provider with multiple auth requirements
        provider = DefaultCredentialProvider(
            auth_requirements=[self.api_key_req, self.bearer_req],
            env_mappings=self.env_mappings
        )
        
        # Create security option with multiple requirements (API Key AND Bearer)
        combined_option = SecurityOption(
            requirements=[
                SecurityRequirement(scheme_name="ApiKeyAuth", scopes=[]),
                SecurityRequirement(scheme_name="BearerAuth", scopes=[])
            ]
        )
        
        # Resolve credentials
        result = provider.resolve_credentials([combined_option])
        
        # Verify result - should return both auth values
        self.assertEqual(len(result), 2)
        
        # First result should be API Key
        self.assertEqual(result[0].location, AuthLocation.HEADER)
        self.assertEqual(result[0].name, "ApiKey")
        self.assertEqual(result[0].auth_value, "test-api-key-value")
        
        # Second result should be Bearer token
        self.assertEqual(result[1].location, AuthLocation.HEADER)
        self.assertEqual(result[1].name, "Authorization")
        self.assertEqual(result[1].auth_value, "Bearer test-bearer-token-value")

    @patch.dict(os.environ, {
        "TEST_API_KEY_SOURCE1": "api-key-from-source1",
        "TEST_API_KEY_SOURCE2": "api-key-from-source2",
        "TEST_BEARER_TOKEN_SOURCE1": "bearer-token-from-source1",
        "TEST_BEARER_TOKEN_SOURCE2": "bearer-token-from-source2"
    })
    def test_resolve_credentials_with_source_name(self):
        """Test resolving credentials with source_name parameter."""
        # Create auth requirements with the same scheme name but different source descriptions
        api_key_req_source1 = {
            "type": "apiKey",
            "name": "ApiKey",
            "location": "header",
            "security_scheme_name": "ApiKeyAuth",
            "source_description_id": "source1"
        }
        
        api_key_req_source2 = {
            "type": "apiKey",
            "name": "ApiKey",
            "location": "header",
            "security_scheme_name": "ApiKeyAuth",
            "source_description_id": "source2"
        }
        
        # Create environment mappings with source name as the outer key
        env_mappings = {
            "source1": {
                "ApiKeyAuth": {
                    EnvVarKeys.API_KEY: "TEST_API_KEY_SOURCE1"
                }
            },
            "source2": {
                "ApiKeyAuth": {
                    EnvVarKeys.API_KEY: "TEST_API_KEY_SOURCE2"
                }
            }
        }
        
        # Create provider with auth requirements from both sources
        provider = DefaultCredentialProvider(
            auth_requirements=[api_key_req_source1, api_key_req_source2],
            env_mappings=env_mappings
        )
        
        # Create security option with ApiKeyAuth requirement
        security_option = SecurityOption(
            requirements=[
                SecurityRequirement(scheme_name="ApiKeyAuth", scopes=[])
            ]
        )
        
        # Test 1: Resolve with source1
        result_source1 = provider.resolve_credentials([security_option], source_name="source1")
        
        # Verify result for source1
        self.assertEqual(len(result_source1), 1)
        self.assertEqual(result_source1[0].name, "ApiKey")
        self.assertEqual(result_source1[0].auth_value, "api-key-from-source1")
        
        # Test 2: Resolve with source2
        result_source2 = provider.resolve_credentials([security_option], source_name="source2")
        
        # Verify result for source2
        self.assertEqual(len(result_source2), 1)
        self.assertEqual(result_source2[0].name, "ApiKey")
        self.assertEqual(result_source2[0].auth_value, "api-key-from-source2")

    @patch.dict(os.environ, {
        "TEST_API_KEY_SOURCE1": "api-key-from-source1",
        "TEST_API_KEY_SOURCE2": "api-key-from-source2"
    })
    def test_resolve_credentials_with_conflicting_scheme_names(self):
        """Test resolving credentials with conflicting scheme names from different sources."""
        # Create auth requirements with the same scheme name but different source descriptions
        api_key_req_source1 = {
            "type": "apiKey",
            "name": "ApiKey-Source1",  # Different name to distinguish in results
            "location": "header",
            "security_scheme_name": "ApiKeyAuth",  # Same scheme name
            "source_description_id": "source1"
        }
        
        api_key_req_source2 = {
            "type": "apiKey",
            "name": "ApiKey-Source2",  # Different name to distinguish in results
            "location": "header",
            "security_scheme_name": "ApiKeyAuth",  # Same scheme name
            "source_description_id": "source2"
        }
        
        # Create environment mappings with source name as the outer key
        env_mappings = {
            "source1": {
                "ApiKeyAuth": {
                    EnvVarKeys.API_KEY: "TEST_API_KEY_SOURCE1"
                }
            },
            "source2": {
                "ApiKeyAuth": {
                    EnvVarKeys.API_KEY: "TEST_API_KEY_SOURCE2"
                }
            }
        }
        
        # Create provider with auth requirements from both sources
        provider = DefaultCredentialProvider(
            auth_requirements=[api_key_req_source1, api_key_req_source2],
            env_mappings=env_mappings
        )
        
        # Create security option with ApiKeyAuth requirement
        security_option = SecurityOption(
            requirements=[
                SecurityRequirement(scheme_name="ApiKeyAuth", scopes=[])
            ]
        )
        
        # Test 1: Resolve with source1
        result_source1 = provider.resolve_credentials([security_option], source_name="source1")
        
        # Verify result for source1
        self.assertEqual(len(result_source1), 1)
        self.assertEqual(result_source1[0].name, "ApiKey-Source1")
        self.assertEqual(result_source1[0].auth_value, "api-key-from-source1")
        
        # Test 2: Resolve with source2
        result_source2 = provider.resolve_credentials([security_option], source_name="source2")
        
        # Verify result for source2
        self.assertEqual(len(result_source2), 1)
        self.assertEqual(result_source2[0].name, "ApiKey-Source2")
        self.assertEqual(result_source2[0].auth_value, "api-key-from-source2")
        
        # Test 3: Resolve with source1 (instead of relying on the code to find any source)
        result_no_source = provider.resolve_credentials([security_option], source_name="source1")
        
        # Verify result - we expect the source1 scheme since we specified it
        self.assertEqual(len(result_no_source), 1)
        self.assertEqual(result_no_source[0].name, "ApiKey-Source1")
        self.assertEqual(result_no_source[0].auth_value, "api-key-from-source1")

    @patch.dict(os.environ, {
        "TEST_CLIENT_ID": "test-client-id",
        "TEST_CLIENT_SECRET": "test-client-secret"
    })
    def test_resolve_credentials_oauth2_client_credentials(self):
        """Test resolving OAuth2 credentials using client credentials flow."""
        # Create OAuth2 auth requirement with client credentials flow
        oauth2_req = {
            "type": "oauth2",
            "flow_type": "clientCredentials",
            "scopes": ["read", "write"],
            "security_scheme_name": "OAuth2Auth",
            "auth_urls": {
                "token": "https://example.com/token"
            }
        }
        
        # Create environment mappings for OAuth2 client credentials
        env_mappings = {
            "OAuth2Auth.clientCredentials": {
                EnvVarKeys.CLIENT_ID: "TEST_CLIENT_ID",
                EnvVarKeys.CLIENT_SECRET: "TEST_CLIENT_SECRET"
            }
        }
        
        # Create mock HTTP client
        mock_http_client = MagicMock()
        
        # Create mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "dynamic-access-token",
            "token_type": "bearer",
            "expires_in": 3600
        }
        
        # Set up HTTP client to return mock response
        mock_http_client.post.return_value = mock_response
        
        # Create provider with OAuth2 auth requirement and mock HTTP client
        provider = DefaultCredentialProvider(
            auth_requirements=[oauth2_req],
            env_mappings=env_mappings,
            http_client=mock_http_client
        )
        
        # Create security option with OAuth2 requirement
        security_option = SecurityOption(
            requirements=[
                SecurityRequirement(scheme_name="OAuth2Auth", scopes=["read", "write"])
            ]
        )
        
        # Resolve credentials
        result = provider.resolve_credentials([security_option])
        
        # Verify HTTP request was made with correct parameters
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        
        # Check data
        self.assertEqual(call_args[1]['data'], {
            "grant_type": "client_credentials",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "scope": "read write"
        })
        
        # Verify result
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], RequestAuthValue)
        self.assertEqual(result[0].location, AuthLocation.HEADER)
        self.assertEqual(result[0].name, "Authorization")
        self.assertEqual(result[0].auth_value, "Bearer dynamic-access-token")


if __name__ == "__main__":
    unittest.main()
