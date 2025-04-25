#!/usr/bin/env python3
"""
Operation Finder for OAK Runner

This module provides functionality to find operations in OpenAPI specifications.
"""

import logging
import re
from typing import Any

import jsonpointer
from oak_runner.auth.models import SecurityOption, SecurityRequirement

# Configure logging
logger = logging.getLogger("arazzo-runner.executor")


class OperationFinder:
    """Finds operations in source descriptions by ID or path"""

    def __init__(self, source_descriptions: dict[str, Any]):
        """
        Initialize the operation finder

        Args:
            source_descriptions: OpenAPI source descriptions
        """
        self.source_descriptions = source_descriptions

    def find_by_id(self, operation_id: str) -> dict | None:
        """
        Find an operation in source descriptions by its operationId

        Args:
            operation_id: Operation ID to find

        Returns:
            Dictionary with operation details or None if not found
        """
        for source_name, source_desc in self.source_descriptions.items():
            # Search through paths and operations
            paths = source_desc.get("paths", {})
            for path, path_item in paths.items():
                for method, operation in path_item.items():
                    if (
                        method in ["get", "post", "put", "delete", "patch"]
                        and operation.get("operationId") == operation_id
                    ):
                        # Found the operation
                        try:
                            servers = source_desc.get("servers")
                            if not servers or not isinstance(servers, list):
                                raise ValueError("Missing or invalid 'servers' list in OpenAPI spec.")
                            base_url = servers[0].get("url")
                            if not base_url or not isinstance(base_url, str):
                                raise ValueError("Missing or invalid 'url' in the first server object.")
                        except (IndexError, ValueError) as e:
                            # Catch IndexError if servers list is empty or ValueError from explicit raises
                            raise ValueError(f"Could not determine base URL from OpenAPI spec servers: {e}") from e

                        return {
                            "source": source_name,
                            "path": path,
                            "method": method,
                            "url": base_url + path,
                            "operation": operation,
                        }

        return None

    def find_by_http_path_and_method(self, http_path: str, http_method: str) -> dict | None:
        """
        Find an operation in source descriptions by its HTTP path and method.

        Args:
            http_path: The HTTP path (e.g., '/users/{id}').
            http_method: The HTTP method (e.g., 'GET', 'POST'). Case-insensitive.

        Returns:
            Dictionary with operation details or None if not found.
        """
        target_method = http_method.lower() # Ensure case-insensitive comparison
        logger.debug(f"Finding operation by HTTP path and method: Path='{http_path}', Method='{target_method}'")

        for source_name, source_desc in self.source_descriptions.items():
            paths = source_desc.get("paths", {})
            if http_path in paths:
                path_item = paths[http_path]
                if target_method in path_item:
                    operation = path_item[target_method]
                    # Found the operation
                    try:
                        servers = source_desc.get("servers")
                        if not servers or not isinstance(servers, list):
                            raise ValueError("Missing or invalid 'servers' list in OpenAPI spec.")
                        base_url = servers[0].get("url")
                        if not base_url or not isinstance(base_url, str):
                            raise ValueError("Missing or invalid 'url' in the first server object.")
                    except (IndexError, ValueError) as e:
                        # Catch IndexError if servers list is empty or ValueError from explicit raises
                        raise ValueError(f"Could not determine base URL from OpenAPI spec servers: {e}") from e

                    logger.debug(f"Found operation in '{source_name}' for {target_method.upper()} {http_path}")
                    return {
                        "source": source_name,
                        "path": http_path,
                        "method": target_method,
                        "url": base_url + http_path, # Base URL + path
                        "operation": operation,
                        "operationId": operation.get("operationId") # Include operationId if available
                    }
                else:
                    logger.debug(f"Method '{target_method}' not found for path '{http_path}' in source '{source_name}'")
            else:
                 # Check for paths with variables
                 for path_key, path_item in paths.items():
                     if '{' in path_key and self._paths_match(path_key, http_path):
                          if target_method in path_item:
                                operation = path_item[target_method]
                                try:
                                    servers = source_desc.get("servers")
                                    if not servers or not isinstance(servers, list):
                                        raise ValueError("Missing or invalid 'servers' list in OpenAPI spec.")
                                    base_url = servers[0].get("url")
                                    if not base_url or not isinstance(base_url, str):
                                        raise ValueError("Missing or invalid 'url' in the first server object.")
                                except (IndexError, ValueError) as e:
                                    # Catch IndexError if servers list is empty or ValueError from explicit raises
                                    raise ValueError(f"Could not determine base URL from OpenAPI spec servers: {e}") from e

                                logger.debug(f"Found operation (template match) in '{source_name}' for {target_method.upper()} {path_key} matching {http_path}")
                                return {
                                    "source": source_name,
                                    "path": path_key, # Return the template path
                                    "method": target_method,
                                    "url": base_url + path_key, # Use template path for URL construction
                                    "operation": operation,
                                    "operationId": operation.get("operationId")
                                }

        logger.warning(f"Operation not found for {target_method.upper()} {http_path}")
        return None

    def _paths_match(self, template_path: str, concrete_path: str) -> bool:
        """Check if a concrete path matches a template path (e.g., /users/{id})."""
        template_segments = template_path.strip('/').split('/')
        concrete_segments = concrete_path.strip('/').split('/')

        if len(template_segments) != len(concrete_segments):
            return False

        for template_seg, concrete_seg in zip(template_segments, concrete_segments):
            if template_seg.startswith('{') and template_seg.endswith('}'):
                continue  # Variable segment matches anything
            if template_seg != concrete_seg:
                return False # Segments must match exactly

        return True

    def find_by_path(self, source_url: str, json_pointer: str) -> dict | None:
        """
        Find an operation in source descriptions by its path

        Args:
            source_url: Source description name or URL
            json_pointer: JSON Pointer to the operation

        Returns:
            Dictionary with operation details or None if not found
        """
        # Log the inputs for debugging
        logger.debug(
            f"Finding operation by path: source_url={source_url}, json_pointer={json_pointer}"
        )

        # Find the source description
        source_desc = self._find_source_description(source_url)
        if not source_desc:
            logger.error(f"Could not find source description for {source_url}")
            return None

        source_name = source_url  # We'll use the provided URL as the name for simplicity

        # Parse the JSON pointer to extract the operation path and method
        operation_info = self._parse_operation_pointer(json_pointer, source_name, source_desc)

        return operation_info

    def _find_source_description(self, source_url: str) -> dict | None:
        """
        Find a source description by URL or name

        Args:
            source_url: Source URL or name

        Returns:
            Source description or None if not found
        """
        # First, try to match by exact name
        if source_url in self.source_descriptions:
            logger.debug(f"Found source description by exact name: {source_url}")
            return self.source_descriptions[source_url]

        # If not an exact match, try to find by URL or name similarity
        for name, desc in self.source_descriptions.items():
            if name in source_url or source_url.endswith(name):
                logger.debug(f"Found source description by partial match: {name}")
                return desc

        return None

    def _parse_operation_pointer(
        self, json_pointer: str, source_name: str, source_desc: dict
    ) -> dict | None:
        """
        Parse a JSON pointer to an operation and extract the relevant details

        Args:
            json_pointer: JSON Pointer to the operation
            source_name: Name of the source
            source_desc: Source description

        Returns:
            Operation details or None if parsing fails
        """
        try:
            paths_obj = source_desc.get("paths", {})
            logger.debug(f"Available paths in {source_name}: {list(paths_obj.keys())}")

            # Ensure the pointer starts with a slash
            if not json_pointer.startswith("/"):
                json_pointer = "/" + json_pointer

            logger.debug(f"Processing JSON Pointer: {json_pointer}")

            # First approach: Extract path and method using regex pattern for standard paths like /paths/<path>/<method>
            operation_info = self._extract_path_method_with_regex(
                json_pointer, source_name, source_desc
            )
            if operation_info:
                return operation_info

            # Second approach: Use full JSON pointer resolution with jsonpointer library
            operation_info = self._resolve_with_jsonpointer(json_pointer, source_name, source_desc)
            if operation_info:
                return operation_info

            # Third approach: Handle special cases for complex paths with path parameters
            operation_info = self._handle_special_cases(json_pointer, source_name, source_desc)
            if operation_info:
                return operation_info

            logger.error(f"Could not parse operation pointer: {json_pointer}")
            return None
        except Exception as e:
            logger.error(f"Error parsing operation pointer: {e}")
            logger.exception("Detailed exception information:")
            return None

    def _extract_path_method_with_regex(
        self, json_pointer: str, source_name: str, source_desc: dict
    ) -> dict | None:
        """
        Extract path and method from a JSON pointer using regex patterns

        Args:
            json_pointer: JSON Pointer to the operation
            source_name: Name of the source
            source_desc: Source description

        Returns:
            Operation details or None if extraction fails
        """
        try:
            # Common pattern for operations in OpenAPI specs: /paths/<path>/<method>
            # The path part may contain encoded forward slashes as ~1
            path_method_pattern = r"/paths(/[^/]+)/([a-z]+)"
            match = re.search(path_method_pattern, json_pointer)

            if match:
                # Get the encoded path and method
                encoded_path, method = match.groups()
                logger.debug(f"Regex matched. Encoded path: {encoded_path}, method: {method}")

                # Decode the path (replace ~1 with / and ~0 with ~)
                decoded_path = encoded_path.replace("~1", "/").replace("~0", "~")
                logger.debug(f"Decoded path: {decoded_path}")

                # Try to find the operation in the source description
                paths_obj = source_desc.get("paths", {})
                operation = paths_obj.get(decoded_path, {}).get(method)

                if operation:
                    # Get the base URL
                    try:
                        servers = source_desc.get("servers")
                        if not servers or not isinstance(servers, list):
                            raise ValueError("Missing or invalid 'servers' list in OpenAPI spec.")
                        base_url = servers[0].get("url")
                        if not base_url or not isinstance(base_url, str):
                            raise ValueError("Missing or invalid 'url' in the first server object.")
                    except (IndexError, ValueError) as e:
                        # Catch IndexError if servers list is empty or ValueError from explicit raises
                        raise ValueError(f"Could not determine base URL from OpenAPI spec servers: {e}") from e

                    # Return the operation details
                    return {
                        "source": source_name,
                        "path": decoded_path,
                        "method": method,
                        "url": base_url + decoded_path,
                        "operation": operation,
                    }
                else:
                    logger.debug(
                        f"Operation not found at decoded path: {decoded_path}, method: {method}"
                    )
            else:
                logger.debug(f"Regex pattern did not match: {json_pointer}")

            return None
        except Exception as e:
            logger.error(f"Error in regex extraction: {e}")
            return None

    def _resolve_with_jsonpointer(
        self, json_pointer: str, source_name: str, source_desc: dict
    ) -> dict | None:
        """
        Resolve a JSON pointer using the jsonpointer library

        Args:
            json_pointer: JSON Pointer to the operation
            source_name: Name of the source
            source_desc: Source description

        Returns:
            Operation details or None if resolution fails
        """
        try:
            # Check if the pointer starts with /paths/
            if not json_pointer.startswith("/paths/"):
                logger.debug(f"Pointer does not start with /paths/: {json_pointer}")
                return None

            # Try to resolve the pointer directly
            operation = jsonpointer.resolve_pointer(source_desc, json_pointer)

            if not isinstance(operation, dict):
                logger.debug(f"Resolved pointer is not a dictionary: {operation}")
                return None

            # We need to determine the path and method
            # Extract from the pointer: /paths/~1foo~1bar/get -> path=/foo/bar, method=get
            parts = json_pointer.split("/")
            if len(parts) >= 4:  # /paths/<path>/<method>
                # The last part should be the method
                method = parts[-1]

                # Combine all middle parts as the path with proper decoding
                path_parts = [p.replace("~1", "/").replace("~0", "~") for p in parts[2:-1]]
                path = "/" + "/".join(path_parts)

                # Verify we have a valid HTTP method
                if method not in ["get", "post", "put", "delete", "patch"]:
                    logger.debug(f"Invalid HTTP method: {method}")
                    return None

                # Get the base URL
                try:
                    servers = source_desc.get("servers")
                    if not servers or not isinstance(servers, list):
                        raise ValueError("Missing or invalid 'servers' list in OpenAPI spec.")
                    base_url = servers[0].get("url")
                    if not base_url or not isinstance(base_url, str):
                        raise ValueError("Missing or invalid 'url' in the first server object.")
                except (IndexError, ValueError) as e:
                    # Catch IndexError if servers list is empty or ValueError from explicit raises
                    raise ValueError(f"Could not determine base URL from OpenAPI spec servers: {e}") from e

                # Verify this is actually a valid operation
                paths_obj = source_desc.get("paths", {})
                if path not in paths_obj or method not in paths_obj.get(path, {}):
                    logger.debug(f"Path/method combination not found: {path}/{method}")
                    # Try normalized path (without trailing slash)
                    norm_path = path.rstrip("/")
                    if norm_path in paths_obj and method in paths_obj.get(norm_path, {}):
                        path = norm_path
                    else:
                        return None

                return {
                    "source": source_name,
                    "path": path,
                    "method": method,
                    "url": base_url + path,
                    "operation": operation,
                }
            else:
                logger.debug(f"Invalid pointer format: {json_pointer}")
                return None

        except (jsonpointer.JsonPointerException, KeyError) as e:
            logger.debug(f"JSON pointer resolution failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in jsonpointer resolution: {e}")
            return None

    def _handle_special_cases(
        self, json_pointer: str, source_name: str, source_desc: dict
    ) -> dict | None:
        """
        Handle special cases for complex paths with path parameters

        Args:
            json_pointer: JSON Pointer to the operation
            source_name: Name of the source
            source_desc: Source description

        Returns:
            Operation details or None if handling fails
        """
        try:
            # Special handling for complex paths like /paths/~1{param}~1resource/get
            # where we need to find the matching path template in the OpenAPI spec

            # Check if this looks like a path with parameters
            if "~1{" in json_pointer:
                logger.debug(f"Handling special case for path with parameters: {json_pointer}")

                # Extract the method from the end of the pointer
                parts = json_pointer.split("/")
                if len(parts) < 3:
                    return None

                method = parts[-1]
                if method not in ["get", "post", "put", "delete", "patch"]:
                    return None

                # Decode the path parts
                pointer_path_parts = [p.replace("~1", "/").replace("~0", "~") for p in parts[2:-1]]
                pointer_path = "/" + "/".join(pointer_path_parts)
                logger.debug(f"Decoded path with parameters: {pointer_path}")

                # The path might have parameters in the form {param}
                # We need to find a matching path template in the OpenAPI spec
                paths_obj = source_desc.get("paths", {})

                # Convert path with parameters to a regex pattern
                # Replace {param} with a wildcard pattern that matches any segment
                path_pattern = re.escape(pointer_path).replace("\\{[^\\}]+\\}", "[^/]+")
                logger.debug(f"Path pattern: {path_pattern}")

                # Check each path in the spec for a match
                for spec_path in paths_obj.keys():
                    # Convert the spec path to a pattern by replacing {param} with wildcards
                    spec_pattern = re.escape(spec_path).replace("\\{[^\\}]+\\}", "[^/]+")

                    # Check if the templates match
                    if (
                        spec_pattern == path_pattern
                        or re.match(spec_pattern, pointer_path)
                        or re.match(path_pattern, spec_path)
                    ):
                        logger.debug(f"Found matching path template: {spec_path}")

                        # Check if the method exists
                        operation = paths_obj.get(spec_path, {}).get(method)
                        if operation:
                            # Get the base URL
                            try:
                                servers = source_desc.get("servers")
                                if not servers or not isinstance(servers, list):
                                    raise ValueError("Missing or invalid 'servers' list in OpenAPI spec.")
                                base_url = servers[0].get("url")
                                if not base_url or not isinstance(base_url, str):
                                    raise ValueError("Missing or invalid 'url' in the first server object.")
                            except (IndexError, ValueError) as e:
                                # Catch IndexError if servers list is empty or ValueError from explicit raises
                                raise ValueError(f"Could not determine base URL from OpenAPI spec servers: {e}") from e

                            return {
                                "source": source_name,
                                "path": spec_path,
                                "method": method,
                                "url": base_url + spec_path,
                                "operation": operation,
                            }

                # If path parameter matching didn't work, try direct name matching
                # This is a simpler approach that might work for common cases
                # For example, if the pointer is /paths/~1{id}~1resource/get
                # then look for a path like "/{id}/resource" in the spec

                for spec_path, path_item in paths_obj.items():
                    if method in path_item:
                        # Simple string comparison to check if they're similar
                        if "{" in spec_path and "}" in spec_path:
                            logger.debug(f"Checking path template match: {spec_path}")

                            # Compare path segments (ignoring the actual parameter names)
                            pointer_segments = pointer_path.split("/")
                            spec_segments = spec_path.split("/")

                            if len(pointer_segments) == len(spec_segments):
                                match = True
                                for i, (p_seg, s_seg) in enumerate(
                                    zip(pointer_segments, spec_segments, strict=False)
                                ):
                                    # Skip empty segments
                                    if not p_seg and not s_seg:
                                        continue

                                    # If spec has a parameter, it matches anything
                                    if "{" in s_seg and "}" in s_seg:
                                        continue

                                    # If pointer has a parameter, it matches anything
                                    if "{" in p_seg and "}" in p_seg:
                                        continue

                                    # Otherwise, segments must match exactly
                                    if p_seg != s_seg:
                                        match = False
                                        break

                                if match:
                                    logger.debug(
                                        f"Found matching path by segment analysis: {spec_path}"
                                    )

                                    # Get the operation and base URL
                                    operation = path_item.get(method)
                                    try:
                                        servers = source_desc.get("servers")
                                        if not servers or not isinstance(servers, list):
                                            raise ValueError("Missing or invalid 'servers' list in OpenAPI spec.")
                                        base_url = servers[0].get("url")
                                        if not base_url or not isinstance(base_url, str):
                                            raise ValueError("Missing or invalid 'url' in the first server object.")
                                    except (IndexError, ValueError) as e:
                                        # Catch IndexError if servers list is empty or ValueError from explicit raises
                                        raise ValueError(f"Could not determine base URL from OpenAPI spec servers: {e}") from e

                                    return {
                                        "source": source_name,
                                        "path": spec_path,
                                        "method": method,
                                        "url": base_url + spec_path,
                                        "operation": operation,
                                    }

            # The code below contains some fallback handling for pattern matching.
            # This is a last resort approach for finding operations, but it should
            # be generic and not contain API-specific special cases.
            #
            # NOTE: As per our development guidelines in CLAUDE.md:
            # "NEVER include spec-specific or data-specific handling in core implementation code"
            #
            # Instead of hardcoding specific patterns for known APIs (like XKCD),
            # we should implement generic algorithms that work for all cases.
            #
            # For the specific examples below, we're using a general approach that:
            # 1. Identifies patterns in the JSON pointer
            # 2. Looks for matching paths in the OpenAPI spec
            # 3. Returns the operation information if found

            # Common pattern: JSON pointer with simple path like /paths/~1resource/get
            simple_path_match = re.match(r"/paths/~1([^/~]+)/([a-z]+)$", json_pointer)
            if simple_path_match:
                resource, method = simple_path_match.groups()
                resource_path = f"/{resource}"
                paths_obj = source_desc.get("paths", {})
                if resource_path in paths_obj and method in paths_obj[resource_path]:
                    logger.debug(
                        f"Found operation using simple path pattern: {resource_path}/{method}"
                    )
                    try:
                        servers = source_desc.get("servers")
                        if not servers or not isinstance(servers, list):
                            raise ValueError("Missing or invalid 'servers' list in OpenAPI spec.")
                        base_url = servers[0].get("url")
                        if not base_url or not isinstance(base_url, str):
                            raise ValueError("Missing or invalid 'url' in the first server object.")
                    except (IndexError, ValueError) as e:
                        # Catch IndexError if servers list is empty or ValueError from explicit raises
                        raise ValueError(f"Could not determine base URL from OpenAPI spec servers: {e}") from e

                    return {
                        "source": source_name,
                        "path": resource_path,
                        "method": method,
                        "url": base_url + resource_path,
                        "operation": paths_obj[resource_path][method],
                    }

            # Common pattern: JSON pointer with path parameter like /paths/~1{param}~1resource/get
            param_path_match = re.match(r"/paths/~1\{([^}]+)\}~1([^/~]+)/([a-z]+)$", json_pointer)
            if param_path_match:
                param_name, resource, method = param_path_match.groups()
                param_path = f"/{{{param_name}}}/{resource}"
                paths_obj = source_desc.get("paths", {})
                if param_path in paths_obj and method in paths_obj[param_path]:
                    logger.debug(
                        f"Found operation using parameter path pattern: {param_path}/{method}"
                    )
                    try:
                        servers = source_desc.get("servers")
                        if not servers or not isinstance(servers, list):
                            raise ValueError("Missing or invalid 'servers' list in OpenAPI spec.")
                        base_url = servers[0].get("url")
                        if not base_url or not isinstance(base_url, str):
                            raise ValueError("Missing or invalid 'url' in the first server object.")
                    except (IndexError, ValueError) as e:
                        # Catch IndexError if servers list is empty or ValueError from explicit raises
                        raise ValueError(f"Could not determine base URL from OpenAPI spec servers: {e}") from e

                    return {
                        "source": source_name,
                        "path": param_path,
                        "method": method,
                        "url": base_url + param_path,
                        "operation": paths_obj[param_path][method],
                    }

            return None
        except Exception as e:
            logger.error(f"Error handling special cases: {e}")
            return None

    def extract_security_requirements(self, operation_info: dict) -> list[SecurityOption]:
        """
        Extract security requirements from operation info and source descriptions.
        Args:
            operation_info: Operation information from operation finder
        Returns:
            List of SecurityOption objects (empty list if none found)
        """
        operation = operation_info.get("operation", {})
        source_name = operation_info.get("source")
        path = operation_info.get("path")

        # 1. Check for operation-level security requirements
        if "security" in operation:
            logger.debug(f"Found operation-level security requirements for {operation.get('operationId')}")
            raw_options = operation.get("security", [])
            return self._convert_to_security_options(raw_options)

        # 2. Check for path-level security requirements (OpenAPI 3.x)
        if source_name in self.source_descriptions and path:
            paths_obj = self.source_descriptions[source_name].get("paths", {})
            path_obj = paths_obj.get(path, {})
            if isinstance(path_obj, dict) and "security" in path_obj:
                logger.debug(f"Found path-level security requirements for path {path} in API {source_name}")
                raw_options = path_obj.get("security", [])
                return self._convert_to_security_options(raw_options)

        # 3. Check for global security requirements in the source description
        if source_name in self.source_descriptions:
            source_desc = self.source_descriptions.get(source_name, {})
            if "security" in source_desc:
                logger.debug(f"Found global security requirements for API {source_name}")
                raw_options = source_desc.get("security", [])
                return self._convert_to_security_options(raw_options)

        # 4. No security requirements found
        logger.debug("No security requirements found")
        return []

    def _convert_to_security_options(self, raw_options: list) -> list[SecurityOption]:
        """
        Convert raw security options from OpenAPI spec to SecurityOption model instances
        Args:
            raw_options: List of raw security option objects from OpenAPI spec
        Returns:
            List of SecurityOption objects
        """
        security_options = []
        for raw_option in raw_options:
            option = SecurityOption()
            for scheme_name, scopes in raw_option.items():
                requirement = SecurityRequirement(
                    scheme_name=scheme_name,
                    scopes=scopes
                )
                option.requirements.append(requirement)
            security_options.append(option)
        return security_options

    def get_operations_for_workflow(self, workflow: dict) -> list[dict]:
        """
        Find all operation references in a workflow dict (Arazzo format).
        Returns a list of operation_info dicts as returned by find_by_id/find_by_path.
        """
        operations = []
        steps = workflow.get("steps", [])
        for step in steps:
            if "operationId" in step:
                op_info = self.find_by_id(step["operationId"])
                if op_info:
                    operations.append(op_info)
            elif "operationPath" in step:
                # operationPath format: <source>#<json_pointer>
                match = re.match(r"([^#]+)#(.+)", step["operationPath"])
                if match:
                    source_url, json_pointer = match.groups()
                    op_info = self.find_by_path(source_url, json_pointer)
                    if op_info:
                        operations.append(op_info)
        return operations
