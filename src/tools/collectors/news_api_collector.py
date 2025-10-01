"""
News API collector for gathering news data from multiple countries

Implements rate limiting and error handling for news data collection.
"""

import requests
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from ..utilities.data_models import NewsArticle, SourceType, ToolResponse
from ..utilities.error_handler import ErrorHandler, APIError


class NewsAPICollector:
    """Collector for News API data with rate limiting and error handling"""

    def __init__(self, api_key: str, rate_limit_per_minute: int = 60):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2"
        self.rate_limit = rate_limit_per_minute
        self.request_interval = 60.0 / rate_limit_per_minute
        self.last_request_time = 0
        self.error_handler = ErrorHandler(__name__)
        self.logger = logging.getLogger(__name__)

    def collect_news(
        self, countries: List[str], category: str = "general"
    ) -> ToolResponse:
        """
        Collect news data for specified countries and category

        Args:
            countries: List of country codes (e.g., ['us', 'jp', 'uk'])
            category: News category (general, business, technology, sports, health)

        Returns:
            ToolResponse containing collected news articles
        """
        try:
            all_articles = []
            collect_time = datetime.now(timezone.utc).isoformat()

            for country in countries:
                self._enforce_rate_limit()
                articles = self._fetch_country_news(country, category, collect_time)
                all_articles.extend(articles)
                self.logger.info(f"Collected {len(articles)} articles from {country}")

            return ToolResponse(
                success=True,
                message=f"Successfully collected {len(all_articles)} articles from {len(countries)} countries",
                data={
                    "articles": [article.to_dict() for article in all_articles],
                    "total_count": len(all_articles),
                    "countries": countries,
                    "category": category,
                    "collected_at": collect_time,
                },
            )

        except Exception as e:
            error_info = self.error_handler.handle_error(
                e, context="collect_news", reraise=False
            )
            return ToolResponse(
                success=False,
                message=f"Failed to collect news data: {str(e)}",
                error=error_info.get("message", str(e)),
            )

    def _fetch_country_news(
        self, country: str, category: str, collect_time: str
    ) -> List[NewsArticle]:
        """Fetch news for a specific country"""
        url = f"{self.base_url}/top-headlines"
        params = {
            "country": country,
            "category": category,
            "apiKey": self.api_key,
            "pageSize": 20,  # Limit to avoid rate limits
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code != 200:
                raise APIError(
                    f"News API request failed for {country}",
                    api_name="NewsAPI",
                    status_code=response.status_code,
                    response_body=response.text[:500],
                )

            data = response.json()

            if data.get("status") != "ok":
                raise APIError(
                    f"News API returned error: {data.get('message', 'Unknown error')}",
                    api_name="NewsAPI",
                )

            articles = []
            for article_data in data.get("articles", []):
                article = self._convert_to_news_article(
                    article_data, country, category, collect_time
                )
                if article:
                    articles.append(article)

            return articles

        except requests.RequestException as e:
            raise APIError(
                f"Network error while fetching news for {country}: {str(e)}",
                api_name="NewsAPI",
            )

    def _convert_to_news_article(
        self,
        article_data: Dict[str, Any],
        country: str,
        category: str,
        collect_time: str,
    ) -> Optional[NewsArticle]:
        """Convert API response to NewsArticle model"""
        try:
            # Skip articles with missing essential data
            if not article_data.get("title") or not article_data.get("url"):
                return None

            return NewsArticle(
                author=article_data.get("author") or "Unknown",
                title=article_data.get("title", ""),
                summary=article_data.get("description") or "",
                url=article_data.get("url", ""),
                published_at=article_data.get("publishedAt", ""),
                content=article_data.get("content") or "",
                collected_at=collect_time,
                source_type=SourceType.API.value,
                country=country,
                category=category,
                source_name=article_data.get("source", {}).get("name", "NewsAPI"),
            )

        except Exception as e:
            self.logger.warning(f"Failed to convert article data: {str(e)}")
            return None

    def _enforce_rate_limit(self):
        """Enforce rate limiting between API requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.request_interval:
            sleep_time = self.request_interval - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()