"""
Unit tests for NewsAPICollector

Tests news data collection, API error handling, and rate limiting.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime, timezone
import time

import sys
import os

# Add project root to Python path
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(test_dir)))
sys.path.insert(0, project_root)

from src.tools.collectors.news_api_collector import NewsAPICollector
from src.tools.utilities.data_models import NewsArticle, SourceType, ToolResponse
from src.tools.utilities.error_handler import APIError


class TestNewsAPICollector(unittest.TestCase):
    """Test cases for NewsAPICollector"""

    def setUp(self):
        """Set up test fixtures"""
        self.api_key = "test_api_key"
        self.collector = NewsAPICollector(self.api_key, rate_limit_per_minute=120)

        # Sample API response based on actual News API structure
        self.sample_api_response = {
            "status": "ok",
            "totalResults": 36,
            "articles": [
                {
                    "source": {
                        "id": "the-washington-post",
                        "name": "The Washington Post",
                    },
                    "author": "Michael Birnbaum, John Hudson",
                    "title": "Trump says he won't allow Israel to annex the West Bank - The Washington Post",
                    "description": "Trump's public opposition to the prospect of annexation helped create space for Arab nations to consider a U.S. plan for ending the war and rebuilding Gaza.",
                    "url": "https://www.washingtonpost.com/politics/2025/09/25/trump-israel-west-bank/",
                    "urlToImage": "https://www.washingtonpost.com/wp-apps/imrs.php?src=https://arc-anglerfish-washpost-prod-washpost.s3.amazonaws.com/public/JOLMYEPG4EMV3T2AOTDVNCM3WY_size-normalized.jpg&w=1440",
                    "publishedAt": "2025-09-26T06:29:18Z",
                    "content": "President Donald Trump said Thursday that he told Israeli Prime Minister Benjamin Netanyahu he will not allow Israel to annex the West Bank, imposing the clearest limit yeton his support as Israel ne… [+38 chars]",
                },
                {
                    "source": {"id": None, "name": "KOMO News"},
                    "author": "Jackie Kent, KOMO News Staff",
                    "title": "DNA evidence confirms Travis Decker is dead, says Chelan County sheriff - KOMO",
                    "description": "The Chelan County Sheriff's Office is set to hold a press conference on Thursday at 4 p.m. following a recent development in the Travis Decker case.",
                    "url": "https://komonews.com/news/local/travis-decker-triple-murder-investigation-update-chelan-county-sheriff-dna-results-washington-state-crime-lab-homicide-us-marshals-fbi",
                    "urlToImage": "https://komonews.com/resources/media2/16x9/1280/986/center/90/d159e56f-305d-42c7-a73f-2d67280f7e35-decker.png",
                    "publishedAt": "2025-09-26T04:12:12Z",
                    "content": "WENATCHEE, Wash. The search is officially over for Travis Decker, the man accused of killing his three young daughters in Chelan County.\r\nChelan County Sheriffs investigators said State Patrol's crim… [+4862 chars]",
                },
                {
                    "source": {"id": "associated-press", "name": "Associated Press"},
                    "author": None,
                    "title": "Canada Post union launches strike as government moves to end most door-to-door mail - AP News",
                    "description": "The Canadian Union of Postal Workers went on strike Thursday after the government announced door-to-door mail delivery would end for nearly all households within the next decade. Canada Post said the strike will mean mail and parcels will not be accepted or d…",
                    "url": "https://apnews.com/article/canada-post-mail-delivery-strike-union-935ba4d9f9ffbfe328603c284700a947",
                    "urlToImage": "https://dims.apnews.com/dims4/default/a7d726d/2147483647/strip/true/crop/6685x3760+0+704/resize/1440x810!/quality/90/?url=https%3A%2F%2Fassets.apnews.com%2Fec%2F90%2Facd66b5ee27a567a3ff93f75c115%2F59ac0a62cc1045d3904786e176f01c76",
                    "publishedAt": "2025-09-26T02:01:00Z",
                    "content": "OTTAWA, Ontario (AP) The Canadian Union of Postal Workers went on strike Thursday after the government announced door-to-door mail delivery would end for nearly all households within the next decade.… [+2659 chars]",
                },
            ],
        }

    @patch("requests.get")
    def test_collect_news_success(self, mock_get):
        """Test successful news collection"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_api_response
        mock_get.return_value = mock_response

        # Test collection
        result = self.collector.collect_news(["us"], "general")

        # Assertions
        self.assertIsInstance(result, ToolResponse)
        self.assertTrue(result.success)
        self.assertIn("articles", result.data)
        self.assertEqual(len(result.data["articles"]), 3)
        self.assertEqual(result.data["total_count"], 3)
        self.assertEqual(result.data["countries"], ["us"])
        self.assertEqual(result.data["category"], "general")

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[1]["params"]["country"], "us")
        self.assertEqual(call_args[1]["params"]["category"], "general")
        self.assertEqual(call_args[1]["params"]["apiKey"], "test_api_key")
        self.assertEqual(call_args[1]["params"]["pageSize"], 20)

    @patch("requests.get")
    def test_collect_news_multiple_countries(self, mock_get):
        """Test news collection for multiple countries"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_api_response
        mock_get.return_value = mock_response

        result = self.collector.collect_news(["us", "jp", "uk"], "technology")

        self.assertTrue(result.success)
        self.assertEqual(len(result.data["countries"]), 3)
        self.assertEqual(result.data["category"], "technology")
        # Should be called 3 times (once per country)
        self.assertEqual(mock_get.call_count, 3)

    @patch("requests.get")
    def test_api_error_handling(self, mock_get):
        """Test API error handling"""
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        result = self.collector.collect_news(["us"], "general")

        self.assertFalse(result.success)
        self.assertIn("Failed to collect news data", result.message)
        self.assertIsNotNone(result.error)

    @patch("requests.get")
    def test_api_status_not_ok(self, mock_get):
        """Test handling of API response with status != 'ok'"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "code": "apiKeyInvalid",
            "message": "Your API key is invalid",
        }
        mock_get.return_value = mock_response

        result = self.collector.collect_news(["us"], "general")

        self.assertFalse(result.success)
        self.assertIn("Failed to collect news data", result.message)
        self.assertIn("Your API key is invalid", result.error)

    @patch("requests.get")
    def test_rate_limit_error(self, mock_get):
        """Test handling of rate limit error from News API"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "code": "rateLimited",
            "message": "You have made too many requests recently. Developer accounts are limited to 100 requests over a 24 hour period.",
        }
        mock_get.return_value = mock_response

        result = self.collector.collect_news(["us"], "general")

        self.assertFalse(result.success)
        self.assertIn("You have made too many requests recently", result.error)

    @patch("requests.get")
    def test_invalid_country_parameter(self, mock_get):
        """Test handling of invalid country parameter"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "error",
            "code": "parameterInvalid",
            "message": "The country parameter is invalid. Please check the documentation for valid country codes.",
        }
        mock_get.return_value = mock_response

        result = self.collector.collect_news(["invalid_country"], "general")

        self.assertFalse(result.success)
        self.assertIn("The country parameter is invalid", result.error)

    @patch("requests.get")
    def test_network_error_handling(self, mock_get):
        """Test network error handling"""
        mock_get.side_effect = requests.ConnectionError("Network error")

        result = self.collector.collect_news(["us"], "general")

        self.assertFalse(result.success)
        self.assertIn("Failed to collect news data", result.message)

    def test_convert_to_news_article(self):
        """Test conversion of API data to NewsArticle"""
        article_data = self.sample_api_response["articles"][0]
        collect_time = datetime.now(timezone.utc).isoformat()

        article = self.collector._convert_to_news_article(
            article_data, "us", "general", collect_time
        )

        self.assertIsInstance(article, NewsArticle)
        self.assertEqual(
            article.title,
            "Trump says he won't allow Israel to annex the West Bank - The Washington Post",
        )
        self.assertEqual(article.author, "Michael Birnbaum, John Hudson")
        self.assertEqual(article.country, "us")
        self.assertEqual(article.category, "general")
        self.assertEqual(article.sourceType, SourceType.API.value)
        self.assertEqual(article.source_name, "The Washington Post")
        self.assertEqual(
            article.url,
            "https://www.washingtonpost.com/politics/2025/09/25/trump-israel-west-bank/",
        )
        self.assertEqual(article.publishedAt, "2025-09-26T06:29:18Z")

    def test_convert_to_news_article_missing_author(self):
        """Test conversion with missing author"""
        article_data = self.sample_api_response["articles"][2]  # Has None author
        collect_time = datetime.now(timezone.utc).isoformat()

        article = self.collector._convert_to_news_article(
            article_data, "jp", "technology", collect_time
        )

        self.assertIsInstance(article, NewsArticle)
        self.assertEqual(article.author, "Unknown")
        self.assertEqual(article.country, "jp")
        self.assertEqual(article.category, "technology")
        self.assertEqual(article.source_name, "Associated Press")
        self.assertEqual(
            article.title,
            "Canada Post union launches strike as government moves to end most door-to-door mail - AP News",
        )

    def test_convert_to_news_article_missing_essential_data(self):
        """Test conversion with missing essential data returns None"""
        article_data = {"author": "Test Author"}  # Missing title and url
        collect_time = datetime.now(timezone.utc).isoformat()

        article = self.collector._convert_to_news_article(
            article_data, "us", "general", collect_time
        )

        self.assertIsNone(article)

    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        collector = NewsAPICollector(
            "test_key", rate_limit_per_minute=60
        )  # 1 request per second

        start_time = time.time()
        collector._enforce_rate_limit()
        collector._enforce_rate_limit()
        end_time = time.time()

        # Second call should be delayed by at least 1 second
        self.assertGreaterEqual(end_time - start_time, 1.0)

    @patch("requests.get")
    def test_empty_articles_response(self, mock_get):
        """Test handling of empty articles response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "ok",
            "totalResults": 0,
            "articles": [],
        }
        mock_get.return_value = mock_response

        result = self.collector.collect_news(["us"], "general")

        self.assertTrue(result.success)
        self.assertEqual(result.data["total_count"], 0)
        self.assertEqual(len(result.data["articles"]), 0)

    @patch("requests.get")
    def test_timeout_handling(self, mock_get):
        """Test timeout error handling"""
        mock_get.side_effect = requests.Timeout("Request timeout")

        result = self.collector.collect_news(["us"], "general")

        self.assertFalse(result.success)
        self.assertIn("Failed to collect news data", result.message)

    @patch("requests.get")
    def test_real_api_structure_validation(self, mock_get):
        """Test with real API structure including edge cases"""
        # Test with real API response structure including None values
        real_api_response = {
            "status": "ok",
            "totalResults": 2,
            "articles": [
                {
                    "source": {"id": "bloomberg", "name": "Bloomberg"},
                    "author": "Lauren Dezenski, Madison Muller, Jennifer A Dlouhy",
                    "title": "Trump Plans 100% Duty on Patented Drugs in New Round of Tariffs - Bloomberg.com",
                    "description": "US President Donald Trump announced a fresh round of tariffs, including a 100% duty on branded or patented pharmaceuticals starting Oct. 1, unless a company is building a manufacturing plant in America.",
                    "url": "https://www.bloomberg.com/news/articles/2025-09-25/trump-plans-100-tariff-on-brand-drugs-unless-us-plants-underway",
                    "urlToImage": "https://assets.bwbx.io/images/users/iqjWHBFdfxIU/iy7dVc3SZ8dk/v0/1200x800.jpg",
                    "publishedAt": "2025-09-26T04:01:00Z",
                    "content": "US President Donald Trump announced a fresh round of tariffs, including a 100% duty on branded or patented pharmaceuticals starting Oct. 1, unless a company is building a manufacturing plant in Ameri… [+69 chars]",
                },
                {
                    # Test article with missing/null fields
                    "source": {"id": None, "name": "Local News"},
                    "author": None,
                    "title": "Local News Article",
                    "description": None,
                    "url": "https://example.com/local-news",
                    "urlToImage": None,
                    "publishedAt": "2025-09-26T03:00:00Z",
                    "content": None,
                },
            ],
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = real_api_response
        mock_get.return_value = mock_response

        result = self.collector.collect_news(["us"], "business")

        self.assertTrue(result.success)
        self.assertEqual(len(result.data["articles"]), 2)

        # Check first article with full data
        first_article = result.data["articles"][0]
        self.assertEqual(first_article["source_name"], "Bloomberg")
        self.assertEqual(
            first_article["author"],
            "Lauren Dezenski, Madison Muller, Jennifer A Dlouhy",
        )

        # Check second article with missing data handled properly
        second_article = result.data["articles"][1]
        self.assertEqual(second_article["author"], "Unknown")
        self.assertEqual(second_article["summary"], "")
        self.assertEqual(second_article["content"], "")
        self.assertEqual(second_article["source_name"], "Local News")

    def test_api_request_parameters(self):
        """Test that API request parameters match News API specification"""
        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok", "articles": []}
            mock_get.return_value = mock_response

            self.collector.collect_news(["jp"], "technology")

            # Verify the request was made with correct parameters
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args

            # Check URL
            self.assertEqual(args[0], "https://newsapi.org/v2/top-headlines")

            # Check parameters
            params = kwargs["params"]
            self.assertEqual(params["country"], "jp")
            self.assertEqual(params["category"], "technology")
            self.assertEqual(params["apiKey"], "test_api_key")
            self.assertEqual(params["pageSize"], 20)

            # Check timeout
            self.assertEqual(kwargs["timeout"], 30)


if __name__ == "__main__":
    unittest.main()
