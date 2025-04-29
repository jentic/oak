"""Configuration management for the Jentic ARK² MCP Plugin."""

import os

from pydantic import BaseModel, Field


class MCPConfig(BaseModel):
    """MCP plugin configuration."""

    host: str = Field(default="127.0.0.1", description="Host to bind the server to")
    port: int = Field(default=8010, description="Port to serve the MCP plugin on")
    base_url: str = Field(
        default="http://localhost:8010",
        description="Base URL for the MCP plugin (used in the manifest)",
    )


class APIHubConfig(BaseModel):
    """API Knowledge Hub configuration."""

    url: str = Field(
        default="https://api.jenticlabs.com", description="URL of the Jentic API Knowledge Hub"
    )
    api_key: str | None = Field(
        default=None, description="API key for authenticating with the Jentic API Knowledge Hub"
    )
    search_server_url: str = Field(
        default="https://directory-api.qa1.eu-west-1.jenticdev.net",
        description="URL of the search server",
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(
        default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    file: str | None = Field(default=None, description="Path to log file (optional)")


class MockConfig(BaseModel):
    """Mock mode configuration."""

    enabled: bool = Field(
        default=False, description="Whether to use mock responses instead of real API calls"
    )
    mock_directory: str = Field(
        default="",  # This will be set dynamically in load_config()
        description="Directory containing mock response data",
    )


class Config(BaseModel):
    """Main configuration for the Jentic ARK² MCP Plugin."""

    mcp: MCPConfig = Field(default_factory=MCPConfig)
    api_hub: APIHubConfig = Field(default_factory=APIHubConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    mock: MockConfig = Field(default_factory=MockConfig)


def is_test_environment() -> bool:
    """Detect if we're running in a test environment.

    Returns:
        True if running in a test environment, False otherwise.
    """
    # Enhanced detection for test environments
    # Check if PYTEST_CURRENT_TEST is set OR if we're running pytest
    is_pytest_current_test = "PYTEST_CURRENT_TEST" in os.environ

    # Check sys.argv for pytest (helps with test collection phase)
    is_pytest_executable = False
    try:
        import sys

        is_pytest_executable = (
            any(arg.endswith("pytest") for arg in sys.argv) or "pytest" in sys.modules
        )
    except ImportError:
        pass

    # We're in a test environment if either condition is true
    return is_pytest_current_test or is_pytest_executable


def load_config() -> Config:
    """Load configuration from environment variables.

    Returns:
        Config object with the loaded configuration.
    """
    # Convert string to boolean for MOCK_ENABLED
    mock_enabled_str = os.environ.get("MOCK_ENABLED", "false").lower()
    mock_enabled = mock_enabled_str in ("true", "1", "yes", "y")

    # Set base directory based on test or production environment
    base_dir = ".test_output" if is_test_environment() else ".jentic"

    # Set default directories for data storage
    mock_data_dir = os.path.join(os.getcwd(), base_dir, "mock_data")

    # Allow override via environment variables
    mock_dir_env = os.environ.get("MOCK_DIRECTORY")
    if mock_dir_env:
        mock_data_dir = mock_dir_env

    return Config(
        mcp=MCPConfig(
            host=os.environ.get("MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("MCP_PORT", "8000")),
            base_url=os.environ.get("MCP_BASE_URL", "http://localhost:8000"),
        ),
        api_hub=APIHubConfig(
            url=os.environ.get("JENTIC_API_URL", "https://api.jenticlabs.com"),
            api_key=os.environ.get("JENTIC_API_KEY"),
            search_server_url=os.environ.get(
                "JENTIC_API_SERVER_URL", "https://directory-api.qa1.eu-west-1.jenticdev.net"
            ),
        ),
        logging=LoggingConfig(
            level=os.environ.get("LOG_LEVEL", "INFO"),
            file=os.environ.get("LOG_FILE"),
        ),
        mock=MockConfig(
            enabled=mock_enabled,
            mock_directory=mock_data_dir,
        ),
    )
