"""Authentication processor for the Jentic MCP Plugin.

This module handles processing authentication requirements from OpenAPI specifications
and Arazzo workflows to generate appropriate configuration and environment variables.
"""

import logging
import re
from typing import Dict, List, Optional, Any

from .auth_parser import (
    AuthRequirement,
    extract_auth_from_openapi,
    extract_auth_from_arazzo,
    extract_security_requirements,
)
from .models import (
    AuthType,
    EnvVarKeys
)

logger = logging.getLogger(__name__)


class AuthProcessor:
    """Processes authentication requirements for APIs."""

    def _normalize_openapi_spec(self, openapi_spec: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize OpenAPI specifications to ensure consistent structure.
        
        Args:
            openapi_spec: OpenAPI specification
            
        Returns:
            Normalized OpenAPI specification
        """
        processed_spec = openapi_spec.copy()  # Make a copy to avoid modifying the original
        
        if isinstance(processed_spec, dict) and ("swagger" in processed_spec or "openapi" in processed_spec):
            # This is an actual OpenAPI spec
            if "components" not in processed_spec and "securityDefinitions" in processed_spec:
                # OpenAPI v2 format uses securityDefinitions
                # Convert to OpenAPI v3 format expected by our parser
                logger.debug("Converting OpenAPI v2 security definitions to v3 format")
                processed_spec["components"] = {"securitySchemes": processed_spec["securityDefinitions"]}
                
            elif "components" not in processed_spec and "securitySchemes" in processed_spec:
                # Some specs have securitySchemes at root level
                logger.debug("Moving root level securitySchemes to components")
                processed_spec["components"] = {"securitySchemes": processed_spec["securitySchemes"]}
        
        return processed_spec

    def process_api_auth(
        self,
        openapi_specs: Dict[str, Dict[str, Any]],
        arazzo_specs: List[Dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Process API authentication requirements and generate auth configuration.
        
        Args:
            openapi_specs: Dictionary mapping source_description_ids to OpenAPI specifications
            arazzo_specs: List of Arazzo workflow specifications (optional)
            
        Returns:
            Processed auth configuration with environment variable mappings
        """
        return self.process(openapi_specs, arazzo_specs)
    
    def process(
        self,
        openapi_specs: Dict[str, Dict[str, Any]],
        arazzo_specs: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Process API authentication requirements from OpenAPI specs and Arazzo workflows.
        
        Args:
            openapi_specs: Dictionary mapping source_description_ids to OpenAPI specifications
            arazzo_specs: Optional list of Arazzo workflow specifications
            
        Returns:
            Dictionary with auth requirements, environment mappings, and auth workflows
        """
        if arazzo_specs is None:
            arazzo_specs = []
            
        if not openapi_specs:
            logger.warning("No OpenAPI specs provided for auth processing")
            return {
                "auth_requirements": [],
                "env_mappings": {},
                "auth_workflows": []
            }
            
        logger.debug(f"Processing auth for {len(openapi_specs)} OpenAPI specs")
        
        # Fix OpenAPI spec structure if needed for each spec
        processed_specs = {}
        for source_id, spec in openapi_specs.items():
            processed_specs[source_id] = self._normalize_openapi_spec(spec)
        
        # Extract auth requirements from OpenAPI specs
        auth_requirements = []
        security_requirements = None
        
        for source_id, spec in processed_specs.items():
            try:
                # Extract auth schemes
                spec_requirements = extract_auth_from_openapi(spec)
                
                # Set the source_description_id for each requirement
                for req in spec_requirements:
                    req.source_description_id = source_id
                    
                if spec_requirements:
                    auth_requirements.extend(spec_requirements)
                
                # Extract security requirements (global and operation-level)
                if not security_requirements and isinstance(spec, dict):
                    security_requirements = extract_security_requirements(spec)
            except Exception as e:
                logger.warning(f"Error extracting auth requirements from spec with ID {source_id}: {str(e)}")
        
        # Generate environment variable mappings
        env_mappings = self.generate_env_mappings(auth_requirements)
        
        # Identify auth workflows
        auth_workflows = self.identify_auth_workflows(auth_requirements, arazzo_specs)
        
        # Create the final auth configuration
        auth_config = []
        for req in auth_requirements:
            auth_item = req.to_dict()
            auth_config.append(auth_item)
        
        result = {
            "auth_requirements": auth_config,
            "env_mappings": env_mappings,
            "auth_workflows": auth_workflows,
        }
        
        # Add security requirements if available
        if security_requirements:
            result["security_requirements"] = security_requirements.model_dump()
            
        return result
    
    def generate_env_mappings(
        self,
        auth_requirements: List[AuthRequirement],
    ) -> Dict[str, Dict[str, str]]:
        """
        Generate environment variable mappings for auth requirements.

        Args:
            auth_requirements: List of auth requirements
            
        Returns:
            Dictionary with mappings of security scheme names to credential keys and environment variable names.
            When multiple source descriptions are present, uses a nested structure with source_name as the outer key.
        """
        # Track unique source descriptions to determine if we need a nested structure
        unique_source_descriptions = set()
        for auth_requirement in auth_requirements:
            source_description_id = auth_requirement.source_description_id or "default"
            unique_source_descriptions.add(source_description_id)
        
        # Determine if we have multiple sources
        has_multiple_sources = len(unique_source_descriptions) > 1
        
        # Create environment mappings structure based on whether we have multiple sources
        if has_multiple_sources:
            # Initialize nested structure with source descriptions as outer keys
            environment_mappings = {source_id: {} for source_id in unique_source_descriptions}
        else:
            # Use flat structure for single source
            environment_mappings = {}
        
        # Process each authentication requirement
        for auth_requirement in auth_requirements:
            source_description_id = auth_requirement.source_description_id or "default"
            security_scheme_name = auth_requirement.security_scheme_name
            
            # Determine the environment variable prefix from API title
            env_var_prefix_base = None
            if auth_requirement.api_title:
                # Extract first word from API title, convert to uppercase for env var naming convention
                api_title_first_word = auth_requirement.api_title.split()[0].upper().replace('-', '_')
                env_var_prefix_base = self._convert_to_env_var(api_title_first_word)

            # Create full environment variable prefix
            sanitized_scheme_name = self._convert_to_env_var(security_scheme_name)
            env_var_prefix = f"{env_var_prefix_base}_{sanitized_scheme_name}" if env_var_prefix_base else sanitized_scheme_name
            
            # For OAuth2, add the flow type as a suffix to distinguish different flows
            scheme_name_suffix = ""
            if auth_requirement.auth_type == AuthType.OAUTH2:
                if auth_requirement.flow_type in ["authorizationCode", "implicit"]:
                    scheme_name_suffix = ".web"
                elif auth_requirement.flow_type:
                    scheme_name_suffix = f".{auth_requirement.flow_type}"
            
            # Use the scheme name with suffix for the mappings
            full_scheme_name = f"{security_scheme_name}{scheme_name_suffix}"
            
            # Get the appropriate mapping dictionary based on structure
            if has_multiple_sources:
                # Use the source-specific mapping
                if full_scheme_name not in environment_mappings[source_description_id]:
                    environment_mappings[source_description_id][full_scheme_name] = {}
                scheme_env_vars = environment_mappings[source_description_id][full_scheme_name]
            else:
                # Use the flat mapping
                if full_scheme_name not in environment_mappings:
                    environment_mappings[full_scheme_name] = {}
                scheme_env_vars = environment_mappings[full_scheme_name]
            
            # Add appropriate environment variable mappings based on authentication type
            if auth_requirement.auth_type == AuthType.API_KEY:
                scheme_env_vars[EnvVarKeys.API_KEY] = f"{env_var_prefix}"
                
            elif auth_requirement.auth_type == AuthType.HTTP:
                http_auth_type = "basic" if "basic" in auth_requirement.schemes else (
                    "bearer" if "bearer" in auth_requirement.schemes or "Bearer" in auth_requirement.schemes else "generic"
                )
                
                if http_auth_type == "basic":
                    scheme_env_vars[EnvVarKeys.USERNAME] = f"{env_var_prefix}_USERNAME"
                    scheme_env_vars[EnvVarKeys.PASSWORD] = f"{env_var_prefix}_PASSWORD"
                elif http_auth_type == "bearer":
                    scheme_env_vars[EnvVarKeys.TOKEN] = f"{env_var_prefix}_TOKEN"
                else:
                    # Generic HTTP auth
                    scheme_env_vars[EnvVarKeys.AUTH_VALUE] = f"{env_var_prefix}_AUTH_VALUE"
                    
            elif auth_requirement.auth_type == AuthType.OAUTH2:
                # Common OAuth2 params
                scheme_env_vars[EnvVarKeys.CLIENT_ID] = f"{env_var_prefix}_CLIENT_ID"
                scheme_env_vars[EnvVarKeys.CLIENT_SECRET] = f"{env_var_prefix}_CLIENT_SECRET"
                
                # Flow-specific params
                if auth_requirement.flow_type == "password":
                    scheme_env_vars[EnvVarKeys.USERNAME] = f"{env_var_prefix}_USERNAME"
                    scheme_env_vars[EnvVarKeys.PASSWORD] = f"{env_var_prefix}_PASSWORD"
                    
                if auth_requirement.flow_type in ["authorizationCode", "implicit"]:
                    scheme_env_vars[EnvVarKeys.REDIRECT_URI] = f"{env_var_prefix}_REDIRECT_URI"
                
                scheme_env_vars[EnvVarKeys.TOKEN] = f"{env_var_prefix}_ACCESS_TOKEN"
                
            elif auth_requirement.auth_type == AuthType.OPENID:
                scheme_env_vars[EnvVarKeys.CLIENT_ID] = f"{env_var_prefix}_CLIENT_ID"
                scheme_env_vars[EnvVarKeys.CLIENT_SECRET] = f"{env_var_prefix}_CLIENT_SECRET"
                scheme_env_vars[EnvVarKeys.TOKEN] = f"{env_var_prefix}_ID_TOKEN"
                
            elif auth_requirement.auth_type == AuthType.CUSTOM:
                # For custom auth, use the name as a key
                normalized_name = self._convert_to_env_var(auth_requirement.name)
                scheme_env_vars[auth_requirement.name] = f"{env_var_prefix}_{normalized_name}"
        
        return environment_mappings

    def identify_auth_workflows(
        self, 
        auth_requirements: List[AuthRequirement],
        arazzo_specs: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify authentication workflows from Arazzo specs.
        
        Args:
            auth_requirements: List of auth requirements
            arazzo_specs: List of Arazzo workflow specifications
            
        Returns:
            List of auth workflow configurations
        """
        auth_workflows = []
        if not arazzo_specs:
            return auth_workflows
        
        # Look for auth-related workflows
        auth_keywords = [
            "auth", "login", "token", "authenticate", "oauth", 
            "signin", "sign_in", "sign-in", "getToken", "get_token"
        ]
        
        # Find workflows that might be authentication workflows
        for arazzo_spec in arazzo_specs:
            workflows = arazzo_spec.get("workflows", [])
            for workflow in workflows:
                workflow_id = workflow.get("id", "")
                summary = workflow.get("summary", "").lower()
                description = workflow.get("description", "").lower()
                
                # Check if this is likely an auth workflow
                is_auth_workflow = False
                for keyword in auth_keywords:
                    if (keyword in workflow_id.lower() or 
                        keyword in summary or 
                        keyword in description):
                        is_auth_workflow = True
                        break
                
                if is_auth_workflow:
                    # Check the outputs for tokens
                    outputs = workflow.get("outputs", {})
                    token_output = None
                    
                    for output_name, output_details in outputs.items():
                        if any(kw in output_name.lower() for kw in ["token", "access", "auth", "bearer"]):
                            token_output = output_name
                            break
                    
                    auth_workflows.append({
                        "workflow_id": workflow_id,
                        "summary": workflow.get("summary", ""),
                        "token_output": token_output,
                        "outputs": list(outputs.keys())
                    })
        
        return auth_workflows

    def _convert_to_env_var(self, value: str) -> str:
        """
        Convert a string to a format suitable for environment variable names.
        
        Args:
            value: String to convert
            
        Returns:
            Converted string suitable for environment variables
        """
        # Convert to uppercase and replace hyphens with underscores
        normalized = value.upper().replace('-', '_')
        
        # Use the sanitize method to handle other special characters
        return self._sanitize_prefix(normalized)

    def _sanitize_prefix(self, prefix: str) -> str:
        """
        Sanitize a string for use in environment variable names.
        
        Args:
            prefix: The text to sanitize
            
        Returns:
            Sanitized text suitable for environment variables
        """
        # Convert to uppercase and replace hyphens with underscores
        sanitized = prefix.upper().replace('-', '_')
        # Replace non-alphanumeric characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', sanitized)
        # Replace multiple consecutive underscores with a single underscore
        sanitized = re.sub(r'_+', '_', sanitized)
        # Remove leading and trailing underscores
        sanitized = sanitized.strip('_')

        return sanitized
