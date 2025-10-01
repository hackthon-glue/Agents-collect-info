"""
Unit tests for WeatherAPICollector

Tests weather data collection, API error handling, and data validation.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime
import sys
import os

# Add project root to Python path
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(test_dir)))
sys.path.insert(0, project_root)

from src.tools.collectors.weather_api_collector import WeatherAPICollector
from src.tools.utilities.data_models import WeatherData, SourceType, ToolResponse
from src.tools.utilities.error_handler import APIError


class TestWeatherAPICollector(unittest.TestCase):
    """Test cases for WeatherAPICollector"""

    def setUp(self):
        """Set up test fixtures"""
        self.api_key = "test_api_key"
        self.collector = WeatherAPICollector(self.api_key, rate_limit_per_minute=120)

        # Sample OpenWeatherMap API response
        self.sample_api_response = {
            "coord": {"lon": 139.6917, "lat": 35.6895},
            "weather": [
                {
                    "id": 803,
                    "main": "Clouds",
                    "description": "broken clouds",
                    "icon": "04d",
                }
            ],
            "base": "stations",
            "main": {
                "temp": 26.3,
                "feels_like": 26.3,
                "temp_min": 26.3,
                "temp_max": 26.3,
                "pressure": 1015,
                "humidity": 47,
                "sea_level": 1015,
                "grnd_level": 1014,
            },
            "visibility": 10000,
            "wind": {"speed": 4.81, "deg": 125, "gust": 3.47},
            "clouds": {"all": 65},
            "dt": 1758948965,
            "sys": {"country": "JP", "sunrise": 1758918760, "sunset": 1758961917},
            "timezone": 32400,
            "id": 1850144,
            "name": "Tokyo",
            "cod": 200,
        }

    @patch("src.tools.collectors.weather_api_collector.requests.get")
    def test_collect_weather_success(self, mock_get):
        """Test successful weather data collection"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_api_response
        mock_get.return_value = mock_response

        # Test collection
        result = self.collector.collect_weather(["jp"])

        # Verify result
        self.assertIsInstance(result, ToolResponse)
        self.assertTrue(result.success)
        self.assertIn("Successfully collected weather data", result.message)
        self.assertIsNotNone(result.data)
        self.assertEqual(len(result.data["weather_data"]), 1)

        # Verify weather data structure
        weather_data = result.data["weather_data"][0]
        self.assertEqual(weather_data["location"], "Tokyo")
        self.assertEqual(weather_data["country"], "JP")
        self.assertEqual(weather_data["temperature"], 26.3)
        self.assertEqual(weather_data["humidity"], 47)

    @patch("src.tools.collectors.weather_api_collector.requests.get")
    def test_collect_weather_multiple_countries(self, mock_get):
        """Test weather collection for multiple countries"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_api_response
        mock_get.return_value = mock_response

        result = self.collector.collect_weather(["us", "jp", "uk"])

        self.assertTrue(result.success)
        self.assertEqual(len(result.data["weather_data"]), 3)
        self.assertEqual(mock_get.call_count, 3)

    @patch("src.tools.collectors.weather_api_collector.requests.get")
    def test_collect_weather_with_custom_cities(self, mock_get):
        """Test weather collection with custom cities"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_api_response
        mock_get.return_value = mock_response

        custom_cities = ["New York,US", "London,UK"]
        result = self.collector.collect_weather(["us", "uk"], cities=custom_cities)

        self.assertTrue(result.success)
        self.assertEqual(len(result.data["weather_data"]), 2)

        # Verify API was called with custom cities
        calls = mock_get.call_args_list
        self.assertIn("New York,US", str(calls[0]))
        self.assertIn("London,UK", str(calls[1]))

    @patch("src.tools.collectors.weather_api_collector.requests.get")
    def test_api_error_handling(self, mock_get):
        """Test handling of API errors"""
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"
        mock_get.return_value = mock_response

        result = self.collector.collect_weather(["us"])

        self.assertFalse(result.success)
        self.assertIn("Failed to collect weather data", result.message)
        self.assertIsNotNone(result.error)

    @patch("src.tools.collectors.weather_api_collector.requests.get")
    def test_api_invalid_response_code(self, mock_get):
        """Test handling of invalid response codes from API"""
        # Mock API response with error code
        error_response = {"cod": 404, "message": "city not found"}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = error_response
        mock_get.return_value = mock_response

        # Use a valid country that has a default capital
        result = self.collector.collect_weather(["us"])

        self.assertFalse(result.success)
        self.assertIn("Failed to collect weather data", result.message)

    @patch("src.tools.collectors.weather_api_collector.requests.get")
    def test_network_error_handling(self, mock_get):
        """Test handling of network errors"""
        # Mock network error
        mock_get.side_effect = requests.ConnectionError("Network error")

        result = self.collector.collect_weather(["us"])

        self.assertFalse(result.success)
        self.assertIn("Failed to collect weather data", result.message)

    @patch("src.tools.collectors.weather_api_collector.requests.get")
    def test_timeout_handling(self, mock_get):
        """Test handling of request timeouts"""
        # Mock timeout error
        mock_get.side_effect = requests.Timeout("Request timeout")

        result = self.collector.collect_weather(["us"])

        self.assertFalse(result.success)
        self.assertIn("Failed to collect weather data", result.message)

    def test_default_capitals_mapping(self):
        """Test default capital cities mapping"""
        locations = self.collector._get_locations(["us", "jp", "uk"], None)

        expected_locations = ["Washington,US", "Tokyo,JP", "London,UK"]
        self.assertEqual(locations, expected_locations)

    def test_unknown_country_handling(self):
        """Test handling of unknown country codes"""
        locations = self.collector._get_locations(["unknown"], None)

        # Should return empty list for unknown countries
        self.assertEqual(locations, [])

    def test_weather_data_conversion(self):
        """Test conversion of API response to WeatherData model"""
        collect_time = datetime.now().isoformat()
        weather_data = self.collector._convert_to_weather_data(
            self.sample_api_response, collect_time
        )

        self.assertIsInstance(weather_data, WeatherData)
        self.assertEqual(weather_data.location, "Tokyo")
        self.assertEqual(weather_data.country, "JP")
        self.assertEqual(weather_data.temperature, 26.3)
        self.assertEqual(weather_data.feels_like, 26.3)
        self.assertEqual(weather_data.humidity, 47)
        self.assertEqual(weather_data.pressure, 1015)
        self.assertEqual(weather_data.wind_speed, 4.81)
        self.assertEqual(weather_data.wind_deg, 125)
        self.assertEqual(weather_data.clouds, 65)
        self.assertEqual(weather_data.visibility, 10000)
        self.assertEqual(weather_data.description, "broken clouds")
        self.assertEqual(weather_data.main_weather, "Clouds")
        self.assertEqual(weather_data.sourceType, SourceType.API.value)
        self.assertEqual(weather_data.latitude, 35.6895)
        self.assertEqual(weather_data.longitude, 139.6917)

    def test_weather_data_to_dict(self):
        """Test WeatherData to_dict conversion"""
        collect_time = datetime.now().isoformat()
        weather_data = self.collector._convert_to_weather_data(
            self.sample_api_response, collect_time
        )

        data_dict = weather_data.to_dict()

        # Verify all required fields are present
        required_fields = [
            "location",
            "country",
            "temperature",
            "feels_like",
            "temp_min",
            "temp_max",
            "pressure",
            "humidity",
            "description",
            "main_weather",
            "wind_speed",
            "wind_deg",
            "clouds",
            "visibility",
            "collected_at",
            "source_type",
            "latitude",
            "longitude",
        ]

        for field in required_fields:
            self.assertIn(field, data_dict)

    @patch("src.tools.collectors.weather_api_collector.time.sleep")
    @patch("src.tools.collectors.weather_api_collector.time.time")
    def test_rate_limiting(self, mock_time, mock_sleep):
        """Test rate limiting functionality"""
        # Mock time progression with enough values for all calls
        mock_time.side_effect = [
            0,
            0,
            0.1,
            0.1,
            2.0,
            2.0,
        ]  # Provide pairs for each call

        # Set up collector with strict rate limit (60 per minute = 1 per second)
        collector = WeatherAPICollector(self.api_key, rate_limit_per_minute=60)

        # First call - should sleep because time gap is less than interval
        collector._enforce_rate_limit()
        mock_sleep.assert_called_once()

        # Reset mock for second test
        mock_sleep.reset_mock()

        # Second call with insufficient time gap should sleep
        collector._enforce_rate_limit()
        mock_sleep.assert_called_once()

        # Reset and test with sufficient time gap
        mock_sleep.reset_mock()
        collector._enforce_rate_limit()
        mock_sleep.assert_not_called()

    def test_malformed_api_response_handling(self):
        """Test handling of malformed API responses"""
        malformed_response = {"invalid": "data"}
        collect_time = datetime.now().isoformat()

        weather_data = self.collector._convert_to_weather_data(
            malformed_response, collect_time
        )

        # Should return None for malformed data
        self.assertIsNone(weather_data)


if __name__ == "__main__":
    unittest.main()
