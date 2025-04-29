"""Mock data generator for the Jentic ARK² MCP Plugin."""

import json
import os
from pathlib import Path


class MockDataGenerator:
    """Generator for default mock data."""

    def ensure_mock_data_exists(self, mock_directory: str) -> None:
        """Ensure that mock data directory and basic mock responses exist.

        Args:
            mock_directory: Directory to store mock data
        """
        mock_dir = Path(mock_directory)
        os.makedirs(mock_dir, exist_ok=True)

        # Create mock search response if it doesn't exist
        search_response_path = mock_dir / "search_api_capabilities.json"
        if not search_response_path.exists():
            self._create_default_search_response(search_response_path)

        # Create mock details response if it doesn't exist
        details_response_path = mock_dir / "get_api_details.json"
        if not details_response_path.exists():
            self._create_default_details_response(details_response_path)

        # Create mock runtime response if it doesn't exist
        runtime_response_path = mock_dir / "generate_runtime.json"
        if not runtime_response_path.exists():
            self._create_default_runtime_response(runtime_response_path)

        # Create mock prompt library response if it doesn't exist
        prompt_response_path = mock_dir / "generate_prompt_library.json"
        if not prompt_response_path.exists():
            self._create_default_prompt_library_response(prompt_response_path)

    def _create_default_search_response(self, path: Path) -> None:
        """Create a default mock search response.

        Args:
            path: Path to save the response
        """
        mock_search_response = [
            {
                "api_id": "openweathermap-v2",
                "api_name": "OpenWeatherMap API",
                "api_description": "Provides current weather data, forecasts, and historical data for any location on Earth",
                "version": "2.5",
                "capability_match_score": 0.95,
                "auth_methods": ["api_key"],
                "categories": ["weather", "geolocation"],
            },
            {
                "api_id": "sendgrid-v3",
                "api_name": "SendGrid API",
                "api_description": "Email delivery service for sending transactional and marketing emails",
                "version": "3.0",
                "capability_match_score": 0.92,
                "auth_methods": ["api_key"],
                "categories": ["email", "marketing"],
            },
            {
                "api_id": "stripe-v1",
                "api_name": "Stripe API",
                "api_description": "Payment processing platform for online businesses",
                "version": "1.0",
                "capability_match_score": 0.88,
                "auth_methods": ["api_key", "oauth"],
                "categories": ["payments", "financial"],
            },
            {
                "api_id": "discord-v1",
                "api_name": "Discord API",
                "api_description": "API for building bots, integrations, and applications for Discord",
                "version": "1.0",
                "capability_match_score": 0.85,
                "auth_methods": ["oauth", "bot_token"],
                "categories": ["messaging", "social", "gaming"],
            },
        ]

        with open(path, "w") as f:
            json.dump(mock_search_response, f, indent=2)

    def _create_default_details_response(self, path: Path) -> None:
        """Create a default mock details response.

        Args:
            path: Path to save the response
        """
        mock_details_response = {
            "openweathermap-v2": {
                "api_id": "openweathermap-v2",
                "name": "OpenWeatherMap API",
                "description": "Provides current weather data, forecasts, and historical data for any location on Earth",
                "version": "2.5",
                "base_url": "https://api.openweathermap.org/data/2.5",
                "auth_methods": [
                    {
                        "type": "api_key",
                        "location": "query",
                        "parameter_name": "appid",
                        "description": "API key obtained from OpenWeatherMap",
                    }
                ],
                "endpoints": {
                    "get_current_weather": {
                        "path": "/weather",
                        "method": "GET",
                        "description": "Current weather data for a specific location",
                        "parameters": {
                            "q": {
                                "type": "string",
                                "description": "City name, state code and country code separated by comma",
                                "required": False,
                                "in": "query",
                                "example": "London,uk",
                            },
                            "lat": {
                                "type": "number",
                                "description": "Latitude coordinate",
                                "required": False,
                                "in": "query",
                                "example": 51.51,
                            },
                            "lon": {
                                "type": "number",
                                "description": "Longitude coordinate",
                                "required": False,
                                "in": "query",
                                "example": -0.13,
                            },
                            "units": {
                                "type": "string",
                                "description": "Units of measurement (standard, metric, imperial)",
                                "required": False,
                                "in": "query",
                                "example": "metric",
                            },
                        },
                    },
                    "get_forecast": {
                        "path": "/forecast",
                        "method": "GET",
                        "description": "5 day forecast with data every 3 hours",
                        "parameters": {
                            "q": {
                                "type": "string",
                                "description": "City name, state code and country code separated by comma",
                                "required": False,
                                "in": "query",
                                "example": "London,uk",
                            },
                            "lat": {
                                "type": "number",
                                "description": "Latitude coordinate",
                                "required": False,
                                "in": "query",
                                "example": 51.51,
                            },
                            "lon": {
                                "type": "number",
                                "description": "Longitude coordinate",
                                "required": False,
                                "in": "query",
                                "example": -0.13,
                            },
                            "units": {
                                "type": "string",
                                "description": "Units of measurement (standard, metric, imperial)",
                                "required": False,
                                "in": "query",
                                "example": "metric",
                            },
                        },
                    },
                },
                "data_models": {
                    "WeatherResponse": {
                        "type": "object",
                        "properties": {
                            "weather": {
                                "type": "array",
                                "description": "Weather condition details",
                            },
                            "main": {"type": "object", "description": "Main weather parameters"},
                            "wind": {"type": "object", "description": "Wind information"},
                            "clouds": {"type": "object", "description": "Cloud information"},
                            "rain": {
                                "type": "object",
                                "description": "Rain information (if applicable)",
                            },
                            "snow": {
                                "type": "object",
                                "description": "Snow information (if applicable)",
                            },
                            "dt": {
                                "type": "integer",
                                "description": "Time of data calculation, unix, UTC",
                            },
                            "sys": {"type": "object", "description": "System parameters"},
                            "timezone": {
                                "type": "integer",
                                "description": "Shift in seconds from UTC",
                            },
                            "id": {"type": "integer", "description": "City ID"},
                            "name": {"type": "string", "description": "City name"},
                        },
                    }
                },
            },
            "discord-v1": {
                "api_id": "discord-v1",
                "name": "Discord API",
                "description": "API for interacting with Discord servers, channels, users, and messages",
                "version": "1.0",
                "base_url": "https://discord.com/api/v10",
                "auth_methods": [
                    {
                        "type": "bearer",
                        "location": "header",
                        "parameter_name": "Authorization",
                        "description": "Bot token obtained from Discord Developer Portal",
                    }
                ],
                "endpoints": {
                    "post_channel_message": {
                        "path": "/channels/{channel_id}/messages",
                        "method": "POST",
                        "description": "Send a message to a channel",
                        "parameters": {
                            "channel_id": {
                                "type": "string",
                                "description": "The ID of the channel",
                                "required": True,
                                "in": "path",
                            },
                            "content": {
                                "type": "string",
                                "description": "The message contents",
                                "required": True,
                                "in": "body",
                            },
                            "tts": {
                                "type": "boolean",
                                "description": "Whether this is a TTS message",
                                "required": False,
                                "in": "body",
                            },
                        },
                    },
                    "get_channel": {
                        "path": "/channels/{channel_id}",
                        "method": "GET",
                        "description": "Get a channel by ID",
                        "parameters": {
                            "channel_id": {
                                "type": "string",
                                "description": "The ID of the channel",
                                "required": True,
                                "in": "path",
                            },
                        },
                    },
                },
                "files": [
                    {
                        "filename": "discord.arazzo.json",
                        "content": {
                            "workflows": [
                                {
                                    "workflowId": "postChannelMessage",
                                    "description": "Send a message to a Discord channel",
                                    "inputs": {
                                        "properties": {
                                            "channel_id": {
                                                "type": "string",
                                                "description": "The ID of the channel to send the message to",
                                            },
                                            "message": {
                                                "type": "string",
                                                "description": "The message content to send",
                                            },
                                        },
                                        "required": ["channel_id", "message"],
                                    },
                                    "steps": [
                                        {
                                            "id": "sendMessage",
                                            "operation": {
                                                "path": "/channels/{channel_id}/messages",
                                                "method": "POST",
                                            },
                                            "parameters": {
                                                "channel_id": "$inputs.channel_id",
                                                "content": "$inputs.message",
                                            },
                                        }
                                    ],
                                    "output": "$steps.sendMessage",
                                }
                            ]
                        },
                    },
                    {
                        "filename": "discord.openapi.json",
                        "content": {
                            "openapi": "3.0.0",
                            "info": {"title": "Discord API", "version": "1.0.0"},
                            "paths": {
                                "/channels/{channel_id}/messages": {
                                    "post": {
                                        "summary": "Send a message to a channel",
                                        "parameters": [
                                            {
                                                "name": "channel_id",
                                                "in": "path",
                                                "required": True,
                                                "schema": {"type": "string"},
                                            }
                                        ],
                                        "requestBody": {
                                            "content": {
                                                "application/json": {
                                                    "schema": {
                                                        "type": "object",
                                                        "properties": {
                                                            "content": {"type": "string"}
                                                        },
                                                    }
                                                }
                                            }
                                        },
                                    }
                                }
                            },
                        },
                    },
                ],
                "data_models": {
                    "Message": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "The ID of the message"},
                            "channel_id": {
                                "type": "string",
                                "description": "The ID of the channel",
                            },
                            "content": {"type": "string", "description": "The message content"},
                            "author": {
                                "type": "object",
                                "description": "The author of the message",
                            },
                            "timestamp": {
                                "type": "string",
                                "description": "When the message was sent",
                            },
                        },
                    }
                },
            },
        }

        with open(path, "w") as f:
            json.dump(mock_details_response, f, indent=2)

    def _create_default_runtime_response(self, path: Path) -> None:
        """Create a default mock runtime response.

        Args:
            path: Path to save the response
        """
        mock_runtime_response = {
            "openweathermap_tool.py": '# Generated OpenWeatherMap API Tool\n\nfrom langchain.tools import BaseTool\nimport requests\n\nclass OpenWeatherMapTool(BaseTool):\n    name = "openweathermap"\n    description = "Tool for accessing OpenWeatherMap API"\n    \n    def __init__(self, api_key):\n        self.api_key = api_key\n        self.base_url = "https://api.openweathermap.org/data/2.5"\n        super().__init__()\n    \n    def _run(self, action, **kwargs):\n        if action == "get_current_weather":\n            return self._get_current_weather(**kwargs)\n        elif action == "get_forecast":\n            return self._get_forecast(**kwargs)\n        else:\n            return {"error": f"Unknown action: {action}"}\n    \n    def _get_current_weather(self, city=None, lat=None, lon=None, units="metric"):\n        params = {"appid": self.api_key, "units": units}\n        if city:\n            params["q"] = city\n        elif lat is not None and lon is not None:\n            params["lat"] = lat\n            params["lon"] = lon\n        else:\n            return {"error": "Either city or lat/lon must be provided"}\n        \n        response = requests.get(f"{self.base_url}/weather", params=params)\n        response.raise_for_status()\n        return response.json()\n    \n    def _get_forecast(self, city=None, lat=None, lon=None, units="metric"):\n        params = {"appid": self.api_key, "units": units}\n        if city:\n            params["q"] = city\n        elif lat is not None and lon is not None:\n            params["lat"] = lat\n            params["lon"] = lon\n        else:\n            return {"error": "Either city or lat/lon must be provided"}\n        \n        response = requests.get(f"{self.base_url}/forecast", params=params)\n        response.raise_for_status()\n        return response.json()',
            "openweathermap_client.py": '# Generated OpenWeatherMap API Client\n\nimport requests\n\nclass OpenWeatherMapClient:\n    def __init__(self, api_key):\n        self.api_key = api_key\n        self.base_url = "https://api.openweathermap.org/data/2.5"\n    \n    def get_current_weather(self, city=None, lat=None, lon=None, units="metric"):\n        params = {"appid": self.api_key, "units": units}\n        if city:\n            params["q"] = city\n        elif lat is not None and lon is not None:\n            params["lat"] = lat\n            params["lon"] = lon\n        else:\n            raise ValueError("Either city or lat/lon must be provided")\n        \n        response = requests.get(f"{self.base_url}/weather", params=params)\n        response.raise_for_status()\n        return response.json()\n    \n    def get_forecast(self, city=None, lat=None, lon=None, units="metric"):\n        params = {"appid": self.api_key, "units": units}\n        if city:\n            params["q"] = city\n        elif lat is not None and lon is not None:\n            params["lat"] = lat\n            params["lon"] = lon\n        else:\n            raise ValueError("Either city or lat/lon must be provided")\n        \n        response = requests.get(f"{self.base_url}/forecast", params=params)\n        response.raise_for_status()\n        return response.json()',
        }

        with open(path, "w") as f:
            json.dump(mock_runtime_response, f, indent=2)

    def _create_default_prompt_library_response(self, path: Path) -> None:
        """Create a default mock prompt library response.

        Args:
            path: Path to save the response
        """
        mock_prompt_library_response = {
            "system_prompt": "You have access to the OpenWeatherMap API, which provides weather data including current weather, forecasts, and historical data.\n\nAPI Base URL: https://api.openweathermap.org/data/2.5\n\nAvailable Endpoints:\n\n1. /weather - Get current weather data\n   - Parameters:\n     - q: City name (required if lat/lon not provided)\n     - lat/lon: Coordinates (required if q not provided)\n     - units: Unit system (standard, metric, imperial)\n     - appid: API key (required)\n\n2. /forecast - Get 5-day forecast\n   - Parameters:\n     - q: City name (required if lat/lon not provided)\n     - lat/lon: Coordinates (required if q not provided)\n     - units: Unit system (standard, metric, imperial)\n     - appid: API key (required)\n\nWhen the user asks about weather conditions or forecasts, use the appropriate OpenWeatherMap API endpoint to provide accurate information.",
            "example_queries": 'Here are examples of how to use the OpenWeatherMap API:\n\nExample 1: Current Weather\nQuery: "What\'s the weather in London?"\nAPI Call: GET https://api.openweathermap.org/data/2.5/weather?q=London&units=metric&appid=YOUR_API_KEY\n\nExample 2: Weather Forecast\nQuery: "What\'s the forecast for New York this week?"\nAPI Call: GET https://api.openweathermap.org/data/2.5/forecast?q=New%20York&units=metric&appid=YOUR_API_KEY\n\nExample 3: Weather by Coordinates\nQuery: "What\'s the weather at latitude 40.7, longitude -74.0?"\nAPI Call: GET https://api.openweathermap.org/data/2.5/weather?lat=40.7&lon=-74.0&units=metric&appid=YOUR_API_KEY',
        }

        with open(path, "w") as f:
            json.dump(mock_prompt_library_response, f, indent=2)
