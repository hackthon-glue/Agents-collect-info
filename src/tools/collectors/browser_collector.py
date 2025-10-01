"""
Browser collector for web scraping using AgentCore Browser

Implements web scraping with browser automation for blog and social media data.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import contextlib

try:
    from bedrock_agentcore.tools.browser_client import BrowserClient
    from browser_use import Agent as BrowserUseAgent
    from browser_use.browser.session import BrowserSession as BU_BrowserSession
    from browser_use.browser import BrowserProfile as BU_BrowserProfile
    from langchain_aws import ChatBedrockConverse

    BROWSER_DEPENDENCIES_AVAILABLE = True
except ImportError:
    # Mock classes for testing when dependencies are not available
    class BrowserClient:
        def __init__(self, region):
            pass

        def start(self):
            pass

        def stop(self):
            pass

        def generate_ws_headers(self):
            return ("ws://mock", {})

    class BrowserUseAgent:
        def __init__(self, **kwargs):
            pass

        async def run(self):
            return "Mock result"

    class BU_BrowserSession:
        def __init__(self, **kwargs):
            pass

        async def start(self):
            pass

        async def close(self):
            pass

    class BU_BrowserProfile:
        def __init__(self, **kwargs):
            pass

    class ChatBedrockConverse:
        def __init__(self, **kwargs):
            pass

    BROWSER_DEPENDENCIES_AVAILABLE = False

from ..utilities.data_models import NewsArticle, SourceType, ToolResponse
from ..utilities.error_handler import ErrorHandler


# TODO: Refactor to have prompt templates on another file
class BrowserCollector:
    """Collector for web data using AgentCore Browser automation"""

    def __init__(self, region: str = "us-west-2"):
        self.region = region
        self.error_handler = ErrorHandler(__name__)
        self.logger = logging.getLogger(__name__)

    def collect_web_data(
        self,
        urls: List[str],
        data_type: str = "blog",
        selectors: Optional[Dict[str, str]] = None,
    ) -> ToolResponse:
        """
        Collect web data from specified URLs using browser automation

        Args:
            urls: List of URLs to scrape
            data_type: Type of data to collect (blog, social_media, news)
            selectors: Optional CSS selectors for specific content extraction

        Returns:
            ToolResponse containing scraped articles formatted as NewsArticle
        """
        try:
            articles = asyncio.run(self._scrape_urls(urls, data_type, selectors))
            collect_time = datetime.now(timezone.utc).isoformat()

            return ToolResponse(
                success=True,
                message=f"Successfully scraped {len(articles)} articles from {len(urls)} URLs",
                data={
                    "articles": [article.to_dict() for article in articles],
                    "total_count": len(articles),
                    "urls": urls,
                    "data_type": data_type,
                    "collected_at": collect_time,
                },
            )

        except Exception as e:
            error_info = self.error_handler.handle_error(
                e, context="collect_web_data", reraise=False
            )
            return ToolResponse(
                success=False,
                message=f"Failed to collect web data: {str(e)}",
                error=error_info.get("message", str(e)),
            )

    async def _scrape_urls(
        self, urls: List[str], data_type: str, selectors: Optional[Dict[str, str]]
    ) -> List[NewsArticle]:
        """Scrape content from URLs using browser automation"""
        if not BROWSER_DEPENDENCIES_AVAILABLE:
            raise ImportError(
                "Browser dependencies not available. Install bedrock_agentcore, browser_use, and langchain_aws."
            )

        articles = []
        client = BrowserClient(region=self.region)
        bu_session = None

        try:
            client.start()
            ws_url, headers = client.generate_ws_headers()
            self.logger.info(f"Browser session created (region={self.region})")

            profile = BU_BrowserProfile(headers=headers, timeout=180000)
            bu_session = BU_BrowserSession(cdp_url=ws_url, browser_profile=profile)

            await bu_session.start()
            self.logger.info("Browser session started successfully")

            bedrock_chat = ChatBedrockConverse(
                model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
                region_name=self.region,
            )

            for url in urls:
                try:
                    article = await self._scrape_single_url(
                        url, data_type, selectors, bu_session, bedrock_chat
                    )
                    if article:
                        articles.append(article)
                        self.logger.info(f"Successfully scraped: {url}")
                except Exception as e:
                    self.logger.warning(f"Failed to scrape {url}: {str(e)}")

        finally:
            if bu_session:
                with contextlib.suppress(Exception):
                    await bu_session.close()
                    self.logger.info("Browser session closed")
            with contextlib.suppress(Exception):
                client.stop()
                self.logger.info("Browser client stopped")

        return articles

    async def _scrape_single_url(
        self,
        url: str,
        data_type: str,
        selectors: Optional[Dict[str, str]],
        bu_session,
        bedrock_chat,
    ) -> Optional[NewsArticle]:
        """Scrape content from a single URL"""
        collect_time = datetime.now(timezone.utc).isoformat()

        # Create extraction task based on selectors or default extraction
        if selectors:
            task = self._create_selector_task(url, selectors)
        else:
            task = self._create_default_extraction_task(url, data_type)

        browser_use_agent = BrowserUseAgent(
            task=task,
            llm=bedrock_chat,
            browser_session=bu_session,
        )

        try:
            result = await browser_use_agent.run()
            return self._parse_extraction_result(result, url, data_type, collect_time)

        except Exception as e:
            self.logger.error(f"Browser automation failed for {url}: {str(e)}")
            return None

    # TODO: Refactor to be scalable to data categories
    def _create_selector_task(self, url: str, selectors: Dict[str, str]) -> str:
        """Create extraction task using CSS selectors"""
        selector_instructions = []
        for field, selector in selectors.items():
            selector_instructions.append(f"- {field}: {selector}")

        return f"""
