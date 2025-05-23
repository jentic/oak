# OAK Runner [Beta]

The OAK Runner is a workflow execution engine that processes and executes API workflows defined in the Arazzo format and individual API calls defined in OpenAPI specifications.

## Usage

### Execute a Workflow
```python
from oak_runner import OAKRunner

runner = OAKRunner.from_arazzo_path("../../workflows/discord.com/workflows.arazzo.json")

result = runner.execute_workflow("workflowId", {"param1": "value1"})
```

### Display Authentication Options
```python
from oak_runner import OAKRunner

runner = OAKRunner.from_arazzo_path("../../workflows/discord.com/workflows.arazzo.json")

print(runner.get_env_mappings())
```

### Execute a Single OpenAPI Operation
```python
from oak_runner import OAKRunner
# Execute a single OpenAPI operation with an operationId
result = runner.execute_operation("operationId", {"param1": "value1"})

# Execute a single OpenAPI operation by path
result = runner.execute_operation("GET /users/@me/guilds", {"param1": "value1"})
```

### Create a Runner with a Custom Base Path
```python
# Create a runner instance with a custom base path for resolving OpenAPI file paths
runner_with_base_path = OAKRunner.from_arazzo_path(
    "./my/arazzo.yaml", 
    base_path="./my/source/description/base"
)
```

## Authentication

Credentials are resolved from environment variables defined by the OAK Runner based on the Arazzo or OpenAPI file. You can see the authentication options by using `runner.get_env_mappings` or the `show-env-mappings` command line tool defined below.

The OAK Runner supports various authentication methods defined in OpenAPI specifications:

- **API Key**: Header, Query, or Cookie API keys
- **OAuth2**: Some OAuth2 Flows (Client Credentials, Password)
- **HTTP**: Basic and Bearer Authentication

### Auth Methods Not Yet Supported
- **OAuth2**: Authorization Code, Implicit
- **OpenID**: OpenID Connect
- **Custom**: Custom Authentication Schemes

## Command Line Usage

Usage:
```sh
uvx oak-runner <command> [command-specific arguments] [global options]
```

**Commands:**

1.  **`show-env-mappings`**: Show environment variable mappings for authentication based on an Arazzo or OpenAPI file.
    ```sh
    uvx oak-runner show-env-mappings [arazzo_path | --openapi-path PATH]
    ```
    -   `arazzo_path`: Path to the Arazzo YAML file (use this OR --openapi-path).
    -   `--openapi-path PATH`: Path to the OpenAPI spec file (use this OR arazzo_path).
    *One of the path arguments is required.*

2.  **`execute-workflow`**: Execute a workflow defined in an Arazzo file.
    ```sh
    uvx oak-runner execute-workflow <arazzo_path> --workflow-id <workflow_id> [--inputs <json_string>]
    ```
    -   `arazzo_path`: *Required*. Path to the Arazzo YAML file containing the workflow.
    -   `--workflow-id WORKFLOW_ID`: *Required*. ID of the workflow to execute.
    -   `--inputs INPUTS`: Optional JSON string of workflow inputs (default: `{}`).

3.  **`execute-operation`**: Execute a single API operation directly from an OpenAPI specification (or an Arazzo file for context).
    ```sh
    uvx oak-runner execute-operation [--arazzo-path PATH | --openapi-path PATH] [--operation-id ID | --operation-path PATH_METHOD] [--inputs <json_string>]
    ```
    -   `--arazzo-path PATH`: Path to an Arazzo file (provides context, use this OR --openapi-path).
    -   `--openapi-path PATH`: Path to the OpenAPI spec file (use this OR --arazzo-path).
        *One of the path arguments is required.*
    -   `--operation-id ID`: The `operationId` from the OpenAPI spec (use this OR --operation-path).
    -   `--operation-path PATH_METHOD`: The HTTP method and path (e.g., 'GET /users/{id}') from the OpenAPI spec (use this OR --operation-id).
        *One of the operation identifiers is required.*
    -   `--inputs INPUTS`: Optional JSON string of operation inputs (parameters, request body) (default: `{}`).

4.  **`list-workflows`**: List all available workflows defined in an Arazzo file.
    ```sh
    uvx oak-runner list-workflows <arazzo_path>
    ```
    -   `arazzo_path`: *Required*. Path to the Arazzo YAML file.

5.  **`describe-workflow`**: Show details of a specific workflow, including its summary, inputs, steps, and outputs.
    ```sh
    uvx oak-runner describe-workflow <arazzo_path> --workflow-id <workflow_id>
    ```
    -   `arazzo_path`: *Required*. Path to the Arazzo YAML file containing the workflow.
    -   `--workflow-id WORKFLOW_ID`: *Required*. ID of the workflow to describe.

6.  **`generate-example`**: Generate an example CLI command to execute a specified workflow, including placeholder inputs.
    ```sh
    uvx oak-runner generate-example <arazzo_path> --workflow-id <workflow_id>
    ```
    -   `arazzo_path`: *Required*. Path to the Arazzo YAML file containing the workflow.
    -   `--workflow-id WORKFLOW_ID`: *Required*. ID of the workflow to generate an example for.


**Global Options:**
- `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: Set the logging level (default: INFO).


**Examples:**

```sh
# Show environment variable mappings using an Arazzo file
uvx oak-runner show-env-mappings ./tests/fixtures/discord/discord.arazzo.yaml

# Show environment variable mappings using an OpenAPI file
uvx oak-runner show-env-mappings --openapi-path ./tests/fixtures/discord/discord.openapi.json

