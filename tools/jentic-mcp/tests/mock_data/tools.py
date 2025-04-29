"""Langchain tools for accessing API functionality."""

import asyncio
from typing import Any

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from .api_client import SpotifyClient


class SpotifyMusicSearchInput(BaseModel):
    """Input for Spotify music search."""

    query: str = Field(..., description="The search query for finding music")
    type: str = Field(default="track", description="Type of search (track, album, artist)")


class SpotifyMusicSearchTool(BaseTool):
    """Tool for searching Spotify music."""

    name = "spotify_music_search"
    description = "Search for music on Spotify by track, album, or artist"
    args_schema = SpotifyMusicSearchInput

    def __init__(self, spotify_client: SpotifyClient):
        """Initialize the tool with a Spotify client."""
        super().__init__()
        self.client = spotify_client

    def _run(self, query: str, type: str = "track") -> dict[str, Any]:
        """Run the tool synchronously."""
        return asyncio.run(self._arun(query, type))

    async def _arun(self, query: str, type: str = "track") -> dict[str, Any]:
        """Run the search asynchronously.

        Args:
            query: Search query
            type: Type of search

        Returns:
            Search results
        """
        results = await self.client.search(query, type)
        return results


class SpotifyPlaylistsTool(BaseTool):
    """Tool for accessing Spotify playlists."""

    name = "spotify_playlists"
    description = "Get user's Spotify playlists"

    def __init__(self, spotify_client: SpotifyClient):
        """Initialize the tool with a Spotify client."""
        super().__init__()
        self.client = spotify_client

    def _run(self) -> dict[str, Any]:
        """Run the tool synchronously."""
        return asyncio.run(self._arun())

    async def _arun(self) -> dict[str, Any]:
        """Get playlists asynchronously.

        Returns:
            Dictionary of playlists
        """
        results = await self.client.get_playlists()
        return results
