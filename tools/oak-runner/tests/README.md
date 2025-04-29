# OAK Runner Testing Framework

This directory contains an automated test framework for Arazzo workflows. The framework enables testing of Arazzo workflows by automatically discovering test fixtures and supports both mock responses and real API calls.

## Overview

The test framework automatically discovers test fixtures in the `fixtures` directory and generates test cases for each fixture. Each test fixture consists of Arazzo workflow specs, OpenAPI specs, and a test configuration file.

The framework supports:
- Automatic test discovery and execution
- Mock HTTP responses based on OpenAPI specs
- Real HTTP mode for actual API calls
- Authentication detection and application
- Custom mock responses for specific API endpoints
- Validation of workflow outputs and API call counts
- Testing of both success and failure scenarios
- Parameter name mapping between workflows and API specs
- Normalized path handling for flexible URL matching

## Directory Structure

- **base_test.py**: Base test class with common utilities
- **test_fixture_discovery.py**: Discovers and runs tests for all fixtures
- **run_real_tests.py**: Script for running tests in real mode
- **mocks/**: HTTP clients and related utilities
  - **http_client.py**: Base HTTP client interface
  - **openapi_mocker.py**: Generates mock responses from OpenAPI specs
  - **real_http_client.py**: Client for making real API calls with authentication
- **fixtures/**: Test fixtures for various scenarios
  - **sample_test/**: A simple echo API test
  - **sample_login_workflow/**: Authentication and profile workflow test
  - **pet_coupons/**: Pet store workflow with parameter mapping
  - **xkcd/**: XKCD comic API with real mode support
  - **discord/**: Discord API with authentication example

## Creating Test Fixtures

A test fixture consists of:

1. **Arazzo Workflow Spec(s)**: YAML file(s) defining the workflow(s) to test
2. **OpenAPI Spec(s)**: YAML/JSON file(s) defining the API operations
3. **test_config.yaml**: Configuration for the test

To create a new test fixture:

1. Create a new subdirectory in the `fixtures` directory
2. Add your Arazzo workflow spec(s) to the directory
3. Add your OpenAPI spec(s) to the directory
4. Create a `test_config.yaml` file with your test configuration

### Test Configuration Format

The `test_config.yaml` file has the following structure:

```yaml
# Global success rate for API operations (1.0 = 100% success)
success_rate: 1.0

# Custom base URLs for API specs (optional)
base_urls:
  api_name: https://api.example.com/v1

# Real mode configuration
real_mode:
  timeout: 30  # API call timeout in seconds
  
# Authentication values for real mode
auth_values:
  apiKey: "your-api-key-here"
  Authorization: "Bearer your-token-here"

# Custom mocks for specific operations
custom_mocks:
  api_name:
    - path: https://api.example.com/v1/endpoint
      method: post
      status_code: 200
      response:
        key: value

# Test workflows with specific inputs and expected outputs
workflows:
  - id: workflowId
    arazzo_spec: workflow.yaml  # Relative path within fixture directory
    inputs:
      key: value
    expect_success: true  # Whether the workflow should succeed or fail
    expected_outputs:
      key: value  # Expected output values
    expected_api_calls: 1  # Expected number of API calls
    
    # Real mode specific configuration
    real_mode:
      # Override inputs for real mode
      params:
        key: real-value
      # Workflow-specific auth values
      auth_values:
        apiKey: "workflow-specific-key"
        
    # Custom mocks for just this workflow
    custom_mocks:
      - path: https://api.example.com/v1/endpoint
        method: post
        status_code: 200
        response:
          key: value
```

## Mock Response Generation

The framework generates mock responses in two ways:

1. **Schema-based generation**: Automatically creates responses based on OpenAPI schema definitions:
   - Creates objects with appropriate properties based on schema types
   - Handles nested objects and arrays
   - Supports common formats (date-time, UUID, email)

2. **Custom mocks**: Explicitly defined mock responses in the test configuration:
   - Global custom mocks apply to all workflows
   - Workflow-specific custom mocks override global mocks
   - Support different status codes for testing error scenarios

## URL and Parameter Handling

The framework includes flexible request matching for API calls:

1. **URL Path Normalization**:
   - Handles API version prefixes (`/api/v3/resource`, `/v2/resource`)
   - Supports both absolute and relative URLs
   - Removes trailing slashes for consistent matching

2. **Parameter Name Mapping**:
   - Maps parameter names between workflow definitions and API specs
   - Handles known parameter equivalences (e.g., `tags` ↔ `pet_tags`)
   - Supports different array serialization formats

## Running Tests

### Mock Mode (Default)

To run all fixtures tests in mock mode:

```bash
pdm run test
# or specifically
pdm run pytest src/tests/oak_runner/test_fixture_discovery.py
```

To run tests for a specific fixture:

```bash
pdm run pytest src/tests/oak_runner/test_fixture_discovery.py::Test_fixture_name::test_workflows
```

For example, to run just the pet coupons workflow tests:

```bash
pdm run pytest src/tests/oak_runner/test_fixture_discovery.py::Test_pet_coupons::test_workflows
```

### Real Mode

To run tests in real mode (making actual API calls):

```bash
# Run all real mode tests
pdm run test-real

# List available real-mode fixtures and workflows
pdm run test-real --list

# Run real tests for a specific fixture
pdm run test-real --fixture xkcd

# Run a specific workflow in real mode
pdm run test-real --fixture xkcd --workflow getCurrentComic

# Run with verbose output
pdm run test-real --verbose

# Run with debug logging
pdm run test-real --debug
```

Real mode tests are only run when explicitly requested through the command line. Even if a fixture has real mode configuration, it won't run in real mode during regular test runs.

## Important Notes

1. **URL Patterns**: When defining mocks, use full URL patterns, but know that the framework handles normalization of paths.

2. **Arazzo Expression Syntax**:
   - For step output references, use `$steps.stepId.outputName` (NOT `$steps.stepId.outputs.outputName`)
   - For input references, use `$inputs.inputName`
   - For response references, use `$response.body.fieldName`
   - For status code references, use `$statusCode`

3. **Workflow Inputs**: In test configuration, you can use either `inputs` or `params` field to provide inputs to workflows.

4. **Mock Responses**: Ensure mock responses include all fields that are referenced in output extractors. Simplified responses with just the needed fields are preferred.

5. **Path Parameters**: For operations with path parameters, make sure to:
   - Include the correct path parameter name in the mocks (e.g., `/channels/{channel_id}/messages`)
   - Add additional fallback mocks with wildcard path parameters if needed (e.g., `/channels/{channel_id}/messages`)
   - Ensure the path parameter value in the workflow matches the mock URL pattern

6. **Success/Failure Testing**: Use `expect_success: false` to test failure scenarios, and configure mocks with appropriate error status codes.

7. **Custom Mocks Priority**: Custom mocks defined at the workflow level take precedence over global mocks. Define the most specific mocks at the workflow level.

8. **Parameter Name Variations**: The framework automatically handles many parameter name variations (e.g., snake_case vs. camelCase), but for custom mappings, update the parameter name maps in the RequestMatcher implementation.

9. **Output Verification**: When testing expected outputs, make sure to use the correct path or name that will be present in the workflow results. You can use flattened paths like `stepId.output_name`.

10. **Authentication Setup**:
    - Authentication requirements are automatically detected from OpenAPI security schemes
    - For real mode tests, provide the required auth values in the `auth_values` section of test_config.yaml
    - For workflow-specific auth, use the `real_mode.auth_values` section in the workflow configuration

11. **Real Mode Parameters**:
    - Use `real_mode.params` in a workflow to override inputs for real API calls
    - Real mode parameters completely override the default inputs when testing in real mode
    - Keep sensitive parameters like API keys out of the repository by using placeholders
