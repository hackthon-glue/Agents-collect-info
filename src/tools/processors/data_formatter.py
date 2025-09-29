"""
Data formatting tool for Strands Data Pipeline

Transforms data to standardized JSON format with required fields and timezone conversion.
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timezone
import pytz
from zoneinfo import ZoneInfo
import json
import os

from ..utilities.data_models import NewsArticle, WeatherData, ToolResponse

logger = logging.getLogger(__name__)


class DataFormatter:
    """Formats data to standardized JSON format for database storage"""

    def __init__(self, timezone_mapping_path="config/mapping/timezone.json"):
        self.country_timezones = self._load_timezone_mapping(timezone_mapping_path)

    def _load_timezone_mapping(self, path: str) -> Dict[str, str]:
        """Loads the timezone mapping from a JSON file."""
        if not os.path.exists(path):
            logger.error(f"Timezone mapping file not found at {path}")
            return {}
        with open(path, "r") as f:
            return json.load(f)

    def format_data(
        self, data: List[Dict[str, Any]], data_type: str, country: str = "us"
    ) -> ToolResponse:
        """
        Transform data to standardized JSON format with timezone conversion

        Args:
            data: List of data objects to format
            data_type: Type of data (news, weather, social_media)
            country: Country code for timezone conversion

        Returns:
            ToolResponse with formatted data
        """
        try:
            formatted_data = []
            errors = []

            for i, item in enumerate(data):
                try:
                    if data_type == "news":
                        formatted_item = self._format_news_item(item, country)
                    elif data_type == "weather":
                        formatted_item = self._format_weather_item(item, country)
                    else:
                        formatted_item = self._format_generic_item(item, country)

                    formatted_data.append(formatted_item)
                except Exception as e:
                    error_msg = f"Item {i}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(f"Error formatting item {i}: {str(e)}")

            if errors:
                return ToolResponse(
                    success=False,
                    message=f"Failed to format {len(errors)} items.",
                    error="\n".join(errors),
                )

            logger.info(
                f"Formatted {len(formatted_data)} {data_type} items for country {country}"
            )

            return ToolResponse(
                success=True,
                message=f"Successfully formatted {len(formatted_data)} {data_type} items",
                data={
                    "formatted_data": formatted_data,
                    "count": len(formatted_data),
                    "errors": [],
                    "transformation_metadata": {
                        "source_country": country,
                        "data_type": data_type,
                        "processed_items": len(data),
                        "successful_items": len(formatted_data),
                        "failed_items": 0,
                    },
                },
            )

        except Exception as e:
            logger.error(f"Error formatting data: {str(e)}")
            return ToolResponse(
                success=False, message="Failed to format data", error=str(e)
            )

    def _format_news_item(self, item: Dict[str, Any], country: str) -> Dict[str, Any]:
        """Format news item to standardized format"""
        # Convert publishedAt to UTC with timezone awareness
        published_at = self._convert_to_utc(item.get("publishedAt", ""), country)
        collect_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        return {
            "author": self._truncate_string(item.get("author", "Unknown"), 255),
            "title": self._truncate_string(item.get("title", ""), 500),
            "summary": self._truncate_string(
                item.get("description", item.get("summary", "")), 1000
            ),
            "url": self._truncate_string(item.get("url", ""), 2000),
            "publishedAt": published_at,
            "content": self._truncate_string(item.get("content", ""), 10000),
            "collectAt": collect_at,
            "sourceType": item.get("sourceType", 0),
            "country": country,
            "category": item.get("category", "general"),
            "source_name": self._truncate_string(
                item.get("source", {}).get("name", ""), 100
            ),
        }

    def _format_weather_item(
        self, item: Dict[str, Any], country: str
    ) -> Dict[str, Any]:
        """Format weather item to standardized format"""
        collect_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        return {
            "location": item.get("name", ""),
            "country": country,
            "temperature": float(item.get("main", {}).get("temp", 0)),
            "feels_like": float(item.get("main", {}).get("feels_like", 0)),
            "temp_min": float(item.get("main", {}).get("temp_min", 0)),
            "temp_max": float(item.get("main", {}).get("temp_max", 0)),
            "pressure": float(item.get("main", {}).get("pressure", 0)),
            "humidity": int(item.get("main", {}).get("humidity", 0)),
            "description": item.get("weather", [{}])[0].get("description", ""),
            "main_weather": item.get("weather", [{}])[0].get("main", ""),
            "wind_speed": float(item.get("wind", {}).get("speed", 0)),
            "wind_deg": int(item.get("wind", {}).get("deg", 0)),
            "clouds": int(item.get("clouds", {}).get("all", 0)),
            "visibility": int(item.get("visibility", 0)),
            "collectAt": collect_at,
            "sourceType": 0,
            "latitude": float(item.get("coord", {}).get("lat", 0)),
            "longitude": float(item.get("coord", {}).get("lon", 0)),
        }

    def _format_generic_item(
        self, item: Dict[str, Any], country: str
    ) -> Dict[str, Any]:
        """Format generic item with basic standardization"""
        collect_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        formatted = dict(item)
        formatted["country"] = country
        formatted["collectAt"] = collect_at

        # Convert publishedAt if present
        if "publishedAt" in formatted:
            formatted["publishedAt"] = self._convert_to_utc(
                formatted["publishedAt"], country
            )

        return formatted

    def _convert_to_utc(self, timestamp_str: str, country: str) -> str:
        """Convert timestamp from local timezone to UTC"""
        if not timestamp_str:
            return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        try:
            # Parse the timestamp
            if timestamp_str.endswith("Z"):
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            elif "+" in timestamp_str or timestamp_str.count("-") > 2:
                dt = datetime.fromisoformat(timestamp_str)
            else:
                # Convert from local timezone to UTC
                dt = datetime.fromisoformat(timestamp_str)
                country_tz = self.country_timezones.get(country, "UTC")
                local_tz = ZoneInfo(country_tz)
                dt = dt.replace(tzinfo=local_tz)

            # Convert to UTC
            utc_dt = dt.astimezone(timezone.utc)
            return utc_dt.isoformat().replace("+00:00", "Z")

        except Exception as e:
            logger.warning(f"Failed to parse timestamp {timestamp_str}: {e}")
            return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _truncate_string(self, value: str, max_length: int) -> str:
        """Truncate string to maximum length"""
        if not isinstance(value, str):
            value = str(value) if value is not None else ""

        if len(value) > max_length:
            return value[: max_length - 3] + "..."
        return value
