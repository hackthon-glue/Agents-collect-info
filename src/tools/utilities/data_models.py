"""
Data models for the Strands Data Pipeline

Defines the core data structures used throughout the pipeline.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from enum import Enum


class SourceType(Enum):
    """Source type enumeration"""

    API = 0
    BROWSER = 1


class DataCategory(Enum):
    """Data category enumeration"""

    NEWS = "news"
    WEATHER = "weather"
    ECONOMIC_INDICATORS = "economic_indicators"
    SOCIAL_MEDIA = "social_media"
    OTHER = "other"


@dataclass
class NewsArticle:
    """Standard news article data model"""

    author: str
    title: str
    summary: str
    url: str
    published_at: str
    content: str
    collected_at: str
    source_type: int
    country: str = "us"
    category: str = "general"
    source_name: str = ""
    fake_news_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "author": self.author,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "published_at": self.published_at,
            "content": self.content,
            "collected_at": self.collected_at,
            "source_type": self.source_type,
            "country": self.country,
            "category": self.category,
            "source_name": self.source_name,
            "fake_news_score": self.fake_news_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewsArticle":
        """Create NewsArticle from dictionary"""
        return cls(
            author=data.get("author", "Unknown"),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            url=data.get("url", ""),
            published_at=data.get("published_at", ""),
            content=data.get("content", ""),
            collected_at=data.get("collected_at", ""),
            source_type=data.get("source_type", 0),
            country=data.get("country", "us"),
            category=data.get("category", "general"),
            source_name=data.get("source_name", ""),
            fake_news_score=data.get("fake_news_score"),
        )

    # Backward compatibility properties
    @property
    def publishedAt(self) -> str:
        return self.published_at
    
    @property
    def collectAt(self) -> str:
        return self.collected_at
    
    @property
    def sourceType(self) -> int:
        return self.source_type


@dataclass
class WeatherData:
    """Weather data model matching OpenWeatherMap API response"""

    location: str
    country: str
    temperature: float
    feels_like: float
    temp_min: float
    temp_max: float
    pressure: float
    humidity: int
    description: str
    main_weather: str
    wind_speed: float
    wind_deg: int
    clouds: int
    visibility: int
    collected_at: str
    source_type: int = 0
    latitude: float = 0.0
    longitude: float = 0.0
    published_at: Optional[str] = None
    sunrise_time: Optional[str] = None
    sunset_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "location": self.location,
            "country": self.country,
            "temperature": self.temperature,
            "feels_like": self.feels_like,
            "temp_min": self.temp_min,
            "temp_max": self.temp_max,
            "pressure": self.pressure,
            "humidity": self.humidity,
            "description": self.description,
            "main_weather": self.main_weather,
            "wind_speed": self.wind_speed,
            "wind_deg": self.wind_deg,
            "clouds": self.clouds,
            "visibility": self.visibility,
            "collected_at": self.collected_at,
            "source_type": self.source_type,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "published_at": self.published_at,
            "sunrise_time": self.sunrise_time,
            "sunset_time": self.sunset_time,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeatherData":
        """Create WeatherData from dictionary"""
        return cls(
            location=data.get("location", ""),
            country=data.get("country", ""),
            temperature=data.get("temperature", 0.0),
            feels_like=data.get("feels_like", 0.0),
            temp_min=data.get("temp_min", 0.0),
            temp_max=data.get("temp_max", 0.0),
            pressure=data.get("pressure", 0.0),
            humidity=data.get("humidity", 0),
            description=data.get("description", ""),
            main_weather=data.get("main_weather", ""),
            wind_speed=data.get("wind_speed", 0.0),
            wind_deg=data.get("wind_deg", 0),
            clouds=data.get("clouds", 0),
            visibility=data.get("visibility", 0),
            collected_at=data.get("collected_at", ""),
            source_type=data.get("source_type", 0),
            latitude=data.get("latitude", 0.0),
            longitude=data.get("longitude", 0.0),
            published_at=data.get("published_at"),
            sunrise_time=data.get("sunrise_time"),
            sunset_time=data.get("sunset_time"),
        )

    # Backward compatibility properties
    @property
    def collectAt(self) -> str:
        return self.collected_at
    
    @property
    def sourceType(self) -> int:
        return self.source_type


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution"""

    countries: List[str] = field(default_factory=lambda: ["us", "jp"])
    collect_news: bool = True
    collect_weather: bool = True
    collect_web_data: bool = False
    news_category: str = "general"
    cities: Optional[List[str]] = None
    web_urls: Optional[List[str]] = None
    web_data_type: str = "blog"
    web_selectors: Optional[Dict[str, str]] = None
    store_in_database: bool = True
    store_in_s3: bool = True
    enable_fake_news_filter: bool = False
    enable_sentiment_analysis: bool = False
    fake_news_threshold: float = 0.7
    use_ai_categorization: bool = False
    s3_metadata: Optional[Dict[str, Any]] = None
    primary_country: str = "us"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "countries": self.countries,
            "collect_news": self.collect_news,
            "collect_weather": self.collect_weather,
            "collect_web_data": self.collect_web_data,
            "news_category": self.news_category,
            "cities": self.cities,
            "web_urls": self.web_urls,
            "web_data_type": self.web_data_type,
            "web_selectors": self.web_selectors,
            "store_in_database": self.store_in_database,
            "store_in_s3": self.store_in_s3,
            "enable_fake_news_filter": self.enable_fake_news_filter,
            "enable_sentiment_analysis": self.enable_sentiment_analysis,
            "fake_news_threshold": self.fake_news_threshold,
            "use_ai_categorization": self.use_ai_categorization,
            "s3_metadata": self.s3_metadata,
            "primary_country": self.primary_country,
        }


@dataclass
class ToolResponse:
    """Standard response format for all tools"""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "success": self.success,
            "message": self.message,
            "timestamp": self.timestamp,
        }
        if self.data is not None:
            result["data"] = self.data
        if self.error is not None:
            result["error"] = self.error
        return result


@dataclass
class ValidationResult:
    """Result of data validation"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class S3StorageConfig:
    """Configuration for S3 storage"""

    bucket_name: str
    prefix_template: str = "{country}/{year}/{month}/{day}/{source_name}/"
    region: str = "us-east-1"
    enable_versioning: bool = True
    enable_encryption: bool = True

    def generate_prefix(
        self, country: str, source_name: str, timestamp: datetime = None
    ) -> str:
        """Generate S3 prefix based on template"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        return self.prefix_template.format(
            country=country,
            year=timestamp.year,
            month=f"{timestamp.month:02d}",
            day=f"{timestamp.day:02d}",
            source_name=source_name,
        )


@dataclass
class DatabaseConfig:
    """Configuration for database connection"""

    host: str
    port: int = 5432
    database: str = "strands_data"
    username: str = ""
    password: str = ""
    ssl_mode: str = "require"
    connection_pool_size: int = 10
    connection_timeout: int = 30

    def get_connection_string(self) -> str:
        """Generate database connection string"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?sslmode={self.ssl_mode}"