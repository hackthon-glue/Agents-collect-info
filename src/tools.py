"""
Tool definitions with @tool decorators for AgentCore integration

This module contains all tool function definitions that will be registered
with AgentCore. Each tool is implemented as a decorated function that calls
the appropriate tool class from the tools/ directory.
"""

from typing import Any, Dict, List, Optional
import logging
from strands import tool
import os

# Tool imports will be added as tools are implemented
from tools.collectors.news_api_collector import NewsAPICollector
from tools.collectors.weather_api_collector import WeatherAPICollector
from tools.collectors.browser_collector import BrowserCollector
from tools.utilities.config_manager import ConfigManager
from tools.processors.data_validator import DataValidator
from tools.processors.data_formatter import DataFormatter
from tools.storage.database_storage import DatabaseStorage
from tools.storage.s3_storage import S3Storage
from tools.analyzers.fake_news_filter import FakeNewsFilter
from tools.processors.metadata_generator import MetadataGenerator
# from tools.analyzers.sentiment_analyzer import SentimentAnalyzer
# from tools.query.rag_query import RAGQuery

logger = logging.getLogger(__name__)


def _filter_fake_news_from_data(data: List[Dict], threshold: float = 0.7) -> tuple[List[Dict], int]:
    """
    Internal function to filter fake news from data list
    
    Returns:
        tuple: (filtered_data, filtered_count)
    """
    try:
        config_manager = ConfigManager()
        endpoint_name = config_manager.get_config_value("sagemaker.fake_news_endpoint")
        region = config_manager.get_config_value("sagemaker.region", "us-east-1")
        enable_filter = config_manager.get_config_value("pipeline.enable_fake_news_filter", False)
        
        if not enable_filter or not endpoint_name:
            return data, 0
        
        filter_tool = FakeNewsFilter(endpoint_name, region)
        filtered_data = []
        filtered_count = 0
        
        for item in data:
            # Extract content for analysis
            content = ""
            if "title" in item and "content" in item:
                content = f"{item['title']}. {item['content']}"
            elif "title" in item:
                content = item["title"]
            elif "content" in item:
                content = item["content"]
            
            if content:
                result = filter_tool.filter_content(content, threshold)
                if result.success and result.data.get("is_credible", True):
                    item["fake_news_score"] = result.data.get("credibility_score")
                    filtered_data.append(item)
                else:
                    filtered_count += 1
                    logger.info(f"Filtered fake news: {item.get('title', 'Unknown')[:50]}...")
            else:
                filtered_data.append(item)
        
        return filtered_data, filtered_count
        
    except Exception as e:
        logger.error(f"Error in fake news filtering: {str(e)}")
        return data, 0


# Data Collection Tools (to be implemented in task 2)
@tool
def collect_news_data(
    countries: List[str], category: str = "general"
) -> Dict[str, Any]:
    """
    Collect news data from free APIs for specified countries

    Args:
        countries: List of country codes (e.g., ['us', 'jp', 'uk'])
        category: News category (general, business, technology, sports, health)

    Returns:
        Dictionary containing collected news articles and metadata
    """
    try:
        config_manager = ConfigManager()
        api_key = config_manager.get_config_value("apis.news_api_key")
        rate_limit = config_manager.get_config_value(
            "apis.rate_limit_requests_per_minute", 60
        )

        if not api_key or api_key == "your_news_api_key_here":
            return {
                "success": False,
                "message": "News API key not configured. Please set NEWS_API_KEY environment variable or update config.json",
                "countries": countries,
                "category": category,
            }

        collector = NewsAPICollector(api_key, rate_limit)
        response = collector.collect_news(countries, category)

        logger.info(
            f"Collected news data for countries {countries}, category {category}"
        )
        return response.to_dict()

    except Exception as e:
        logger.error(f"Error in collect_news_data: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to collect news data: {str(e)}",
            "countries": countries,
            "category": category,
        }


