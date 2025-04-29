#!/usr/bin/env python3
"""
OpenAPI Mock Response Generator

This module provides utilities for generating mock responses based on OpenAPI specifications.
It dynamically creates responses that conform to the defined schemas, allowing for comprehensive
testing of Arazzo workflows.
"""

import json
import logging
import random
import re
import string
from collections.abc import Callable
from typing import Any

import yaml

from .http_client import MockHTTPExecutor

logger = logging.getLogger("arazzo-test")


class OpenAPIMocker:
    """
    Generates mock responses based on OpenAPI specifications

    This class parses OpenAPI specifications and creates mock responses for API operations,
    allowing Arazzo workflows to be tested without making real API calls.
    """

    def __init__(self, http_client: MockHTTPExecutor = None):
        """
        Initialize the OpenAPI mocker

        Args:
            http_client: Optional HTTP client to configure. If None, a new one is created.
        """
        self.http_client = http_client or MockHTTPExecutor()
        self.specs = {}  # Maps spec names to parsed specs

    def load_spec(self, spec_path: str, name: str | None = None) -> str:
        """
        Load an OpenAPI specification from a file

        Args:
            spec_path: Path to the OpenAPI spec file (JSON or YAML)
            name: Optional name for the spec. If None, one will be generated

        Returns:
            Name of the loaded spec for future reference
        """
        # Determine name if not provided
        if name is None:
            import os

            name = os.path.basename(spec_path).split(".")[0]

        # Load the file
        with open(spec_path) as f:
            content = f.read()

        # Parse as JSON or YAML
        try:
            if spec_path.endswith(".json"):
                spec = json.loads(content)
            else:
                spec = yaml.safe_load(content)
        except Exception as e:
            raise ValueError(f"Failed to parse OpenAPI spec at {spec_path}: {e}")

        # Store the spec
        self.specs[name] = spec
        logger.info(f"Loaded OpenAPI spec '{name}' from {spec_path}")

        return name

    def mock_all_operations(
        self,
        spec_name: str,
        base_url: str | None = None,
        success_rate: float = 1.0,
        delay_range: tuple[float, float] | None = None,
    ) -> None:
        """
        Configure mock responses for all operations in a spec

        Args:
            spec_name: Name of the previously loaded spec
            base_url: Base URL to use for the API. If None, uses the first server URL in the spec
            success_rate: Probability of returning a success response (vs. error)
            delay_range: Optional range of seconds to delay responses (min, max)
        """
        if spec_name not in self.specs:
            raise ValueError(f"OpenAPI spec '{spec_name}' not found. Load it first.")

        spec = self.specs[spec_name]

        # Determine base URL
        if base_url is None:
            servers = spec.get("servers", [])
            if servers and "url" in servers[0]:
                base_url = servers[0]["url"]
            else:
                base_url = "https://api.example.com"

        # Remove trailing slash from base URL
        if base_url.endswith("/"):
            base_url = base_url[:-1]

        logger.info(f"Mocking all operations for '{spec_name}' at {base_url}")

        # Process all paths
        for path, path_item in spec.get("paths", {}).items():
            for method, operation in path_item.items():
                if method.lower() not in [
                    "get",
                    "post",
                    "put",
                    "delete",
                    "patch",
                    "options",
                    "head",
                ]:
                    continue

                self.mock_operation(
                    spec_name=spec_name,
                    path=path,
                    method=method,
                    base_url=base_url,
                    success_rate=success_rate,
                )

    def mock_operation(
        self,
        spec_name: str,
        path: str,
        method: str,
        base_url: str | None = None,
        operation_id: str | None = None,
        success_rate: float = 1.0,
        custom_response_generator: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        """
        Configure a mock response for a specific operation

        Args:
            spec_name: Name of the previously loaded spec
            path: API path (e.g., "/pets")
            method: HTTP method (e.g., "get", "post")
            base_url: Base URL to use. If None, uses the first server URL in the spec
            operation_id: If provided, matches the operationId instead of path/method
            success_rate: Probability of returning a success response (vs. error)
            custom_response_generator: Optional function to generate a custom response
        """
        if spec_name not in self.specs:
            raise ValueError(f"OpenAPI spec '{spec_name}' not found. Load it first.")

        spec = self.specs[spec_name]

        # Determine base URL
        if base_url is None:
            servers = spec.get("servers", [])
            if servers and "url" in servers[0]:
                base_url = servers[0]["url"]
            else:
                base_url = "https://api.example.com"

        # Remove trailing slash from base URL
        if base_url.endswith("/"):
            base_url = base_url[:-1]

        # Find the operation
        operation_spec = None

        if operation_id:
            # Find by operationId
            for p, path_item in spec.get("paths", {}).items():
                for m, op in path_item.items():
                    if m.lower() not in [
                        "get",
                        "post",
                        "put",
                        "delete",
                        "patch",
                        "options",
                        "head",
                    ]:
                        continue

                    if op.get("operationId") == operation_id:
                        operation_spec = op
                        path = p
                        method = m
                        break

                if operation_spec:
                    break
        else:
            # Find by path and method
            path_spec = spec.get("paths", {}).get(path, {})
            operation_spec = path_spec.get(method.lower())

        if not operation_spec:
            raise ValueError(f"Operation not found: {method.upper()} {path}")

        # Prepare URL pattern
        # Convert path parameters to regex
        url_pattern = re.escape(base_url + path)
        url_pattern = re.sub(r"\\{([^}]+)\\}", r"(?P<\1>[^/]+)", url_pattern)

        # Create dynamic response generator
        def generate_json_response(request: dict[str, Any]) -> dict[str, Any]:
            # Decide if this will be a success or error response
            is_success = random.random() < success_rate

            # Get appropriate response spec
            responses = operation_spec.get("responses", {})

            if is_success:
                # Find a success response (2xx)
                success_codes = [code for code in responses.keys() if str(code).startswith("2")]

                if success_codes:
                    response_code = random.choice(success_codes)
                    response_spec = responses[response_code]
                else:
                    # Default to 200 OK with empty response
                    return {}
            else:
                # Find an error response (4xx or 5xx)
                error_codes = [
                    code for code in responses.keys() if str(code).startswith(("4", "5"))
                ]

                if error_codes:
                    response_code = random.choice(error_codes)
                    response_spec = responses[response_code]
                else:
                    # Default to 500 with generic error
                    return {"error": "Internal Server Error"}

            # Find schema for response
            content = response_spec.get("content", {})
            json_content = content.get("application/json", {})
            schema = json_content.get("schema")

            if not schema:
                return {"message": response_spec.get("description", "OK")}

            # Generate mock data from schema
            data = self._generate_mock_data_from_schema(schema, spec)

            # For debugging
            logger.debug(
                f"Generated response for {method.upper()} {path}: success={is_success}, data={data}"
            )

            return data

        # Allow custom override
        if custom_response_generator:

            def json_generator(request: dict[str, Any]) -> dict[str, Any]:
                default_response = generate_json_response(request)
                return custom_response_generator(request, default_response)

        else:
            json_generator = generate_json_response

        # Add to HTTP client
        self.http_client.add_dynamic_response(
            method=method,
            url_pattern=url_pattern,
            status_code=(
                401 if success_rate == 0.0 else 200
            ),  # Use appropriate status code based on success rate
            json_generator=json_generator,
        )

        logger.info(f"Mocked operation: {method.upper()} {base_url}{path}")

    def _generate_mock_data_from_schema(self, schema: dict[str, Any], spec: dict[str, Any]) -> Any:
        """
        Generate mock data from an OpenAPI schema

        Args:
            schema: Schema definition from OpenAPI spec
            spec: Full OpenAPI spec for resolving references

        Returns:
            Generated mock data matching the schema
        """
        # Resolve references
        if "$ref" in schema:
            schema = self._resolve_ref(schema["$ref"], spec)

        schema_type = schema.get("type")

        # Handle different types
        if schema_type == "object":
            return self._generate_mock_object(schema, spec)
        elif schema_type == "array":
            return self._generate_mock_array(schema, spec)
        elif schema_type == "string":
            return self._generate_mock_string(schema)
        elif schema_type == "number" or schema_type == "integer":
            return self._generate_mock_number(schema)
        elif schema_type == "boolean":
            return random.choice([True, False])
        elif schema_type == "null":
            return None

        # Handle oneOf, anyOf, allOf
        if "oneOf" in schema:
            chosen_schema = random.choice(schema["oneOf"])
            return self._generate_mock_data_from_schema(chosen_schema, spec)
        elif "anyOf" in schema:
            chosen_schema = random.choice(schema["anyOf"])
            return self._generate_mock_data_from_schema(chosen_schema, spec)
        elif "allOf" in schema:
            # Merge all schemas (simple implementation)
            merged_schema = {}
            for s in schema["allOf"]:
                if "$ref" in s:
                    s = self._resolve_ref(s["$ref"], spec)
                if s.get("type") == "object":
                    merged_schema.update(s.get("properties", {}))

            mock_object = {}
            for prop, prop_schema in merged_schema.items():
                mock_object[prop] = self._generate_mock_data_from_schema(prop_schema, spec)
            return mock_object

        # Default to empty object for unknown types
        return {}

    def _generate_mock_object(self, schema: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
        """Generate mock data for object schema"""
        result = {}

        # Add required properties
        for prop in schema.get("required", []):
            if prop in schema.get("properties", {}):
                prop_schema = schema["properties"][prop]
                result[prop] = self._generate_mock_data_from_schema(prop_schema, spec)

        # Add some non-required properties (50% chance for each)
        for prop, prop_schema in schema.get("properties", {}).items():
            if prop not in result and random.random() > 0.5:
                result[prop] = self._generate_mock_data_from_schema(prop_schema, spec)

        # Handle additionalProperties
        additional_props = schema.get("additionalProperties")
        if additional_props and random.random() > 0.7:
            # Add a couple of random properties
            for _ in range(random.randint(1, 3)):
                random_key = "prop_" + "".join(random.choices(string.ascii_lowercase, k=5))
                if isinstance(additional_props, dict):
                    prop_value = self._generate_mock_data_from_schema(additional_props, spec)
                else:
                    prop_value = "additional value"
                result[random_key] = prop_value

        return result

    def _generate_mock_array(self, schema: dict[str, Any], spec: dict[str, Any]) -> list[Any]:
        """Generate mock data for array schema"""
        items_schema = schema.get("items", {})
        min_items = schema.get("minItems", 0)
        max_items = schema.get("maxItems", 10)

        # Limit to reasonable size for testing
        if max_items > 20:
            max_items = 20

        # Decide how many items to generate
        count = random.randint(min_items, max_items)

        # Generate items
        result = []
        for _ in range(count):
            item = self._generate_mock_data_from_schema(items_schema, spec)
            result.append(item)

        return result

    def _generate_mock_string(self, schema: dict[str, Any]) -> str:
        """Generate mock data for string schema"""
        string_format = schema.get("format", "")

        if string_format == "date":
            import datetime

            # Random date in last 10 years
            days = random.randint(0, 3650)
            date = datetime.date.today() - datetime.timedelta(days=days)
            return date.isoformat()

        elif string_format == "date-time":
            import datetime

            # Random date in last 10 years
            days = random.randint(0, 3650)
            hours = random.randint(0, 23)
            minutes = random.randint(0, 59)
            seconds = random.randint(0, 59)

            date = datetime.datetime.now() - datetime.timedelta(
                days=days, hours=hours, minutes=minutes, seconds=seconds
            )
            return date.isoformat() + "Z"

        elif string_format == "email":
            domains = ["example.com", "test.org", "mock.net"]
            username = "user_" + "".join(random.choices(string.ascii_lowercase, k=5))
            domain = random.choice(domains)
            return f"{username}@{domain}"

        elif string_format == "uri" or string_format == "url":
            protocols = ["http", "https"]
            domains = ["example.com", "test.org", "mock.net"]
            paths = ["api", "v1", "resources", "items"]

            protocol = random.choice(protocols)
            domain = random.choice(domains)
            path = "/".join(random.sample(paths, random.randint(1, 3)))

            return f"{protocol}://{domain}/{path}"

        elif string_format == "uuid":
            import uuid

            return str(uuid.uuid4())

        elif string_format == "password":
            chars = string.ascii_letters + string.digits + "!@#$%^&*"
            length = random.randint(8, 16)
            return "".join(random.choices(chars, k=length))

        elif "enum" in schema:
            return random.choice(schema["enum"])

        else:
            # Regular string - try to make it relevant to the property name
            min_length = schema.get("minLength", 1)
            max_length = schema.get("maxLength", 20)

            # Keep it reasonable
            if max_length > 100:
                max_length = 100

            length = random.randint(min_length, max_length)
            return "string_" + "".join(random.choices(string.ascii_lowercase, k=length - 7))

    def _generate_mock_number(self, schema: dict[str, Any]) -> int | float:
        """Generate mock data for number/integer schema"""
        is_integer = schema.get("type") == "integer"
        minimum = schema.get("minimum", 0)
        maximum = schema.get("maximum", 1000)

        # Handle exclusives
        if schema.get("exclusiveMinimum") and minimum is not None:
            minimum += 1 if is_integer else 0.01

        if schema.get("exclusiveMaximum") and maximum is not None:
            maximum -= 1 if is_integer else 0.01

        # If we have multiples of, ensure the result matches
        multiple_of = schema.get("multipleOf")

        if is_integer:
            if multiple_of and isinstance(multiple_of, int):
                # Find a multiple of the specified value within range
                possible_values = list(
                    range(
                        minimum // multiple_of * multiple_of,
                        maximum // multiple_of * multiple_of + multiple_of,
                        multiple_of,
                    )
                )
                return random.choice(possible_values) if possible_values else minimum
            else:
                return random.randint(minimum, maximum)
        else:
            if multiple_of:
                # This is simplified and might not be perfectly accurate for all cases
                base = random.uniform(minimum, maximum)
                return round(base // multiple_of * multiple_of, 8)
            else:
                return random.uniform(minimum, maximum)

    def _resolve_ref(self, ref: str, spec: dict[str, Any]) -> dict[str, Any]:
        """
        Resolve a JSON reference within the OpenAPI spec

        Args:
            ref: Reference string (e.g., "#/components/schemas/Pet")
            spec: OpenAPI spec containing the reference

        Returns:
            Resolved schema
        """
        if not ref.startswith("#/"):
            logger.warning(f"Only local references are supported: {ref}")
            return {}

        path = ref[2:].split("/")
        current = spec

        for segment in path:
            if segment not in current:
                logger.warning(f"Could not resolve reference {ref}, segment {segment} not found")
                return {}
            current = current[segment]

        return current
