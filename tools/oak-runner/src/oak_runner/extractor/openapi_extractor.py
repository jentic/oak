#!/usr/bin/env python3
"""
OpenAPI Parameter and Response Extractor for OAK Runner

This module provides functionality to extract input parameters and output schemas
from an OpenAPI specification for a given API operation.
"""

import logging
from typing import Any, Dict

import jsonpointer
import copy

from oak_runner.models import OpenAPIDoc
from oak_runner.executor.operation_finder import OperationFinder

# Configure logging (using the same logger as operation_finder for consistency)
logger = logging.getLogger("oak_runner.extractor")


def _resolve_ref(spec: Dict[str, Any], ref: str) -> Dict[str, Any]:
    """
    Resolves a JSON pointer $ref, returning the referenced dictionary.
    """
    logger.debug(f"Attempting to resolve ref: {ref}")
    try:
        # Ensure the ref starts with '#/' as expected for internal refs
        if not ref.startswith('#/'):
            # Currently only supporting internal references
            raise ValueError(f"Invalid or unsupported $ref format: {ref}. Only internal refs starting with '#/' are supported.")
        try:
            # Remove the leading '#' before resolving
            resolved_data = jsonpointer.resolve_pointer(spec, ref[1:])
            # If the resolved part itself contains a $ref, resolve it recursively
            if isinstance(resolved_data, dict) and '$ref' in resolved_data:
                # Prevent infinite loops for recursive refs (simple check)
                if resolved_data['$ref'] == ref:
                    logger.warning(f"Detected self-referencing $ref, stopping recursion: {ref}")
                    return resolved_data  # Return as is, let caller handle
                return _resolve_ref(spec, resolved_data['$ref'])
            if not isinstance(resolved_data, dict):
                logger.warning(f"Resolved $ref '{ref}' is not a dictionary, returning empty dict.")
                return {}
            # Return a deep copy to prevent modification of the original spec component
            logger.debug(f"Resolved ref '{ref}' to: {resolved_data}")
            return copy.deepcopy(resolved_data)
        except jsonpointer.JsonPointerException as e:
            logger.error(f"Could not resolve reference '{ref}': {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during $ref resolution for {ref}: {e}")
            raise
    except ValueError as e:
        logger.error(f"Invalid or unsupported $ref format: {e}")
        raise


# --- New Recursive Resolver ---
def _resolve_schema_refs(schema_part: Any, full_spec: Dict[str, Any]) -> Any:
    """Recursively resolves all $ref pointers within a schema fragment."""
    logger.debug(f"Entering _resolve_schema_refs with part type: {type(schema_part)}")  # Avoid logging potentially large schemas
    # Make a deep copy first to avoid modifying original spec or intermediate dicts/lists
    current_part = copy.deepcopy(schema_part)

    if isinstance(current_part, dict):
        if '$ref' in current_part:  # Check original ref before potential modification
            try:
                ref_path = current_part['$ref']
                # Resolve the ref from the ORIGINAL full_spec
                resolved_content = _resolve_ref(full_spec, ref_path)
                # Recursively resolve within the newly resolved content
                # The deepcopy ensures this result is independent
                result = _resolve_schema_refs(resolved_content, full_spec)
                logger.debug(f"Exiting _resolve_schema_refs (from $ref path), returning type: {type(result)}")
                return result
            except (jsonpointer.JsonPointerException, ValueError, KeyError) as e:
                logger.warning(f"Could not resolve nested $ref '{ref_path}': {e}")
                logger.debug(f"Exiting _resolve_schema_refs (from $ref error), returning original ref dict type: {type(current_part)}")
                return current_part  # Return the copied dict with the unresolved $ref on error
        else:
            # Process dictionary items recursively on the copied dict
            for k, v in current_part.items():
                # Modify the copy in place
                current_part[k] = _resolve_schema_refs(v, full_spec)
            logger.debug(f"Exiting _resolve_schema_refs (from dict walk), returning type: {type(current_part)}")
            return current_part  # Return the modified copy
    elif isinstance(current_part, list):
        # Process list items recursively on the copied list
        for i, item in enumerate(current_part):
            # Modify the copy in place
            current_part[i] = _resolve_schema_refs(item, full_spec)
        logger.debug(f"Exiting _resolve_schema_refs (from list walk), returning type: {type(current_part)}")
        return current_part  # Return the modified copy
    else:
        # Return the copy of non-dict/list items
        logger.debug(f"Exiting _resolve_schema_refs (from base case), returning type: {type(current_part)}")
        return current_part


