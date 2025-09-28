"""
Weather API collector for gathering weather data from OpenWeatherMap

Implements rate limiting and error handling for weather data collection.
"""

import requests
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from ..utilities.data_models import WeatherData, SourceType, ToolResponse
from ..utilities.error_handler import ErrorHandler, APIError


class WeatherAPICollector:
    """Collector for OpenWeatherMap API data with rate limiting and error handling"""

    # Default capital cities for countries
    DEFAULT_CAPITALS = {
        "us": "Washington,US",
        "jp": "Tokyo,JP",
        "uk": "London,UK",
        "ca": "Ottawa,CA",
        "au": "Canberra,AU",
        "de": "Berlin,DE",
        "fr": "Paris,FR",
        "it": "Rome,IT",
        "es": "Madrid,ES",
        "br": "Brasilia,BR",
        "in": "New Delhi,IN",
        "cn": "Beijing,CN",
        "kr": "Seoul,KR",
        "mx": "Mexico City,MX",
        "ru": "Moscow,RU",
    }

    def __init__(self, api_key: str, rate_limit_per_minute: int = 60):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.rate_limit = rate_limit_per_minute
        self.request_interval = 60.0 / rate_limit_per_minute
        self.last_request_time = 0
        self.error_handler = ErrorHandler(__name__)
        self.logger = logging.getLogger(__name__)

    # TODO: Refactor to use Geocoding API for location lookup.
    # The 'q' parameter for city name is deprecated. For better accuracy,
    # it's recommended to first convert city/country to latitude and longitude
    # using the Geocoding API and then use 'lat' and 'lon' to fetch weather data.
    def collect_weather(
        self, countries: List[str], cities: Optional[List[str]] = None
    ) -> ToolResponse:
        """
        Collect weather data for specified countries and cities

        Args:
            countries: List of country codes (e.g., ['us', 'jp', 'uk'])
            cities: Optional list of cities, defaults to capital cities

        Returns:
            ToolResponse containing collected weather data
        """
        try:
            all_weather_data = []
            # TODO: Is it OK all datetime should be utc (London GMT)?
            collect_time = datetime.now(timezone.utc).isoformat()

            # Use provided cities or default to capitals
            locations = self._get_locations(countries, cities)

            for location in locations:
                self._enforce_rate_limit()
                weather_data = self._fetch_weather_data(location, collect_time)
                if weather_data:
                    all_weather_data.append(weather_data)
                    self.logger.info(f"Collected weather data for {location}")

            return ToolResponse(
                success=True,
                message=f"Successfully collected weather data for {len(all_weather_data)} locations",
                data={
                    "weather_data": [data.to_dict() for data in all_weather_data],
                    "total_count": len(all_weather_data),
                    "locations": locations,
                    "collected_at": collect_time,
                },
            )

        except Exception as e:
            error_info = self.error_handler.handle_error(
                e, context="collect_weather", reraise=False
            )
            return ToolResponse(
                success=False,
                message=f"Failed to collect weather data: {str(e)}",
                error=error_info.get("message", str(e)),
            )

    def _get_locations(
        self, countries: List[str], cities: Optional[List[str]]
    ) -> List[str]:
        """Get list of locations to query"""
        if cities:
            return cities

        locations = []
        for country in countries:
            capital = self.DEFAULT_CAPITALS.get(country.lower())
            if capital:
                locations.append(capital)
            else:
                self.logger.warning(f"No default capital found for country: {country}")

        return locations

    def _fetch_weather_data(
        self, location: str, collect_time: str
    ) -> Optional[WeatherData]:
        """Fetch weather data for a specific location"""
        params = {"q": location, "appid": self.api_key, "units": "metric", "lang": "en"}

        try:
            response = requests.get(self.base_url, params=params, timeout=30)

            if response.status_code != 200:
                raise APIError(
                    f"Weather API request failed for {location}",
                    api_name="OpenWeatherMap",
                    status_code=response.status_code,
                    response_body=response.text[:500],
                )

            data = response.json()

            if data.get("cod") != 200:
                raise APIError(
                    f"Weather API returned error: {data.get('message', 'Unknown error')}",
                    api_name="OpenWeatherMap",
                )

            return self._convert_to_weather_data(data, collect_time)

        except requests.RequestException as e:
            raise APIError(
                f"Network error while fetching weather for {location}: {str(e)}",
                api_name="OpenWeatherMap",
            )

    def _convert_to_weather_data(
        self, api_data: Dict[str, Any], collect_time: str
    ) -> Optional[WeatherData]:
        """Convert API response to WeatherData model"""
        try:
            # Check for required fields
            if not api_data.get("name") or not api_data.get("main"):
                return None

            main_data = api_data.get("main", {})
            weather_data = api_data.get("weather", [{}])[0]
            wind_data = api_data.get("wind", {})
            clouds_data = api_data.get("clouds", {})
            coord_data = api_data.get("coord", {})
            sys_data = api_data.get("sys", {})

            return WeatherData(
                location=api_data.get("name", "Unknown"),
                country=sys_data.get("country", ""),
                temperature=main_data.get("temp", 0.0),
                feels_like=main_data.get("feels_like", 0.0),
                temp_min=main_data.get("temp_min", 0.0),
                temp_max=main_data.get("temp_max", 0.0),
                pressure=main_data.get("pressure", 0.0),
                humidity=main_data.get("humidity", 0),
                description=weather_data.get("description", ""),
                main_weather=weather_data.get("main", ""),
                wind_speed=wind_data.get("speed", 0.0),
                wind_deg=wind_data.get("deg", 0),
                clouds=clouds_data.get("all", 0),
                visibility=api_data.get("visibility", 0),
                collectAt=collect_time,
                sourceType=SourceType.API.value,
                latitude=coord_data.get("lat", 0.0),
                longitude=coord_data.get("lon", 0.0),
            )

        except Exception as e:
            self.logger.warning(f"Failed to convert weather data: {str(e)}")
            return None

    def _enforce_rate_limit(self):
        """Enforce rate limiting between API requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_interval:
            sleep_time = self.request_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()
