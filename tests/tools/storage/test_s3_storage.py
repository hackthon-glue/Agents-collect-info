"""
Unit tests for S3Storage class

Tests S3 storage functionality with mocked AWS operations
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import json
from botocore.exceptions import ClientError, NoCredentialsError

from src.tools.storage.s3_storage import S3Storage
from src.tools.utilities.data_models import S3StorageConfig, ToolResponse


class TestS3Storage:
    """Test cases for S3Storage class"""

    @pytest.fixture
    def s3_config(self):
        """Create test S3 configuration"""
        return S3StorageConfig(
            bucket_name="test-bucket",
            prefix_template="{country}/{year}/{month}/{day}/{source_name}/",
            region="us-east-1",
            enable_versioning=True,
            enable_encryption=True,
        )

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing"""
        return [
            {
                "title": "Test News 1",
                "content": "Test content 1",
                "country": "us",
                "source_name": "test-source",
                "published_at": "2024-01-15T10:30:00Z",
                "author": "Test Author",
            },
            {
                "title": "Test News 2",
                "content": "Test content 2",
                "country": "us",
                "source_name": "test-source",
                "published_at": "2024-01-15T11:00:00Z",
                "author": "Test Author 2",
            },
        ]

    @pytest.fixture
    def mixed_country_data(self):
        """Create sample data with mixed countries"""
        return [
            {
                "title": "US News",
                "country": "us",
                "source_name": "us-source",
                "published_at": "2024-01-15T10:30:00Z",
            },
            {
                "title": "JP News",
                "country": "jp",
                "source_name": "jp-source",
                "published_at": "2024-01-15T10:30:00Z",
            },
        ]

    @patch("boto3.client")
    def test_init_success(self, mock_boto_client, s3_config):
        """Test successful S3Storage initialization"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        storage = S3Storage(s3_config)

        assert storage.config == s3_config
        assert storage.s3_client == mock_client
        mock_boto_client.assert_called_once_with("s3", region_name="us-east-1")

    @patch("boto3.client")
    def test_init_no_credentials(self, mock_boto_client, s3_config):
        """Test S3Storage initialization with no credentials"""
        mock_boto_client.side_effect = NoCredentialsError()

        with pytest.raises(NoCredentialsError):
            S3Storage(s3_config)

    @patch("boto3.client")
    def test_store_data_success(self, mock_boto_client, s3_config, sample_data):
        """Test successful data storage"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        storage = S3Storage(s3_config)
        result = storage.store_data(sample_data)

        assert result.success is True
        assert "Stored 2/2 items individually" in result.message
        assert result.data["total_items"] == 2
        assert result.data["successful_uploads"] == 2
        assert result.data["bucket"] == "test-bucket"

        # Verify S3 put_object was called for each item
        assert mock_client.put_object.call_count == 2
        call_args = mock_client.put_object.call_args
        assert call_args[1]["Bucket"] == "test-bucket"
        assert call_args[1]["ContentType"] == "application/json"
        assert call_args[1]["ServerSideEncryption"] == "AES256"

    @patch("boto3.client")
    def test_store_data_mixed_countries(
        self, mock_boto_client, s3_config, mixed_country_data
    ):
        """Test data storage with mixed countries"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        storage = S3Storage(s3_config)
        result = storage.store_data(mixed_country_data)

        assert result.success is True
        assert result.data["total_items"] == 2
        assert result.data["successful_uploads"] == 2  # Two different countries

        # Verify S3 put_object was called twice (once per country)
        assert mock_client.put_object.call_count == 2

    @patch("boto3.client")
    def test_store_data_empty_list(self, mock_boto_client, s3_config):
        """Test storage with empty data list"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        storage = S3Storage(s3_config)
        result = storage.store_data([])

        assert result.success is False
        assert "No data provided" in result.message
        mock_client.put_object.assert_not_called()

    @patch("boto3.client")
    def test_store_data_no_bucket_config(self, mock_boto_client, sample_data):
        """Test storage with no bucket configured"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        config = S3StorageConfig(bucket_name="")
        storage = S3Storage(config)
        result = storage.store_data(sample_data)

        assert result.success is False
        assert "bucket name not configured" in result.message
        mock_client.put_object.assert_not_called()

    @patch("boto3.client")
    def test_store_data_with_metadata(self, mock_boto_client, s3_config, sample_data):
        """Test data storage with metadata"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        metadata = {"pipeline_version": "1.0", "processed_by": "test"}

        storage = S3Storage(s3_config)
        result = storage.store_data(sample_data, metadata)

        assert result.success is True

        # Verify metadata was included in the stored data
        call_args = mock_client.put_object.call_args
        stored_data = json.loads(call_args[1]["Body"])
        assert stored_data["metadata"]["pipeline_version"] == "1.0"
        assert stored_data["metadata"]["processed_by"] == "test"

    @patch("boto3.client")
    def test_store_data_client_error_retry(
        self, mock_boto_client, s3_config, sample_data
    ):
        """Test retry mechanism on ClientError"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # First two calls fail, third succeeds
        mock_client.put_object.side_effect = [
            ClientError({"Error": {"Code": "ServiceUnavailable"}}, "PutObject"),
            ClientError({"Error": {"Code": "ServiceUnavailable"}}, "PutObject"),
            None,  # Success on third attempt
        ]

        storage = S3Storage(s3_config)
        result = storage.store_data(sample_data)

        assert result.success is True
        assert mock_client.put_object.call_count == 6  # 2 items * 3 attempts each

    @patch("boto3.client")
    def test_store_data_client_error_max_retries(
        self, mock_boto_client, s3_config, sample_data
    ):
        """Test failure after max retries"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # All attempts fail
        mock_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "PutObject"
        )

        storage = S3Storage(s3_config)
        result = storage.store_data(sample_data)

        assert result.success is False
        assert mock_client.put_object.call_count == 6  # 2 items * 3 attempts each

    @patch("boto3.client")
    def test_list_stored_data_success(self, mock_boto_client, s3_config):
        """Test listing stored data"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        # Mock S3 response
        mock_client.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "us/2024/01/15/test-source/data_20240115_103000.json",
                    "Size": 1024,
                    "LastModified": datetime(
                        2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
                    ),
                    "ETag": '"abc123"',
                }
            ]
        }

        storage = S3Storage(s3_config)
        objects = storage.list_stored_data(country="us")

        assert len(objects) == 1
        assert (
            objects[0]["key"] == "us/2024/01/15/test-source/data_20240115_103000.json"
        )
        assert objects[0]["size"] == 1024

    @patch("boto3.client")
    def test_list_stored_data_error(self, mock_boto_client, s3_config):
        """Test listing stored data with error"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        mock_client.list_objects_v2.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "ListObjectsV2"
        )

        storage = S3Storage(s3_config)
        objects = storage.list_stored_data()

        assert objects == []

    @patch("boto3.client")
    def test_trigger_knowledge_base_sync(self, mock_boto_client, s3_config):
        """Test Knowledge Base sync trigger"""
        mock_client = Mock()
        mock_boto_client.return_value = mock_client

        storage = S3Storage(s3_config)
        result = storage.trigger_knowledge_base_sync("test/key.json")

        # Currently just logs, so should return True
        assert result is True

    def test_s3_config_generate_prefix(self):
        """Test S3 prefix generation"""
        config = S3StorageConfig(
            bucket_name="test",
            prefix_template="{country}/{year}/{month}/{day}/{source_name}/",
        )

        test_date = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        prefix = config.generate_prefix("us", "test-source", test_date)

        assert prefix == "us/2024/01/15/test-source/"

    def test_s3_config_generate_prefix_no_timestamp(self):
        """Test S3 prefix generation without timestamp"""
        config = S3StorageConfig(
            bucket_name="test",
            prefix_template="{country}/{year}/{month}/{day}/{source_name}/",
        )

        prefix = config.generate_prefix("us", "test-source")

        # Should use current date
        assert prefix.startswith("us/")
        assert prefix.endswith("/test-source/")
