"""API Client for interacting with the Spotify Music API."""

from typing import Any

import httpx


class SpotifyClient:
    """Client for interacting with the Spotify Music API."""

    def __init__(self, auth_token: str):
        """Initialize with authentication token.

        Args:
            auth_token: OAuth token for API access
        """
        self.base_url = "https://api.spotify.com/v1"
        self.headers = {"Authorization": f"Bearer {auth_token}"}

    async def search(self, query: str, type: str = "track") -> dict[str, Any]:
        """Search for tracks, albums, or artists.

        Args:
            query: Search query
            type: Type of search (track, album, artist)

        Returns:
            Search results
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/search", headers=self.headers, params={"q": query, "type": type}
            )
            response.raise_for_status()
            return response.json()

    async def get_playlists(self) -> dict[str, Any]:
        """Get user's playlists.

        Returns:
            Dictionary of playlists
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/me/playlists", headers=self.headers)
            response.raise_for_status()
            return response.json()
