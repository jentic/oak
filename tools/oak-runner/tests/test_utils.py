"""Tests for the utils module."""

import unittest
from unittest.mock import patch

from oak_runner.utils import extract_api_title_prefix, sanitize_for_env_var


class TestExtractApiTitlePrefix(unittest.TestCase):
    """Test cases for the extract_api_title_prefix function."""

    def test_basic_title(self):
        """Test with a basic title."""
        self.assertEqual(extract_api_title_prefix("Petstore"), "PETSTORE")
        self.assertEqual(extract_api_title_prefix("Pet Store API"), "PET")

    def test_skip_words(self):
        """Test that skip words are properly handled."""
        # Test each skip word
        self.assertEqual(extract_api_title_prefix("The Petstore"), "PETSTORE")
        self.assertEqual(extract_api_title_prefix("A Petstore"), "PETSTORE")
        self.assertEqual(extract_api_title_prefix("An Example API"), "EXAMPLE")
        
        # Test multiple skip words
        self.assertEqual(extract_api_title_prefix("The OpenAPI Petstore"), "PETSTORE")
        self.assertEqual(extract_api_title_prefix("An API for The Petstore"), "FOR")

    def test_case_insensitive_skip_words(self):
        """Test that skip words are case-insensitive."""
        self.assertEqual(extract_api_title_prefix("THE PETSTORE"), "PETSTORE")
        self.assertEqual(extract_api_title_prefix("openAPI Documentation"), "DOCUMENTATION")
        self.assertEqual(extract_api_title_prefix("SWAGGER Petstore"), "PETSTORE")

    def test_empty_or_none_title(self):
        """Test with empty or None title."""
        self.assertIsNone(extract_api_title_prefix(""))
        self.assertIsNone(extract_api_title_prefix(" "))
        self.assertIsNone(extract_api_title_prefix("  \t \n "))
        self.assertIsNone(extract_api_title_prefix(None))

    def test_special_characters(self):
        """Test with special characters in the title."""
        # The sanitize_for_env_var function will handle special characters
        self.assertEqual(extract_api_title_prefix("My-API 123"), "MY_API")
        self.assertEqual(extract_api_title_prefix("The My-API 2.0"), "MY_API")
        self.assertEqual(extract_api_title_prefix("My-API 2.0"), "MY_API")
