#!/usr/bin/env python3
"""
OpenAPI Parameter and Response Extractor for OAK Runner

This module provides functionality to extract input parameters and output schemas
from an OpenAPI specification for a given API operation.
"""

import logging
from typing import Any, Dict, Optional, List, Union

import jsonpointer
import copy
import re

from oak_runner.executor.operation_finder import OperationFinder
from oak_runner.auth.models import SecurityOption
from ..models import ServerConfiguration, ServerVariable

# Configure logging (using the same logger as operation_finder for consistency)
logger = logging.getLogger("oak_runner.extractor")


def _format_security_options_to_dict_list(
    security_options_list: List[SecurityOption],
    operation_info: Dict[str, Any] # For logging context
) -> List[Dict[str, List[str]]]:
    """
    Converts a list of SecurityOption objects into a list of dictionaries
    representing OpenAPI security requirements.

    Args:
        security_options_list: The list of SecurityOption objects.
        operation_info: The operation details dictionary for logging context.

    Returns:
        A list of dictionaries, where each dictionary represents an OR security option,
        and its key-value pairs represent ANDed security schemes.
    """
    formatted_requirements = []
    if not security_options_list:
        return formatted_requirements

    for sec_opt in security_options_list:
        current_option_dict = {}
        if sec_opt.requirements:  # Check if the list is not None and not empty
            for sec_req in sec_opt.requirements:
                try:
                    current_option_dict[sec_req.scheme_name] = sec_req.scopes
                except AttributeError as e:
                    op_path = operation_info.get('path', 'unknown_path')
                    op_method = operation_info.get('http_method', 'unknown_method').upper()
                    logger.warning(
                        f"Missing attributes on SecurityRequirement object for operation {op_method} {op_path}. Error: {e}"
                    )
        
        # Handle OpenAPI's concept of an empty security requirement object {},
        # (optional authentication), represented by an empty list of requirements.
        if sec_opt.requirements == []: # Explicitly check for an empty list
            formatted_requirements.append({})
        elif current_option_dict: # Add if populated from non-empty requirements
            formatted_requirements.append(current_option_dict)

    return formatted_requirements


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
    input_max_depth: Optional[int] = None,
    output_max_depth: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Finds the specified operation within the spec and extracts input parameters
    structured as an OpenAPI object schema and the full schema for the success
    (200 or 201) response.

    Args:
        spec: The full OpenAPI specification dictionary.
        http_path: The HTTP path of the target operation (e.g., '/users/{id}').
        http_method: The HTTP method of the target operation (e.g., 'get', 'post').
        input_max_depth: If set, limits the depth of the input structure.
        output_max_depth: If set, limits the depth of the output structure.

    Returns:
        A dictionary containing 'inputs', 'outputs', and 'security_requirements'. 
        Returns the full, unsimplified dict structure if both max depth arguments are None.
        'inputs' is structured like an OpenAPI schema object:
            {'type': 'object', 'properties': {param_name: {param_schema_or_simple_type}, ...}}
            Non-body params map to {'type': openapi_type_string}.
            The JSON request body schema is included under the 'body' key if present.
        'outputs' contains the full resolved schema for the 200 JSON response.
        'security_requirements' contains the security requirements for the operation.

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
            },
            "security_requirements": [
                # List of SecurityOption objects
            ]
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
        # Return early if operation not found
        return {"inputs": {}, "outputs": {}, "security_requirements": []}

    # Initialize with new structure for inputs
    extracted_details: Dict[str, Any] = {
        "inputs": {"type": "object", "properties": {}, "required": []},
        "outputs": {},
        "security_requirements": []
    }
    operation = operation_info.get("operation")
    if not operation or not isinstance(operation, dict):
        logger.warning("Operation object missing or invalid in operation_info.")
        return extracted_details

    # Extract security requirements using OperationFinder
    security_options_list: List[SecurityOption] = finder.extract_security_requirements(operation_info)
    
    extracted_details["security_requirements"] = _format_security_options_to_dict_list(
        security_options_list, operation_info
    )

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

    # --- Ensure all URL path parameters are present and required ---
    # Find all {param} in the http_path
    url_param_names = re.findall(r'{([^}/]+)}', http_path)
    for url_param in url_param_names:
        param_key = (url_param, 'path')
        if param_key not in seen_params:
            all_parameters.append({
                'name': url_param,
                'in': 'path',
                'required': True,
                'schema': {'type': 'string'}
            })
            seen_params.add(param_key)
    # --- End ensure URL params ---

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

            # Add to properties as { 'type': 'openapi_type_string' }
            # Required status will be tracked in the top-level 'required' list
            is_required = param.get('required', False) # Default to false if not present
            extracted_details["inputs"]["properties"][param_name] = {
                "type": openapi_type
                # Removed "required": is_required from here
            }
            if is_required:
                # Add to top-level required list if not already present
                if param_name not in extracted_details["inputs"]["required"]:
                    extracted_details["inputs"]["required"].append(param_name)

    # Process Request Body for inputs
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

                # --- Flatten body properties into inputs --- 
                if isinstance(fully_resolved_body_schema, dict) and fully_resolved_body_schema.get("type") == "object":
                    body_properties = fully_resolved_body_schema.get("properties", {})
                    for prop_name, prop_schema in body_properties.items():
                        if prop_name in extracted_details["inputs"]["properties"]:
                            # Handle potential name collisions (e.g., param 'id' and body field 'id')
                            # Current approach: Body property overwrites if name collides. Log warning.
                            logger.warning(f"Body property '{prop_name}' overwrites existing parameter with the same name.")
                        extracted_details["inputs"]["properties"][prop_name] = prop_schema

                    # Add required body properties to the main 'required' list
                    body_required = fully_resolved_body_schema.get('required', [])
                    for req_prop_name in body_required:
                        if req_prop_name not in extracted_details["inputs"]["required"]:
                            extracted_details["inputs"]["required"].append(req_prop_name)
                else:
                    # If body is not an object (e.g., array, primitive) or has no properties, don't flatten.
                    # Log a warning as we are not adding it under 'body' key either per the requirement.
                    logger.warning(f"Request body for {http_method.upper()} {http_path} is not an object with properties. Skipping flattening.")
                # --- End flatten --- 

                # Removed code that added the schema under 'body'
                # Removed code that checked 'required' on the nested 'body' object

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

    # --- Limit output depth (conditionally) ---
    if input_max_depth is not None:
        if isinstance(extracted_details.get("inputs"), (dict, list)):
            extracted_details["inputs"] = _limit_dict_depth(extracted_details["inputs"], input_max_depth)
    if output_max_depth is not None:
        if isinstance(extracted_details.get("outputs"), (dict, list)):
            extracted_details["outputs"] = _limit_dict_depth(extracted_details["outputs"], output_max_depth)

    # If both max depths are None, return the full, unsimplified details
    return extracted_details


def _limit_dict_depth(data: Union[Dict, List, Any], max_depth: int, current_depth: int = 0) -> Union[Dict, List, Any]:
    """Recursively limits the depth of a dictionary or list structure."""
    
    if isinstance(data, dict):
        if current_depth >= max_depth:
            return data.get('type', 'object') # Limit hit for dict
        else:
            # Recurse into dict
            limited_dict = {}
            for key, value in data.items():
                limited_dict[key] = _limit_dict_depth(value, max_depth, current_depth + 1)
            return limited_dict
    elif isinstance(data, list):
        if current_depth >= max_depth:
            return 'array' # Limit hit for list
        else:
            # Recurse into list
            limited_list = []
            for item in data:
                limited_list.append(_limit_dict_depth(item, max_depth, current_depth + 1))
            return limited_list
    else:
        # It's a primitive, return the value itself regardless of depth
        return data