Navigate to {url} and extract content using these CSS selectors:
{chr(10).join(selector_instructions)}

Return the extracted data in JSON format with these fields:
- title: Article title
- content: Main article content
- author: Author name (if available)
- publishedAt: Publication date (if available)
- summary: Brief summary or description

If any field is not found, return empty string for that field.
"""

    def _create_default_extraction_task(self, url: str, data_type: str) -> str:
        """Create default extraction task based on data type"""
        if data_type == "blog":
            return f"""
Navigate to {url} and extract blog post content:
1. Find the main article title
2. Extract the full article content/body text
3. Look for author information
4. Find publication date if available
5. Extract a brief summary or description

Return the data in JSON format with fields: title, content, author, publishedAt, summary
"""
        elif data_type == "social_media":
            return f"""
Navigate to {url} and extract social media post content:
1. Find the main post text/content
2. Extract author/username
3. Look for post timestamp
4. Get any additional context or description

Return the data in JSON format with fields: title, content, author, publishedAt, summary
"""
        else:  # news or default
            return f"""
Navigate to {url} and extract news article content:
1. Find the headline/title
2. Extract the article body text
3. Look for author byline
4. Find publication date
5. Extract article summary or lead paragraph

Return the data in JSON format with fields: title, content, author, publishedAt, summary
"""

    def _parse_extraction_result(
        self, result: str, url: str, data_type: str, collect_time: str
    ) -> Optional[NewsArticle]:
        """Parse browser automation result into NewsArticle"""
        try:
            # Try to extract JSON from result
            import json
            import re

            # Look for JSON in the result
            json_match = re.search(r"\{.*\}", result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # Fallback: create article from plain text result
                data = {
                    "title": f"Content from {url}",
                    "content": result[:1000],  # Limit content length
                    "author": "Unknown",
                    "publishedAt": "",
                    "summary": result[:200] if len(result) > 200 else result,
                }

            return NewsArticle(
                author=data.get("author", "Unknown"),
                title=data.get("title", f"Content from {url}"),
                summary=data.get("summary", "")[:500],  # Limit summary length
                url=url,
                published_at=data.get("publishedAt", ""),
                content=data.get("content", "")[:2000],  # Limit content length
                collected_at=collect_time,
                source_type=SourceType.BROWSER.value,
                country="unknown",  # Will be set by caller if needed
                category=data_type,
                source_name=self._extract_domain(url),
            )

        except Exception as e:
            self.logger.warning(
                f"Failed to parse extraction result for {url}: {str(e)}"
            )
            # Return basic article with available data
            return NewsArticle(
                author="Unknown",
                title=f"Content from {url}",
                summary="",
                url=url,
                published_at="",
                content=result[:1000] if result else "",
                collected_at=collect_time,
                source_type=SourceType.BROWSER.value,
                country="unknown",
                category=data_type,
                source_name=self._extract_domain(url),
            )

    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL"""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain if domain else "unknown"
        except Exception:
            return "unknown"
