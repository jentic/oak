"""Version information for the ARK² MCP Plugin."""

import datetime

from mcp import __version__


def get_version_info() -> dict[str, str]:
    """Get version information for the ARK² MCP Plugin.

    Returns:
        Dict[str, str]: Version information including version number and build date.
    """
    return {
        "version": __version__,
        "build_date": datetime.datetime.now().strftime("%Y-%m-%d"),
    }
