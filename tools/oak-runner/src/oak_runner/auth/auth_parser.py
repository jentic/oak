#!/usr/bin/env python3
"""
Authentication Parser for OAK Runner.

This module extracts authentication requirements from OpenAPI specifications
and Arazzo workflows.
"""

import logging
from enum import Enum
from typing import Any

import yaml

from .models import (
    ApiKeyScheme,
    AuthLocation,
    AuthType,
    SecurityScheme,
    CustomScheme,
    HttpAuthScheme,
    HttpSchemeType,
    OAuth2Scheme,
    OAuth2FlowType,
    OAuth2Urls,
    OpenIDScheme,
    SecurityRequirement,
    SecurityOption,
    auth_requirement_to_schema,
)

# Configure logging
logger = logging.getLogger("arazzo-runner.auth")


class AuthRequirement:
    """Represents an authentication requirement extracted from API specifications."""

    def __init__(
        self,
        auth_type: AuthType,
        name: str,
        location: AuthLocation | None = None,
        description: str | None = None,
        required: bool = True,
        schemes: list[str] | None = None,
        scopes: list[str] | None = None,
        flow_type: str | None = None,
        auth_urls: dict[str, str] | None = None,
        security_scheme_name: str | None = None,
        api_title: str | None = None,
        source_description_id: str | None = None,
    ):
        """
        Initialize an authentication requirement.

        Args:
            auth_type: Type of authentication (API_KEY, HTTP, OAUTH2, etc.)
            name: Name of the authentication parameter or scheme
            location: Where the auth parameter should be provided
            description: Human-readable description of the auth requirement
            required: Whether this auth is required or optional
            schemes: For HTTP auth, the specific schemes (bearer, basic, etc.)
            scopes: For OAuth2, the required scopes
            flow_type: For OAuth2, the flow type (implicit, authorizationCode, etc.)
            auth_urls: For OAuth2, the authorization and token URLs
            security_scheme_name: Original name of the security scheme in the OpenAPI spec
            api_title: Title of the API source description
            source_description_id: Identifier for the source of this auth requirement (e.g., API name or file path)
        """
        self.auth_type = auth_type
        self.name = name
        self.location = location
        self.description = description
        self.required = required
        self.schemes = schemes or []
        self.scopes = scopes or []
        self.flow_type = flow_type
        self.auth_urls = auth_urls or {}
        self.security_scheme_name = security_scheme_name or name
        self.api_title = api_title
        self.source_description_id = source_description_id

    def __str__(self) -> str:
        """Return a string representation of the auth requirement."""
        base = f"{self.auth_type.value}:{self.name}"
        if self.location:
            base += f" (in {self.location.value})"
        if self.schemes:
            base += f" schemes={self.schemes}"
        if self.scopes:
            base += f" scopes={self.scopes}"
        return base

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "type": self.auth_type.value,
            "name": self.name,
            "security_scheme_name": self.security_scheme_name,
            "required": self.required,
        }

        if self.location:
            result["location"] = self.location.value

        if self.description:
            result["description"] = self.description

        if self.schemes:
            result["schemes"] = self.schemes

        if self.scopes:
            result["scopes"] = self.scopes

        if self.flow_type:
            result["flow_type"] = self.flow_type

        if self.auth_urls:
            result["auth_urls"] = self.auth_urls

        if self.api_title:
            result["api_title"] = self.api_title

        if self.source_description_id:
            result["source_description_id"] = self.source_description_id

        return result
        
    def to_pydantic_schema(self) -> SecurityScheme:
        """Convert to a Pydantic schema object."""
        return auth_requirement_to_schema(self)