@tool
def collect_weather_data(
    countries: List[str], cities: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Collect weather data from OpenWeatherMap API for specified countries

    Args:
        countries: List of country codes (e.g., ['us', 'jp', 'uk'])
        cities: List of cities (optional, defaults to capitals)

    Returns:
        Dictionary containing weather data for specified locations
    """
    try:
        config_manager = ConfigManager()
        api_key = config_manager.get_config_value("apis.weather_api_key")
        rate_limit = config_manager.get_config_value(
            "apis.rate_limit_requests_per_minute", 60
        )

        if not api_key or api_key == "your_weather_api_key_here":
            return {
                "success": False,
                "message": "Weather API key not configured. Please set WEATHER_API_KEY environment variable or update config.json",
                "countries": countries,
                "cities": cities,
            }

        collector = WeatherAPICollector(api_key, rate_limit)
        response = collector.collect_weather(countries, cities)

        logger.info(f"Collected weather data for countries {countries}")
        return response.to_dict()

    except Exception as e:
        logger.error(f"Error in collect_weather_data: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to collect weather data: {str(e)}",
            "countries": countries,
            "cities": cities,
        }


@tool
def collect_web_data(
    urls: List[str], data_type: str = "blog", selectors: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Collect data from web sources using AgentCore Browser

    Args:
        urls: List of URLs to scrape
        data_type: Type of data to collect (blog, social_media, news)
        selectors: CSS selectors for data extraction

    Returns:
        Dictionary containing scraped web data formatted to API structure
    """
    try:
        config_manager = ConfigManager()
        region = config_manager.get_config_value("aws.region", "us-west-2")

        collector = BrowserCollector(region)
        response = collector.collect_web_data(urls, data_type, selectors)

        logger.info(f"Collected web data from {len(urls)} URLs, type: {data_type}")
        return response.to_dict()

    except Exception as e:
        logger.error(f"Error in collect_web_data: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to collect web data: {str(e)}",
            "urls": urls,
            "data_type": data_type,
        }


# Data Processing Tools (to be implemented in task 3)
@tool
def validate_data(data: List[Dict], schema_type: str) -> Dict[str, Any]:
    """
    Validate collected data against predefined schemas

    Args:
        data: List of data objects to validate
        schema_type: Schema type (news, weather, social_media)

    Returns:
        Dictionary containing validation results and cleaned data
    """
    try:
        validator = DataValidator()
        result = validator.validate_data(data, schema_type)

        logger.info(
            f"Validated {len(data)} {schema_type} items: {len(result.errors)} errors, {len(result.warnings)} warnings"
        )

        return {
            "success": result.is_valid,
            "message": f"Validated {len(data)} {schema_type} items"
            + (
                f" with {len(result.errors)} errors"
                if result.errors
                else " successfully"
            ),
            "data_count": len(data),
            "schema_type": schema_type,
            "validation_result": result.to_dict(),
            "valid_items": len(data) - len([e for e in result.errors if "Item" in e]),
            "error_count": len(result.errors),
            "warning_count": len(result.warnings),
        }

    except Exception as e:
        logger.error(f"Error in validate_data: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to validate data: {str(e)}",
            "data_count": len(data),
            "schema_type": schema_type,
            "error": str(e),
        }


@tool
def format_data(
    data: List[Dict], data_type: str, country: str = "us"
) -> Dict[str, Any]:
    """
    Transform data to standardized JSON format with timezone conversion

    Args:
        data: List of data objects to format
        data_type: Type of data (news, weather, social_media)
        country: Country code for timezone conversion

    Returns:
        Dictionary containing formatted data ready for database storage
    """
    try:
        formatter = DataFormatter()
        response = formatter.format_data(data, data_type, country)

        logger.info(f"Formatted {len(data)} {data_type} items for country {country}")
        return response.to_dict()

    except Exception as e:
        logger.error(f"Error in format_data: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to format data: {str(e)}",
            "data_count": len(data),
            "data_type": data_type,
            "country": country,
            "error": str(e),
        }


# Storage Tools (to be implemented in task 4)
@tool
def store_in_database(categorized_data: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """
    Store categorized data in PostgreSQL/Aurora database with fake news filtering

    Args:
        categorized_data: Data organized by categories (news, weather, etc.)

    Returns:
        Dictionary containing storage results and statistics
    """
    try:
        config_manager = ConfigManager()
        db_config = config_manager.get_database_config()
        threshold = config_manager.get_config_value("pipeline.fake_news_threshold", 0.7)
        
        if not db_config.host or db_config.host == "your_db_host":
            return {
                "success": False,
                "message": "Database not configured. Please set DB_HOST and other database environment variables or update config.json",
                "categories": list(categorized_data.keys()),
                "total_items": sum(len(items) for items in categorized_data.values()),
            }
        
        storage = DatabaseStorage(db_config)
        results = {}
        total_stored = 0
        total_filtered = 0
        
        # Store news data with fake news filtering
        if "news" in categorized_data:
            from tools.utilities.data_models import NewsArticle
            
            # Filter fake news before storing
            filtered_news, filtered_count = _filter_fake_news_from_data(categorized_data["news"], threshold)
            total_filtered += filtered_count
            
            news_articles = [NewsArticle.from_dict(item) for item in filtered_news]
            news_result = storage.store_news_data(news_articles)
            results["news"] = news_result.to_dict()
            results["news"]["filtered_fake_news"] = filtered_count
            if news_result.success:
                total_stored += news_result.data.get("stored_count", 0)
        
        # Store weather data (no filtering needed)
        if "weather" in categorized_data:
            from tools.utilities.data_models import WeatherData
            weather_data = [WeatherData.from_dict(item) for item in categorized_data["weather"]]
            weather_result = storage.store_weather_data(weather_data)
            results["weather"] = weather_result.to_dict()
            if weather_result.success:
                total_stored += weather_result.data.get("stored_count", 0)
        
        storage.close_connections()
        
        message = f"Successfully stored {total_stored} items in database"
        if total_filtered > 0:
            message += f" (filtered {total_filtered} fake news items)"
        
        logger.info(message)
        return {
            "success": True,
            "message": message,
            "categories": list(categorized_data.keys()),
            "total_items": sum(len(items) for items in categorized_data.values()),
            "total_stored": total_stored,
            "total_filtered": total_filtered,
            "results": results,
        }
        
    except Exception as e:
        logger.error(f"Error in store_in_database: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to store data in database: {str(e)}",
            "categories": list(categorized_data.keys()),
            "total_items": sum(len(items) for items in categorized_data.values()),
            "error": str(e),
        }


@tool
def store_in_s3(data: List[Dict], metadata: Optional[Dict] = None, knowledge_base_id: Optional[str] = None, data_source_id: Optional[str] = None, enable_metadata_generation: bool = True) -> Dict[str, Any]:
    """
    Store JSON data in S3 with prefix structure and trigger Knowledge Base sync, with fake news filtering and metadata generation

    Args:
        data: Data to store in S3
        metadata: Optional metadata for RAG enhancement
        knowledge_base_id: Bedrock Knowledge Base ID for sync
        data_source_id: Knowledge Base data source ID for sync
        enable_metadata_generation: Generate AI metadata for RAG optimization

    Returns:
        Dictionary containing S3 storage results and Knowledge Base sync status
    """
    try:
        config_manager = ConfigManager()
        s3_config = config_manager.get_s3_config()
        threshold = config_manager.get_config_value("pipeline.fake_news_threshold", 0.7)
        
        if not s3_config.bucket_name:
            return {
                "success": False,
                "message": "S3 bucket not configured. Please set S3_BUCKET_NAME environment variable or update config.json",
                "data_count": len(data),
                "has_metadata": metadata is not None,
            }
        
        # Filter fake news before storing
        filtered_data, filtered_count = _filter_fake_news_from_data(data, threshold)
        
        # Get Knowledge Base config from environment or config
        if not knowledge_base_id:
            knowledge_base_id = config_manager.get_config_value("knowledge_base.knowledge_base_id")
        if not data_source_id:
            data_source_id = config_manager.get_config_value("knowledge_base.data_source_id")
        
        # Check if metadata generation is enabled in config
        if enable_metadata_generation is None:
            enable_metadata_generation = config_manager.get_config_value("pipeline.enable_metadata_generation", True)
        
        storage = S3Storage(s3_config, knowledge_base_id, data_source_id, enable_metadata_generation)
        response = storage.store_data(filtered_data, metadata)
        
        # Add filtering info to response
        if response.success and response.data:
            response.data["total_filtered"] = filtered_count
            response.data["original_count"] = len(data)
            response.data["metadata_generation_enabled"] = enable_metadata_generation
        
        message = f"Stored {len(filtered_data)} items in S3 with Knowledge Base sync"
        if filtered_count > 0:
            message += f" (filtered {filtered_count} fake news items)"
        if enable_metadata_generation:
            message += " with AI metadata"
        
        logger.info(message)
        return response.to_dict()
        
    except Exception as e:
        logger.error(f"Error in store_in_s3: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to store data in S3: {str(e)}",
            "data_count": len(data),
            "has_metadata": metadata is not None,
            "error": str(e),
        }


# Analysis Tools
@tool
def filter_fake_news(content: str, threshold: float = 0.7) -> Dict[str, Any]:
    """
    Filter content for fake news using SageMaker endpoint

    Args:
        content: Text content to analyze
        threshold: Credibility threshold (0.0 to 1.0)

    Returns:
        Dictionary containing credibility score and filter decision
    """
    try:
        config_manager = ConfigManager()
        endpoint_name = config_manager.get_config_value("sagemaker.fake_news_endpoint")
        region = config_manager.get_config_value("sagemaker.region", "us-east-1")
        
        if not endpoint_name:
            return {
                "success": False,
                "message": "SageMaker fake news endpoint not configured. Please set endpoint in config.json",
                "content_length": len(content),
                "threshold": threshold,
            }
        
        filter_tool = FakeNewsFilter(endpoint_name, region)
        response = filter_tool.filter_content(content, threshold)
        
        logger.info(f"Filtered content for fake news: credibility score available")
        return response.to_dict()
        
    except Exception as e:
        logger.error(f"Error in filter_fake_news: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to filter fake news: {str(e)}",
            "content_length": len(content),
            "threshold": threshold,
            "error": str(e),
        }


@tool
def filter_fake_news_batch(contents: List[str], threshold: float = 0.7) -> Dict[str, Any]:
    """
    Filter multiple content items for fake news using SageMaker endpoint

    Args:
        contents: List of text content to analyze
        threshold: Credibility threshold (0.0 to 1.0)

    Returns:
        Dictionary containing batch analysis results
    """
    try:
        config_manager = ConfigManager()
        endpoint_name = config_manager.get_config_value("sagemaker.fake_news_endpoint")
        region = config_manager.get_config_value("sagemaker.region", "us-east-1")
        
        if not endpoint_name:
            return {
                "success": False,
                "message": "SageMaker fake news endpoint not configured. Please set endpoint in config.json",
                "total_items": len(contents),
                "threshold": threshold,
            }
        
        filter_tool = FakeNewsFilter(endpoint_name, region)
        response = filter_tool.batch_filter(contents, threshold)
        
        logger.info(f"Batch filtered {len(contents)} items for fake news")
        return response.to_dict()
        
    except Exception as e:
        logger.error(f"Error in filter_fake_news_batch: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to batch filter fake news: {str(e)}",
            "total_items": len(contents),
            "threshold": threshold,
            "error": str(e),
        }


@tool
def analyze_sentiment(content: str) -> Dict[str, Any]:
    """
    Analyze sentiment of text content

    Args:
        content: Text content to analyze

    Returns:
        Dictionary containing sentiment scores and classifications
    """
    logger.info("Tool placeholder: analyze_sentiment")
    return {
        "success": False,
        "message": "Tool not yet implemented - will be available in task 5.2",
        "content_length": len(content),
    }


@tool
def trigger_knowledge_base_sync(knowledge_base_id: Optional[str] = None, data_source_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Manually trigger Knowledge Base synchronization

    Args:
        knowledge_base_id: Bedrock Knowledge Base ID
        data_source_id: Knowledge Base data source ID

    Returns:
        Dictionary containing sync trigger results
    """
    try:
        config_manager = ConfigManager()
        s3_config = config_manager.get_s3_config()
        
        # Get Knowledge Base config from environment or config
        if not knowledge_base_id:
            knowledge_base_id = config_manager.get_config_value("knowledge_base.knowledge_base_id")
        if not data_source_id:
            data_source_id = config_manager.get_config_value("knowledge_base.data_source_id")
        
        if not knowledge_base_id or not data_source_id:
            return {
                "success": False,
                "message": "Knowledge Base ID or Data Source ID not configured",
                "knowledge_base_id": knowledge_base_id,
                "data_source_id": data_source_id,
            }
        
        storage = S3Storage(s3_config, knowledge_base_id, data_source_id)
        sync_result = storage.trigger_knowledge_base_sync()
        
        return {
            "success": sync_result,
            "message": "Knowledge Base sync triggered successfully" if sync_result else "Failed to trigger Knowledge Base sync",
            "knowledge_base_id": knowledge_base_id,
            "data_source_id": data_source_id,
        }
        
    except Exception as e:
        logger.error(f"Error in trigger_knowledge_base_sync: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to trigger Knowledge Base sync: {str(e)}",
            "error": str(e),
        }


@tool
def get_knowledge_base_sync_status(job_id: str, knowledge_base_id: Optional[str] = None, data_source_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the status of a Knowledge Base ingestion job

    Args:
        job_id: Ingestion job ID
        knowledge_base_id: Bedrock Knowledge Base ID
        data_source_id: Knowledge Base data source ID

    Returns:
        Dictionary containing job status information
    """
    try:
        config_manager = ConfigManager()
        s3_config = config_manager.get_s3_config()
        
        # Get Knowledge Base config from environment or config
        if not knowledge_base_id:
            knowledge_base_id = config_manager.get_config_value("knowledge_base.knowledge_base_id")
        if not data_source_id:
            data_source_id = config_manager.get_config_value("knowledge_base.data_source_id")
        
        storage = S3Storage(s3_config, knowledge_base_id, data_source_id)
        status = storage.get_ingestion_job_status(job_id)
        
        return {
            "success": "error" not in status,
            "message": "Retrieved job status successfully" if "error" not in status else status["error"],
            "job_status": status,
        }
        
    except Exception as e:
        logger.error(f"Error in get_knowledge_base_sync_status: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to get sync status: {str(e)}",
            "error": str(e),
        }


# Query Tools (to be implemented in task 6)
@tool
def generate_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate RAG-optimized metadata for a data item

    Args:
        data: Data item to generate metadata for

    Returns:
        Dictionary containing generated metadata (summary, keywords, semantic tags)
    """
    try:
        config_manager = ConfigManager()
        region = config_manager.get_config_value("aws.region", "us-east-1")
        model_id = config_manager.get_config_value("bedrock.metadata_model_id", "amazon.nova-lite-v1:0")
        
        generator = MetadataGenerator(region=region, model_id=model_id)
        response = generator.generate_metadata(data)
        
        logger.info("Generated metadata for data item")
        return response.to_dict()
        
    except Exception as e:
        logger.error(f"Error in generate_metadata: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to generate metadata: {str(e)}",
            "error": str(e),
        }


@tool
def query_rag(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Process natural language queries using RAG (Retrieval-Augmented Generation)

    Args:
        query: Natural language query
        max_results: Maximum number of results to return

    Returns:
        Dictionary containing generated response and source citations
    """
    logger.info(f"Tool placeholder: query_rag for query: {query}")
    return {
        "success": False,
        "message": "Tool not yet implemented - will be available in task 6.1",
        "query": query,
        "max_results": max_results,
    }