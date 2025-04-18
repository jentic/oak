## Core Components

### OAKRunner (runner.py)

The main orchestrator that:
- Manages workflow execution state
- Walks through workflow steps
- Handles inputs and outputs
- Processes success/failure actions
- Implements flow control based on step results
- Provides access to authentication environment mappings

### StepExecutor (executor.py)

Executes individual workflow steps by:
- Resolving operations by ID or path
- Preparing parameters and request bodies
- Making HTTP requests to APIs
- Evaluating success criteria
- Extracting outputs from responses

### ExpressionEvaluator (evaluator.py)

Resolves dynamic expressions in workflows:
- Evaluates runtime expressions in context
- Supports dot notation for object properties
- Handles array indexing
- Processes object/array expressions
- Evaluates conditions and criteria

### HTTPExecutor (http.py)

Handles API communication:
- Makes HTTP requests to external APIs
- Handles parameters, headers, cookies
- Processes different content types
- Parses API responses
- Applies authentication based on security requirements

### Authentication (auth/)

Manages API authentication:
- Extracts authentication requirements from OpenAPI specs
- Supports various authentication types (API Key, OAuth2, HTTP Basic/Bearer)
- Generates environment variable mappings for credentials
- Resolves credentials from environment variables
- Applies authentication to API requests

### Models (models.py)

Defines data structures for the runner:
- ExecutionState for tracking workflow state
- StepStatus enum for step execution status
- ActionType enum for flow control actions