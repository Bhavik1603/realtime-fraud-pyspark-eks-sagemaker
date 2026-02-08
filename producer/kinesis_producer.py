"""
Kinesis Producer Wrapper

Provides a production-grade wrapper around boto3 Kinesis client with:
- Batch processing for efficiency
- Error handling and retries
- Metrics and logging
- Support for LocalStack and real AWS
"""

import json
import time
from typing import Any, Dict, List, Optional

import boto3
import structlog
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = structlog.get_logger(__name__)


class KinesisProducer:
    """
    High-level Kinesis producer with batching, error handling, and monitoring.

    This class wraps the boto3 Kinesis client and provides production-ready
    features for streaming data to Kinesis.
    """

    def __init__(
        self,
        stream_name: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        partition_key_field: str = "transaction_id",
        max_retries: int = 3,
        retry_delay: float = 0.5,
    ) -> None:
        """
        Initialize Kinesis producer.

        Args:
            stream_name: Name of the Kinesis stream
            region: AWS region
            endpoint_url: Custom endpoint (e.g., for LocalStack). If None, uses AWS.
            partition_key_field: Field name to use as partition key
            max_retries: Maximum number of retry attempts for failed records
            retry_delay: Delay between retries in seconds

        Raises:
            ClientError: If unable to connect to Kinesis
        """
        self.stream_name = stream_name
        self.partition_key_field = partition_key_field
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Configure boto3 client with retries
        boto_config = Config(
            region_name=region,
            retries={"max_attempts": max_retries, "mode": "standard"},
            connect_timeout=5,
            read_timeout=10,
        )

        # Create Kinesis client
        client_kwargs: Dict[str, Any] = {"config": boto_config}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
            # For LocalStack, we need dummy credentials
            client_kwargs["aws_access_key_id"] = "test"
            client_kwargs["aws_secret_access_key"] = "test"

        self.client = boto3.client("kinesis", **client_kwargs)

        # Metrics tracking
        self.metrics = {
            "total_records_sent": 0,
            "total_records_failed": 0,
            "total_batches_sent": 0,
            "total_bytes_sent": 0,
        }

        logger.info(
            "Kinesis producer initialized",
            stream_name=stream_name,
            region=region,
            endpoint_url=endpoint_url or "AWS",
        )

    def verify_stream_exists(self) -> bool:
        """
        Verify that the Kinesis stream exists and is active.

        Returns:
            True if stream exists and is active, False otherwise

        Raises:
            ClientError: If unable to describe stream
        """
        try:
            response = self.client.describe_stream(StreamName=self.stream_name)
            status = response["StreamDescription"]["StreamStatus"]

            logger.info(
                "Stream status checked",
                stream_name=self.stream_name,
                status=status,
            )

            return status == "ACTIVE"

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logger.warning("Stream not found", stream_name=self.stream_name)
                return False
            raise

    def create_stream_if_not_exists(self, shard_count: int = 1) -> None:
        """
        Create the Kinesis stream if it doesn't exist.

        Args:
            shard_count: Number of shards for the new stream

        Raises:
            ClientError: If unable to create stream
        """
        try:
            if self.verify_stream_exists():
                logger.info("Stream already exists", stream_name=self.stream_name)
                return

            logger.info(
                "Creating stream",
                stream_name=self.stream_name,
                shard_count=shard_count,
            )

            self.client.create_stream(StreamName=self.stream_name, ShardCount=shard_count)

            # Wait for stream to become active
            waiter = self.client.get_waiter("stream_exists")
            waiter.wait(StreamName=self.stream_name)

            logger.info("Stream created successfully", stream_name=self.stream_name)

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceInUseException":
                logger.info("Stream already exists (concurrent creation)")
            else:
                logger.error("Failed to create stream", error=str(e))
                raise

    def put_record(self, record: Dict[str, Any], partition_key: Optional[str] = None) -> bool:
        """
        Send a single record to Kinesis.

        Args:
            record: Dictionary to send (will be JSON serialized)
            partition_key: Optional partition key. If None, uses partition_key_field.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Serialize record to JSON
            data = json.dumps(record, ensure_ascii=False)

            # Determine partition key
            if partition_key is None:
                partition_key = str(record.get(self.partition_key_field, "default"))

            # Send to Kinesis
            response = self.client.put_record(
                StreamName=self.stream_name, Data=data.encode("utf-8"), PartitionKey=partition_key
            )

            # Update metrics
            self.metrics["total_records_sent"] += 1
            self.metrics["total_bytes_sent"] += len(data.encode("utf-8"))

            logger.debug(
                "Record sent",
                shard_id=response.get("ShardId"),
                sequence_number=response.get("SequenceNumber"),
            )

            return True

        except (BotoCoreError, ClientError) as e:
            logger.error("Failed to send record", error=str(e), record_id=partition_key)
            self.metrics["total_records_failed"] += 1
            return False

    def put_records_batch(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Send a batch of records to Kinesis using put_records API.

        This is more efficient than multiple put_record calls.

        Args:
            records: List of dictionaries to send

        Returns:
            Dictionary with success/failure counts
        """
        if not records:
            return {"successful": 0, "failed": 0}

        try:
            # Prepare batch
            kinesis_records = []
            for record in records:
                data = json.dumps(record, ensure_ascii=False)
                partition_key = str(record.get(self.partition_key_field, "default"))

                kinesis_records.append({"Data": data.encode("utf-8"), "PartitionKey": partition_key})

            # Send batch
            response = self.client.put_records(StreamName=self.stream_name, Records=kinesis_records)

            # Process response
            failed_count = response.get("FailedRecordCount", 0)
            successful_count = len(records) - failed_count

            # Update metrics
            self.metrics["total_records_sent"] += successful_count
            self.metrics["total_records_failed"] += failed_count
            self.metrics["total_batches_sent"] += 1

            # Calculate bytes sent
            total_bytes = sum(len(json.dumps(r).encode("utf-8")) for r in records)
            self.metrics["total_bytes_sent"] += total_bytes

            logger.info(
                "Batch sent",
                batch_size=len(records),
                successful=successful_count,
                failed=failed_count,
            )

            # Retry failed records if any
            if failed_count > 0:
                self._handle_failed_records(records, response["Records"])

            return {"successful": successful_count, "failed": failed_count}

        except (BotoCoreError, ClientError) as e:
            logger.error("Failed to send batch", error=str(e), batch_size=len(records))
            self.metrics["total_records_failed"] += len(records)
            return {"successful": 0, "failed": len(records)}

    def _handle_failed_records(
        self, original_records: List[Dict[str, Any]], response_records: List[Dict[str, Any]]
    ) -> None:
        """
        Handle and retry failed records from a batch.

        Args:
            original_records: Original records that were sent
            response_records: Response records from put_records
        """
        failed_records = []
        for idx, response_record in enumerate(response_records):
            if "ErrorCode" in response_record:
                logger.warning(
                    "Record failed",
                    error_code=response_record["ErrorCode"],
                    error_message=response_record.get("ErrorMessage"),
                )
                failed_records.append(original_records[idx])

        # Retry failed records (simple retry, could be enhanced with exponential backoff)
        if failed_records:
            logger.info("Retrying failed records", count=len(failed_records))
            time.sleep(self.retry_delay)
            self.put_records_batch(failed_records)

    def get_metrics(self) -> Dict[str, int]:
        """
        Get producer metrics.

        Returns:
            Dictionary containing metrics
        """
        return self.metrics.copy()

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self.metrics = {
            "total_records_sent": 0,
            "total_records_failed": 0,
            "total_batches_sent": 0,
            "total_bytes_sent": 0,
        }
        logger.info("Metrics reset")

    def close(self) -> None:
        """
        Close the Kinesis client and clean up resources.

        Logs final metrics before closing.
        """
        logger.info("Closing Kinesis producer", final_metrics=self.metrics)
        # boto3 client doesn't need explicit closing, but we log metrics