def extract_auth_from_openapi(openapi_spec: dict[str, Any]) -> list[AuthRequirement]:
    """
    Extract authentication requirements from an OpenAPI specification.

    Args:
        openapi_spec: Parsed OpenAPI specification

    Returns:
        List of authentication requirements
    """
    auth_requirements = []

    # Extract API title from the OpenAPI spec
    api_title = openapi_spec.get("info", {}).get("title", "")

    # Check for security schemes in components
    security_schemes = openapi_spec.get("components", {}).get("securitySchemes", {})

    # Process each security scheme
    for scheme_name, scheme_data in security_schemes.items():
        auth_type_str = scheme_data.get("type", "")

        try:
            auth_type = AuthType(auth_type_str)
        except ValueError:
            logger.warning(f"Unknown security scheme type: {auth_type_str}, using CUSTOM")
            auth_type = AuthType.CUSTOM

        description = scheme_data.get("description", "")

        if auth_type == AuthType.API_KEY:
            # API Key auth
            location_str = scheme_data.get("in", "")
            try:
                location = AuthLocation(location_str)
            except ValueError:
                logger.warning(f"Unknown API key location: {location_str}, defaulting to HEADER")
                location = AuthLocation.HEADER

            param_name = scheme_data.get("name", scheme_name)

            auth_requirements.append(
                AuthRequirement(
                    auth_type=auth_type, 
                    name=param_name, 
                    location=location, 
                    description=description,
                    security_scheme_name=scheme_name,
                    api_title=api_title,
                )
            )

        elif auth_type == AuthType.HTTP:
            # HTTP authentication (Basic, Bearer, etc.)
            scheme = scheme_data.get("scheme", "").lower()

            auth_requirements.append(
                AuthRequirement(
                    auth_type=auth_type,
                    name=scheme_name,
                    description=description,
                    schemes=[scheme],
                    location=AuthLocation.HEADER,  # HTTP auth is always in header
                    security_scheme_name=scheme_name,
                    api_title=api_title,
                )
            )

        elif auth_type == AuthType.OAUTH2:
            # OAuth2 authentication
            flows = scheme_data.get("flows", {})

            for flow_type, flow_data in flows.items():
                scopes = list(flow_data.get("scopes", {}).keys())

                auth_urls = {}
                if "authorizationUrl" in flow_data:
                    auth_urls["authorization"] = flow_data["authorizationUrl"]
                if "tokenUrl" in flow_data:
                    auth_urls["token"] = flow_data["tokenUrl"]
                if "refreshUrl" in flow_data:
                    auth_urls["refresh"] = flow_data["refreshUrl"]

                auth_requirements.append(
                    AuthRequirement(
                        auth_type=auth_type,
                        name=scheme_name,
                        description=description,
                        scopes=scopes,
                        flow_type=flow_type,
                        auth_urls=auth_urls,
                        security_scheme_name=scheme_name,
                        api_title=api_title,
                    )
                )

        elif auth_type == AuthType.OPENID:
            # OpenID Connect authentication
            openid_url = scheme_data.get("openIdConnectUrl", "")
            
            auth_requirements.append(
                AuthRequirement(
                    auth_type=auth_type,
                    name=scheme_name,
                    description=description,
                    auth_urls={"openIdConnectUrl": openid_url},
                    security_scheme_name=scheme_name,
                    api_title=api_title,
                )
            )
            
        else:
            # Custom or unknown authentication type
            auth_requirements.append(
                AuthRequirement(
                    auth_type=AuthType.CUSTOM,
                    name=scheme_name,
                    description=description,
                    security_scheme_name=scheme_name,
                    api_title=api_title,
                )
            )

    # Check for global security requirements
    global_security = openapi_spec.get("security", [])
    if global_security:
        logger.debug(f"Found global security requirements: {global_security}")

    return auth_requirements


def extract_auth_from_arazzo(arazzo_spec: dict[str, Any]) -> list[AuthRequirement]:
    """
    Extract authentication requirements from an Arazzo workflow specification.

    Args:
        arazzo_spec: Parsed Arazzo specification

    Returns:
        List of authentication requirements
    """
    auth_requirements = []
    auth_params: set[tuple[str, str, str]] = set()  # (name, location, description)

    # Check steps for auth parameters
    steps = arazzo_spec.get("steps", [])
    for step in steps:
        # Check for API operation parameters
        operation = step.get("operation", {})
        if operation:
            # Extract parameters from operation
            params = operation.get("parameters", [])
            _extract_auth_params_from_list(params, auth_params)
    
    # Check for steps in workflows
    workflows = arazzo_spec.get("workflows", [])
    for workflow in workflows:
        workflow_steps = workflow.get("steps", [])
        for step in workflow_steps:
            # Extract parameters from step
            params = step.get("parameters", [])
            _extract_auth_params_from_list(params, auth_params)

    # Convert auth params to requirements
    for param_name, param_location, description in auth_params:
        auth_type = _determine_auth_type(param_name, param_location)
        location = None
        try:
            location = AuthLocation(param_location)
        except ValueError:
            logger.warning(f"Unknown parameter location: {param_location}")

        auth_requirements.append(
            AuthRequirement(
                auth_type=auth_type,
                name=param_name,
                location=location,
                description=description,
                api_title='Arazzo',
                source_description_id='Arazzo'
            )
        )

    return auth_requirements


def _extract_auth_params_from_list(
    params_list: list[dict[str, Any]], auth_params: set[tuple[str, str, str]]
):
    """
    Extract authentication parameters from a list of parameter objects.

    Args:
        params_list: List of parameter objects
        auth_params: Set to collect authentication parameters
    """
    for param in params_list:
        param_name = param.get("name", "")
        param_location = param.get("in", "")
        description = param.get("description", "")

        # Skip non-auth parameters
        if not param_name or not param_location:
            continue

        # Check if this looks like an auth parameter
        lower_name = param_name.lower()
        if (
            "api" in lower_name
            and "key" in lower_name
            or "token" in lower_name
            or "auth" in lower_name
            or "access" in lower_name
            or "secret" in lower_name
            or "credential" in lower_name
        ):
            auth_params.add((param_name, param_location, description))


