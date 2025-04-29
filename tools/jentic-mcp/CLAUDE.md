# Jentic Project Development Guide

## Working with jentic-mcp

### Code Modification Guidelines
- **Clean Refactoring**: When modifying code, DO NOT leave compatibility layers, stubs, or comments about what the code used to look like. Make changes directly without preserving deprecated functionality.
- **Don't Auto-Run Linting**: Don't automatically run linting tools unless specifically requested by the user.

### Build & Test Commands for jentic-mcp
- Install dependencies: `pdm install`
- Run all tests: `pdm run test`
- Run specific test: `pdm run test tests/test_tools.py`
- Run linters: `pdm run lint` (includes black, isort, ruff, mypy)
- Run MCP HTTP server: `pdm run mcp-http`
- Run MCP stdio mode: `pdm run mcp-stdio` (Note: Use only for ad hoc testing)
- Run with mock data: `pdm run mcp-mock-http`, `pdm run mcp-mock-stdio`
- Run with debug stdio: `pdm run mcp-debug-stdio`
- Run with debug logging: `pdm run mcp serve --transport http --log-level DEBUG`
- Log to file: `pdm run mcp serve --transport http --log-file jentic_mcp.log`

### Testing MCP Commands
When testing MCP functionality from the command line, use the following format:

```bash
# For stdio mode (MCP format)
echo '{"type": "search_apis", "data": {"capability_description": "spotify music"}}' | pdm run mcp-mock-stdio

# For search examples
echo '{"type": "search_apis", "data": {"capability_description": "xkcd comic"}}' | pdm run mcp-mock-stdio
echo '{"type": "search_apis", "data": {"capability_description": "spotify music"}}' | pdm run mcp-mock-stdio
echo '{"type": "search_apis", "data": {"capability_description": "discord message"}}' | pdm run mcp-mock-stdio
```

Always use mock mode for testing to avoid dependency on external services.

### Running Integration Tests

For running the integration tests that combine real API and MCP.

```bash
# Run real integration test to generate test data
pdm run test-real-integration
```

#### How Integration Tests Work

The integration tests verify the full workflow processing pipeline:

1. **Real Integration Test (`test-real-integration`):**
   - Executes `scripts/run_real_integration_test.py`
   - Searches for API capabilities (Spotify, Discord) using the MCP
   - Creates selection sets and generates configuration
   - The output is stored in `.test_output/integration_test/` directory

2. **Important Notes on Workflow Dependencies:**
   - Auth workflows like `getSpotifyToken` should never be executed directly in tests
   - Workflows with `dependsOn` property will automatically execute their dependencies
   - Always ensure environment variables are set correctly for auth credentials
   - For Spotify tests: `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`

### jentic-mcp Structure
- `src/mcp/`: Main MCP package (tools, handlers, transports)
- `src/mcp/adapters/`: Adapter implementations
- `src/mcp/core/`: Core functionality (API hub, code generator)
- `tests/`: Test suite

## Code Style Guidelines
- Python version: 3.10+
- Line length: 100 characters
- Strict typing: Required for all functions (disallow_untyped_defs=true)
- Imports: Use isort with black profile (sorted alphabetically)
- Formatting: Use black for consistent code style
- Linting: ruff (E, F, B, W, I, N, UP, YTT, S rules)
- Type checking: mypy with strict settings (no_implicit_optional=true, strict_optional=true)
- Documentation: Triple double-quotes for docstrings
- Naming: snake_case for variables/functions, PascalCase for classes
- Error handling: Prefer explicit error handling with typed exceptions
- File size: Files should not exceed 600 lines. If they do, consider splitting them into logical components
  - Splitting strategy: Extract cohesive functionality into separate modules
  - Aim for single responsibility per module when refactoring large files
