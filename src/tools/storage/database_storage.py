"""
Database storage tool for Aurora PostgreSQL

Handles storing collected data in PostgreSQL database with connection pooling and retry logic.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

from ..utilities.data_models import (
    NewsArticle,
    WeatherData,
    DatabaseConfig,
    ToolResponse,
)
from ..utilities.error_handler import ErrorHandler
from .db_schemas import build_insert_query


class DatabaseStorage:
    """Handles database operations for Aurora PostgreSQL"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler()
        self._connection_pool = None
        self._initialize_connection_pool()

    def _initialize_connection_pool(self):
        """Initialize PostgreSQL connection pool"""
        try:
            self._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.config.connection_pool_size,
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
                sslmode=self.config.ssl_mode,
                connect_timeout=self.config.connection_timeout,
            )
            self.logger.info("Database connection pool initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get database connection from pool with automatic cleanup"""
        connection = None
        try:
            connection = self._connection_pool.getconn()
            yield connection
        except Exception as e:
            if connection:
                connection.rollback()
            raise e
        finally:
            if connection:
                self._connection_pool.putconn(connection)

    def _get_country_id(self, country_code: str, cursor) -> Optional[int]:
        """Get country ID from country code"""
        cursor.execute(
            "SELECT id FROM public.insights_country WHERE code = %s",
            (country_code.upper(),),
        )
        result = cursor.fetchone()
        return result["id"] if result else None

    def _store_data_batch(self, data_list: List[Any], insert_func, data_type: str) -> ToolResponse:
        """Generic method for storing data in batches"""
        if not data_list:
            return ToolResponse(
                success=True,
                message=f"No {data_type} to store",
                data={"stored_count": 0},
            )

        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    stored_count = insert_func(cursor, data_list)
                    conn.commit()

            return ToolResponse(
                success=True,
                message=f"Successfully stored {stored_count} {data_type}",
                data={"stored_count": stored_count},
            )

        except Exception as e:
            error_msg = f"Failed to store {data_type}: {str(e)}"
            self.logger.error(error_msg)
            return ToolResponse(
                success=False, message=f"Failed to store {data_type}", error=error_msg
            )

    def _insert_news_articles(self, cursor, news_articles: List[NewsArticle]) -> int:
        """Insert news articles using schema-based query"""
        insert_query = build_insert_query("news")
        stored_count = 0
        
        for article in news_articles:
            country_id = self._get_country_id(article.country, cursor)
            if not country_id:
                self.logger.warning(f"Country {article.country} not found in database")
                continue
                
            cursor.execute(insert_query, (
                country_id, article.source_name, article.author, article.title,
                article.summary, article.content, article.url, article.published_at,
                article.collected_at, article.source_type, article.category,
                article.fake_news_score, json.dumps(article.to_dict())
            ))
            
            if cursor.rowcount > 0:
                stored_count += 1
                
        return stored_count

    def _insert_weather_data(self, cursor, weather_data: List[WeatherData]) -> int:
        """Insert weather data using schema-based query"""
        insert_query = build_insert_query("weather")
        stored_count = 0
        
        for weather in weather_data:
            country_id = self._get_country_id(weather.country, cursor)
            if not country_id:
                self.logger.warning(f"Country {weather.country} not found in database")
                continue
                
            cursor.execute(insert_query, (
                country_id, weather.location, weather.latitude, weather.longitude,
                weather.main_weather, weather.description, int(weather.temperature * 10),
                int(weather.feels_like * 10), int(weather.temp_min * 10), int(weather.temp_max * 10),
                int(weather.pressure), weather.humidity, weather.wind_speed, weather.wind_deg,
                weather.clouds, weather.visibility, weather.published_at or weather.collected_at,
                weather.collected_at, weather.source_type, weather.sunrise_time,
                weather.sunset_time, json.dumps(weather.to_dict())
            ))
            
            stored_count += 1
            
        return stored_count

    def store_news_data(self, news_articles: List[NewsArticle]) -> ToolResponse:
        """Store news articles in database"""
        return self._store_data_batch(news_articles, self._insert_news_articles, "news articles")

    def store_weather_data(self, weather_data: List[WeatherData]) -> ToolResponse:
        """Store weather data in database"""
        return self._store_data_batch(weather_data, self._insert_weather_data, "weather records")

    def store_collection_history(self, execution_data: Dict[str, Any]) -> ToolResponse:
        """Store collection execution history"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    country_id = self._get_country_id(
                        execution_data.get("country", "US"), cursor
                    )
                    if not country_id:
                        return ToolResponse(
                            success=False, message="Country not found in database"
                        )

                    insert_query = """
                    INSERT INTO public.collection_history (
                        execution_id, country_id, api_type, execution_date,
                        execution_timestamp, status, records_collected,
                        records_processed, records_stored, error_message,
                        execution_duration_ms, request_parameters, collected_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """

                    cursor.execute(
                        insert_query,
                        (
                            execution_data.get("execution_id"),
                            country_id,
                            execution_data.get("api_type"),
                            execution_data.get("execution_date"),
                            execution_data.get("execution_timestamp"),
                            execution_data.get("status"),
                            execution_data.get("records_collected", 0),
                            execution_data.get("records_processed", 0),
                            execution_data.get("records_stored", 0),
                            execution_data.get("error_message"),
                            execution_data.get("execution_duration_ms"),
                            json.dumps(execution_data.get("request_parameters", {})),
                            datetime.now(timezone.utc).isoformat(),
                        ),
                    )

                    conn.commit()

            return ToolResponse(
                success=True, message="Collection history stored successfully"
            )

        except Exception as e:
            error_msg = f"Failed to store collection history: {str(e)}"
            self.logger.error(error_msg)
            return ToolResponse(
                success=False,
                message="Failed to store collection history",
                error=error_msg,
            )

    def close_connections(self):
        """Close all database connections"""
        if self._connection_pool:
            self._connection_pool.closeall()
            self.logger.info("Database connections closed")
