"""Search matching logic for the Jentic ARK² MCP Plugin."""

from typing import Any


class SearchMatcher:
    """Matcher for search queries against workflows."""

    def __init__(self):
        """Initialize the search matcher."""
        # Define standard keyword sets for different categories
        self.music_keywords = [
            "music",
            "song",
            "track",
            "audio",
            "play",
            "listen",
            "playlist",
            "spotify",
            "playback",
        ]
        self.message_keywords = ["message", "chat", "discord", "dm", "channel", "server", "guild"]
        self.comic_keywords = ["comic", "xkcd", "webcomic", "cartoon"]

    def calculate_match_scores(
        self, workflows: list[dict[str, Any]], query: str, keywords: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Calculate match scores for workflows based on the search query.

        Args:
            workflows: List of workflow summaries
            query: The search query string
            keywords: Optional list of keywords to match

        Returns:
            List of workflow summaries with updated match scores
        """
        if not workflows:
            return []

        # Prepare the query and keywords for matching
        query_lower = query.lower()
        keywords_lower = [k.lower() for k in keywords] if keywords else []

        print(
            f"Calculating match scores for {len(workflows)} workflows with query: '{query_lower}' and keywords: {keywords_lower}"
        )

        # Simple scoring system - could be enhanced with more sophisticated algorithms
        scored_workflows = []
        for workflow in workflows:
            score = 0.0
            workflow_id = workflow["workflow_id"]
            api_id = workflow["api_id"]

            # Match against summary and description
            summary_lower = workflow["summary"].lower()
            description_lower = workflow["description"].lower()

            # Also match against workflow_id because many queries might look for specific operations
            workflow_id_lower = workflow_id.lower()

            print(f"  Checking workflow: {workflow_id}")
            print(f"    Summary: {summary_lower}")
            print(f"    Description: {description_lower}")

            # Check for direct matches in workflow ID
            if any(kw in workflow_id_lower for kw in keywords_lower):
                score += 0.8
                print("    Keyword match in workflow_id: +0.8")

            # Check for workflow_id term matches in query
            if workflow_id_lower in query_lower:
                score += 0.9
                print("    Workflow ID match in query: +0.9")

            # Check for direct matches in summary
            if query_lower in summary_lower:
                score += 0.7
                print("    Query match in summary: +0.7")

            # Check for direct matches in description
            if query_lower in description_lower:
                score += 0.5
                print("    Query match in description: +0.5")

            # Check for keyword matches
            for keyword in keywords_lower:
                if keyword in summary_lower:
                    score += 0.3
                    print(f"    Keyword '{keyword}' in summary: +0.3")
                if keyword in description_lower:
                    score += 0.2
                    print(f"    Keyword '{keyword}' in description: +0.2")

            # Semantic matching for music-related queries
            if "spotify" in api_id.lower():
                # If it's a Spotify workflow, check if the query is music-related
                if any(kw in query_lower for kw in self.music_keywords):
                    score += 0.7
                    print("    Semantic match: music query + Spotify workflow: +0.7")

                # Special case for specific music-related workflows
                if "track" in workflow_id_lower and any(
                    kw in query_lower for kw in ["search", "find", "look for"]
                ):
                    score += 0.3
                    print("    Special case: track search workflow match: +0.3")

                if "music" in query_lower or "song" in query_lower or "playlist" in query_lower:
                    if "search" in workflow_id_lower:
                        score += 0.3
                        print("    Special case: music search match: +0.3")

            # Semantic matching for message-related queries
            if "discord" in api_id.lower():
                # If it's a Discord workflow, check if the query is message-related
                if any(kw in query_lower for kw in self.message_keywords):
                    score += 0.7
                    print("    Semantic match: message query + Discord workflow: +0.7")

                # Special case for specific messaging workflows
                if "message" in workflow_id_lower and (
                    "send" in query_lower or "post" in query_lower
                ):
                    score += 0.3
                    print("    Special case: send message workflow match: +0.3")

            # Semantic matching for comic-related queries
            if "xkcd" in api_id.lower():
                # If it's an XKCD workflow, check if the query is comic-related
                if any(kw in query_lower for kw in self.comic_keywords):
                    score += 0.7
                    print("    Semantic match: comic query + XKCD workflow: +0.7")

                # Special case for specific comic workflows
                if "current" in workflow_id_lower and "latest" in query_lower:
                    score += 0.3
                    print("    Special case: latest comic workflow match: +0.3")

            # Special case for exact API name matches
            if "spotify" in query_lower and "spotify" in api_id.lower():
                score += 0.4
                print("    API name match (spotify): +0.4")

            if "discord" in query_lower and "discord" in api_id.lower():
                score += 0.4
                print("    API name match (discord): +0.4")

            if "xkcd" in query_lower and "xkcd" in api_id.lower():
                score += 0.4
                print("    API name match (xkcd): +0.4")

            print(f"    Final score: {score}")

            # Only include if there's some match
            if score > 0:
                workflow_copy = workflow.copy()
                workflow_copy["match_score"] = min(0.95, score)  # Cap at 0.95
                scored_workflows.append(workflow_copy)

        print(f"Returning {len(scored_workflows)} matched workflows")
        return scored_workflows

    def boost_api_score(self, api_id: str, query: str) -> float:
        """Apply boosting for specific API + query combinations.

        Args:
            api_id: The API ID
            query: The search query

        Returns:
            The boosted score value
        """
        query_lower = query.lower()

        # Boost for XKCD + comic-related queries
        if "xkcd" in api_id.lower() and any(kw in query_lower for kw in self.comic_keywords):
            return 0.98  # Higher than the openweathermap score

        # Boost for Spotify + music-related queries
        elif "spotify" in api_id.lower() and any(kw in query_lower for kw in self.music_keywords):
            return 0.98

        # Boost for Discord + message-related queries
        elif "discord" in api_id.lower() and any(kw in query_lower for kw in self.message_keywords):
            return 0.98

        # Default score
        return 0.95

    def get_api_details(self, api_id: str) -> dict[str, Any]:
        """Get API display details based on API ID.

        Args:
            api_id: The API ID

        Returns:
            Dictionary with API display details
        """
        if "spotify" in api_id.lower():
            return {
                "display_name": "Spotify",
                "description": "Spotify Web API for searching and managing music, tracks, playlists, and more",
                "categories": ["music", "entertainment", "streaming"],
            }
        elif "discord" in api_id.lower():
            return {
                "display_name": "Discord",
                "description": "Discord API for messaging, user management, and server interactions",
                "categories": ["communication", "messaging", "social"],
            }
        elif "xkcd" in api_id.lower():
            return {
                "display_name": "XKCD",
                "description": "Comic data from XKCD, a webcomic of romance, sarcasm, math, and language",
                "categories": ["comics", "entertainment"],
            }
        else:
            # Default for unknown APIs
            api_name = api_id.split("-")[0].title()
            return {
                "display_name": api_name,
                "description": f"API for {api_id.split('-')[0]} related functionality",
                "categories": [api_id.split("-")[0]],
            }
