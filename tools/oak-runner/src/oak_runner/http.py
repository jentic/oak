#!/usr/bin/env python3
"""
HTTP Client for OAK Runner

This module provides HTTP request handling for the OAK Runner.
"""

import logging
from typing import Any
from typing import Optional
from oak_runner.auth.models import SecurityOption, RequestAuthValue, AuthLocation
from oak_runner.auth.default_credential_provider import DefaultCredentialProvider
import requests

# Configure logging
logger = logging.getLogger("arazzo-runner.http")


class HTTPExecutor:
    """HTTP client for executing API requests in Arazzo workflows"""

    def __init__(self, http_client=None, auth_provider: Optional[DefaultCredentialProvider] = None):
        """
        Initialize the HTTP client

        Args:
            http_client: Optional HTTP client (defaults to requests.Session)
        """
        self.http_client = http_client or requests.Session()
        self.auth_provider: Optional[DefaultCredentialProvider] = auth_provider

    def execute_request(
        self, method: str, url: str, parameters: dict[str, Any], request_body: dict | None, security_options: list[SecurityOption] | None = None, source_name: str | None = None
    ) -> dict:
        """
        Execute an HTTP request using the configured client

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: URL to request
            parameters: Dictionary of parameters by location (path, query, header, cookie)
            request_body: Optional request body
            security_options: Optional list of security options for authentication
            source_name: Source API name to distinguish between APIs with conflicting scheme names

        Returns:
            response: Dictionary with status_code, headers, body
        """
        # Replace path parameters in the URL
        path_params = parameters.get("path", {})
        for name, value in path_params.items():
            url = url.replace(f"{{{name}}}", str(value))

        # Prepare query parameters
        query_params = parameters.get("query", {})

        # Prepare headers
        headers = parameters.get("header", {})

        # Prepare cookies
        cookies = parameters.get("cookie", {})

        # Log security options
        if security_options:
            logger.debug(f"Security options: {security_options}")
            for i, option in enumerate(security_options):
                logger.debug(f"Option {i} requirements: {option}")

        # Apply authentication headers from auth_provider if available
        self._apply_auth_to_request(url, headers, query_params, cookies, security_options, source_name)

        # Prepare request body
        data = None
        json_data = None

        if request_body:
            content_type = request_body.get("contentType")
            payload = request_body.get("payload")

            if content_type:
                headers["Content-Type"] = content_type

            if content_type and "json" in content_type.lower():
                json_data = payload
            elif content_type and ("form" in content_type.lower() or "x-www-form-urlencoded" in content_type.lower()):
                # Handle form data
                if isinstance(payload, dict):
                    data = payload
                else:
                    logger.warning(f"Form content type specified, but payload is not a dictionary: {type(payload)}. Sending as raw data.")
                    data = payload
            elif payload is not None:
                # Raw data - ensure it's bytes or string for the 'data' parameter
                if isinstance(payload, (str, bytes)):
                    data = payload
                else:
                    # Attempt to serialize other types? Or raise error? Let's log and convert to string for now.
                    logger.warning(f"Payload type {type(payload)} not directly supported for raw data. Converting to string.")
                    data = str(payload)

        # Log request details for debugging
        logger.debug(f"Making {method} request to {url}")
        logger.debug(f"Request headers: {headers}")
        if query_params:
            logger.debug(f"Query parameters: {query_params}")
        if cookies:
            logger.debug(f"Cookies: {cookies}")

        # Execute the request
        response = self.http_client.request(
            method=method,
            url=url,
            params=query_params,
            headers=headers,
            cookies=cookies,
            data=data,
            json=json_data,
        )

        # Process the response
        try:
            response_json = response.json()
        except:
            response_json = None

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response_json if response_json is not None else response.text,
        }

    def _apply_auth_to_request(
        self,
        url: str,
        headers: dict[str, str],
        query_params: dict[str, str],
        cookies: dict[str, str],
        security_options: list[SecurityOption] | None = None,
        source_name: str | None = None,
    ) -> None:
        """
        Apply authentication values from auth_provider to the request

        Args:
            url: The request URL
            headers: Headers dictionary to modify
            query_params: Query parameters dictionary to modify
            cookies: Cookies dictionary to modify
            security_options: List of security options to use for authentication
        """
        if not self.auth_provider:
            logger.debug("No auth_provider available, skipping auth application")
            return

        try:
            # If security options are provided, use them to resolve credentials
            if security_options and hasattr(self.auth_provider, "resolve_credentials"):
                logger.debug(f"Resolving credentials for security options: {security_options}")
                
                # Get auth values for the security requirements
                request_auth_values: list[RequestAuthValue] = self.auth_provider.resolve_credentials(security_options, source_name)
                
                if not request_auth_values:
                    logger.debug("No credentials resolved for the security requirements")
                    return
                
                # Apply each auth value to the request
                for auth_value in request_auth_values:
                    if auth_value.location == AuthLocation.QUERY:
                        query_params[auth_value.name] = auth_value.auth_value
                        logger.debug(f"Applied '{auth_value.name}' as query parameter")
                    elif auth_value.location == AuthLocation.HEADER:
                        headers[auth_value.name] = auth_value.auth_value
                        logger.debug(f"Applied '{auth_value.name}' as header")
                    elif auth_value.location == AuthLocation.COOKIE:
                        cookies[auth_value.name] = auth_value.auth_value
                        logger.debug(f"Applied '{auth_value.name}' as cookie")
                    else:
                        # Default to header for unknown locations
                        headers[auth_value.name] = auth_value.auth_value
                        logger.debug(f"Applied '{auth_value.name}' as header (default)")

            # Also check for direct auth values in auth_provider
            if hasattr(self.auth_provider, "get_auth_value"):
                for header_name in ["Authorization", "Api-Key", "X-Api-Key", "Token"]:
                    if header_name not in headers:
                        auth_value = self.auth_provider.get_auth_value(header_name)
                        if auth_value:
                            headers[header_name] = auth_value
                            logger.debug(f"Applied {header_name} from auth_provider")
        except Exception as e:
            logger.error(f"Error applying auth to request: {e}")
            # Don't re-raise, just log and continue
