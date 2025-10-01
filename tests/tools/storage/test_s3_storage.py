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
    def test_init_with_knowledge_base(self, mock_boto_client, s3_config):
        """Test S3Storage initialization with Knowledge Base configuration"""
        mock_s3_client = Mock()
        mock_bedrock_client = Mock()
        mock_boto_client.side_effect = [mock_s3_client, mock_bedrock_client]

        storage = S3Storage(s3_config, "kb-123", "ds-456")

        assert storage.knowledge_base_id == "kb-123"
        assert storage.data_source_id == "ds-456"
        assert storage.s3_client == mock_s3_client
        assert storage.bedrock_agent_client == mock_bedrock_client
        assert mock_boto_client.call_count == 2

    @patch("boto3.client")
    def test_store_data_with_kb_sync(self, mock_boto_client, s3_config, sample_data):
        """Test data storage with Knowledge Base sync"""
        mock_s3_client = Mock()
        mock_bedrock_client = Mock()
        mock_boto_client.side_effect = [mock_s3_client, mock_bedrock_client]
        
        mock_bedrock_client.start_ingestion_job.return_value = {
            'ingestionJob': {'ingestionJobId': 'job-123'}
        }

        storage = S3Storage(s3_config, "kb-123", "ds-456")
        result = storage.store_data(sample_data)

        assert result.success is True
        assert "KB sync triggered for 2 items" in result.message
        assert result.data["kb_syncs_triggered"] == 2
        assert mock_bedrock_client.start_ingestion_job.call_count == 2

    @patch("boto3.client")
    def test_trigger_knowledge_base_sync_success(self, mock_boto_client, s3_config):
        """Test successful Knowledge Base sync trigger"""
        mock_s3_client = Mock()
        mock_bedrock_client = Mock()
        mock_boto_client.side_effect = [mock_s3_client, mock_bedrock_client]
        
        mock_bedrock_client.start_ingestion_job.return_value = {
            'ingestionJob': {'ingestionJobId': 'job-123'}
        }

        storage = S3Storage(s3_config, "kb-123", "ds-456")
        result = storage.trigger_knowledge_base_sync("test/key.json")

        assert result is True
        mock_bedrock_client.start_ingestion_job.assert_called_once_with(
            knowledgeBaseId="kb-123",
            dataSourceId="ds-456",
            description="Sync triggered for S3 data upload: test/key.json"
        )

    @patch("boto3.client")
    def test_trigger_knowledge_base_sync_no_config(self, mock_boto_client, s3_config):
        """Test Knowledge Base sync without configuration"""
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client

        storage = S3Storage(s3_config)  # No KB config
        result = storage.trigger_knowledge_base_sync("test/key.json")

        assert result is False

    @patch("boto3.client")
    def test_trigger_knowledge_base_sync_conflict(self, mock_boto_client, s3_config):
        """Test Knowledge Base sync with conflict (job already running)"""
        mock_s3_client = Mock()
        mock_bedrock_client = Mock()
        mock_boto_client.side_effect = [mock_s3_client, mock_bedrock_client]
        
        mock_bedrock_client.start_ingestion_job.side_effect = ClientError(
            {"Error": {"Code": "ConflictException"}}, "StartIngestionJob"
        )

        storage = S3Storage(s3_config, "kb-123", "ds-456")
        result = storage.trigger_knowledge_base_sync("test/key.json")

        assert result is True  # Conflict is considered success

    @patch("boto3.client")
    def test_trigger_knowledge_base_sync_retry(self, mock_boto_client, s3_config):
        """Test Knowledge Base sync with retry mechanism"""
        mock_s3_client = Mock()
        mock_bedrock_client = Mock()
        mock_boto_client.side_effect = [mock_s3_client, mock_bedrock_client]
        
        # First two calls fail, third succeeds
        mock_bedrock_client.start_ingestion_job.side_effect = [
            ClientError({"Error": {"Code": "ThrottlingException"}}, "StartIngestionJob"),
            ClientError({"Error": {"Code": "ThrottlingException"}}, "StartIngestionJob"),
            {'ingestionJob': {'ingestionJobId': 'job-123'}}
        ]

        storage = S3Storage(s3_config, "kb-123", "ds-456")
        result = storage.trigger_knowledge_base_sync("test/key.json")

        assert result is True
        assert mock_bedrock_client.start_ingestion_job.call_count == 3

    @patch("boto3.client")
    def test_trigger_knowledge_base_sync_max_retries(self, mock_boto_client, s3_config):
        """Test Knowledge Base sync failure after max retries"""
        mock_s3_client = Mock()
        mock_bedrock_client = Mock()
        mock_boto_client.side_effect = [mock_s3_client, mock_bedrock_client]
        
        mock_bedrock_client.start_ingestion_job.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException"}}, "StartIngestionJob"
        )

        storage = S3Storage(s3_config, "kb-123", "ds-456")
        result = storage.trigger_knowledge_base_sync("test/key.json")

        assert result is False
        assert mock_bedrock_client.start_ingestion_job.call_count == 3

    @patch("boto3.client")
    def test_get_ingestion_job_status_success(self, mock_boto_client, s3_config):
        """Test getting ingestion job status"""
        mock_s3_client = Mock()
        mock_bedrock_client = Mock()
        mock_boto_client.side_effect = [mock_s3_client, mock_bedrock_client]
        
        mock_bedrock_client.get_ingestion_job.return_value = {
            'ingestionJob': {
                'ingestionJobId': 'job-123',
                'status': 'IN_PROGRESS',
                'startedAt': datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
                'updatedAt': datetime(2024, 1, 15, 10, 35, 0, tzinfo=timezone.utc),
                'description': 'Test sync',
                'statistics': {'numberOfDocumentsScanned': 10}
            }
        }

        storage = S3Storage(s3_config, "kb-123", "ds-456")
        status = storage.get_ingestion_job_status("job-123")

        assert status["job_id"] == "job-123"
        assert status["status"] == "IN_PROGRESS"
        assert status["statistics"]["numberOfDocumentsScanned"] == 10

    @patch("boto3.client")
    def test_get_ingestion_job_status_no_config(self, mock_boto_client, s3_config):
        """Test getting ingestion job status without configuration"""
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client

        storage = S3Storage(s3_config)  # No KB config
        status = storage.get_ingestion_job_status("job-123")

        assert "error" in status
        assert "not configured" in status["error"]

    @patch("boto3.client")
    def test_list_ingestion_jobs_success(self, mock_boto_client, s3_config):
        """Test listing ingestion jobs"""
        mock_s3_client = Mock()
        mock_bedrock_client = Mock()
        mock_boto_client.side_effect = [mock_s3_client, mock_bedrock_client]
        
        mock_bedrock_client.list_ingestion_jobs.return_value = {
            'ingestionJobSummaries': [
                {
                    'ingestionJobId': 'job-123',
                    'status': 'COMPLETE',
                    'startedAt': datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
                    'updatedAt': datetime(2024, 1, 15, 10, 35, 0, tzinfo=timezone.utc),
                    'description': 'Test sync 1',
                    'statistics': {'numberOfDocumentsScanned': 10}
                },
                {
                    'ingestionJobId': 'job-456',
                    'status': 'IN_PROGRESS',
                    'startedAt': datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
                    'updatedAt': datetime(2024, 1, 15, 11, 5, 0, tzinfo=timezone.utc),
                    'description': 'Test sync 2',
                    'statistics': {'numberOfDocumentsScanned': 5}
                }
            ]
        }

        storage = S3Storage(s3_config, "kb-123", "ds-456")
        jobs = storage.list_ingestion_jobs()

        assert len(jobs) == 2
        assert jobs[0]["job_id"] == "job-123"
        assert jobs[0]["status"] == "COMPLETE"
        assert jobs[1]["job_id"] == "job-456"
        assert jobs[1]["status"] == "IN_PROGRESS"

    @patch("boto3.client")
    def test_list_ingestion_jobs_no_config(self, mock_boto_client, s3_config):
        """Test listing ingestion jobs without configuration"""
        mock_s3_client = Mock()
        mock_boto_client.return_value = mock_s3_client

        storage = S3Storage(s3_config)  # No KB config
        jobs = storage.list_ingestion_jobs()

        assert jobs == []

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

    @patch("boto3.client")
    def test_full_pipeline_with_kb_sync(self, mock_boto_client, s3_config, sample_data):
        """Test complete pipeline with Knowledge Base sync integration"""
        mock_s3_client = Mock()
        mock_bedrock_client = Mock()
        mock_boto_client.side_effect = [mock_s3_client, mock_bedrock_client]
        
        mock_bedrock_client.start_ingestion_job.return_value = {
            'ingestionJob': {'ingestionJobId': 'job-123'}
        }
        mock_bedrock_client.get_ingestion_job.return_value = {
            'ingestionJob': {
                'ingestionJobId': 'job-123',
                'status': 'COMPLETE',
                'startedAt': datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
                'updatedAt': datetime(2024, 1, 15, 10, 35, 0, tzinfo=timezone.utc),
                'description': 'Test sync',
                'statistics': {'numberOfDocumentsScanned': 2}
            }
        }

        storage = S3Storage(s3_config, "kb-123", "ds-456")
        
        # Store data (should trigger KB sync)
        store_result = storage.store_data(sample_data)
        assert store_result.success is True
        assert store_result.data["kb_syncs_triggered"] == 2
        
        # Check job status
        status = storage.get_ingestion_job_status("job-123")
        assert status["status"] == "COMPLETE"
        assert status["statistics"]["numberOfDocumentsScanned"] == 2
        
        # Verify all calls were made
        assert mock_s3_client.put_object.call_count == 2
        assert mock_bedrock_client.start_ingestion_job.call_count == 2
        mock_bedrock_client.get_ingestion_job.assert_called_once()
