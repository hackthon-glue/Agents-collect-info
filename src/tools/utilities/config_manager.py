"""
Configuration management for the Strands Data Pipeline

Handles loading and managing configuration from various sources:
- Environment variables
- Configuration files
- Default values
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from .data_models import PipelineConfig, S3StorageConfig, DatabaseConfig


class ConfigManager:
    """Manages configuration for the Strands Data Pipeline"""

    def __init__(self, config_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file or os.getenv(
            "STRANDS_CONFIG_FILE", "config.json"
        )
        self._config_cache: Optional[Dict[str, Any]] = None

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from all sources"""
        if self._config_cache is not None:
            return self._config_cache

        # Start with default configuration
        config = self._get_default_config()

        # Override with file configuration if exists
        file_config = self._load_config_file()
        if file_config:
            config.update(file_config)

        # Override with environment variables
        env_config = self._load_env_config()
        config.update(env_config)

        # Cache the configuration
        self._config_cache = config

        self.logger.info("Configuration loaded successfully")
        return config

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration values"""
        return {
            # Agent configuration
            "agent_id": "strands-data-pipeline",
            "agent_name": "Strands Data Pipeline Agent",
            "log_level": "INFO",
            # Pipeline configuration
            "pipeline": {
                "countries": ["us", "jp"],
                "collect_news": True,
                "collect_weather": True,
                "collect_web_data": False,
                "news_category": "general",
                "store_in_database": True,
                "store_in_s3": True,
                "enable_fake_news_filter": False,
                "enable_sentiment_analysis": False,
                "fake_news_threshold": 0.7,
                "use_ai_categorization": False,
                "primary_country": "us",
            },
            # API configuration
            "apis": {
                "news_api_key": "",
                "weather_api_key": "",
                "rate_limit_requests_per_minute": 60,
                "request_timeout": 30,
            },
            # Database configuration
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": "strands_data",
                "username": "",
                "password": "",
                "ssl_mode": "require",
                "connection_pool_size": 10,
                "connection_timeout": 30,
            },
            # S3 configuration
            "s3": {
                "bucket_name": "",
                "region": "us-east-1",
                "prefix_template": "{country}/{year}/{month}/{day}/{source_name}/",
                "enable_versioning": True,
                "enable_encryption": True,
            },
            # Knowledge Base configuration
            "knowledge_base": {
                "opensearch_endpoint": "",
                "index_name": "strands-data",
                "enable_sync": True,
            },
            # SageMaker configuration (for fake news filtering)
            "sagemaker": {"fake_news_endpoint": "", "region": "us-east-1"},
            # Monitoring and logging
            "monitoring": {
                "enable_metrics": True,
                "metrics_namespace": "StrandsAgent",
                "log_retention_days": 30,
            },
        }

    def _load_config_file(self) -> Optional[Dict[str, Any]]:
        """Load configuration from JSON file"""
        try:
            config_path = Path(self.config_file)
            if config_path.exists():
                with open(config_path, "r") as f:
                    config = json.load(f)
                self.logger.info(f"Loaded configuration from {config_path}")
                return config
            else:
                self.logger.info(
                    f"Configuration file {config_path} not found, using defaults"
                )
                return None
        except Exception as e:
            self.logger.warning(
                f"Failed to load configuration file {self.config_file}: {e}"
            )
            return None

    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_config = {}

        # Agent configuration
        if os.getenv("STRANDS_LOG_LEVEL"):
            env_config["log_level"] = os.getenv("STRANDS_LOG_LEVEL")

        # API keys
        api_config = {}
        if os.getenv("NEWS_API_KEY"):
            api_config["news_api_key"] = os.getenv("NEWS_API_KEY")
        if os.getenv("WEATHER_API_KEY"):
            api_config["weather_api_key"] = os.getenv("WEATHER_API_KEY")
        if api_config:
            env_config["apis"] = api_config

        # Database configuration
        db_config = {}
        if os.getenv("DB_HOST"):
            db_config["host"] = os.getenv("DB_HOST")
        if os.getenv("DB_PORT"):
            db_config["port"] = int(os.getenv("DB_PORT"))
        if os.getenv("DB_NAME"):
            db_config["database"] = os.getenv("DB_NAME")
        if os.getenv("DB_USERNAME"):
            db_config["username"] = os.getenv("DB_USERNAME")
        if os.getenv("DB_PASSWORD"):
            db_config["password"] = os.getenv("DB_PASSWORD")
        if db_config:
            env_config["database"] = db_config

        # S3 configuration
        s3_config = {}
        if os.getenv("S3_BUCKET_NAME"):
            s3_config["bucket_name"] = os.getenv("S3_BUCKET_NAME")
        if os.getenv("S3_REGION"):
            s3_config["region"] = os.getenv("S3_REGION")
        if s3_config:
            env_config["s3"] = s3_config

        # Knowledge Base configuration
        kb_config = {}
        if os.getenv("OPENSEARCH_ENDPOINT"):
            kb_config["opensearch_endpoint"] = os.getenv("OPENSEARCH_ENDPOINT")
        if kb_config:
            env_config["knowledge_base"] = kb_config

        # SageMaker configuration
        sm_config = {}
        if os.getenv("SAGEMAKER_FAKE_NEWS_ENDPOINT"):
            sm_config["fake_news_endpoint"] = os.getenv("SAGEMAKER_FAKE_NEWS_ENDPOINT")
        if sm_config:
            env_config["sagemaker"] = sm_config

        if env_config:
            self.logger.info("Loaded configuration from environment variables")

        return env_config

    def get_pipeline_config(self) -> PipelineConfig:
        """Get pipeline configuration as PipelineConfig object"""
        config = self.load_config()
        pipeline_config = config.get("pipeline", {})

        return PipelineConfig(
            countries=pipeline_config.get("countries", ["us", "jp"]),
            collect_news=pipeline_config.get("collect_news", True),
            collect_weather=pipeline_config.get("collect_weather", True),
            collect_web_data=pipeline_config.get("collect_web_data", False),
            news_category=pipeline_config.get("news_category", "general"),
            cities=pipeline_config.get("cities"),
            web_urls=pipeline_config.get("web_urls"),
            web_data_type=pipeline_config.get("web_data_type", "blog"),
            web_selectors=pipeline_config.get("web_selectors"),
            store_in_database=pipeline_config.get("store_in_database", True),
            store_in_s3=pipeline_config.get("store_in_s3", True),
            enable_fake_news_filter=pipeline_config.get(
                "enable_fake_news_filter", False
            ),
            enable_sentiment_analysis=pipeline_config.get(
                "enable_sentiment_analysis", False
            ),
            fake_news_threshold=pipeline_config.get("fake_news_threshold", 0.7),
            use_ai_categorization=pipeline_config.get("use_ai_categorization", False),
            s3_metadata=pipeline_config.get("s3_metadata"),
            primary_country=pipeline_config.get("primary_country", "us"),
        )

    def get_s3_config(self) -> S3StorageConfig:
        """Get S3 configuration as S3StorageConfig object"""
        config = self.load_config()
        s3_config = config.get("s3", {})

        return S3StorageConfig(
            bucket_name=s3_config.get("bucket_name", ""),
            prefix_template=s3_config.get(
                "prefix_template", "{country}/{year}/{month}/{day}/{source_name}/"
            ),
            region=s3_config.get("region", "us-east-1"),
            enable_versioning=s3_config.get("enable_versioning", True),
            enable_encryption=s3_config.get("enable_encryption", True),
        )

    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration as DatabaseConfig object"""
        config = self.load_config()
        db_config = config.get("database", {})

        return DatabaseConfig(
            host=db_config.get("host", "localhost"),
            port=db_config.get("port", 5432),
            database=db_config.get("database", "strands_data"),
            username=db_config.get("username", ""),
            password=db_config.get("password", ""),
            ssl_mode=db_config.get("ssl_mode", "require"),
            connection_pool_size=db_config.get("connection_pool_size", 10),
            connection_timeout=db_config.get("connection_timeout", 30),
        )

    def get_config_value(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'apis.news_api_key')"""
        config = self.load_config()
        keys = key_path.split(".")

        current = config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current

    def reload_config(self):
        """Reload configuration from sources"""
        self._config_cache = None
        self.load_config()
        self.logger.info("Configuration reloaded")
