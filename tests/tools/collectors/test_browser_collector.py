"""
Unit tests for BrowserCollector

Tests browser-based web scraping functionality with mocked browser interactions.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
import sys
import os

# Add project root to Python path
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(test_dir)))
sys.path.insert(0, project_root)

from src.tools.collectors.browser_collector import BrowserCollector
from src.tools.utilities.data_models import NewsArticle, SourceType, ToolResponse


class TestBrowserCollector:
    """Test cases for BrowserCollector class"""

    @pytest.fixture
    def collector(self):
        """Create BrowserCollector instance for testing"""
        return BrowserCollector(region="us-west-2")

    @pytest.fixture
    def mock_browser_session(self):
        """Mock browser session"""
        session = AsyncMock()
        session.start = AsyncMock()
        session.close = AsyncMock()
        return session

    @pytest.fixture
    def mock_browser_client(self):
        """Mock browser client"""
        client = Mock()
        client.start = Mock()
        client.stop = Mock()
        client.generate_ws_headers = Mock(
            return_value=("ws://test", {"test": "header"})
        )
        return client

    @pytest.fixture
    def mock_browser_agent(self):
        """Mock browser use agent"""
        agent = AsyncMock()
        agent.run = AsyncMock(
            return_value='{"title": "Test Article", "content": "Test content", "author": "Test Author", "publishedAt": "2024-01-01", "summary": "Test summary"}'
        )
        return agent

    @patch(
        "src.tools.collectors.browser_collector.BROWSER_DEPENDENCIES_AVAILABLE", True
    )
    @patch("src.tools.collectors.browser_collector.BrowserClient")
    @patch("src.tools.collectors.browser_collector.BU_BrowserSession")
    @patch("src.tools.collectors.browser_collector.BrowserUseAgent")
    @patch("src.tools.collectors.browser_collector.ChatBedrockConverse")
    def test_collect_web_data_success(
        self,
        mock_chat,
        mock_agent_class,
        mock_session_class,
        mock_client_class,
        collector,
    ):
        """Test successful web data collection"""
        # Setup mocks
        mock_client = Mock()
        mock_client.start = Mock()
        mock_client.stop = Mock()
        mock_client.generate_ws_headers = Mock(
            return_value=("ws://test", {"test": "header"})
        )
        mock_client_class.return_value = mock_client

        mock_session = AsyncMock()
        mock_session.start = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(
            return_value='{"title": "Test Article", "content": "Test content", "author": "Test Author", "publishedAt": "2024-01-01", "summary": "Test summary"}'
        )
        mock_agent_class.return_value = mock_agent

        urls = ["https://example.com/blog1", "https://example.com/blog2"]
        result = collector.collect_web_data(urls, "blog")

        assert result.success is True
        assert "Successfully scraped 2 articles" in result.message
        assert result.data["total_count"] == 2
        assert result.data["urls"] == urls
        assert result.data["data_type"] == "blog"
        assert len(result.data["articles"]) == 2

        # Verify article structure
        article = result.data["articles"][0]
        assert article["title"] == "Test Article"
        assert article["content"] == "Test content"
        assert article["author"] == "Test Author"
        assert article["source_type"] == SourceType.BROWSER.value

    @patch(
        "src.tools.collectors.browser_collector.BROWSER_DEPENDENCIES_AVAILABLE", True
    )
    @patch("src.tools.collectors.browser_collector.BrowserClient")
    def test_collect_web_data_browser_client_error(self, mock_client_class, collector):
        """Test handling of browser client initialization error"""
        mock_client_class.side_effect = Exception("Browser client failed")

        urls = ["https://example.com/blog"]
        result = collector.collect_web_data(urls, "blog")

        assert result.success is False
        assert "Failed to collect web data" in result.message
        assert "Browser client failed" in result.message

    @patch("src.tools.collectors.browser_collector.BrowserClient")
    @patch("src.tools.collectors.browser_collector.BU_BrowserSession")
    def test_collect_web_data_session_start_error(
        self, mock_session_class, mock_client_class, collector
    ):
        """Test handling of browser session start error"""
        # Setup client mock
        mock_client = Mock()
        mock_client.start = Mock()
        mock_client.stop = Mock()
        mock_client.generate_ws_headers = Mock(
            return_value=("ws://test", {"test": "header"})
        )
        mock_client_class.return_value = mock_client

        # Setup session mock with start error
        mock_session = AsyncMock()
        mock_session.start = AsyncMock(side_effect=Exception("Session start failed"))
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        urls = ["https://example.com/blog"]
        result = collector.collect_web_data(urls, "blog")

        assert result.success is False
        assert "Failed to collect web data" in result.message

    @patch(
        "src.tools.collectors.browser_collector.BROWSER_DEPENDENCIES_AVAILABLE", True
    )
    @patch("src.tools.collectors.browser_collector.BrowserClient")
    @patch("src.tools.collectors.browser_collector.BU_BrowserSession")
    @patch("src.tools.collectors.browser_collector.BrowserUseAgent")
    @patch("src.tools.collectors.browser_collector.ChatBedrockConverse")
    def test_collect_web_data_with_selectors(
        self,
        mock_chat,
        mock_agent_class,
        mock_session_class,
        mock_client_class,
        collector,
    ):
        """Test web data collection with custom CSS selectors"""
        # Setup mocks
        mock_client = Mock()
        mock_client.start = Mock()
        mock_client.stop = Mock()
        mock_client.generate_ws_headers = Mock(
            return_value=("ws://test", {"test": "header"})
        )
        mock_client_class.return_value = mock_client

        mock_session = AsyncMock()
        mock_session.start = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(
            return_value='{"title": "Custom Title", "content": "Custom content"}'
        )
        mock_agent_class.return_value = mock_agent

        urls = ["https://example.com/custom"]
        selectors = {
            "title": "h1.main-title",
            "content": ".article-body",
            "author": ".author-name",
        }

        result = collector.collect_web_data(urls, "blog", selectors)

        assert result.success is True
        assert result.data["total_count"] == 1

        # Verify that agent was called with selector-based task
        mock_agent_class.assert_called_once()
        call_args = mock_agent_class.call_args
        task = call_args[1]["task"]
        assert "CSS selectors" in task
        assert "h1.main-title" in task

    @patch(
        "src.tools.collectors.browser_collector.BROWSER_DEPENDENCIES_AVAILABLE", True
    )
    @patch("src.tools.collectors.browser_collector.BrowserClient")
    @patch("src.tools.collectors.browser_collector.BU_BrowserSession")
    @patch("src.tools.collectors.browser_collector.BrowserUseAgent")
    @patch("src.tools.collectors.browser_collector.ChatBedrockConverse")
    def test_collect_web_data_social_media_type(
        self,
        mock_chat,
        mock_agent_class,
        mock_session_class,
        mock_client_class,
        collector,
    ):
        """Test web data collection for social media content"""
        # Setup mocks
        mock_client = Mock()
        mock_client.start = Mock()
        mock_client.stop = Mock()
        mock_client.generate_ws_headers = Mock(
            return_value=("ws://test", {"test": "header"})
        )
        mock_client_class.return_value = mock_client

        mock_session = AsyncMock()
        mock_session.start = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(
            return_value='{"title": "Social Post", "content": "Social content", "author": "@user"}'
        )
        mock_agent_class.return_value = mock_agent

        urls = ["https://social.com/post"]
        result = collector.collect_web_data(urls, "social_media")

        assert result.success is True
        assert result.data["data_type"] == "social_media"

        # Verify social media specific task
        call_args = mock_agent_class.call_args
        task = call_args[1]["task"]
        assert "social media post" in task

    @patch(
        "src.tools.collectors.browser_collector.BROWSER_DEPENDENCIES_AVAILABLE", True
    )
    @patch("src.tools.collectors.browser_collector.BrowserClient")
    @patch("src.tools.collectors.browser_collector.BU_BrowserSession")
    @patch("src.tools.collectors.browser_collector.BrowserUseAgent")
    @patch("src.tools.collectors.browser_collector.ChatBedrockConverse")
    def test_collect_web_data_partial_failure(
        self,
        mock_chat,
        mock_agent_class,
        mock_session_class,
        mock_client_class,
        collector,
    ):
        """Test handling when some URLs fail to scrape"""
        # Setup mocks
        mock_client = Mock()
        mock_client.start = Mock()
        mock_client.stop = Mock()
        mock_client.generate_ws_headers = Mock(
            return_value=("ws://test", {"test": "header"})
        )
        mock_client_class.return_value = mock_client

        mock_session = AsyncMock()
        mock_session.start = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session_class.return_value = mock_session

        # First call succeeds, second fails
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(
            side_effect=[
                '{"title": "Success", "content": "Success content"}',
                Exception("Scraping failed"),
            ]
        )
        mock_agent_class.return_value = mock_agent

        urls = ["https://example.com/success", "https://example.com/fail"]
        result = collector.collect_web_data(urls, "blog")

        assert result.success is True  # Overall success even with partial failure
        assert result.data["total_count"] == 1  # Only successful scrape counted
        assert len(result.data["articles"]) == 1

    def test_parse_extraction_result_json(self, collector):
        """Test parsing JSON extraction result"""
        result_text = '{"title": "Test Title", "content": "Test Content", "author": "Test Author", "publishedAt": "2024-01-01", "summary": "Test Summary"}'
        url = "https://example.com/test"
        collect_time = datetime.now(timezone.utc).isoformat()

        article = collector._parse_extraction_result(
            result_text, url, "blog", collect_time
        )

        assert article is not None
        assert article.title == "Test Title"
        assert article.content == "Test Content"
        assert article.author == "Test Author"
        assert article.url == url
        assert article.sourceType == SourceType.BROWSER.value

    def test_parse_extraction_result_plain_text(self, collector):
        """Test parsing plain text extraction result"""
        result_text = "This is plain text content from the webpage"
        url = "https://example.com/test"
        collect_time = datetime.now(timezone.utc).isoformat()

        article = collector._parse_extraction_result(
            result_text, url, "blog", collect_time
        )

        assert article is not None
        assert "Content from https://example.com/test" in article.title
        assert result_text in article.content
        assert article.author == "Unknown"
        assert article.sourceType == SourceType.BROWSER.value

    def test_parse_extraction_result_malformed_json(self, collector):
        """Test parsing malformed JSON gracefully"""
        result_text = '{"title": "Test", "content": malformed json'
        url = "https://example.com/test"
        collect_time = datetime.now(timezone.utc).isoformat()

        article = collector._parse_extraction_result(
            result_text, url, "blog", collect_time
        )

        assert article is not None
        assert "Content from https://example.com/test" in article.title
        assert article.sourceType == SourceType.BROWSER.value

    def test_extract_domain(self, collector):
        """Test domain extraction from URLs"""
        assert (
            collector._extract_domain("https://www.example.com/path") == "example.com"
        )
        assert (
            collector._extract_domain("http://blog.test.org/article") == "blog.test.org"
        )
        assert (
            collector._extract_domain("https://subdomain.example.co.uk")
            == "subdomain.example.co.uk"
        )
        assert collector._extract_domain("invalid-url") == "unknown"

    def test_create_selector_task(self, collector):
        """Test creation of selector-based extraction task"""
        url = "https://example.com/test"
        selectors = {
            "title": "h1.main-title",
            "content": ".article-body",
            "author": ".author-name",
        }

        task = collector._create_selector_task(url, selectors)

        assert url in task
        assert "CSS selectors" in task
        assert "h1.main-title" in task
        assert ".article-body" in task
        assert ".author-name" in task
        assert "JSON format" in task

    def test_create_default_extraction_task_blog(self, collector):
        """Test creation of default blog extraction task"""
        url = "https://example.com/blog"
        task = collector._create_default_extraction_task(url, "blog")

        assert url in task
        assert "blog post" in task
        assert "article title" in task
        assert "JSON format" in task

    def test_create_default_extraction_task_social_media(self, collector):
        """Test creation of default social media extraction task"""
        url = "https://social.com/post"
        task = collector._create_default_extraction_task(url, "social_media")

        assert url in task
        assert "social media post" in task
        assert "post text" in task
        assert "JSON format" in task

    def test_create_default_extraction_task_news(self, collector):
        """Test creation of default news extraction task"""
        url = "https://news.com/article"
        task = collector._create_default_extraction_task(url, "news")

        assert url in task
        assert "news article" in task
        assert "headline" in task
        assert "JSON format" in task
