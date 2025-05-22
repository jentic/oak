### OAK Runner: Server Variables Support - Design & Implementation Plan

#### 1. Introduction
This document outlines the design and implementation plan to add support for server variables in OAK Runner, as defined in OpenAPI 3.x specifications. This feature will allow users to define API server URLs with dynamic parts (e.g., `https://{customer}.api.com` or `api.{hostname}.com`), which can be resolved at runtime.

#### 2. Goals
- Parse `servers` objects, including their `url` templates and `variables` definitions, from OpenAPI specifications.
- Provide a mechanism for OAK Runner to resolve these variables at runtime using:
    1. Explicitly passed runtime parameters.
    2. Environment variables.
    3. Default values specified in the OpenAPI document.
- Describe available server configurations and their variables to the user (human or LLM), including how to provide values.
- Ensure this functionality works seamlessly for both direct OpenAPI operation executions and operations executed as part of an Arazzo workflow (without altering Arazzo workflow definitions).

#### 3. Design Details

##### 3.1. Core Data Models (`src/oak_runner/models/server_config.py`)
New Pydantic models will represent server configurations:
-   **`ServerVariable`**:
    -   `name: str` (populated from the key in the OpenAPI `variables` map)
    -   `description: Optional[str]`
    -   `default_value: Optional[str]` (maps to `default` in OpenAPI, via Field alias)
    -   `enum_values: Optional[List[str]]` (maps to `enum` in OpenAPI, via Field alias)
-   **`ServerConfiguration`**:
    -   `url_template: str` (maps to `url` in OpenAPI, via Field alias)
    -   `description: Optional[str]`
    -   `variables: Dict[str, ServerVariable]` (map of variable names to `ServerVariable` objects)
    -   `api_title_prefix: Optional[str] = None` (derived from `info.title` of the OpenAPI spec, e.g., first word, uppercase)

##### 3.2. Parsing Server Configurations & URL Resolution Utility (`src/oak_runner/extractor/openapi_extractor.py` & `src/oak_runner/utils.py`)
-   **Extraction (`openapi_extractor.py`):**
    -   A new function `extract_server_configurations(spec_dict: Dict[str, Any]) -> List[ServerConfiguration]` will be created in `src/oak_runner/extractor/openapi_extractor.py`.
    -   It takes a loaded OpenAPI specification (as a dictionary).
    -   It first attempts to extract `spec_dict.get('info', {}).get('title')`.
    -   If a title is found, it generates an `api_title_prefix` by taking the first word, converting it to uppercase, and sanitizing it (e.g., replacing non-alphanumeric characters with underscores, similar to existing `_convert_to_env_var` logic).
    -   It accesses `spec_dict.get('servers', [])`.
    -   It parses each server entry into a `ServerConfiguration` Pydantic model, passing the generated `api_title_prefix` (if any) to each `ServerConfiguration` instance.
    -   It returns the list of parsed `ServerConfiguration` objects.
-   **Integration & Storage (`utils.py`):**
    -   The helper function `_parse_and_store_server_configurations(spec_dict: Dict[str, Any]) -> None` in `src/oak_runner/utils.py` will be responsible for orchestrating the parsing.
    -   It will call `extract_server_configurations()` from `openapi_extractor.py`.
    -   The returned list of `ServerConfiguration` objects is then stored by this function into the `spec_dict` under a new key, e.g., `_oak_server_configurations`.
