"""
Producer Main Entry Point

Orchestrates the synthetic data generation and streaming to Kinesis.
Provides CLI interface for running the producer with various configurations.
"""

import argparse
import signal
import sys
import time
from pathlib import Path
from typing import Optional

import structlog

from producer.config import get_config
from producer.data_generator import TransactionGenerator
from producer.kinesis_producer import KinesisProducer

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum: int, frame: Optional[object]) -> None:
    """
    Handle shutdown signals (SIGINT, SIGTERM) for graceful shutdown.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global shutdown_requested
    logger = structlog.get_logger(__name__)
    logger.warning("Shutdown signal received", signal=signum)
    shutdown_requested = True


def setup_logging(level: str = "INFO", log_format: str = "json") -> None:
    """
    Configure structured logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ('json' or 'text')
    """
    log_level = getattr(structlog.stdlib, level.upper(), structlog.stdlib.INFO)

    if log_format == "json":
        processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def run_producer(
    num_transactions: int,
    batch_size: int,
    use_aws: bool = False,
    stream_name: Optional[str] = None,
    config_path: Optional[Path] = None,
) -> None:
    """
    Run the transaction producer.

    Args:
        num_transactions: Total number of transactions to generate
        batch_size: Number of transactions per batch
        use_aws: If True, use real AWS; if False, use LocalStack
        stream_name: Override stream name from config
        config_path: Path to config file (optional)
    """
    logger = structlog.get_logger(__name__)

    # Load configuration
    logger.info("Loading configuration")
    config = get_config(config_path=config_path)

    # Setup logging
    setup_logging(level=config.logging.level, log_format=config.logging.format)

    # Override config with CLI parameters
    if stream_name:
        config.producer.stream_name = stream_name
    if batch_size:
        config.producer.batch_size = batch_size

    # Determine endpoint URL
    endpoint_url = None if use_aws else config.aws.localstack.endpoint_url

    logger.info(
        "Starting fraud transaction producer",
        stream_name=config.producer.stream_name,
        num_transactions=num_transactions,
        batch_size=config.producer.batch_size,
        fraud_ratio=config.producer.fraud_ratio,
        environment="AWS" if use_aws else "LocalStack",
    )

    # Initialize components
    try:
        # Create transaction generator
        generator = TransactionGenerator(
            fraud_ratio=config.producer.fraud_ratio,
            num_merchants=config.producer.num_merchants,
            num_customers=config.producer.num_customers,
        )
        logger.info("Transaction generator initialized")

        # Create Kinesis producer
        producer = KinesisProducer(
            stream_name=config.producer.stream_name,
            region=config.aws.region,
            endpoint_url=endpoint_url,
            partition_key_field=config.producer.partition_key_field,
        )
        logger.info("Kinesis producer initialized")

        # Verify or create stream
        if not producer.verify_stream_exists():
            logger.warning("Stream does not exist, creating...")
            producer.create_stream_if_not_exists(shard_count=1)
            # Wait a bit for stream to be ready
            time.sleep(2)

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Produce transactions in batches
        total_sent = 0
        batch_count = 0
        start_time = time.time()

        while total_sent < num_transactions and not shutdown_requested:
            # Calculate batch size (don't exceed num_transactions)
            current_batch_size = min(config.producer.batch_size, num_transactions - total_sent)

            # Generate batch
            transactions = generator.generate_batch(current_batch_size)

            # Get fraud statistics for this batch
            fraud_stats = generator.get_fraud_statistics(transactions)

            logger.info(
                "Generated batch",
                batch_number=batch_count + 1,
                batch_size=current_batch_size,
                fraud_count=fraud_stats["fraud_count"],
                fraud_percentage=fraud_stats["fraud_percentage"],
            )

            # Send to Kinesis
            result = producer.put_records_batch(transactions)

            total_sent += result["successful"]
            batch_count += 1

            logger.info(
                "Batch sent to Kinesis",
                total_sent=total_sent,
                target=num_transactions,
                progress_pct=round((total_sent / num_transactions) * 100, 2),
            )

            # Rate limiting (optional)
            if config.producer.batch_interval_ms > 0 and total_sent < num_transactions:
                time.sleep(config.producer.batch_interval_ms / 1000.0)

        # Calculate statistics
        elapsed_time = time.time() - start_time
        metrics = producer.get_metrics()

        logger.info(
            "Producer finished",
            total_records=total_sent,
            batches=batch_count,
            elapsed_seconds=round(elapsed_time, 2),
            records_per_second=round(total_sent / elapsed_time, 2) if elapsed_time > 0 else 0,
            total_bytes=metrics["total_bytes_sent"],
            failed_records=metrics["total_records_failed"],
        )

        # Clean up
        producer.close()

    except KeyboardInterrupt:
        logger.warning("Producer interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Producer failed", error=str(e), exception_type=type(e).__name__)
        raise


def main() -> None:
    """
    Main entry point for the producer CLI.

    Parses command-line arguments and runs the producer.
    """
    parser = argparse.ArgumentParser(
        description="Fraud Detection Transaction Producer - Streams synthetic data to Kinesis",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--num-transactions",
        type=int,
        default=100,
        help="Total number of transactions to generate",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of transactions per batch",
    )

    parser.add_argument(
        "--use-aws",
        action="store_true",
        help="Use real AWS instead of LocalStack",
    )

    parser.add_argument(
        "--stream-name",
        type=str,
        help="Override Kinesis stream name from config",
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config.yaml file",
    )

    args = parser.parse_args()

    # Run producer
    run_producer(
        num_transactions=args.num_transactions,
        batch_size=args.batch_size,
        use_aws=args.use_aws,
        stream_name=args.stream_name,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()
