"""
S3 storage implementation for the Strands Data Pipeline

Handles storing JSON data in S3 with structured prefix organization
and retry mechanisms for reliable uploads.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dateutil import parser
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import time

from ..utilities.data_models import ToolResponse, S3StorageConfig
from ..utilities.error_handler import ErrorHandler


class S3Storage:
    """S3 storage handler with retry mechanisms and structured prefixes"""

    def __init__(self, config: S3StorageConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler()

        try:
            self.s3_client = boto3.client("s3", region_name=config.region)
        except NoCredentialsError:
            self.logger.error("AWS credentials not configured")
            raise

    def store_data(
        self, data: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None
    ) -> ToolResponse:
        """
        Store each data item as individual JSON file in S3

        Args:
            data: List of data items to store
            metadata: Optional metadata for enhanced storage

        Returns:
            ToolResponse with storage results
        """
        try:
            if not data:
                return ToolResponse(
                    success=False, message="No data provided for storage"
                )

            if not self.config.bucket_name:
                return ToolResponse(
                    success=False, message="S3 bucket name not configured"
                )

            storage_results = []

            for item in data:
                result = self._store_single_item(item, metadata)
                storage_results.append(result)

            successful_uploads = sum(1 for r in storage_results if r["success"])

            return ToolResponse(
                success=successful_uploads > 0,
                message=f"Stored {successful_uploads}/{len(data)} items individually",
                data={
                    "total_items": len(data),
                    "successful_uploads": successful_uploads,
                    "failed_uploads": len(data) - successful_uploads,
                    "storage_results": storage_results,
                    "bucket": self.config.bucket_name,
                },
            )

        except Exception as e:
            error_msg = f"Failed to store data in S3: {str(e)}"
            self.logger.error(error_msg)
            return ToolResponse(success=False, message=error_msg, error=str(e))

    def _store_single_item(
        self, item: Dict[str, Any], metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Store a single item as individual JSON file with retry mechanism"""
        # Extract item information for prefix generation
        country = item.get("country", "unknown")
        source_name = item.get("source_name", "unknown")

        # Parse published date
        published_at = item.get("published_at", item.get("publishedAt", ""))
        try:
            if published_at:
                published_date = parser.parse(published_at)
            else:
                published_date = datetime.now(timezone.utc)
        except:
            published_date = datetime.now(timezone.utc)

        # Generate S3 prefix and unique filename
        prefix = self.config.generate_prefix(
            country=country, source_name=source_name, timestamp=published_date
        )

        # Create unique filename using title hash or timestamp
        import hashlib

        title = item.get("title", item.get("url", "unknown"))
        title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"{title_hash}_{timestamp}.json"
        s3_key = f"{prefix}{filename}"

        # Prepare data for storage
        storage_data = {
            "metadata": {
                "stored_at": datetime.now(timezone.utc).isoformat(),
                "prefix": prefix,
                **(metadata or {}),
            },
            "data": item,
        }

        # Upload with retry
        for attempt in range(3):
            try:
                self.s3_client.put_object(
                    Bucket=self.config.bucket_name,
                    Key=s3_key,
                    Body=json.dumps(storage_data, ensure_ascii=False, indent=2),
                    ContentType="application/json",
                    ServerSideEncryption=(
                        "AES256" if self.config.enable_encryption else None
                    ),
                )

                self.logger.info(
                    f"Successfully stored item at s3://{self.config.bucket_name}/{s3_key}"
                )

                return {
                    "success": True,
                    "s3_key": s3_key,
                    "prefix": prefix,
                    "attempt": attempt + 1,
                }

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if attempt == 2:  # Last attempt
                    self.logger.error(
                        f"Failed to upload to S3 after 3 attempts: {error_code}"
                    )
                    return {
                        "success": False,
                        "s3_key": s3_key,
                        "error": error_code,
                        "attempts": 3,
                    }
                else:
                    self.logger.warning(
                        f"Upload attempt {attempt + 1} failed: {error_code}, retrying..."
                    )
                    time.sleep(2**attempt)  # Exponential backoff

            except Exception as e:
                if attempt == 2:
                    self.logger.error(f"Unexpected error during upload: {str(e)}")
                    return {
                        "success": False,
                        "s3_key": s3_key,
                        "error": str(e),
                        "attempts": 3,
                    }
                else:
                    time.sleep(2**attempt)

    def trigger_knowledge_base_sync(self, s3_key: str) -> bool:
        """
        Trigger Knowledge Base synchronization for uploaded data

        Args:
            s3_key: S3 key of uploaded data

        Returns:
            True if sync triggered successfully
        """
        try:
            # This would integrate with OpenSearch Serverless
            # For now, just log the sync trigger
            self.logger.info(f"Knowledge Base sync triggered for {s3_key}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to trigger Knowledge Base sync: {str(e)}")
            return False

    def list_stored_data(
        self,
        country: Optional[str] = None,
        source_name: Optional[str] = None,
        date_prefix: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List stored data with optional filtering

        Args:
            country: Filter by country
            source_name: Filter by source name
            date_prefix: Filter by date (YYYY/MM/DD format)

        Returns:
            List of stored data metadata
        """
        try:
            # Build prefix for filtering
            prefix_parts = []
            if country:
                prefix_parts.append(country)
                if date_prefix:
                    prefix_parts.append(date_prefix)
                    if source_name:
                        prefix_parts.append(source_name)
                elif source_name:
                    # Can't filter by source without date in this structure
                    pass

            prefix = "/".join(prefix_parts) + "/" if prefix_parts else ""

            response = self.s3_client.list_objects_v2(
                Bucket=self.config.bucket_name, Prefix=prefix
            )

            objects = []
            for obj in response.get("Contents", []):
                objects.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                        "etag": obj["ETag"],
                    }
                )

            return objects

        except Exception as e:
            self.logger.error(f"Failed to list stored data: {str(e)}")
            return []
