"""
Unit tests for DataFormatter class

Tests data transformation and timezone handling functionality.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.tools.processors.data_formatter import DataFormatter


class TestDataFormatter(unittest.TestCase):
    """Test cases for DataFormatter class"""

    def setUp(self):
        """Set up test fixtures"""
        self.formatter = DataFormatter()

    def test_format_news_data(self):
        """Test formatting news data"""
        raw_news = [
            {
                "title": "Test News Article",
                "author": "Test Author",
                "description": "Test description",
                "url": "https://example.com/news",
                "publishedAt": "2024-01-15T10:30:00Z",
                "content": "Test content",
                "source": {"name": "Test Source"},
                "category": "technology",
            }
        ]

        result = self.formatter.format_data(raw_news, "news", "us")

        self.assertTrue(result.success)
        self.assertEqual(len(result.data["formatted_data"]), 1)

        formatted_item = result.data["formatted_data"][0]
        self.assertEqual(formatted_item["title"], "Test News Article")
        self.assertEqual(formatted_item["country"], "us")
        self.assertEqual(formatted_item["sourceType"], 0)
        self.assertIn("collectAt", formatted_item)

    def test_format_weather_data(self):
        """Test formatting weather data"""
        raw_weather = [
            {
                "name": "New York",
                "main": {
                    "temp": 20.5,
                    "feels_like": 18.2,
                    "temp_min": 15.0,
                    "temp_max": 25.0,
                    "pressure": 1013.25,
                    "humidity": 65,
                },
                "weather": [{"main": "Clear", "description": "clear sky"}],
                "wind": {"speed": 3.5, "deg": 180},
                "clouds": {"all": 10},
                "visibility": 10000,
                "coord": {"lat": 40.7128, "lon": -74.0060},
            }
        ]

        result = self.formatter.format_data(raw_weather, "weather", "us")

        self.assertTrue(result.success)
        formatted_item = result.data["formatted_data"][0]
        self.assertEqual(formatted_item["location"], "New York")
        self.assertEqual(formatted_item["temperature"], 20.5)
        self.assertEqual(formatted_item["country"], "us")

    def test_timezone_conversion_utc(self):
        """Test UTC timezone conversion"""
        utc_time = "2024-01-15T10:30:00Z"
        result = self.formatter._convert_to_utc(utc_time, "us")
        self.assertEqual(result, "2024-01-15T10:30:00Z")

    def test_timezone_conversion_local(self):
        """Test local timezone conversion"""
        local_time = "2024-01-15T10:30:00"
        result = self.formatter._convert_to_utc(local_time, "jp")
        # Should convert from JST to UTC (subtract 9 hours)
        self.assertIn("2024-01-15T01:30:00Z", result)

    def test_string_truncation(self):
        """Test string truncation functionality"""
        long_string = "a" * 1000
        result = self.formatter._truncate_string(long_string, 100)
        self.assertEqual(len(result), 100)
        self.assertTrue(result.endswith("..."))

    def test_invalid_timestamp_handling(self):
        """Test handling of invalid timestamps"""
        invalid_time = "invalid-timestamp"
        result = self.formatter._convert_to_utc(invalid_time, "us")
        # Should return current UTC time
        self.assertTrue(result.endswith("Z"))

    def test_empty_data_formatting(self):
        """Test formatting empty data list"""
        result = self.formatter.format_data([], "news", "us")
        self.assertTrue(result.success)
        self.assertEqual(len(result.data["formatted_data"]), 0)

    def test_error_handling(self):
        """Test error handling in format_data"""
        # Test with invalid data structure
        invalid_data = [{"invalid": "structure"}]

        with patch.object(
            self.formatter, "_format_news_item", side_effect=Exception("Test error")
        ):
            result = self.formatter.format_data(invalid_data, "news", "us")
            self.assertFalse(result.success)
            self.assertIn("Test error", result.error)


if __name__ == "__main__":
    unittest.main()