-   The existing functions in `utils.py` like `load_source_descriptions()` and `load_openapi_file()` will be modified to call `_parse_and_store_server_configurations()` immediately after an OpenAPI spec dictionary is loaded.
-   **Server URL Resolution Utility (`src/oak_runner/utils.py`):**
    -   A utility function `resolve_server_base_url(config: ServerConfiguration, runtime_params: Optional[Dict[str, str]] = None) -> str` will be implemented in `src/oak_runner/utils.py`.
    -   It takes a `ServerConfiguration` object and optional `runtime_params` (e.g., `{"customer": "acme"}`).
    -   For each variable in the `config.url_template`:
        1.  Uses value from `runtime_params` if provided for the variable name.
        2.  Else, constructs the environment variable name. If `config.api_title_prefix` is set, the format is `f"{config.api_title_prefix}_OAK_SERVER_{variable_name.upper()}"`. Otherwise, it's `f"OAK_SERVER_{variable_name.upper()}"`. It then attempts to use the value from this environment variable.
        3.  Else, uses the `default_value` from the corresponding `ServerVariable` in `config.variables`.
        4.  If still unresolved and the variable is present in the template, raises a `ValueError`.
        5.  If the corresponding `ServerVariable.enum_values` is set, logs a warning if the resolved value is not in the enum (does not fail the call initially).
        -   Returns the fully resolved URL string.

##### 3.3. Execution Logic (`src/oak_runner/http.py` - `HTTPExecutor`)
-   The `HTTPExecutor`'s method responsible for making HTTP calls (e.g., `execute_request()`) will accept a fully resolved `url` string.
-   The resolution of the base URL part of this `url` (if it involves server variables) will happen in `StepExecutor` *before* calling `HTTPExecutor`.
-   The `StepExecutor` will:
    1.  Retrieve the selected `ServerConfiguration`.
    2.  Call the `resolve_server_base_url(selected_config, runtime_server_params)` utility function from `src/oak_runner/utils.py` to get the final base URL for the server.
    3.  Combine this resolved base URL with the operation's specific path (e.g., from the `url` field in the operation definition, which might be `/users/{id}`).
    4.  Pass this combined, fully resolved URL to `HTTPExecutor`.
-   If no server configurations are applicable or the operation's URL is already absolute and static (no host variables), that URL is used directly. Existing logic for handling operations without server objects or with fully static URLs should be maintained.

##### 3.4. Parameter Threading (`src/oak_runner/executor.py`, `src/oak_runner/runner.py`)
-   **`OAKRunner` (`runner.py`)**: Methods like `execute_operation` (for direct OpenAPI calls) and relevant workflow execution methods (e.g., `start_workflow`, `execute_next_step`) need to be able to accept `server_runtime_params: Optional[Dict[str, str]]`.
-   **`StepExecutor` (`executor.py`):**
    -   The `StepExecutor` will receive `server_runtime_params` from the `OAKRunner`.
    -   When preparing to execute an OpenAPI operation (e.g., in `_resolve_final_url_template` method):
        -   It will retrieve the list of `ServerConfiguration` objects from the loaded `spec_dict` (e.g., `spec_dict.get('_oak_server_configurations')`).
        -   It will then select the appropriate `ServerConfiguration` to use (e.g., default to the first one).
        -   If a `ServerConfiguration` is selected, it calls the `resolve_server_base_url(selected_config, server_runtime_params)` utility function (from `utils.py`) to get the resolved server base URL.
        -   This resolved server base is then combined with the operation's specific path (e.g., `/users/{userId}`).
        -   The resulting final URL (with server variables resolved, but path/query parameters potentially still templated) is then used for the `HTTPExecutor` call.
-   The source of `server_runtime_params` can be:
    -   Direct input from the user/LLM when invoking an operation.
    -   Derived from the workflow context (e.g., workflow inputs, outputs from prior steps, or static values configured for the workflow).

