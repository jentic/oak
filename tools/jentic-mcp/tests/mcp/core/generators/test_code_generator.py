"""Tests for the code generator module."""

import unittest
from unittest import mock

from mcp.core.generators.code_generator import _normalise_format, generate_code_sample
from mcp.core.generators.code_samples import CODE_SAMPLES


class TestCodeGenerator(unittest.TestCase):
    """Test cases for the code generator functions."""

    def test_normalise_format(self):
        """Test the _normalise_format function with various inputs."""
        # Test exact matches
        self.assertEqual(_normalise_format("claude"), "claude")
        self.assertEqual(_normalise_format("chatgpt"), "chatgpt")
        self.assertEqual(_normalise_format("anthropic"), "claude")
        self.assertEqual(_normalise_format("openai"), "chatgpt")

        # Test case insensitivity
        self.assertEqual(_normalise_format("Claude"), "claude")
        self.assertEqual(_normalise_format("CHATGPT"), "chatgpt")
        self.assertEqual(_normalise_format("OpenAI"), "chatgpt")

        # Test with spaces, hyphens, and underscores
        self.assertEqual(_normalise_format("chat-gpt"), "chatgpt")
        self.assertEqual(_normalise_format("chat gpt"), "chatgpt")
        self.assertEqual(_normalise_format("chat_gpt"), "chatgpt")

        # Test unknown format (should default to claude)
        self.assertEqual(_normalise_format("unknown_format"), "claude")
        self.assertEqual(_normalise_format("llama"), "claude")
        self.assertEqual(_normalise_format(""), "claude")

    def test_generate_code_sample_valid_format_and_language(self):
        """Test generate_code_sample with valid format and language."""
        # Test with existing format and language
        with mock.patch.dict(
            CODE_SAMPLES,
            {
                "claude": {"python": "claude python code"},
                "chatgpt": {"python": "chatgpt python code"},
            },
        ):
            result = generate_code_sample("claude", "python")
            self.assertEqual(result, "claude python code")

            result = generate_code_sample("chatgpt", "python")
            self.assertEqual(result, "chatgpt python code")

    def test_generate_code_sample_format_normalization(self):
        """Test format normalization in generate_code_sample."""
        # Should normalize different format variations to the right key
        with mock.patch.dict(
            CODE_SAMPLES,
            {
                "claude": {"python": "claude python code"},
                "chatgpt": {"python": "chatgpt python code"},
            },
        ):
            # Test Claude variations
            result = generate_code_sample("Claude", "python")
            self.assertEqual(result, "claude python code")

            result = generate_code_sample("anthropic", "python")
            self.assertEqual(result, "claude python code")

            # Test ChatGPT variations
            result = generate_code_sample("OpenAI", "python")
            self.assertEqual(result, "chatgpt python code")

            result = generate_code_sample("chat-gpt", "python")
            self.assertEqual(result, "chatgpt python code")

    def test_generate_code_sample_default_parameters(self):
        """Test generate_code_sample with default parameters."""
        with mock.patch.dict(CODE_SAMPLES, {"claude": {"python": "claude python code"}}):
            # Default should be claude and python
            result = generate_code_sample()
            self.assertEqual(result, "claude python code")

    def test_generate_code_sample_unknown_language(self):
        """Test generate_code_sample with unknown language."""
        with mock.patch.dict(CODE_SAMPLES, {"claude": {"python": "claude python code"}}):
            # Should return error with available languages
            result = generate_code_sample("claude", "ruby")
            self.assertIn("Sample not found for programming language: ruby", result)
            self.assertIn("Available languages for claude", result)
            self.assertIn("python", result)

    def test_generate_code_sample_unknown_format(self):
        """Test generate_code_sample with unknown format."""
        with mock.patch.dict(
            CODE_SAMPLES,
            {
                "claude": {"python": "claude python code"},
                "chatgpt": {"python": "chatgpt python code"},
            },
        ):
            # Unknown format should return error with available formats
            # Will be normalized to claude first, so we need to test with something
            # that won't be normalized to a known format
            with mock.patch(
                "mcp.core.generators.code_generator._normalise_format"
            ) as mock_normalize:
                mock_normalize.return_value = "unknown"
                result = generate_code_sample("unknown", "python")
                self.assertIn("Sample not found for format", result)
                self.assertIn("Available formats", result)
                self.assertIn("claude", result)
                self.assertIn("chatgpt", result)


if __name__ == "__main__":
    unittest.main()