def extract_operation_io(
    spec: Dict[str, Any],
    http_path: str,
    http_method: str,
    simplify: bool = False
) -> Dict[str, Dict[str, Any]]:
    """
    Finds the specified operation within the spec and extracts input parameters
    structured as an OpenAPI object schema and the full schema for the success
    (200 or 201) response.

    Args:
        spec: The full OpenAPI specification dictionary.
        http_path: The HTTP path of the target operation (e.g., '/users/{id}').
        http_method: The HTTP method of the target operation (e.g., 'get', 'post').
        simplify: If True, simplify the extracted schemas for LLM consumption.

    Returns:
        A dictionary containing 'inputs' and 'outputs'.
        Returns empty dicts if operation not found or on error.
        'inputs' is structured like an OpenAPI schema object:
            {'type': 'object', 'properties': {param_name: {param_schema_or_simple_type}, ...}}
            Non-body params map to {'type': openapi_type_string}.
            The JSON request body schema is included under the 'body' key if present.
        'outputs' contains the full resolved schema for the 200 JSON response.

        Example:
        {
            "inputs": {
                "type": "object",
                "properties": {
                    "userId": {"type": "integer"},   # Non-body param
                    "limit": {"type": "integer"},
                    "body": {                     # Full resolved schema for JSON request body
                        "type": "object",
                        "properties": {
                            "items": {"type": "array", "items": {"type": "string"}},
                            "customer_notes": {"type": "string"}
                        },
                        "required": ["items"]
                    }
                }
            },
            "outputs": { # Full resolved schema for 200 JSON response
                 "type": "object",
                 "properties": {
                      "id": {"type": "string", "format": "uuid"},
                      "status": {"type": "string", "enum": ["pending", "shipped"]}
                 }
            }
        }
    """
    # Find the operation first using OperationFinder
    # Wrap the spec for OperationFinder
    source_name = spec.get("info", {}).get("title", "default_spec")
    source_descriptions = {source_name: spec}
    finder = OperationFinder(source_descriptions)
    operation_info = finder.find_by_http_path_and_method(http_path, http_method.lower())

    if not operation_info:
        logger.warning(f"Operation {http_method.upper()} {http_path} not found in the spec.")
        return {"inputs": {}, "outputs": {}}

    # Initialize with new structure for inputs
    extracted_details: Dict[str, Dict[str, Any]] = {
        "inputs": {"type": "object", "properties": {}},
        "outputs": {}
    }
    operation = operation_info.get("operation")
    if not operation or not isinstance(operation, dict):
        logger.warning("Operation object missing or invalid in operation_info.")
        return extracted_details

    all_parameters = []
    seen_params = set()

    # Check for path-level parameters first
    path_item_ref = f"#/paths/{operation_info.get('path', '').lstrip('/')}"
    try:
        escaped_path = operation_info.get('path', '').lstrip('/').replace('~', '~0').replace('/', '~1')
        path_item_ref = f"#/paths/{escaped_path}"
        path_item = jsonpointer.resolve_pointer(spec, path_item_ref[1:])
        if path_item and isinstance(path_item, dict) and 'parameters' in path_item:
            for param in path_item['parameters']:
                try:
                    resolved_param = param
                    if '$ref' in param:
                        resolved_param = _resolve_ref(spec, param['$ref'])
                    param_key = (resolved_param.get('name'), resolved_param.get('in'))
                    if param_key not in seen_params:
                        all_parameters.append(resolved_param)
                        seen_params.add(param_key)
                except (jsonpointer.JsonPointerException, ValueError, KeyError) as e:
                    logger.warning(f"Skipping path-level parameter due to resolution/format error: {e}")
    except jsonpointer.JsonPointerException:
        logger.debug(f"Could not find or resolve path item: {path_item_ref}")

    # Add/override with operation-level parameters
    if 'parameters' in operation:
        for param in operation['parameters']:
            try:
                resolved_param = param
                if '$ref' in param:
                    resolved_param = _resolve_ref(spec, param['$ref'])
                param_key = (resolved_param.get('name'), resolved_param.get('in'))
                existing_index = next((i for i, p in enumerate(all_parameters) if (p.get('name'), p.get('in')) == param_key), None)
                if existing_index is not None:
                    all_parameters[existing_index] = resolved_param
                elif param_key not in seen_params:
                    all_parameters.append(resolved_param)
                    seen_params.add(param_key)
            except (jsonpointer.JsonPointerException, ValueError, KeyError) as e:
                logger.warning(f"Skipping operation-level parameter due to resolution/format error: {e}")

    # Process collected parameters into simplified inputs
    for param in all_parameters:
        param_name = param.get('name')
        param_in = param.get('in')
        param_schema = param.get('schema')
        if param_name and param_in != 'body':  # Body handled separately
            if not param_schema:
                logger.warning(f"Parameter '{param_name}' in '{param_in}' is missing schema, mapping type to 'any'")
                param_type = 'any'
            else:
                # Resolve schema ref if present
                if isinstance(param_schema, dict) and '$ref' in param_schema:
                    try:
                        param_schema = _resolve_ref(spec, param_schema['$ref'])
                    except (jsonpointer.JsonPointerException, ValueError) as ref_e:
                        logger.warning(f"Could not resolve schema $ref for parameter '{param_name}': {ref_e}")
                        param_schema = {}  # Fallback to empty schema
            openapi_type = 'string'  # Default OpenAPI type
            if isinstance(param_schema, dict):
                oapi_type_from_schema = param_schema.get('type')
                # Map to basic OpenAPI types
                if oapi_type_from_schema in ['string', 'integer', 'number', 'boolean', 'array', 'object']:
                    openapi_type = oapi_type_from_schema
                # TODO: More nuanced mapping (e.g., number format to float/double?)?

            # Add to properties as { 'type': 'openapi_type_string', 'required': boolean }
            is_required = param.get('required', False) # Default to false if not present
            extracted_details["inputs"]["properties"][param_name] = {
                "type": openapi_type,
                "required": is_required
            }

    # Process Request Body for inputs['body']
    if 'requestBody' in operation:
        try:
            request_body = operation['requestBody']
            if '$ref' in request_body:
                request_body = _resolve_ref(spec, request_body['$ref'])

            # Check for application/json content
            json_content = request_body.get('content', {}).get('application/json', {})
            body_schema = json_content.get('schema')

            if body_schema:
                if '$ref' in body_schema:
                    body_schema = _resolve_ref(spec, body_schema['$ref'])

                # Recursively resolve nested refs within the body schema
                fully_resolved_body_schema = _resolve_schema_refs(body_schema, spec)
                # Add the fully resolved body schema under the 'body' key in properties
                extracted_details["inputs"]["properties"]['body'] = fully_resolved_body_schema

                # Ensure 'required' key exists for object schemas
                body_schema_dict = extracted_details["inputs"]["properties"].get('body')
                if isinstance(body_schema_dict, dict) and body_schema_dict.get("type") == "object" and "required" not in body_schema_dict:
                    body_schema_dict["required"] = []

        except (jsonpointer.JsonPointerException, ValueError, KeyError) as e:
            logger.warning(f"Skipping request body processing due to error: {e}")

    # Process 200 or 201 Response for outputs
    if 'responses' in operation:
        responses = operation.get('responses', {})
        # Prioritize 200, fallback to 201 for success output schema
        success_response = responses.get('200') or responses.get('201')
        if success_response:
            try:
                resolved_response = success_response
                if isinstance(success_response, dict) and '$ref' in success_response:
                    resolved_response = _resolve_ref(spec, success_response['$ref'])

                # Check for application/json content in the resolved successful response
                json_content = resolved_response.get('content', {}).get('application/json', {})
                response_schema = json_content.get('schema')

                if response_schema:
                    if '$ref' in response_schema:
                        response_schema = _resolve_ref(spec, response_schema['$ref'])

                    # Recursively resolve nested refs within the response schema
                    logger.debug(f"Output schema BEFORE recursive resolve: {response_schema}")
                    fully_resolved_output_schema = _resolve_schema_refs(response_schema, spec)
                    logger.debug(f"Output schema AFTER recursive resolve: {fully_resolved_output_schema}")
                    extracted_details["outputs"] = fully_resolved_output_schema

            except (jsonpointer.JsonPointerException, ValueError, KeyError) as e:
                logger.warning(f"Skipping success response processing due to error: {e}")
        else:
            logger.debug("No '200' or '201' response found for this operation.")

    # --- Simplify final schemas (conditionally) ---
    if simplify:
        if isinstance(extracted_details.get("inputs"), dict):
            extracted_details["inputs"] = _simplify_schema(extracted_details["inputs"])
        if isinstance(extracted_details.get("outputs"), dict):
            extracted_details["outputs"] = _simplify_schema(extracted_details["outputs"])
            # Post-process Simplified Outputs: remove top-level 'required' if present (USER preference)
            if "required" in extracted_details["outputs"]:
                del extracted_details["outputs"]["required"]

    return extracted_details