##### 3.5. User-Facing Descriptions (`src/oak_runner/runner.py`, `src/oak_runner/__main__.py`)
-   When OAK Runner describes an operation or provides a consolidated list of expected environment variables (e.g., via a `describe_operation` method in `OAKRunner`, or a CLI command like `show_env_mappings` handled in `__main__.py`), it will:
    1.  Access `spec_dict['_oak_server_configurations']` from the loaded specification.
    2.  If server configurations are available:
        a.  For operation-specific descriptions: Focus on the first (default) `ServerConfiguration` or the relevant one for the operation.
        b.  For general environment variable listings (like `show_env_mappings`): Iterate through all defined `ServerConfiguration` objects or a representative set if too numerous.
    3.  For each relevant `ServerConfiguration` and its `variables`:
        a.  Display its `url_template` (especially for operation descriptions).
        b.  List its defined `variables` (name, description, default value).
        c.  Clearly instruct the user on how to provide values. The environment variable format will depend on whether an API title prefix was derived: `[API_TITLE_PREFIX_]OAK_SERVER_<VAR_NAME_UPPERCASE>` (e.g., `PETSTORE_OAK_SERVER_REGION` or `OAK_SERVER_REGION` if no title/prefix). Explain that `API_TITLE_PREFIX` is typically the first word of the API's title, uppercased and sanitized.
    4.  Ensure that the output of commands like `show_env_mappings` comprehensively lists all such environment variables derived from any server configurations present in the loaded spec, in addition to other environment variables the runner might expect, clearly showing the prefixing logic.

##### 3.6. Workflow Integration
-   No changes are required for Arazzo workflow definitions (`.json` or `.yaml` files).
-   When a workflow step references an OpenAPI operation, the OAK Runner will load the corresponding OpenAPI spec.
-   The server variable parsing (in `utils.py`) and resolution (via `resolve_server_base_url` in `utils.py` called by `StepExecutor`) will apply automatically when that operation is executed.
-   The `server_runtime_params` for a workflow step can be assembled from the workflow's execution context (e.g., global inputs, outputs from prior steps).

#### 4. Implementation Plan

##### Phase 1: Core Models & User-Facing Descriptions
1.  **Task 1.1: Create `ServerVariable` and `ServerConfiguration` Models**
    -   File: `src/oak_runner/models/server_config.py`
    -   Implement Pydantic models as described in section 3.1. This includes:
        -   `ServerVariable`.
        -   `ServerConfiguration` with the `api_title_prefix: Optional[str]` field.
        -   Appropriate Pydantic `Field` aliases for OpenAPI field names like `default` and `enum`.
2.  **Task 1.2: Implement User-Facing Descriptions and CLI Output for Server Variables**
    -   Files: `src/oak_runner/runner.py`, `src/oak_runner/__main__.py` (for CLI integration)
    -   Enhance functionality in `OAKRunner` for describing operations and in `__main__.py` for commands like `show_env_mappings` to include details about server variables as outlined in the updated section 3.5.
    -   This includes displaying the new environment variable format: `[API_TITLE_PREFIX_]OAK_SERVER_<VAR_NAME_UPPERCASE>`, and explaining how `API_TITLE_PREFIX` is derived.

##### Phase 2: Server Configuration Parsing & Resolution Utility
1.  **Task 2.1: Implement `extract_server_configurations` in `openapi_extractor.py`**
    -   File: `src/oak_runner/extractor/openapi_extractor.py`
    -   Add import: `from ..models.server_config import ServerConfiguration, ServerVariable`.
    -   Create the function `extract_server_configurations(spec_dict: Dict[str, Any]) -> List[ServerConfiguration]`.
    -   Implement logic to extract `spec_dict.get('info', {}).get('title')`.
    -   Generate `api_title_prefix` from the title (first word, uppercase, sanitized - consider creating or reusing a utility for this sanitization, e.g., `_convert_to_env_var`).
    -   Parse `spec_dict.get('servers', [])` into a list of `ServerConfiguration` objects, populating `api_title_prefix` in each.
    -   Handle potential errors gracefully.
2.  **Task 2.2: Integrate Server Configuration Parsing in `utils.py`**
    -   File: `src/oak_runner/utils.py`
    -   Add import: `from .extractor.openapi_extractor import extract_server_configurations`.
    -   Add import: `from .models.server_config import ServerConfiguration` (for type hinting).
    -   Implement (or modify if it exists from a previous stub) the helper function `_parse_and_store_server_configurations(spec_dict: Dict[str, Any]) -> None`.
        -   This function calls `extract_server_configurations(spec_dict)` from `openapi_extractor.py`.
        -   It then stores the returned list of `ServerConfiguration` objects into the `spec_dict` under the key `_oak_server_configurations`.
    -   Modify `load_source_descriptions()` and `load_openapi_file()`: After loading an OpenAPI spec into a dictionary, call `_parse_and_store_server_configurations()` on it.
