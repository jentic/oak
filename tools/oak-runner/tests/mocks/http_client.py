#!/usr/bin/env python3
"""
Mock HTTP Client for OAK Runner Testing

This module provides a configurable mock HTTP client that can be used for testing
Arazzo workflows without making real API calls.
"""

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from re import Pattern
from typing import Any

logger = logging.getLogger("arazzo-test")


@dataclass
class MockResponse:
    """Mock HTTP response for testing"""

    status_code: int
    json_data: dict[str, Any] | None = None
    text: str | None = None
    headers: dict[str, str] | None = None

    def __post_init__(self):
        """Initialize default values"""
        if self.text is None:
            self.text = json.dumps(self.json_data) if self.json_data is not None else ""
        if self.headers is None:
            self.headers = {}

    def json(self) -> dict[str, Any]:
        """Return JSON data"""
        if self.json_data is None:
            raise ValueError("No JSON data")
        return self.json_data

    def raise_for_status(self) -> None:
        """Raise an exception if status code is 4XX or 5XX"""
        if 400 <= self.status_code < 600:
            raise Exception(f"HTTP Error: {self.status_code}")


class RequestMatcher:
    """Matches HTTP requests based on various criteria"""

    def __init__(
        self,
        method: str,
        url_pattern: str | Pattern,
        query_params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        body_contains: list[str] | None = None,
    ):
        """
        Initialize a request matcher

        Args:
            method: HTTP method (GET, POST, etc.)
            url_pattern: URL pattern (string or regex)
            query_params: Query parameters to match
            headers: Headers to match
            json_body: JSON body to match (exact match)
            body_contains: Strings that must be present in the body
        """
        self.method = method.lower()
        self.original_url_pattern = url_pattern

        # Process the URL pattern to handle both absolute and relative URLs
        if isinstance(url_pattern, str):
            import urllib.parse

            # Normalize URL pattern (convert path params like {id} to regex)
            pattern_with_path_params = re.sub(r"\{([^}]+)\}", r"[^/]+", url_pattern)

            # Handle absolute URLs by extracting the path component
            if url_pattern.startswith("http://") or url_pattern.startswith("https://"):
                parsed_url = urllib.parse.urlparse(url_pattern)
                path = parsed_url.path

                # Apply path normalization in a generic way:
                # Strip API version prefixes from paths for matching
                # This handles patterns like /api/v1, /api/v2, /v3, etc.
                normalized_path = self._normalize_api_path(path)
                if normalized_path != path:
                    logger.debug(f"Normalized path from {path} to {normalized_path}")
                    path = normalized_path

                # Also normalize the pattern with path params
                normalized_pattern = self._normalize_full_url_pattern(pattern_with_path_params)
                if normalized_pattern != pattern_with_path_params:
                    logger.debug(
                        f"Normalized full pattern from {pattern_with_path_params} to {normalized_pattern}"
                    )
                    pattern_with_path_params = normalized_pattern

                # Create path pattern that matches the path part of the URL
                self.path_pattern = self._create_regex_pattern(path)

                # Create full pattern that matches the entire URL
                self.full_pattern = self._create_regex_pattern(pattern_with_path_params)

                # Store original components for logging
                self.base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                self.path = path
                self.original_path = parsed_url.path  # Keep the original for reference
            else:
                # For relative URLs, there's only a path
                # Apply the same path normalization
                normalized_path = self._normalize_api_path(url_pattern)
                if normalized_path != url_pattern:
                    logger.debug(
                        f"Normalized relative path from {url_pattern} to {normalized_path}"
                    )
                    url_pattern = normalized_path

                # Also normalize the pattern
                pattern_with_path_params = self._normalize_api_path(pattern_with_path_params)

                self.path_pattern = self._create_regex_pattern(pattern_with_path_params)
                self.full_pattern = None
                self.base_url = None
                self.path = url_pattern
                self.original_path = url_pattern  # Keep the original for reference

            logger.debug(f"Created URL matcher with path pattern: {self.path_pattern.pattern}")
            if self.full_pattern:
                logger.debug(f"And full URL pattern: {self.full_pattern.pattern}")
        else:
            # If it's already a regex pattern, use it directly
            self.path_pattern = url_pattern
            self.full_pattern = None
            self.base_url = None
            self.path = None

        self.query_params = query_params
        self.headers = headers
        self.json_body = json_body
        self.body_contains = body_contains

    def _normalize_api_path(self, path: str) -> str:
        """
        Normalize API paths by removing common version prefixes.
        This method can be extended to handle different API path formats.

        Args:
            path: The URL path to normalize

        Returns:
            The normalized path
        """
        # Common API version prefixes to strip for normalization
        # This makes URL matching more flexible across different API versions
        api_prefixes = [
            r"^/api/v\d+",  # Matches /api/v1, /api/v2, etc.
            r"^/v\d+",  # Matches /v1, /v2, etc.
            r"^/api",  # Matches /api
        ]

        # Only keep the actual resource path after the version prefix
        for prefix in api_prefixes:
            # Look for prefix followed by a path (/something)
            match = re.match(f"{prefix}(/.*)", path)
            if match:
                # Return just the resource path without the prefix
                return match.group(1)

        # No prefix matched, return original path
        return path

    def _normalize_full_url_pattern(self, url_pattern: str) -> str:
        """
        Normalize a full URL pattern by handling API version prefixes in the path component.

        Args:
            url_pattern: The full URL pattern to normalize

        Returns:
            The normalized pattern
        """
        # For full URLs, handle both http and https
        if url_pattern.startswith("http"):
            # Extract host and path
            match = re.match(r"^(https?://[^/]+)(/.*)", url_pattern)
            if match:
                host = match.group(1)
                path = match.group(2)

                # Normalize the path component
                normalized_path = self._normalize_api_path(path)
                if normalized_path != path:
                    return f"{host}{normalized_path}"

        # Return original if no normalization was done
        return url_pattern

    def _create_regex_pattern(self, url_str: str) -> Pattern:
        """Convert a URL string to a regex pattern, escaping special chars and handling wildcards"""
        # Escape dots and other regex special chars (except already escaped ones)
        pattern = re.sub(r"(?<!\\)\.", r"\.", url_str)

        # Handle wildcards (* becomes .*)
        pattern = pattern.replace("*", ".*")

        # Ensure start/end anchors
        return re.compile(f"^{pattern}$")

    def matches(self, request: dict[str, Any]) -> bool:
        """
        Check if the request matches this matcher

        Args:
            request: Request dictionary with method, url, and kwargs

        Returns:
            True if the request matches, False otherwise
        """
        # Check method
        if request["method"].lower() != self.method:
            logger.debug(
                f"Method mismatch: expected {self.method}, got {request['method'].lower()}"
            )
            return False

        # Check URL pattern
        url = request["url"]
        import urllib.parse

        # Handle URL matching based on whether it's absolute or relative
        if url.startswith("http://") or url.startswith("https://"):
            # This is an absolute URL
            parsed_url = urllib.parse.urlparse(url)
            request_path = parsed_url.path

            # Normalize the request path using the same rules
            normalized_request_path = self._normalize_api_path(request_path)

            # Try matching strategies in order of preference

            # 1. Try to match using the full pattern first
            if self.full_pattern and self.full_pattern.search(url):
                logger.debug(
                    f"Full URL pattern match: '{url}' matches '{self.original_url_pattern}'"
                )

            # 2. Try matching the normalized path with our path pattern
            elif self.path_pattern.search(normalized_request_path):
                logger.debug(
                    f"Normalized path match: '{normalized_request_path}' (from '{request_path}') matches '{self.path}'"
                )

            # 3. Try matching the original path directly
            elif self.path_pattern.search(request_path):
                logger.debug(f"Original path match: '{request_path}' matches '{self.path}'")

            # No match found
            else:
                logger.debug(
                    f"URL mismatch: neither full URL nor paths match. Request: '{url}', paths: '{request_path}'/'{normalized_request_path}'"
                )
                return False
        else:
            # This is a relative URL/path
            # Normalize the request path
            normalized_url = self._normalize_api_path(url)

            # Try matching the normalized path first
            if normalized_url != url and self.path_pattern.search(normalized_url):
                logger.debug(
                    f"Normalized path match: '{normalized_url}' (from '{url}') matches '{self.path}'"
                )

            # Then try the original path
            elif self.path_pattern.search(url):
                logger.debug(f"Path pattern match: '{url}' matches '{self.path}'")

            # No match found
            else:
                logger.debug(
                    f"URL path mismatch: '{url}' (normalized: '{normalized_url}') does not match path pattern '{self.path_pattern.pattern}'"
                )
                return False

        # Check query parameters
        if self.query_params:
            request_params = request["kwargs"].get("params", {})
            logger.debug(f"Request params: {request_params}")
            logger.debug(f"Expected params: {self.query_params}")

            for expected_key, expected_value in self.query_params.items():
                # Try to find a matching key - handle parameter name variations
                matched_key = None
                actual_value = None

                # Direct match
                if expected_key in request_params:
                    matched_key = expected_key
                    actual_value = request_params[expected_key]
                else:
                    # Instead of hardcoded parameter mappings, look for case-insensitive matches
                    # This handles common parameter name variations without special cases
                    for key in request_params:
                        if key.lower() == expected_key.lower():
                            matched_key = key
                            actual_value = request_params[key]
                            logger.debug(
                                f"Found case-insensitive parameter match: {key} for {expected_key}"
                            )
                            break

                # If we still haven't found a match, report failure
                if matched_key is None:
                    logger.debug(
                        f"Query param not found: expected '{expected_key}' (or equivalent), "
                        f"available keys: {list(request_params.keys())}"
                    )
                    return False

                # Now compare the values
                if isinstance(expected_value, list):
                    if isinstance(actual_value, list):
                        # Both are lists, compare contents
                        expected_set = set(str(v) for v in expected_value)
                        actual_set = set(str(v) for v in actual_value)

                        # Check if sets have elements in common (not requiring exact match)
                        if not expected_set.intersection(actual_set):
                            logger.debug(
                                f"Array param no common elements: expected {expected_value}, got {actual_value}"
                            )
                            return False
                        logger.debug(
                            f"Array param matched common elements between {expected_value} and {actual_value}"
                        )
                    elif isinstance(actual_value, str):
                        # Expected array, got string - try comma-split
                        if "," in actual_value:
                            actual_list = [item.strip() for item in actual_value.split(",")]
                            actual_set = set(actual_list)
                            expected_set = set(str(v) for v in expected_value)

                            # Check for common elements
                            if not expected_set.intersection(actual_set):
                                logger.debug(
                                    f"Array param no common elements: expected {expected_value}, got {actual_value} (split to {actual_list})"
                                )
                                return False
                            logger.debug(
                                f"Array param matched common elements between {expected_value} and {actual_list}"
                            )
                        else:
                            # Single string value, check if it's in the expected list
                            expected_str_values = [str(v) for v in expected_value]
                            if actual_value not in expected_str_values:
                                logger.debug(
                                    f"Single value not in expected array: {actual_value} not in {expected_value}"
                                )
                                return False
                            logger.debug(
                                f"Single value {actual_value} found in expected array {expected_value}"
                            )
                    else:
                        logger.debug(
                            f"Array parameter type mismatch: expected list, got {type(actual_value)}"
                        )
                        return False
                else:
                    # Non-array comparison
                    if str(actual_value) != str(expected_value):
                        logger.debug(
                            f"Parameter value mismatch: expected {expected_value}, got {actual_value}"
                        )
                        return False
                    logger.debug(
                        f"Parameter {matched_key}={actual_value} matched expected {expected_key}={expected_value}"
                    )

        # Check headers
        if self.headers:
            request_headers = request["kwargs"].get("headers", {})
            for key, value in self.headers.items():
                if key not in request_headers or request_headers[key] != value:
                    logger.debug(
                        f"Header mismatch: expected {key}={value}, got {request_headers.get(key, 'missing')}"
                    )
                    return False

        # Check JSON body
        if self.json_body:
            request_json = request["kwargs"].get("json")
            if request_json != self.json_body:
                logger.debug(f"JSON body mismatch: expected {self.json_body}, got {request_json}")
                return False

        # Check body contains
        if self.body_contains:
            request_data = request["kwargs"].get("data", "")
            if isinstance(request_data, bytes):
                request_data = request_data.decode("utf-8")
            for text in self.body_contains:
                if text not in request_data:
                    logger.debug(f"Body content mismatch: expected to contain '{text}', not found")
                    return False

        logger.debug(
            f"All matcher criteria passed for {self.method} {getattr(self.path_pattern, 'pattern', str(self.path_pattern))}"
        )
        return True


