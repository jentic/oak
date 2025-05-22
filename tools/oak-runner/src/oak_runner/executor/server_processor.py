"""
ServerProcessor: Handles server configuration and URL resolution logic for OAK Runner.
"""
from typing import Any, Dict, List, Optional
import re
from urllib.parse import urlparse, urljoin
from ..models import ServerConfiguration

import logging

logger = logging.getLogger("oak_runner.server_processor")

from ..utils import extract_api_title_prefix, create_env_var_name


class ServerProcessor:
    """
    Component to encapsulate all server configuration and URL resolution logic.
    """
    def __init__(self, source_descriptions: dict[str, Any]) -> None:
        self.source_descriptions = source_descriptions

    @staticmethod
    def resolve_server_base_url(server_config: ServerConfiguration, runtime_params: Optional[Dict[str, str]] = None) -> str:
        """
        Resolves the templated server URL using provided parameters, environment variables,
        or default values for a given ServerConfiguration.

        Args:
            server_config: The ServerConfiguration object.
            runtime_params: A dictionary of runtime parameters to substitute.

        Returns:
            The resolved server base URL as a string.

        Raises:
            ValueError: If a required variable in the template cannot be resolved.
        """
        import os
        resolved_url = server_config.url_template
        if runtime_params is None:
            runtime_params = {}

        # Find all variable placeholders like {var_name} in the URL template
        template_vars_in_url: set[str] = set(re.findall(r"{(.*?)}", server_config.url_template))

        for var_name in template_vars_in_url:
            server_var_details = server_config.variables.get(var_name)

            if not server_var_details:
                # This implies a mismatch: a variable placeholder in the URL template
                # does not have a corresponding definition in the 'variables' section.
                # OpenAPI spec dictates that all variables in the URL template MUST be defined.
                raise ValueError(
                    f"Variable '{var_name}' in URL template '{server_config.url_template}' has no corresponding "
                    f"definition in server variables. This may indicate an invalid OpenAPI document."
                )

            resolved_value: Optional[str] = None

            # Construct the environment variable name using the utility function
            prefix = f"{server_config.api_title_prefix}_OAK_SERVER" if server_config.api_title_prefix else "OAK_SERVER"
            env_var_name = create_env_var_name(
                var_name=var_name,
                prefix=prefix
            )

            # 1. Try to use value from runtime_params (keyed by env_var_name)
            if runtime_params is not None and env_var_name in runtime_params:
                resolved_value = runtime_params[env_var_name]
                if resolved_value is not None:
                    logger.debug(f"Server variable '{var_name}' (using key '{env_var_name}'): resolved from runtime_params.")
            
            # 2. Else, if not resolved from runtime_params (or if value was None), try os.getenv
            if resolved_value is None:
                env_os_value = os.getenv(env_var_name)
                if env_os_value is not None:
                    resolved_value = env_os_value
                    logger.debug(f"Server variable '{var_name}' (using env var '{env_var_name}'): resolved from environment.")

            # 3. Else, if still not resolved, use ServerVariable.default_value
            if resolved_value is None and server_var_details.default_value is not None:
                resolved_value = server_var_details.default_value
                logger.debug(f"Server variable '{var_name}': resolved from default_value.")

            # 4. If still unresolved, this variable is mandatory and no value was found
            if resolved_value is None:
                raise ValueError(
                    f"Required server variable '{var_name}' could not be resolved for URL template "
                    f"'{server_config.url_template}'. No value found in runtime_params (key: '{env_var_name}'), "
                    f"environment (variable: '{env_var_name}'), or as a default."
                )

            # 5. If ServerVariable.enum_values is set, log a warning if the resolved value is not in the enum
            if server_var_details.enum_values and resolved_value not in server_var_details.enum_values:
                logger.warning(
                    f"Value '{resolved_value}' for server variable '{var_name}' is not in its defined "
                    f"enum values: {server_var_details.enum_values}. URL: '{server_config.url_template}'"
                )

            # Substitute the resolved value into the URL template
            resolved_url = resolved_url.replace(f"{{{var_name}}}", resolved_value)

        return resolved_url

    @staticmethod
    def extract_server_configurations(spec_dict: dict[str, Any]) -> list[ServerConfiguration]:
        """
        Extracts server configurations from a loaded OpenAPI specification dictionary.

        Args:
            spec_dict: The loaded OpenAPI specification as a dictionary.

        Returns:
            A list of ServerConfiguration objects parsed from the spec.
        """
        logger.debug('extracting server confs...')    
        server_configs: list[ServerConfiguration] = []
        api_title = spec_dict.get('info', {}).get('title')
        api_title_prefix = extract_api_title_prefix(api_title) if api_title else None
        raw_server_list = spec_dict.get('servers', [])
        if not isinstance(raw_server_list, list):
            logger.warning("'servers' field in OpenAPI spec is not a list. Skipping server configuration parsing.")
            return []    
        for i, server_data in enumerate(raw_server_list):
            if not isinstance(server_data, dict):
                logger.warning(f"Server entry at index {i} is not a dictionary. Skipping this entry.")
                continue
            logger.info('server_data:')
            logger.info(server_data)
            try:
                config_data = server_data.copy()
                config_data['api_title_prefix'] = api_title_prefix
                server_config_instance = ServerConfiguration(**config_data)
                server_configs.append(server_config_instance)
                logger.debug(f"Successfully parsed server configuration for URL: {server_config_instance.url_template}")
            except Exception as e:
                logger.error(f"Failed to parse server entry at index {i} (URL: {server_data.get('url', 'N/A')}): {e}", exc_info=True)
        if not server_configs and raw_server_list:
            logger.info("Found server entries in spec, but none could be parsed into ServerConfiguration objects.")
        elif not raw_server_list:
            logger.info("No 'servers' defined in the OpenAPI specification.")
        else:
            logger.info(f"Successfully extracted {len(server_configs)} server configuration(s).")
        return server_configs

    @staticmethod
    def format_server_config_details(config: ServerConfiguration) -> str:
        """
        Formats the details of a ServerConfiguration for user-friendly display.

        This includes the URL template, its description, and for each variable:
        its name, description, default value, possible enum values, and the
        exact environment variable name that can be used to set it.

        Args:
            config: The ServerConfiguration object to format.

        Returns:
            A string containing the formatted details.
        """
        details: list[str] = []

        details.append(f"Server URL Template: {config.url_template}")
        if config.description:
            details.append(f"  Description: {config.description}")
        
        if config.api_title_prefix:
            details.append(f"  (Associated API Title Prefix for ENV VARS: {config.api_title_prefix})")

        if not config.variables:
            details.append("  This server URL has no dynamic variables.")
        else:
            details.append("  Variables:")
            for var_name, var_details in config.variables.items():
                details.append(f"    - Variable: '{var_name}'")
                if var_details.description:
                    details.append(f"      Description: {var_details.description}")
                
                prefix = f"{config.api_title_prefix}_OAK_SERVER" if config.api_title_prefix else "OAK_SERVER"
                env_var_name = create_env_var_name(
                    var_name=var_name,
                    prefix=prefix
                )
                details.append(f"      Set via ENV: {env_var_name}")

                if var_details.default_value is not None:
                    details.append(f"      Default: '{var_details.default_value}'")
                else:
                    details.append(f"      Default: (none)")

                if var_details.enum_values:
                    details.append(f"      Possible Values: {', '.join(var_details.enum_values)}")
                else:
                    details.append(f"      Possible Values: (any)")
        
        return "\n".join(details)

    @staticmethod
    def url_contains_template_vars_in_host(url_string: Optional[str]) -> bool:
        if not url_string:
            return False
        parsed_url = urlparse(url_string)
        if parsed_url.netloc:
            if re.search(r"\{[^}]+\}", parsed_url.netloc):
                return True
        return False

    def get_env_mappings(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Extract environment variable mappings for all server variables across all source descriptions.
        
        Returns:
            A nested dictionary structure mapping source names to server URLs to variable mappings.
            Format:
            {
                "source_name": {
                    "server_url": {
                        "variable_name": "ENV_VAR_NAME"
                    }
                }
            }
        """
        env_mappings = {}
        
        # Process each source description
        for source_name, spec_dict in self.source_descriptions.items():
            # Extract server configurations for this source
            server_configs = self.extract_server_configurations(spec_dict)
            
            if not server_configs:
                continue
                
            # Initialize the mapping for this source
            source_mappings = {}
            
            # Process each server configuration
            for i, server_config in enumerate(server_configs):
                # Use URL template as the key for this server
                server_url = server_config.url_template
                
                # Skip servers without variables
                if not server_config.variables:
                    continue
                
                # Initialize the mapping for this server
                server_mappings = {}
                
                # Process each variable in this server configuration
                for var_name, var_details in server_config.variables.items():
                    # Create the environment variable name
                    prefix = f"{server_config.api_title_prefix}_OAK_SERVER" if server_config.api_title_prefix else "OAK_SERVER"
                    env_var_name = create_env_var_name(
                        var_name=var_name,
                        prefix=prefix
                    )
                    
                    # Store the mapping
                    server_mappings[var_name] = env_var_name
                
                # Only add this server if it has variables
                if server_mappings:
                    source_mappings[server_url] = server_mappings
            
            # Only add this source if it has servers with variables
            if source_mappings:
                env_mappings[source_name] = source_mappings
        
        return env_mappings

    def resolve_final_url(
        self,
        operation_url_template: Optional[str],
        server_runtime_params: Optional[Dict[str, str]],
        source_name: Optional[str] = 'default',
    ) -> str:
        """
        Resolve the final URL for an operation, including server variable resolution.
        """
        if not operation_url_template:
            logger.error("operation_url_template is None or empty.")
            raise ValueError("Operation URL template cannot be None or empty.")

        is_absolute_url = operation_url_template.startswith("http://") or operation_url_template.startswith("https://")
        has_vars_in_host = self.url_contains_template_vars_in_host(operation_url_template)

        # Case 1: operation_url_template is a full URL and has NO server variables in its host. Use as is.
        if not has_vars_in_host:
            return operation_url_template

        # Case 2: We need to use server configurations from the spec.
        if not source_name:
            logger.error(f"No source_name provided. Cannot resolve URL '{operation_url_template}' which requires server configuration.")
            raise ValueError(f"Cannot resolve URL '{operation_url_template}': source_name is required to load server configurations.")

        spec_doc: Optional[Any] = self.source_descriptions.get(source_name)
        if not spec_doc:
            logger.error(f"Spec not found for source_name='{source_name}'. Cannot resolve URL '{operation_url_template}'.")
            raise ValueError(f"Cannot resolve URL '{operation_url_template}': OpenAPI spec for source '{source_name}' not found.")

        server_configs: List[ServerConfiguration] = ServerProcessor.extract_server_configurations(spec_doc)
        if not server_configs:
            logger.error(f"No server configurations found in spec for source_name='{source_name}'. Cannot resolve URL '{operation_url_template}'.")
            raise ValueError(f"Cannot resolve URL '{operation_url_template}': No server configurations found in spec for '{source_name}'.")

        selected_config = server_configs[0]  # Default to the first server config

        try:
            resolved_server_base = self.resolve_server_base_url(server_config=selected_config, runtime_params=server_runtime_params)
        except ValueError as e:
            logger.error(f"Error resolving variables in ServerConfiguration ('{selected_config.url_template}'): {e}")
            raise ValueError(f"Failed to resolve server variables for server configuration '{selected_config.url_template}': {e}") from e

        # Extract the path, query, and fragment from operation_url_template.
        parsed_operation_url = urlparse(operation_url_template)
        operation_path_part = parsed_operation_url.path
        if parsed_operation_url.query:
            operation_path_part += "?" + parsed_operation_url.query
        if parsed_operation_url.fragment:
            operation_path_part += "#" + parsed_operation_url.fragment

        # Ensure operation_path_part is suitable for urljoin
        if operation_path_part and not operation_path_part.startswith("/"):
            operation_path_part = "/" + operation_path_part
        elif not operation_path_part:
            operation_path_part = "/"

        final_url = urljoin(resolved_server_base.rstrip('/') + '/', operation_path_part.lstrip('/'))
        return final_url