3.  **Task 2.3: Implement `resolve_server_base_url` Utility Function in `utils.py`**
    -   File: `src/oak_runner/utils.py`
    -   Implement the function `resolve_server_base_url(config: ServerConfiguration, runtime_params: Optional[Dict[str, str]] = None) -> str` as described in section 3.2.

##### Phase 3: Execution Logic and Parameter Threading
1.  **Task 3.1: Update `StepExecutor` for Dynamic Base URL Resolution**
    -   File: `src/oak_runner/executor/step_executor.py` (e.g., in `_resolve_final_url_template` or similar method)
    -   Modify methods responsible for preparing/executing individual OpenAPI operation steps.
    -   If a selected `ServerConfiguration` is available, call the `resolve_server_base_url(selected_config, server_runtime_params)` utility function from `utils.py` to obtain the resolved server base URL.
    -   Ensure this resolved base URL is correctly combined with the operation's specific path (e.g., using `urllib.parse.urljoin`).
    -   The final resolved URL is then passed to the `HTTPExecutor`.
2.  **Task 3.2: Update `OAKRunner` for Server Parameter Input**
    -   File: `src/oak_runner/runner.py`
    -   Modify public methods for operation execution (e.g., `execute_operation` if available, or methods involved in `execute_next_step` for workflows) to accept `server_runtime_params: Optional[Dict[str, str]]`.
    -   Ensure these parameters are correctly passed down to `StepExecutor`.

##### Phase 4: Testing
1.  **Task 4.1: Unit Tests for `resolve_server_base_url` Utility Function**
    -   File: Tests for `src/oak_runner/utils.py`
    -   Test variable substitution from runtime params, environment variables (with and without `api_title_prefix`), and defaults.
    -   Test precedence of these sources.
    -   Test error handling for unresolved required variables.
    -   Test enum validation warnings.
    -   Test scenarios with no variables in the `ServerConfiguration.url_template`.
2.  **Task 4.2: Unit Tests for Server Configuration Parsing**
    -   Test `extract_server_configurations` in `src/oak_runner/extractor/openapi_extractor.py`:
        -   Correct parsing of server objects and variables.
        -   Correct extraction and generation of `api_title_prefix` from `info.title`.
        -   Correct population of `api_title_prefix` in `ServerConfiguration` instances.
        -   Handling of valid `servers` arrays, empty/missing `servers` array, malformed entries.
    -   Test `_parse_and_store_server_configurations` in `src/oak_runner/utils.py` to ensure correct call to extractor and storage of results into `spec_dict`.
3.  **Task 4.3: Integration Tests for `StepExecutor` and `HTTPExecutor`**
    -   Test HTTP calls where the base URL is constructed by `StepExecutor` using server variables (resolved via `resolve_server_base_url` from `utils.py`) and correctly passed to `HTTPExecutor`.
4.  **Task 4.4: End-to-End Tests for `OAKRunner`**
    -   Test user-facing descriptions (from `OAKRunner` and `__main__.py` CLI commands) correctly include server variable information using the new `[API_TITLE_PREFIX_]OAK_SERVER_<VAR_NAME_UPPERCASE>` format (verifying Task 1.2).
    -   Test execution of OpenAPI operations (both directly and via simple workflows) that utilize server variables, ensuring correct behavior with environment variables set using the new naming convention (verifying Phase 3 functionality).

#### 5. Future Considerations (Out of Scope for Initial Implementation)
-   Allowing users to select a non-default server configuration if multiple are defined in the OpenAPI spec (e.g., via an index or matching criteria).
-   Stricter validation against `enum` values for server variables (e.g., option to fail if value is not in enum).
-   More sophisticated merging of `runtime_server_params` from different sources (e.g., global workflow inputs vs. step-specific overrides).