def _determine_auth_type(param_name: str, param_location: str) -> AuthType:
    """
    Determine the authentication type based on parameter name and location.

    Args:
        param_name: Name of the parameter
        param_location: Location of the parameter

    Returns:
        Determined authentication type
    """
    lower_name = param_name.lower()

    if "api" in lower_name and "key" in lower_name:
        return AuthType.API_KEY

    if "bearer" in lower_name or "token" in lower_name:
        return AuthType.HTTP

    if "basic" in lower_name or ("user" in lower_name and "pass" in lower_name):
        return AuthType.HTTP

    if "oauth" in lower_name:
        return AuthType.OAUTH2

    if "openid" in lower_name:
        return AuthType.OPENID

    # Default to API Key for header/query auth parameters
    if param_location in ["header", "query"]:
        return AuthType.API_KEY

    return AuthType.CUSTOM


def auth_requirements_to_dict(auth_requirements: list[AuthRequirement]) -> list[dict[str, Any]]:
    """
    Convert auth requirements to a list of dictionaries.

    Args:
        auth_requirements: List of authentication requirements

    Returns:
        List of dictionaries
    """
    result = []
    for req in auth_requirements:
        result.append(req.to_dict())
    return result


def auth_requirements_to_pydantic(auth_requirements: list[AuthRequirement]) -> list[SecurityScheme]:
    """
    Convert authentication requirements to Pydantic schema objects.

    Args:
        auth_requirements: List of authentication requirements

    Returns:
        List of Pydantic schema objects
    """
    return [req.to_pydantic_schema() for req in auth_requirements]


def format_auth_requirements_markdown(auth_requirements: list[AuthRequirement]) -> str:
    """
    Format authentication requirements as Markdown.

    Args:
        auth_requirements: List of authentication requirements

    Returns:
        Markdown formatted string
    """
    if not auth_requirements:
        return "No authentication requirements found."

    lines = ["# Authentication Requirements", ""]

    # Group by auth type
    by_type = {}
    for req in auth_requirements:
        auth_type = req.auth_type.value
        if auth_type not in by_type:
            by_type[auth_type] = []
        by_type[auth_type].append(req)

    # Format each auth type
    for auth_type, reqs in by_type.items():
        lines.append(f"## {auth_type.title()} Authentication")
        lines.append("")

        for req in reqs:
            lines.append(f"### {req.name}")
            if req.description:
                lines.append(f"*{req.description}*")
            lines.append("")

            details = []
            if req.location:
                details.append(f"- **Location**: {req.location.value}")
            if req.required:
                details.append("- **Required**: Yes")
            else:
                details.append("- **Required**: No")

            if req.auth_type == AuthType.HTTP and req.schemes:
                details.append(f"- **Scheme**: {', '.join(req.schemes)}")

            if req.auth_type == AuthType.OAUTH2:
                if req.flow_type:
                    details.append(f"- **Flow**: {req.flow_type}")
                if req.scopes:
                    details.append(f"- **Scopes**: {', '.join(req.scopes)}")
                if req.auth_urls:
                    for url_type, url in req.auth_urls.items():
                        details.append(f"- **{url_type.title()} URL**: {url}")

            lines.extend(details)
            lines.append("")

    return "\n".join(lines)


def summarize_auth_requirements(auth_requirements: list[AuthRequirement]) -> str:
    """
    Generate a concise summary of authentication requirements.

    Args:
        auth_requirements: List of authentication requirements

    Returns:
        Summary string
    """
    if not auth_requirements:
        return "No authentication required."

    # Count by type
    type_counts = {}
    for req in auth_requirements:
        auth_type = req.auth_type.value
        if auth_type not in type_counts:
            type_counts[auth_type] = 0
        type_counts[auth_type] += 1

    summary_parts = []
    for auth_type, count in type_counts.items():
        if count == 1:
            # Get the specific requirement
            for req in auth_requirements:
                if req.auth_type.value == auth_type:
                    if auth_type == "apiKey":
                        location = req.location.value if req.location else "header"
                        summary_parts.append(f"API Key ({req.name} in {location})")
                    elif auth_type == "http":
                        scheme = req.schemes[0] if req.schemes else "bearer"
                        summary_parts.append(f"{scheme.title()} Authentication")
                    elif auth_type == "oauth2":
                        flow = req.flow_type if req.flow_type else "authorization code"
                        summary_parts.append(f"OAuth2 ({flow})")
                    elif auth_type == "openIdConnect":
                        summary_parts.append("OpenID Connect")
                    else:
                        summary_parts.append(f"{auth_type.title()} Authentication")
                    break
        else:
            # Multiple requirements of the same type
            if auth_type == "apiKey":
                summary_parts.append(f"{count} API Keys")
            elif auth_type == "http":
                summary_parts.append(f"{count} HTTP Authentication methods")
            elif auth_type == "oauth2":
                summary_parts.append(f"{count} OAuth2 flows")
            elif auth_type == "openIdConnect":
                summary_parts.append(f"{count} OpenID Connect providers")
            else:
                summary_parts.append(f"{count} {auth_type.title()} Authentication methods")

    if len(summary_parts) == 1:
        return f"Authentication required: {summary_parts[0]}"
    else:
        return f"Authentication required: {', '.join(summary_parts[:-1])} and {summary_parts[-1]}"
