"""
LocalStack Setup Script

Initializes LocalStack environment for local development:
- Creates Kinesis stream
- Verifies stream is active
- Sets up any other required AWS resources
"""

import sys
import time
from typing import Optional

import boto3
import structlog
from botocore.exceptions import ClientError

# Configure simple logging for setup script
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger(__name__)


def create_kinesis_stream(
    stream_name: str,
    shard_count: int = 1,
    endpoint_url: str = "http://localhost:4566",
    region: str = "us-east-1",
) -> bool:
    """
    Create a Kinesis stream in LocalStack.

    Args:
        stream_name: Name of the stream to create
        shard_count: Number of shards
        endpoint_url: LocalStack endpoint URL
        region: AWS region

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(
            "Creating Kinesis stream",
            stream_name=stream_name,
            shard_count=shard_count,
            endpoint=endpoint_url,
        )

        # Create Kinesis client
        kinesis = boto3.client(
            "kinesis",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )

        # Check if stream already exists
        try:
            response = kinesis.describe_stream(StreamName=stream_name)
            status = response["StreamDescription"]["StreamStatus"]
            logger.info("Stream already exists", stream_name=stream_name, status=status)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceNotFoundException":
                raise

        # Create the stream
        kinesis.create_stream(StreamName=stream_name, ShardCount=shard_count)

        # Wait for stream to become active
        logger.info("Waiting for stream to become active...")
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = kinesis.describe_stream(StreamName=stream_name)
                status = response["StreamDescription"]["StreamStatus"]

                if status == "ACTIVE":
                    logger.info("Stream is active", stream_name=stream_name)
                    return True

                logger.info(
                    "Stream not ready yet",
                    status=status,
                    attempt=attempt + 1,
                    max_attempts=max_attempts,
                )
                time.sleep(2)

            except ClientError as e:
                logger.warning("Error checking stream status", error=str(e))
                time.sleep(2)

        logger.error("Stream did not become active in time")
        return False

    except Exception as e:
        logger.error("Failed to create stream", error=str(e), exception_type=type(e).__name__)
        return False


def verify_localstack_connection(endpoint_url: str = "http://localhost:4566") -> bool:
    """
    Verify that LocalStack is running and accessible.

    Args:
        endpoint_url: LocalStack endpoint URL

    Returns:
        True if LocalStack is accessible, False otherwise
    """
    try:
        logger.info("Verifying LocalStack connection", endpoint=endpoint_url)

        # Try to list Kinesis streams as a health check
        kinesis = boto3.client(
            "kinesis",
            endpoint_url=endpoint_url,
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )

        kinesis.list_streams()
        logger.info("LocalStack connection successful")
        return True

    except Exception as e:
        logger.error(
            "Failed to connect to LocalStack",
            error=str(e),
            hint="Make sure LocalStack is running: docker-compose up -d",
        )
        return False


def setup_s3_bucket(
    bucket_name: str = "fraud-detection-data",
    endpoint_url: str = "http://localhost:4566",
    region: str = "us-east-1",
) -> bool:
    """
    Create S3 bucket for storing processed data (for future sprints).

    Args:
        bucket_name: Name of the bucket to create
        endpoint_url: LocalStack endpoint URL
        region: AWS region

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Creating S3 bucket", bucket_name=bucket_name)

        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )

        # Check if bucket exists
        try:
            s3.head_bucket(Bucket=bucket_name)
            logger.info("S3 bucket already exists", bucket_name=bucket_name)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] != "404":
                raise

        # Create bucket
        s3.create_bucket(Bucket=bucket_name)
        logger.info("S3 bucket created", bucket_name=bucket_name)
        return True

    except Exception as e:
        logger.error("Failed to create S3 bucket", error=str(e))
        return False


def main() -> None:
    """Main setup script for LocalStack resources."""
    logger.info("=" * 60)
    logger.info("LocalStack Setup - Fraud Detection System")
    logger.info("=" * 60)

    # Step 1: Verify LocalStack is running
    if not verify_localstack_connection():
        logger.error("Cannot proceed without LocalStack connection")
        logger.info("Start LocalStack with: docker-compose up -d")
        sys.exit(1)

    # Step 2: Create Kinesis stream
    stream_created = create_kinesis_stream(stream_name="fraud-transactions", shard_count=1)

    if not stream_created:
        logger.error("Failed to create Kinesis stream")
        sys.exit(1)

    # Step 3: Create S3 bucket (for future use)
    bucket_created = setup_s3_bucket(bucket_name="fraud-detection-data")

    # Summary
    logger.info("=" * 60)
    logger.info("Setup Summary")
    logger.info("=" * 60)
    logger.info(
        "Kinesis Stream",
        status="✓ Created" if stream_created else "✗ Failed",
        name="fraud-transactions",
    )
    logger.info(
        "S3 Bucket",
        status="✓ Created" if bucket_created else "✗ Failed",
        name="fraud-detection-data",
    )
    logger.info("=" * 60)

    if stream_created:
        logger.info("Setup completed successfully!")
        logger.info("You can now run the producer: python -m producer.main")
    else:
        logger.error("Setup incomplete - please check errors above")
        sys.exit(1)


if __name__ == "__main__":
    main()
