"""
Unit tests for metadata generator
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from src.tools.processors.metadata_generator import MetadataGenerator


class TestMetadataGenerator(unittest.TestCase):
    """Test cases for MetadataGenerator"""

    def setUp(self):
        """Set up test fixtures"""
        self.generator = MetadataGenerator(region="us-east-1")

    def test_generate_metadata_news(self):
        """Test metadata generation for news data"""
        data = {
            "title": "Breaking News: AI Advances",
            "content": "Artificial intelligence has made significant progress in natural language processing.",
            "country": "us",
            "source_name": "TechNews",
            "published_at": "2024-01-15T10:00:00Z"
        }

        with patch.object(self.generator, 'bedrock_client') as mock_client:
            mock_client.converse.return_value = {
                "output": {
                    "message": {
                        "content": [{
                            "text": '{"summary": "AI advances in NLP", "keywords": ["AI", "NLP"], "semantic_tags": ["technology"], "location": "us", "temporal_context": "2024-01-15"}'
                        }]
                    }
                }
            }

            result = self.generator.generate_metadata(data)

            self.assertTrue(result.success)
            self.assertIn("summary", result.data)
            self.assertIn("keywords", result.data)
            self.assertIn("semantic_tags", result.data)
            self.assertEqual(result.data["data_type"], "news")

    def test_generate_metadata_weather(self):
        """Test metadata generation for weather data"""
        data = {
            "location": "Tokyo",
            "temperature": 15.5,
            "humidity": 60,
            "description": "Partly cloudy",
            "country": "jp"
        }

        result = self.generator.generate_metadata(data)

        self.assertTrue(result.success)
        self.assertEqual(result.data["data_type"], "weather")

    def test_fallback_metadata_generation(self):
        """Test fallback metadata generation when Bedrock fails"""
        data = {
            "title": "Test Article",
            "content": "This is a test article with some content for metadata generation.",
            "country": "us"
        }

        with patch.object(self.generator, 'bedrock_client') as mock_client:
            mock_client.converse.side_effect = Exception("Bedrock error")

            result = self.generator.generate_metadata(data)

            self.assertTrue(result.success)
            self.assertIn("summary", result.data)
            self.assertIn("keywords", result.data)

    def test_extract_content_news(self):
        """Test content extraction from news data"""
        data = {
            "title": "Test Title",
            "content": "Test content"
        }

        content = self.generator._extract_content(data)

        self.assertIn("Test Title", content)
        self.assertIn("Test content", content)

    def test_extract_content_weather(self):
        """Test content extraction from weather data"""
        data = {
            "location": "New York",
            "description": "Sunny",
            "temperature": 25
        }

        content = self.generator._extract_content(data)

        self.assertIn("New York", content)
        self.assertIn("Sunny", content)


if __name__ == "__main__":
    unittest.main()
