#!/usr/bin/env python3
"""
Tests for environment variable mappings in OAK Runner
"""

import unittest
from unittest.mock import MagicMock, patch

from oak_runner.models import ServerConfiguration, ServerVariable
from oak_runner.runner import OAKRunner


class TestEnvMappings(unittest.TestCase):
    """Test case for environment variable mappings"""

    def test_get_env_mappings_includes_server_variables(self):
        """Test that get_env_mappings includes server variables when they exist"""
        # Create mock OpenAPI specs with server variables
        mock_openapi_specs = {
            "test_api": {
                "info": {
                    "title": "Test API",
                    "version": "1.0.0"
                },
                "servers": [
                    {
                        "url": "https://{environment}.api.example.com/v{version}",
                        "description": "API server",
                        "variables": {
                            "environment": {
                                "default": "dev",
                                "enum": ["dev", "staging", "prod"],
                                "description": "API environment"
                            },
                            "version": {
                                "default": "1",
                                "enum": ["1", "2"],
                                "description": "API version"
                            }
                        }
                    }
                ]
            }
        }

        # Create mock auth provider with predefined env mappings
        mock_auth_provider = MagicMock()
        mock_auth_provider.env_mappings = {
            "ApiKey": {
                "apiKey": "TEST_API_KEY"
            }
        }

        # Create OAKRunner with mocked dependencies
        with patch('oak_runner.http.HTTPExecutor') as mock_http_executor:
            runner = OAKRunner(
                arazzo_doc={},
                source_descriptions=mock_openapi_specs,
                auth_provider=mock_auth_provider
            )

            # Get environment mappings
            env_mappings = runner.get_env_mappings()

            # Verify auth mappings are included
            self.assertIn("auth", env_mappings)
            self.assertEqual(env_mappings["auth"], mock_auth_provider.env_mappings)

            # Verify server mappings are included
            self.assertIn("servers", env_mappings)
            self.assertIn("test_api", env_mappings["servers"])
            
            # Verify the server URL mapping
            server_url = "https://{environment}.api.example.com/v{version}"
            self.assertIn(server_url, env_mappings["servers"]["test_api"])
            
            # Verify the variable mappings
            server_vars = env_mappings["servers"]["test_api"][server_url]
            self.assertIn("environment", server_vars)
            self.assertIn("version", server_vars)
            
            # Verify the environment variable names
            self.assertEqual(server_vars["environment"], "TEST_OAK_SERVER_ENVIRONMENT")
            self.assertEqual(server_vars["version"], "TEST_OAK_SERVER_VERSION")


    def test_get_env_mappings_omits_servers_key_when_no_variables(self):
        """Test that get_env_mappings doesn't include servers key when no server variables exist"""
        # Create mock OpenAPI specs with no server variables
        mock_openapi_specs = {
            "test_api": {
                "info": {
                    "title": "Test API",
                    "version": "1.0.0"
                },
                # No servers defined
            }
        }

        # Create mock auth provider with predefined env mappings
        mock_auth_provider = MagicMock()
        mock_auth_provider.env_mappings = {
            "ApiKey": {
                "apiKey": "TEST_API_KEY"
            }
        }

        # Create OAKRunner with mocked dependencies
        with patch('oak_runner.http.HTTPExecutor') as mock_http_executor:
            runner = OAKRunner(
                arazzo_doc={},
                source_descriptions=mock_openapi_specs,
                auth_provider=mock_auth_provider
            )

            # Get environment mappings
            env_mappings = runner.get_env_mappings()

            # Verify auth mappings are included
            self.assertIn("auth", env_mappings)
            self.assertEqual(env_mappings["auth"], mock_auth_provider.env_mappings)

            # Verify servers key is NOT included
            self.assertNotIn("servers", env_mappings)
            
    def test_get_env_mappings_includes_multiple_api_specs(self):
        """Test that get_env_mappings includes server variables from multiple API specs"""
        # Create mock OpenAPI specs with different server variables
        mock_openapi_specs = {
            "payment_api": {
                "info": {
                    "title": "Payment API",
                    "version": "1.0.0"
                },
                "servers": [
                    {
                        "url": "https://{environment}.payments.example.com/v{version}",
                        "description": "Payment API server",
                        "variables": {
                            "environment": {
                                "default": "dev",
                                "enum": ["dev", "staging", "prod"],
                                "description": "Payment API environment"
                            },
                            "version": {
                                "default": "1",
                                "enum": ["1", "2"],
                                "description": "Payment API version"
                            }
                        }
                    }
                ]
            },
            "user_api": {
                "info": {
                    "title": "User API",
                    "version": "1.0.0"
                },
                "servers": [
                    {
                        "url": "https://{region}.users.example.com",
                        "description": "User API server",
                        "variables": {
                            "region": {
                                "default": "us-east",
                                "enum": ["us-east", "us-west", "eu-central"],
                                "description": "User API region"
                            }
                        }
                    }
                ]
            }
        }

        # Create mock auth provider with predefined env mappings
        mock_auth_provider = MagicMock()
        mock_auth_provider.env_mappings = {
            "PaymentAuth": {
                "apiKey": "PAYMENT_API_KEY"
            },
            "UserAuth": {
                "apiKey": "USER_API_KEY"
            }
        }

        # Create mock Arazzo workflow document that references both APIs
        mock_arazzo_doc = {
            "sourceDescriptions": [
                {"name": "payment_api", "url": "payment_api.yaml", "type": "openapi"},
                {"name": "user_api", "url": "user_api.yaml", "type": "openapi"}
            ],
            "workflows": [
                {
                    "workflowId": "test_workflow",
                    "steps": [
                        {"stepId": "step1", "operationId": "makePayment", "source": "payment_api"},
                        {"stepId": "step2", "operationId": "getUser", "source": "user_api"}
                    ]
                }
            ]
        }

        # Create OAKRunner with mocked dependencies
        with patch('oak_runner.http.HTTPExecutor') as mock_http_executor:
            runner = OAKRunner(
                arazzo_doc=mock_arazzo_doc,
                source_descriptions=mock_openapi_specs,
                auth_provider=mock_auth_provider
            )

            # Get environment mappings
            env_mappings = runner.get_env_mappings()

            # Verify auth mappings are included
            self.assertIn("auth", env_mappings)
            self.assertEqual(env_mappings["auth"], mock_auth_provider.env_mappings)

            # Verify server mappings are included
            self.assertIn("servers", env_mappings)
            
            # Verify both API specs are included in server mappings
            self.assertIn("payment_api", env_mappings["servers"])
            self.assertIn("user_api", env_mappings["servers"])
            
            # Verify payment_api server variables
            payment_server_url = "https://{environment}.payments.example.com/v{version}"
            self.assertIn(payment_server_url, env_mappings["servers"]["payment_api"])
            payment_vars = env_mappings["servers"]["payment_api"][payment_server_url]
            self.assertIn("environment", payment_vars)
            self.assertIn("version", payment_vars)
            self.assertEqual(payment_vars["environment"], "PAYMENT_OAK_SERVER_ENVIRONMENT")
            self.assertEqual(payment_vars["version"], "PAYMENT_OAK_SERVER_VERSION")
            
            # Verify user_api server variables
            user_server_url = "https://{region}.users.example.com"
            self.assertIn(user_server_url, env_mappings["servers"]["user_api"])
            user_vars = env_mappings["servers"]["user_api"][user_server_url]
            self.assertIn("region", user_vars)
            self.assertEqual(user_vars["region"], "USER_OAK_SERVER_REGION")


if __name__ == "__main__":
    unittest.main()