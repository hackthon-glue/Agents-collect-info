"""
Unit tests for DataValidator

Tests schema validation and error handling for news, weather, and social media data.
"""

import unittest
import sys
import os
from datetime import datetime, timezone

# Add project root to Python path
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(test_dir)))
sys.path.insert(0, project_root)

from src.tools.processors.data_validator import DataValidator
from src.tools.utilities.data_models import ValidationResult


class TestDataValidator(unittest.TestCase):
    """Test cases for DataValidator"""

    def setUp(self):
        """Set up test fixtures"""
        self.validator = DataValidator()
        self.current_time = datetime.now(timezone.utc).isoformat()

    def test_valid_news_data(self):
        """Test validation of valid news data"""
        valid_news = [
            {
                "author": "John Doe",
                "title": "Test News Article",
                "summary": "This is a test summary",
                "url": "https://example.com/news",
                "publishedAt": "2025-01-26T10:00:00Z",
                "content": "Full article content here",
                "collectAt": self.current_time,
                "sourceType": 0,
                "country": "us",
                "category": "general",
                "source_name": "Test Source",
            }
        ]

        result = self.validator.validate_data(valid_news, "news")

        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)

    def test_invalid_news_data_missing_required(self):
        """Test validation with missing required fields"""
        invalid_news = [
            {
                "author": "John Doe",
                # Missing title, url, publishedAt, collectAt, sourceType, country
                "summary": "This is a test summary",
            }
        ]

        result = self.validator.validate_data(invalid_news, "news")

        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
        self.assertIn("Missing required field 'title'", str(result.errors))

    def test_invalid_news_data_wrong_types(self):
        """Test validation with wrong data types"""
        invalid_news = [
            {
                "author": 123,  # Should be string
                "title": "Test News Article",
                "url": "https://example.com/news",
                "publishedAt": "2025-01-26T10:00:00Z",
                "collectAt": self.current_time,
                "sourceType": "invalid",  # Should be int
                "country": "us",
            }
        ]

        result = self.validator.validate_data(invalid_news, "news")

        self.assertFalse(result.is_valid)
        self.assertTrue(any("should be str" in error for error in result.errors))
        self.assertTrue(any("should be int" in error for error in result.errors))

    def test_invalid_news_data_pattern_mismatch(self):
        """Test validation with pattern mismatches"""
        invalid_news = [
            {
                "title": "Test News Article",
                "url": "invalid-url",  # Should start with http/https
                "publishedAt": "invalid-date",  # Should match ISO format
                "collectAt": self.current_time,
                "sourceType": 0,
                "country": "USA",  # Should be 2-letter code
            }
        ]

        result = self.validator.validate_data(invalid_news, "news")

        self.assertFalse(result.is_valid)
        self.assertTrue(
            any("doesn't match required pattern" in error for error in result.errors)
        )

    def test_valid_weather_data(self):
        """Test validation of valid weather data"""
        valid_weather = [
            {
                "location": "New York",
                "country": "us",
                "temperature": 25.5,
                "feels_like": 27.0,
                "temp_min": 20.0,
                "temp_max": 30.0,
                "pressure": 1013.25,
                "humidity": 65,
                "description": "Clear sky",
                "main_weather": "Clear",
                "wind_speed": 5.2,
                "wind_deg": 180,
                "clouds": 10,
                "visibility": 10000,
                "collectAt": self.current_time,
                "sourceType": 0,
                "latitude": 40.7128,
                "longitude": -74.0060,
            }
        ]

        result = self.validator.validate_data(valid_weather, "weather")

        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)

    def test_invalid_weather_data_out_of_range(self):
        """Test validation with out-of-range values"""
        invalid_weather = [
            {
                "location": "Test City",
                "country": "us",
                "temperature": 150.0,  # Too high
                "humidity": 150,  # Should be 0-100
                "collectAt": self.current_time,
                "sourceType": 0,
                "latitude": 100.0,  # Should be -90 to 90
                "longitude": 200.0,  # Should be -180 to 180
            }
        ]

        result = self.validator.validate_data(invalid_weather, "weather")

        self.assertFalse(result.is_valid)
        self.assertTrue(any("above maximum" in error for error in result.errors))

    def test_valid_social_media_data(self):
        """Test validation of valid social media data"""
        valid_social = [
            {
                "content": "This is a social media post",
                "platform": "twitter",
                "author": "user123",
                "url": "https://twitter.com/user123/status/123",
                "publishedAt": self.current_time,
                "collectAt": self.current_time,
                "sourceType": 1,
                "country": "us",
                "engagement": {"likes": 10, "shares": 5},
            }
        ]

        result = self.validator.validate_data(valid_social, "social_media")

        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)

    def test_invalid_social_media_data_missing_required(self):
        """Test social media validation with missing required fields"""
        invalid_social = [
            {
                "platform": "twitter",
                # Missing content, collectAt, sourceType
                "author": "user123",
            }
        ]

        result = self.validator.validate_data(invalid_social, "social_media")

        self.assertFalse(result.is_valid)
        self.assertTrue(
            any("Missing required field 'content'" in error for error in result.errors)
        )

    def test_unknown_schema_type(self):
        """Test validation with unknown schema type"""
        data = [{"test": "data"}]

        result = self.validator.validate_data(data, "unknown_type")

        self.assertFalse(result.is_valid)
        self.assertIn("Unknown schema type: unknown_type", result.errors)

    def test_empty_data_list(self):
        """Test validation with empty data list"""
        result = self.validator.validate_data([], "news")

        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)

    def test_string_length_validation(self):
        """Test string length validation"""
        invalid_news = [
            {
                "title": "Hi",  # Too short (min 5)
                "url": "https://example.com/news",
                "publishedAt": "2025-01-26T10:00:00Z",
                "collectAt": self.current_time,
                "sourceType": 0,
                "country": "us",
                "summary": "x" * 1500,  # Too long (max 1000)
            }
        ]

        result = self.validator.validate_data(invalid_news, "news")

        self.assertFalse(result.is_valid)
        self.assertTrue(any("too short" in error for error in result.errors))
        self.assertTrue(any("too long" in warning for warning in result.warnings))

    def test_empty_required_field(self):
        """Test validation with empty required fields"""
        invalid_news = [
            {
                "title": "",  # Empty string
                "url": "https://example.com/news",
                "publishedAt": "2025-01-26T10:00:00Z",
                "collectAt": self.current_time,
                "sourceType": 0,
                "country": "us",
            }
        ]

        result = self.validator.validate_data(invalid_news, "news")

        self.assertFalse(result.is_valid)
        self.assertTrue(any("is empty" in error for error in result.errors))

    def test_multiple_items_validation(self):
        """Test validation of multiple items with mixed validity"""
        mixed_data = [
            {
                # Valid item
                "title": "Valid News Article",
                "url": "https://example.com/valid",
                "publishedAt": "2025-01-26T10:00:00Z",
                "collectAt": self.current_time,
                "sourceType": 0,
                "country": "us",
            },
            {
                # Invalid item
                "title": "Invalid",  # Too short
                "url": "invalid-url",  # Invalid pattern
                "publishedAt": "2025-01-26T10:00:00Z",
                "collectAt": self.current_time,
                "sourceType": 0,
                "country": "us",
            },
        ]

        result = self.validator.validate_data(mixed_data, "news")

        # Should be invalid due to second item
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)


if __name__ == "__main__":
    unittest.main()