# Helper function to check if a schema part might need resolving

def _simplify_schema(schema: Any) -> Any:
    """Recursively simplify a schema fragment for LLM consumption."""
    if isinstance(schema, list):
        return [_simplify_schema(item) for item in schema]

    if not isinstance(schema, dict):
        return schema

    simplified = {}
    for key, value in schema.items():
        if key in {'description', 'title', 'pattern', 'example', 'examples',
                   'maxLength', 'minLength', 'maximum', 'minimum',
                   'maxItems', 'minItems', 'uniqueItems',
                   'maxProperties', 'minProperties',
                   'contentEncoding', 'contentMediaType',
                   'deprecated', 'externalDocs', 'xml', 'format'}:
            continue

        if key == 'oneOf':
            # Check for nullable pattern: [{type: null}, {schema}] or [{schema}, {type: null}]
            if len(value) == 2 and any(item == {'type': 'null'} for item in value):
                other_schema = value[0] if value[1] == {'type': 'null'} else value[1]
                simplified_other = _simplify_schema(other_schema)
                if isinstance(simplified_other, dict):
                    simplified_other['nullable'] = True # Add nullable marker
                    # Merge the simplified nullable schema into the current level
                    # Avoids creating a nested structure just for nullability
                    for k, v in simplified_other.items():
                        simplified[k] = v
                    continue # Skip adding the 'oneOf' key itself
                else:
                    # Handle case where the non-null part is simple (e.g. just string)
                    # This case might not happen often with real schemas but good to consider
                    simplified[key] = value # Keep original if simplification failed

            # Check for enum pattern: [{const: v1}, {const: v2}, ...]
            elif all(isinstance(item, dict) and 'const' in item for item in value):
                enum_values = [item['const'] for item in value]
                simplified['enum'] = enum_values
                # If type is not already present, try to infer from first const
                if 'type' not in simplified and enum_values:
                    const_type = type(enum_values[0])
                    if const_type is str:
                        simplified['type'] = 'string'
                    elif const_type is int:
                        simplified['type'] = 'integer'
                    elif const_type is float:
                        simplified['type'] = 'number'
                    elif const_type is bool:
                        simplified['type'] = 'boolean'
                continue # Skip adding the 'oneOf' key itself
            else:
                # Simplify items within oneOf recursively
                simplified[key] = [_simplify_schema(item) for item in value]
        elif key == 'allOf':
             # Simplification: Take the first schema in allOf, ignore others
             # This is a basic strategy and might lose information
             if value and isinstance(value, list):
                 first_schema = _simplify_schema(value[0])
                 if isinstance(first_schema, dict):
                      for k, v in first_schema.items():
                          simplified[k] = v
                 else:
                     simplified[key] = [_simplify_schema(v) for v in value] # fallback: simplify all
             continue # Skip adding 'allOf' key
        elif key == 'anyOf':
            simplified[key] = [_simplify_schema(item) for item in value]
        elif key == 'properties':
            simplified[key] = {prop_name: _simplify_schema(prop_schema)
                               for prop_name, prop_schema in value.items()}
        elif key == 'items':
            simplified[key] = _simplify_schema(value)
        elif key == 'additionalProperties':
            # Can be boolean or schema, simplify if schema
            simplified[key] = _simplify_schema(value)
        else:
            # Keep other keys like 'type', 'required', 'enum' (if not from oneOf)
            simplified[key] = value # Keep value as is (no deeper simplification needed)

    return simplified
