#!/usr/bin/env python3
"""
Real HTTP Client for OAK Runner Testing

This module provides a real HTTP client that can be used for testing
Arazzo workflows by making actual API calls to servers.
"""

import logging
from typing import Any

import requests

logger = logging.getLogger("arazzo-test")


class RealHTTPExecutor:
    """
    Real HTTP client for testing

    This class makes actual HTTP requests to servers for testing.
    It maintains the same interface as MockHTTPExecutor for compatibility.
    """

    def __init__(
        self,
        base_urls: dict[str, str] | None = None,
        auth_values: dict[str, str] | None = None,
    ):
        """
        Initialize a real HTTP client

        Args:
            base_urls: Optional mapping of API names to base URLs
            auth_values: Optional mapping of auth names to values
        """
        self.requests = []
        self.base_urls = base_urls or {}
        self.auth_values = auth_values or {}
        self.session = requests.Session()

    def get(self, url, **kwargs):
        """Helper method for GET requests that mimics requests.get"""
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        """Helper method for POST requests that mimics requests.post"""
        return self.request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        """Helper method for PUT requests that mimics requests.put"""
        return self.request("PUT", url, **kwargs)

    def delete(self, url, **kwargs):
        """Helper method for DELETE requests that mimics requests.delete"""
        return self.request("DELETE", url, **kwargs)

    def patch(self, url, **kwargs):
        """Helper method for PATCH requests that mimics requests.patch"""
        return self.request("PATCH", url, **kwargs)

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Execute an HTTP request

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: URL to request
            **kwargs: Additional request parameters

        Returns:
            Response object
        """
        # Extract timeout from config or use default
        timeout = kwargs.pop("timeout", 30)  # Default 30 second timeout

        # Initialize headers if not present
        if "headers" not in kwargs:
            kwargs["headers"] = {}

        # Apply authentication values if available
        self._apply_auth_values(kwargs)

        # Record the request
        request_data = {"method": method, "url": url, "kwargs": kwargs}
        self.requests.append(request_data)

        # Log request details
        logger.debug("==== REAL HTTP REQUEST ====")
        logger.debug(f"Method: {method.upper()}")
        logger.debug(f"URL: {url}")
        logger.debug(f"Params: {kwargs.get('params', {})}")
        logger.debug(f"Headers: {kwargs.get('headers', {})}")
        if "json" in kwargs:
            logger.debug(f"JSON Body: {kwargs['json']}")
        if "data" in kwargs:
            logger.debug(f"Data Body: {kwargs['data']}")
        logger.debug("==========================")

        # Make the actual request
        response = self.session.request(method=method, url=url, timeout=timeout, **kwargs)

        logger.debug(f"Response status: {response.status_code}")
        try:
            logger.debug(f"Response body: {response.json()}")
        except Exception:
            logger.debug(f"Response text: {response.text[:200]}")

        return response

    def _apply_auth_values(self, kwargs: dict[str, Any]) -> None:
        """
        Apply authentication values to the request parameters

        Args:
            kwargs: Request parameters to modify
        """
        if not self.auth_values:
            return

        headers = kwargs.get("headers", {})
        params = kwargs.get("params", {})

        # Apply API key authentication in headers
        for auth_name, auth_value in self.auth_values.items():
            # Check if this is a common auth header name
            if auth_name.lower() in ["authorization", "api-key", "apikey", "x-api-key"]:
                headers[auth_name] = auth_value
                logger.debug(f"Applied header auth {auth_name}")
            # Check if this is a bearer token
            elif auth_name.lower() == "bearer":
                headers["Authorization"] = f"Bearer {auth_value}"
                logger.debug("Applied Bearer token auth")
            # Check if this is a basic auth value
            elif auth_name.lower() == "basic" and ":" in auth_value:
                import base64

                # Basic auth value should be in format "username:password"
                auth_bytes = auth_value.encode("utf-8")
                encoded = base64.b64encode(auth_bytes).decode("utf-8")
                headers["Authorization"] = f"Basic {encoded}"
                logger.debug("Applied Basic auth")
            # For OAuth2 tokens
            elif auth_name.lower() in ["oauth", "oauth2", "token", "access_token"]:
                headers["Authorization"] = f"Bearer {auth_value}"
                logger.debug("Applied OAuth token")

        # Update the request parameters
        kwargs["headers"] = headers

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

    # Stub methods to maintain interface compatibility with MockHTTPExecutor
    def add_matcher(self, *args, **kwargs):
        """Stub method for compatibility"""
        logger.warning("add_matcher called on RealHTTPExecutor - has no effect")
        pass

    def add_static_response(self, *args, **kwargs):
        """Stub method for compatibility"""
        logger.warning("add_static_response called on RealHTTPExecutor - has no effect")
        pass

    def add_dynamic_response(self, *args, **kwargs):
        """Stub method for compatibility"""
        logger.warning("add_dynamic_response called on RealHTTPExecutor - has no effect")
        pass

    def set_default_response(self, *args, **kwargs):
        """Stub method for compatibility"""
        logger.warning("set_default_response called on RealHTTPExecutor - has no effect")
        pass

    # Add empty matchers list for compatibility with MockHTTPExecutor.matchers attribute
    @property
    def matchers(self):
        """Return empty matchers list for compatibility"""
        return []