class DynamicMockResponse:
    """Dynamically generates mock responses based on request data"""

    def __init__(
        self,
        status_code: int = 200,
        json_generator: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        headers_generator: Callable[[dict[str, Any]], dict[str, str]] | None = None,
        text_generator: Callable[[dict[str, Any]], str] | None = None,
    ):
        """
        Initialize a dynamic mock response

        Args:
            status_code: HTTP status code to return
            json_generator: Function that generates JSON response based on request
            headers_generator: Function that generates headers based on request
            text_generator: Function that generates text response based on request
        """
        self.status_code = status_code
        self.json_generator = json_generator
        self.headers_generator = headers_generator
        self.text_generator = text_generator

    def generate_response(self, request: dict[str, Any]) -> MockResponse:
        """
        Generate a mock response based on the request

        Args:
            request: Request dictionary with method, url, and kwargs

        Returns:
            MockResponse object
        """
        json_data = None
        if self.json_generator:
            json_data = self.json_generator(request)

        headers = {}
        if self.headers_generator:
            headers = self.headers_generator(request)

        text = None
        if self.text_generator:
            text = self.text_generator(request)

        return MockResponse(
            status_code=self.status_code, json_data=json_data, headers=headers, text=text
        )


class MockHTTPExecutor:
    """
    Configurable mock HTTP client for testing

    This class can be used to mock HTTP responses for testing. It can be configured
    with static responses or dynamic response generators.
    """

    def __init__(self):
        """Initialize an empty mock HTTP client"""
        self.requests = []
        self.matchers = []
        self.default_response = MockResponse(404, {"error": "Not found"})

    def get(self, url, **kwargs):
        """
        Helper method for GET requests that mimics requests.get

        Args:
            url: URL to request
            **kwargs: Additional request parameters

        Returns:
            MockResponse object
        """
        return self.request("GET", url, **kwargs)

    def add_matcher(
        self, matcher: RequestMatcher, response: MockResponse | DynamicMockResponse
    ) -> None:
        """
        Add a request matcher and associated response

        Args:
            matcher: Request matcher to use
            response: Static or dynamic response to return when matched
        """
        self.matchers.append((matcher, response))

    def add_static_response(
        self,
        method: str,
        url_pattern: str | Pattern,
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        text: str | None = None,
        query_params: dict[str, str] | None = None,
        request_headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        body_contains: list[str] | None = None,
    ) -> None:
        """
        Add a static response for a specific request pattern

        Args:
            method: HTTP method (GET, POST, etc.)
            url_pattern: URL pattern (string or regex)
            status_code: HTTP status code to return
            json_data: JSON data to return
            headers: Headers to return
            text: Text response to return
            query_params: Query parameters to match
            request_headers: Headers to match
            json_body: JSON body to match
            body_contains: Strings that must be present in the body
        """
        matcher = RequestMatcher(
            method=method,
            url_pattern=url_pattern,
            query_params=query_params,
            headers=request_headers,
            json_body=json_body,
            body_contains=body_contains,
        )

        response = MockResponse(
            status_code=status_code, json_data=json_data, headers=headers, text=text
        )

        self.add_matcher(matcher, response)

    def add_dynamic_response(
        self,
        method: str,
        url_pattern: str | Pattern,
        status_code: int = 200,
        json_generator: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        headers_generator: Callable[[dict[str, Any]], dict[str, str]] | None = None,
        text_generator: Callable[[dict[str, Any]], str] | None = None,
        query_params: dict[str, str] | None = None,
        request_headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        body_contains: list[str] | None = None,
    ) -> None:
        """
        Add a dynamic response generator for a specific request pattern

        Args:
            method: HTTP method (GET, POST, etc.)
            url_pattern: URL pattern (string or regex)
            status_code: HTTP status code to return
            json_generator: Function that generates JSON response based on request
            headers_generator: Function that generates headers based on request
            text_generator: Function that generates text response based on request
            query_params: Query parameters to match
            request_headers: Headers to match
            json_body: JSON body to match
            body_contains: Strings that must be present in the body
        """
        matcher = RequestMatcher(
            method=method,
            url_pattern=url_pattern,
            query_params=query_params,
            headers=request_headers,
            json_body=json_body,
            body_contains=body_contains,
        )

        response = DynamicMockResponse(
            status_code=status_code,
            json_generator=json_generator,
            headers_generator=headers_generator,
            text_generator=text_generator,
        )

        self.add_matcher(matcher, response)

    def set_default_response(self, response: MockResponse) -> None:
        """
        Set the default response for unmatched requests

        Args:
            response: Response to return for unmatched requests
        """
        self.default_response = response

    def request(self, method: str, url: str, **kwargs) -> MockResponse:
        """
        Mock HTTP request method

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL to request
            **kwargs: Additional request parameters

        Returns:
            MockResponse object
        """
        # Record the request
        request_data = {"method": method, "url": url, "kwargs": kwargs}
        self.requests.append(request_data)

        # Print extra detailed logs for debugging
        logger.debug("==== MOCK HTTP REQUEST DETAILS ====")
        logger.debug(f"Method: {method.upper()}")
        logger.debug(f"URL: {url}")
        logger.debug(f"Params: {kwargs.get('params', {})}")
        logger.debug(f"Headers: {kwargs.get('headers', {})}")
        if "json" in kwargs:
            logger.debug(f"JSON Body: {kwargs['json']}")
        if "data" in kwargs:
            logger.debug(f"Data Body: {kwargs['data']}")
        logger.debug("==================================")

        # Normal matcher processing for other endpoints
        logger.debug(
            f"Looking for match for {method.upper()} {url} among {len(self.matchers)} matchers"
        )
        for i, (matcher, response) in enumerate(self.matchers):
            logger.debug(
                f"Trying matcher {i+1}: {matcher.method} {getattr(matcher.path_pattern, 'pattern', str(matcher.path_pattern))}"
            )

            if matcher.matches(request_data):
                logger.debug(f"Found matching response for: {method.upper()} {url}")

                # Handle dynamic responses
                if isinstance(response, DynamicMockResponse):
                    resp = response.generate_response(request_data)
                    logger.debug(f"Generated dynamic response: {resp.json_data}")
                    return resp

                logger.debug(
                    f"Using static response (status {response.status_code}): {response.json_data}"
                )
                return response
            else:
                logger.debug(f"Matcher {i+1} did not match")

        logger.debug(
            f"No matching response found for: {method.upper()} {url}. Using default: {self.default_response.status_code}"
        )
        return self.default_response

    def get_request_count(self) -> int:
        """Get the total number of requests made"""
        return len(self.requests)

    def get_last_request(self) -> dict[str, Any] | None:
        """Get the last request made"""
        if not self.requests:
            return None
        return self.requests[-1]

    def reset(self) -> None:
        """Reset the request history"""
        self.requests = []
