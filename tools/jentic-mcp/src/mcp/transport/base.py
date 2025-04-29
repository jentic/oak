"""Base transport layer for the ARK² MCP Plugin."""

import abc


class BaseTransport(abc.ABC):
    """Base class for transport implementations."""

    @abc.abstractmethod
    async def start(self) -> None:
        """Start the transport server/listener.

        This method should initialize and start the transport mechanism.
        For HTTP, this would start the web server.
        For stdio, this would start reading from stdin.
        """
        pass

    @abc.abstractmethod
    async def stop(self) -> None:
        """Stop the transport server/listener.

        This method should gracefully shut down the transport mechanism.
        """
        pass

    @property
    @abc.abstractmethod
    def is_running(self) -> bool:
        """Check if the transport is currently running."""
        pass
