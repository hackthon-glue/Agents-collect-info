"""
Unit tests for DatabaseStorage class

Tests database operations with mocked PostgreSQL connections.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timezone
import sys

# Mock psycopg2 before importing DatabaseStorage
sys.modules["psycopg2"] = MagicMock()
sys.modules["psycopg2.pool"] = MagicMock()
sys.modules["psycopg2.extras"] = MagicMock()

from src.tools.storage.database_storage import DatabaseStorage
from src.tools.utilities.data_models import NewsArticle, WeatherData, DatabaseConfig


class TestDatabaseStorage(unittest.TestCase):
    """Test cases for DatabaseStorage class"""

    def setUp(self):
        """Set up test fixtures"""
        self.db_config = DatabaseConfig(
            host="test-host",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass",
            ssl_mode="require",
            connection_pool_size=5,
            connection_timeout=30,
        )

        self.sample_news = [
            NewsArticle(
                author="Test Author",
                title="Test News Title",
                summary="Test summary",
                url="https://example.com/news1",
                published_at="2024-01-01T12:00:00Z",
                content="Test content",
                collected_at="2024-01-01T12:05:00Z",
                source_type=0,
                country="us",
                category="general",
                source_name="Test Source",
            )
        ]

        self.sample_weather = [
            WeatherData(
                location="New York",
                country="us",
                temperature=25.5,
                feels_like=27.0,
                temp_min=23.0,
                temp_max=28.0,
                pressure=1013.25,
                humidity=65,
                description="Clear sky",
                main_weather="Clear",
                wind_speed=5.2,
                wind_deg=180,
                clouds=10,
                visibility=10000,
                collected_at="2024-01-01T12:00:00Z",
                source_type=0,
                latitude=40.7128,
                longitude=-74.0060,
            )
        ]

    @patch("src.tools.storage.database_storage.psycopg2.pool.ThreadedConnectionPool")
    def test_initialize_connection_pool(self, mock_pool):
        """Test connection pool initialization"""
        mock_pool.return_value = Mock()

        storage = DatabaseStorage(self.db_config)

        mock_pool.assert_called_once_with(
            minconn=1,
            maxconn=5,
            host="test-host",
            port=5432,
            database="test_db",
            user="test_user",
            password="test_pass",
            sslmode="require",
            connect_timeout=30,
        )

    @patch("src.tools.storage.database_storage.psycopg2.pool.ThreadedConnectionPool")
    def test_store_news_data_success(self, mock_pool):
        """Test successful news data storage"""
        # Mock connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {"id": 1}  # Country ID
        mock_cursor.rowcount = 1

        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_cursor
        mock_context_manager.__exit__.return_value = None
        mock_connection.cursor.return_value = mock_context_manager

        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_connection
        mock_pool.return_value = mock_pool_instance

        storage = DatabaseStorage(self.db_config)
        result = storage.store_news_data(self.sample_news)

        self.assertTrue(result.success)
        self.assertEqual(result.data["stored_count"], 1)
        mock_cursor.execute.assert_called()
        mock_connection.commit.assert_called_once()

    @patch("src.tools.storage.database_storage.psycopg2.pool.ThreadedConnectionPool")
    def test_store_news_data_country_not_found(self, mock_pool):
        """Test news data storage when country not found"""
        # Mock connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None  # Country not found

        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_cursor
        mock_context_manager.__exit__.return_value = None
        mock_connection.cursor.return_value = mock_context_manager

        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_connection
        mock_pool.return_value = mock_pool_instance

        storage = DatabaseStorage(self.db_config)
        result = storage.store_news_data(self.sample_news)

        self.assertTrue(result.success)
        self.assertEqual(result.data["stored_count"], 0)

    @patch("src.tools.storage.database_storage.psycopg2.pool.ThreadedConnectionPool")
    def test_store_weather_data_success(self, mock_pool):
        """Test successful weather data storage"""
        # Mock connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {"id": 1}  # Country ID

        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_cursor
        mock_context_manager.__exit__.return_value = None
        mock_connection.cursor.return_value = mock_context_manager

        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_connection
        mock_pool.return_value = mock_pool_instance

        storage = DatabaseStorage(self.db_config)
        result = storage.store_weather_data(self.sample_weather)

        self.assertTrue(result.success)
        self.assertEqual(result.data["stored_count"], 1)
        mock_cursor.execute.assert_called()
        mock_connection.commit.assert_called_once()

    @patch("src.tools.storage.database_storage.psycopg2.pool.ThreadedConnectionPool")
    def test_store_collection_history_success(self, mock_pool):
        """Test successful collection history storage"""
        # Mock connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {"id": 1}  # Country ID

        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_cursor
        mock_context_manager.__exit__.return_value = None
        mock_connection.cursor.return_value = mock_context_manager

        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_connection
        mock_pool.return_value = mock_pool_instance

        execution_data = {
            "execution_id": "test-123",
            "country": "us",
            "api_type": "news_api",
            "execution_date": "2024-01-01",
            "execution_timestamp": "2024-01-01T12:00:00Z",
            "status": "success",
            "records_collected": 10,
            "records_processed": 10,
            "records_stored": 10,
            "execution_duration_ms": 5000,
            "request_parameters": {"category": "general"},
        }

        storage = DatabaseStorage(self.db_config)
        result = storage.store_collection_history(execution_data)

        self.assertTrue(result.success)
        mock_cursor.execute.assert_called()
        mock_connection.commit.assert_called_once()

    @patch("src.tools.storage.database_storage.psycopg2.pool.ThreadedConnectionPool")
    def test_database_error_handling(self, mock_pool):
        """Test database error handling"""
        # Mock connection that raises exception
        mock_connection = Mock()
        mock_connection.cursor.side_effect = Exception("Database connection failed")

        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_connection
        mock_pool.return_value = mock_pool_instance

        storage = DatabaseStorage(self.db_config)
        result = storage.store_news_data(self.sample_news)

        self.assertFalse(result.success)
        self.assertIn("Failed to store news articles", result.message)
        self.assertIsNotNone(result.error)

    @patch("src.tools.storage.database_storage.psycopg2.pool.ThreadedConnectionPool")
    def test_empty_data_handling(self, mock_pool):
        """Test handling of empty data lists"""
        mock_pool.return_value = Mock()

        storage = DatabaseStorage(self.db_config)

        # Test empty news data
        result = storage.store_news_data([])
        self.assertTrue(result.success)
        self.assertEqual(result.data["stored_count"], 0)

        # Test empty weather data
        result = storage.store_weather_data([])
        self.assertTrue(result.success)
        self.assertEqual(result.data["stored_count"], 0)

    @patch("src.tools.storage.database_storage.psycopg2.pool.ThreadedConnectionPool")
    def test_close_connections(self, mock_pool):
        """Test connection pool cleanup"""
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance

        storage = DatabaseStorage(self.db_config)
        storage.close_connections()

        mock_pool_instance.closeall.assert_called_once()


if __name__ == "__main__":
    unittest.main()
