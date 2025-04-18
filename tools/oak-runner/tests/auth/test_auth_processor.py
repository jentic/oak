"""Tests for the auth processor module."""

import unittest

from oak_runner.auth.auth_parser import AuthType, AuthLocation, AuthRequirement
from oak_runner.auth.models import EnvVarKeys
from oak_runner.auth.auth_processor import AuthProcessor


class TestAuthProcessor(unittest.TestCase):
    """Test cases for the AuthProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.auth_processor = AuthProcessor()

        # Simple mock OpenAPI spec with auth requirements
        self.mock_openapi_spec = {
            "components": {
                "securitySchemes": {
                    "api_key": {
                        "type": "apiKey",
                        "name": "x-api-key",
                        "in": "header",
                        "description": "API key for authentication",
                    },
                    "oauth2": {
                        "type": "oauth2",
                        "flows": {
                            "clientCredentials": {
                                "tokenUrl": "https://api.example.com/oauth2/token",
                                "scopes": {"read": "Read access", "write": "Write access"},
                            }
                        },
                    },
                    "basic_auth": {
                        "type": "http",
                        "scheme": "basic",
                        "description": "Basic HTTP authentication",
                    },
                }
            },
            "security": [{"api_key": []}, {"oauth2": ["read", "write"]}],
        }

        # Simple mock Arazzo workflow with auth params
        self.mock_arazzo_spec = {
            "workflows": [
                {
                    "id": "getItems",
                    "parameters": [
                        {
                            "name": "Authorization",
                            "in": "header",
                            "value": "Bearer $dependencies.getToken.token",
                        }
                    ],
                },
                {
                    "id": "getToken",
                    "summary": "Get an authentication token",
                    "outputs": {"token": {"description": "The authentication token"}},
                },
            ]
        }

    def test_normalize_api_id_for_env(self):
        """Test normalizing API IDs for environment variables."""
        test_cases = [
            ("spotify", "SPOTIFY"),
            ("google-maps", "GOOGLE_MAPS"),
            ("aws.s3", "AWS_S3"),
            ("stripe.com/v1", "STRIPE_COM_V1"),
            ("my.api-name_123", "MY_API_NAME_123"),
        ]

        for api_id, expected in test_cases:
            result = self.auth_processor._convert_to_env_var(api_id)
            self.assertEqual(result, expected)

    def test_generate_env_mappings(self):
        """Test generating environment variable mappings."""
        # Create mock auth requirements
        api_key_req = AuthRequirement(
            auth_type=AuthType.API_KEY, 
            name="x-api-key", 
            location=AuthLocation.HEADER,
            security_scheme_name="ApiKey",
            api_title="Test API"
        )

        oauth2_req = AuthRequirement(
            auth_type=AuthType.OAUTH2,
            name="oauth2",
            flow_type="clientCredentials",
            security_scheme_name="OAuth2",
            api_title="Test API"
        )

        basic_req = AuthRequirement(
            auth_type=AuthType.HTTP, 
            name="basic_auth", 
            schemes=["basic"],
            security_scheme_name="BasicAuth",
            api_title="Test API"
        )

        auth_requirements = [api_key_req, oauth2_req, basic_req]

        # Test with auth requirements that have api_title
        mappings = self.auth_processor.generate_env_mappings(auth_requirements)

        # Check API key mappings
        self.assertIn("ApiKey", mappings)
        self.assertIn("apiKey", mappings["ApiKey"])
        self.assertEqual(mappings["ApiKey"]["apiKey"], "TEST_APIKEY")

        # Check OAuth2 mappings
        self.assertIn("OAuth2.clientCredentials", mappings)
        self.assertIn("client_id", mappings["OAuth2.clientCredentials"])
        self.assertEqual(mappings["OAuth2.clientCredentials"]["client_id"], "TEST_OAUTH2_CLIENT_ID")
        self.assertIn("client_secret", mappings["OAuth2.clientCredentials"])
        self.assertEqual(mappings["OAuth2.clientCredentials"]["client_secret"], "TEST_OAUTH2_CLIENT_SECRET")
        self.assertIn("token", mappings["OAuth2.clientCredentials"])
        self.assertEqual(mappings["OAuth2.clientCredentials"]["token"], "TEST_OAUTH2_ACCESS_TOKEN")

        # Check Basic auth mappings
        self.assertIn("BasicAuth", mappings)
        self.assertIn("username", mappings["BasicAuth"])
        self.assertEqual(mappings["BasicAuth"]["username"], "TEST_BASICAUTH_USERNAME")
        self.assertIn("password", mappings["BasicAuth"])
        self.assertEqual(mappings["BasicAuth"]["password"], "TEST_BASICAUTH_PASSWORD")

    def test_process_api_auth_with_direct_methods(self):
        """Test processing API authentication directly through class methods instead of external dependencies."""
        # Mock OpenAPI spec with auth requirements
        openapi_spec = {
            "components": {
                "securitySchemes": {
                    "api_key": {
                        "type": "apiKey",
                        "name": "x-api-key",
                        "in": "header",
                        "description": "API key for authentication",
                    }
                }
            }
        }

        # Process auth requirements
        result = self.auth_processor.process_api_auth({'source_id': openapi_spec})

        # Check the result structure
        self.assertIn("auth_requirements", result)
        self.assertIn("env_mappings", result)
        self.assertIn("auth_workflows", result)

        # Check that we have the API key requirement
        self.assertEqual(len(result["auth_requirements"]), 1)
        self.assertEqual(result["auth_requirements"][0]["type"], "apiKey")

    def test_api_prefix_sanitization(self):
        """Test that API prefixes with special characters are properly sanitized."""
        from oak_runner.auth.auth_parser import AuthLocation, AuthRequirement

        # Test cases with API titles containing special characters
        test_cases = [
            # API title with spaces and special chars
            "My API Name 123",
            # API title with multiple special chars
            "api@#$%^&*()_+",
            # API title with international characters
            "café-api",
            # API title with numbers and symbols
            "123-NAME!",
            # API title with existing underscores and special chars
            "my__name__name!!",
            # API title with consecutive special chars
            "api##name",
        ]

        for api_title in test_cases:
            # Create a simple auth requirement with the API title
            api_key_req = AuthRequirement(
                auth_type=AuthType.API_KEY, 
                name="x-api-key", 
                location=AuthLocation.HEADER,
                security_scheme_name="ApiKey",
                api_title=api_title
            )

            # Generate env mappings
            mappings = self.auth_processor.generate_env_mappings([api_key_req])

            # Get the actual generated env var
            self.assertIn("ApiKey", mappings)
            self.assertIn("apiKey", mappings["ApiKey"])
            actual_env_var = mappings["ApiKey"]["apiKey"]

            # Extract expected prefix from api_title
            expected_prefix = self.auth_processor._convert_to_env_var(api_title.split()[0].upper())
            expected_env_var = f"{expected_prefix}_APIKEY"

            # Check that the generated env var has been properly sanitized
            self.assertEqual(
                actual_env_var,
                expected_env_var,
                f"For API title '{api_title}', expected '{expected_env_var}' but got '{actual_env_var}'",
            )

    def test_api_title_prefix_in_env_mappings(self):
        """Test that API title is used as prefix in environment variable mappings when available."""
        from oak_runner.auth.auth_parser import AuthLocation, AuthRequirement
        
        # Create auth requirements with different API titles
        req_with_title = AuthRequirement(
            auth_type=AuthType.API_KEY,
            name="x-api-key",
            location=AuthLocation.HEADER,
            security_scheme_name="ApiKey",
            api_title="Discord API"  # This should be used for prefix
        )
        
        req_without_title = AuthRequirement(
            auth_type=AuthType.API_KEY,
            name="api-token",
            location=AuthLocation.HEADER,
            security_scheme_name="TokenKey"
            # No api_title
        )
        
        # Test with auth requirements
        mappings = self.auth_processor.generate_env_mappings([req_with_title, req_without_title])
        
        # Check that API title is used for prefix when available
        self.assertIn("ApiKey", mappings)
        self.assertIn(EnvVarKeys.API_KEY, mappings["ApiKey"])
        self.assertEqual(mappings["ApiKey"][EnvVarKeys.API_KEY], "DISCORD_APIKEY")
        
        # Check that no prefix is used when API title is not available
        self.assertIn("TokenKey", mappings)
        self.assertIn(EnvVarKeys.API_KEY, mappings["TokenKey"])
        # Since there's no api_title and we're not passing api_name or api_id anymore,
        # the prefix should be None, resulting in just the scheme name
        self.assertEqual(mappings["TokenKey"][EnvVarKeys.API_KEY], "TOKENKEY")

    def test_generate_env_mappings_with_multiple_sources(self):
        """Test generating environment variable mappings with multiple source descriptions."""
        # Create mock auth requirements from different sources
        source1_api_key_req = AuthRequirement(
            auth_type=AuthType.API_KEY, 
            name="x-api-key", 
            location=AuthLocation.HEADER,
            security_scheme_name="ApiKey",
            api_title="Source1 API",
            source_description_id="source1"
        )
        
        source1_oauth2_req = AuthRequirement(
            auth_type=AuthType.OAUTH2,
            name="oauth2",
            flow_type="clientCredentials",
            security_scheme_name="OAuth2",
            api_title="Source1 API",
            source_description_id="source1"
        )
        
        # Same scheme name as source1 but from a different source
        source2_api_key_req = AuthRequirement(
            auth_type=AuthType.API_KEY, 
            name="api-key", 
            location=AuthLocation.HEADER,
            security_scheme_name="ApiKey",  # Same name as in source1
            api_title="Source2 API",
            source_description_id="source2"
        )
        
        source2_bearer_req = AuthRequirement(
            auth_type=AuthType.HTTP, 
            name="bearer_auth", 
            schemes=["bearer"],
            security_scheme_name="BearerAuth",
            api_title="Source2 API",
            source_description_id="source2"
        )
        
        auth_requirements = [
            source1_api_key_req, 
            source1_oauth2_req, 
            source2_api_key_req, 
            source2_bearer_req
        ]
        
        # Generate mappings with multiple source descriptions
        mappings = self.auth_processor.generate_env_mappings(auth_requirements)
        
        # Verify the structure has source descriptions as outer keys
        self.assertIn("source1", mappings)
        self.assertIn("source2", mappings)
        
        # Check Source1 API key mappings
        self.assertIn("ApiKey", mappings["source1"])
        self.assertIn(EnvVarKeys.API_KEY, mappings["source1"]["ApiKey"])
        self.assertEqual(mappings["source1"]["ApiKey"][EnvVarKeys.API_KEY], "SOURCE1_APIKEY")
        
        # Check Source1 OAuth2 mappings
        self.assertIn("OAuth2.clientCredentials", mappings["source1"])
        self.assertIn(EnvVarKeys.CLIENT_ID, mappings["source1"]["OAuth2.clientCredentials"])
        self.assertEqual(mappings["source1"]["OAuth2.clientCredentials"][EnvVarKeys.CLIENT_ID], "SOURCE1_OAUTH2_CLIENT_ID")
        
        # Check Source2 API key mappings (same scheme name as Source1)
        self.assertIn("ApiKey", mappings["source2"])
        self.assertIn(EnvVarKeys.API_KEY, mappings["source2"]["ApiKey"])
        self.assertEqual(mappings["source2"]["ApiKey"][EnvVarKeys.API_KEY], "SOURCE2_APIKEY")
        
        # Check Source2 Bearer auth mappings
        self.assertIn("BearerAuth", mappings["source2"])
        self.assertIn(EnvVarKeys.TOKEN, mappings["source2"]["BearerAuth"])
        self.assertEqual(mappings["source2"]["BearerAuth"][EnvVarKeys.TOKEN], "SOURCE2_BEARERAUTH_TOKEN")


if __name__ == "__main__":
    unittest.main()