# Execute a workflow
uvx oak-runner execute-workflow ./tests/fixtures/discord/discord.arazzo.yaml --workflow-id getUserInfoAndSendMessage --inputs '{\"recipient_id\": \"1234567890\", \"message_content\": \"Hello!\"}'

# Execute a specific operation using its operationId and an OpenAPI file
uvx oak-runner execute-operation --openapi-path ./tests/fixtures/discord/discord.openapi.json --operation-id list_my_guilds --inputs '{}'

# Execute a specific operation using its path/method and an Arazzo file (for context)
uvx oak-runner execute-operation --arazzo-path ./tests/fixtures/discord/discord.arazzo.yaml --operation-path 'GET /users/@me/guilds' --inputs '{}' --log-level DEBUG

# List all available workflows
uvx oak-runner list-workflows ./tests/fixtures/discord/discord.arazzo.yaml

# Describe a specific workflow
uvx oak-runner describe-workflow ./tests/fixtures/discord/discord.arazzo.yaml --workflow-id getUserInfoAndSendMessage

# Generate an example CLI command to execute a workflow
uvx oak-runner generate-example ./tests/fixtures/discord/discord.arazzo.yaml --workflow-id getUserInfoAndSendMessage
```

**Help:**
```sh
# General help
uvx oak-runner --help

# Help for a specific command (e.g., execute-operation)
uvx oak-runner execute-operation --help
```

## Server URL Configuration

OAK Runner supports dynamic server URLs as defined in the `servers` object of an OpenAPI specification. This allows you to define API server URLs with templated variables (e.g., `https://{instance_id}.api.example.com/v1` or `https://api.example.com/{region}/users`).

### Variable Resolution

When an operation requires a server URL with variables, OAK Runner resolves these variables in the following order of precedence:

1.  **Runtime Parameters**: Values passed explicitly when executing an operation or workflow (e.g., via the `--server-variables` CLI argument or the `runtime_params` parameter in `execute_operation`/`execute_workflow` methods). These parameters should be provided as a dictionary where keys match the expected environment variable names for the server variables (see below).
2.  **Environment Variables**: If not provided as a runtime parameter, OAK Runner attempts to find an environment variable.
3.  **Default Values**: If not found in runtime parameters or environment variables, the `default` value specified for the variable in the OpenAPI document's `servers` object is used.

If a variable in the URL template cannot be resolved through any of these means, and it does not have a default value, an error will occur.

### Environment Variable Naming

The environment variables for server URLs follow these naming conventions:

-   If the OpenAPI specification's `info.title` is available and an `API_TITLE_PREFIX` can be derived from it (typically the first word of the title, uppercased and sanitized, e.g., `PETSTORE` from "Petstore API"), the format is:
    `[API_TITLE_PREFIX_]OAK_SERVER_<VAR_NAME_UPPERCASE>`
    Example: `PETSTORE_OAK_SERVER_REGION=us-east-1`

-   If an `API_TITLE_PREFIX` cannot be derived (e.g., `info.title` is missing or empty), the format is:
    `OAK_SERVER_<VAR_NAME_UPPERCASE>`
    Example: `OAK_SERVER_INSTANCE_ID=my-instance-123`

The `<VAR_NAME_UPPERCASE>` corresponds to the variable name defined in the `servers` object's `variables` map (e.g., `region` or `instance_id`), converted to uppercase.

You can use the `show-env-mappings` CLI command to see the expected environment variable names for server URLs, alongside authentication variables, for a given OpenAPI specification.

### Example

Consider an OpenAPI specification with:
- `info.title: "My Custom API"`
- A server definition:
  ```yaml
  servers:
    - url: "https://{instance}.api.example.com/{version}"
      variables:
        instance:
          default: "prod"
          description: "The API instance name."
        version:
          default: "v1"
          description: "API version."
  ```

To set the `instance` to "dev" and `version` to "v2" via environment variables, you would set:
```sh
export MYCUSTOM_OAK_SERVER_INSTANCE=dev
export MYCUSTOM_OAK_SERVER_VERSION=v2
```
(Assuming "MYCUSTOM" is derived from "My Custom API").

Alternatively, to provide these at runtime via the CLI when executing an operation:
```sh
uvx oak-runner execute-operation --openapi-path path/to/spec.yaml --operation-id someOperation \
  --server-variables '{"MYCUSTOM_OAK_SERVER_INSTANCE": "staging", "MYCUSTOM_OAK_SERVER_VERSION": "v2beta"}'
```


## Overview

OAK Runner orchestrates API workflows by:

- Loading and validating Arazzo workflow documents
- Executing workflow steps sequentially or conditionally
- Evaluating runtime expressions and success criteria
- Extracting and transforming data between steps
- Handling flow control (continue, goto, retry, end)
- Supporting nested workflow execution
- Providing event callbacks for workflow lifecycle events
- Managing authentication requirements across different APIs


## Testing

The OAK Runner includes a comprehensive testing framework for workflow validation:

- Automated test fixtures for different workflow scenarios
- Mock HTTP responses based on OpenAPI specs
- Custom mock responses for specific endpoints
- Validation of workflow outputs and API call counts

For details on testing, see [OAK Runner Testing Framework](./tests/README.md)

## Arazzo Format

The Arazzo specification is our workflow definition format that orchestrates API calls using OpenAPI specifications.

- Schema: [arazzo-schema.yaml](arazzo_spec/arazzo-schema.yaml)
- Documentation: [arazzo-spec.md](arazzo_spec/arazzo-spec.md)
