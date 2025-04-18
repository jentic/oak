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
pdm run python -m oak_runner <command> [command-specific arguments] [global options]
```

**Commands:**

1.  **`show-env-mappings`**: Show environment variable mappings for authentication based on an Arazzo or OpenAPI file.
    ```sh
    pdm run python -m oak_runner show-env-mappings [arazzo_path | --openapi-path PATH]
    ```
    -   `arazzo_path`: Path to the Arazzo YAML file (use this OR --openapi-path).
    -   `--openapi-path PATH`: Path to the OpenAPI spec file (use this OR arazzo_path).
    *One of the path arguments is required.*

2.  **`execute-workflow`**: Execute a workflow defined in an Arazzo file.
    ```sh
    pdm run python -m oak_runner execute-workflow <arazzo_path> --workflow-id <workflow_id> [--inputs <json_string>]
    ```
    -   `arazzo_path`: *Required*. Path to the Arazzo YAML file containing the workflow.
    -   `--workflow-id WORKFLOW_ID`: *Required*. ID of the workflow to execute.
    -   `--inputs INPUTS`: Optional JSON string of workflow inputs (default: `{}`).

3.  **`execute-operation`**: Execute a single API operation directly from an OpenAPI specification (or an Arazzo file for context).
    ```sh
    pdm run python -m oak_runner execute-operation [--arazzo-path PATH | --openapi-path PATH] [--operation-id ID | --operation-path PATH_METHOD] [--inputs <json_string>]
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
    pdm run python -m oak_runner list-workflows <arazzo_path>
    ```
    -   `arazzo_path`: *Required*. Path to the Arazzo YAML file.

5.  **`describe-workflow`**: Show details of a specific workflow, including its summary, inputs, steps, and outputs.
    ```sh
    pdm run python -m oak_runner describe-workflow <arazzo_path> --workflow-id <workflow_id>
    ```
    -   `arazzo_path`: *Required*. Path to the Arazzo YAML file containing the workflow.
    -   `--workflow-id WORKFLOW_ID`: *Required*. ID of the workflow to describe.

6.  **`generate-example`**: Generate an example CLI command to execute a specified workflow, including placeholder inputs.
    ```sh
    pdm run python -m oak_runner generate-example <arazzo_path> --workflow-id <workflow_id>
    ```
    -   `arazzo_path`: *Required*. Path to the Arazzo YAML file containing the workflow.
    -   `--workflow-id WORKFLOW_ID`: *Required*. ID of the workflow to generate an example for.


**Global Options:**
- `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: Set the logging level (default: INFO).


**Examples:**

```sh
# Show environment variable mappings using an Arazzo file
pdm run python -m oak_runner show-env-mappings ./tests/fixtures/discord/discord.arazzo.yaml

# Show environment variable mappings using an OpenAPI file
pdm run python -m oak_runner show-env-mappings --openapi-path ./tests/fixtures/discord/discord.openapi.json

# Execute a workflow
pdm run python -m oak_runner execute-workflow ./tests/fixtures/discord/discord.arazzo.yaml --workflow-id getUserInfoAndSendMessage --inputs '{\"recipient_id\": \"1234567890\", \"message_content\": \"Hello!\"}'

# Execute a specific operation using its operationId and an OpenAPI file
pdm run python -m oak_runner execute-operation --openapi-path ./tests/fixtures/discord/discord.openapi.json --operation-id list_my_guilds --inputs '{}'

# Execute a specific operation using its path/method and an Arazzo file (for context)
pdm run python -m oak_runner execute-operation --arazzo-path ./tests/fixtures/discord/discord.arazzo.yaml --operation-path 'GET /users/@me/guilds' --inputs '{}' --log-level DEBUG

# List all available workflows
pdm run python -m oak_runner list-workflows ./tests/fixtures/discord/discord.arazzo.yaml

# Describe a specific workflow
pdm run python -m oak_runner describe-workflow ./tests/fixtures/discord/discord.arazzo.yaml --workflow-id getUserInfoAndSendMessage

# Generate an example CLI command to execute a workflow
pdm run python -m oak_runner generate-example ./tests/fixtures/discord/discord.arazzo.yaml --workflow-id getUserInfoAndSendMessage
```

**Help:**
```sh
# General help
pdm run python -m oak_runner --help

# Help for a specific command (e.g., execute-operation)
pdm run python -m oak_runner execute-operation --help
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
