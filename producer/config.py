"""
Configuration Management Module

Handles loading and validation of configuration from YAML files and environment variables.
Provides type-safe configuration objects using dataclasses.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


@dataclass
class LocalStackConfig:
    """LocalStack-specific configuration for local AWS simulation."""

    enabled: bool = True
    endpoint_url: str = "http://localhost:4566"
    access_key_id: str = "test"
    secret_access_key: str = "test"


@dataclass
class AWSConfig:
    """AWS service configuration."""

    region: str = "us-east-1"
    localstack: LocalStackConfig = field(default_factory=LocalStackConfig)


@dataclass
class ProducerConfig:
    """
    Producer configuration for synthetic data generation and Kinesis streaming.

    Attributes:
        stream_name: Name of the Kinesis stream
        partition_key_field: Field name to use for Kinesis partitioning
        batch_size: Number of records to send in each batch
        batch_interval_ms: Milliseconds to wait between batches
        max_records_per_second: Rate limiting threshold
        fraud_ratio: Proportion of fraudulent transactions (0.0 to 1.0)
        num_merchants: Number of unique merchant IDs to generate
        num_customers: Number of unique customer IDs to generate
    """

    stream_name: str = "fraud-transactions"
    partition_key_field: str = "transaction_id"
    batch_size: int = 10
    batch_interval_ms: int = 1000
    max_records_per_second: int = 100
    fraud_ratio: float = 0.05
    num_merchants: int = 1000
    num_customers: int = 5000


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "json"
    output: str = "console"


@dataclass
class AppConfig:
    """
    Application-wide configuration container.

    Combines all configuration sections into a single object.
    """

    producer: ProducerConfig
    aws: AWSConfig
    logging: LoggingConfig

    @classmethod
    def from_yaml(cls, config_path: Optional[Path] = None) -> "AppConfig":
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to config.yaml file. If None, uses default location.

        Returns:
            AppConfig instance populated from YAML

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is malformed
        """
        if config_path is None:
            # Default to config/config.yaml relative to project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config_dict = yaml.safe_load(f)

        # Parse nested configurations
        producer_config = ProducerConfig(**config_dict.get("producer", {}))

        aws_dict = config_dict.get("aws", {})
        localstack_config = LocalStackConfig(**aws_dict.get("localstack", {}))
        aws_config = AWSConfig(
            region=aws_dict.get("region", "us-east-1"), localstack=localstack_config
        )

        logging_config = LoggingConfig(**config_dict.get("logging", {}))

        return cls(producer=producer_config, aws=aws_config, logging=logging_config)

    @classmethod
    def from_env(cls) -> "AppConfig":
        """
        Load configuration from environment variables.

        Environment variables should be prefixed with the section name:
        - PRODUCER_STREAM_NAME
        - AWS_REGION
        - LOGGING_LEVEL
        etc.

        Returns:
            AppConfig instance populated from environment variables
        """
        producer_config = ProducerConfig(
            stream_name=os.getenv("PRODUCER_STREAM_NAME", "fraud-transactions"),
            batch_size=int(os.getenv("PRODUCER_BATCH_SIZE", "10")),
            fraud_ratio=float(os.getenv("PRODUCER_FRAUD_RATIO", "0.05")),
        )

        localstack_enabled = os.getenv("AWS_LOCALSTACK_ENABLED", "true").lower() == "true"
        localstack_config = LocalStackConfig(
            enabled=localstack_enabled,
            endpoint_url=os.getenv("AWS_LOCALSTACK_ENDPOINT", "http://localhost:4566"),
        )

        aws_config = AWSConfig(
            region=os.getenv("AWS_REGION", "us-east-1"), localstack=localstack_config
        )

        logging_config = LoggingConfig(
            level=os.getenv("LOGGING_LEVEL", "INFO"),
            format=os.getenv("LOGGING_FORMAT", "json"),
        )

        return cls(producer=producer_config, aws=aws_config, logging=logging_config)


def get_config(config_path: Optional[Path] = None, use_env: bool = False) -> AppConfig:
    """
    Convenience function to get configuration.

    Args:
        config_path: Path to YAML config file
        use_env: If True, load from environment variables; if False, load from YAML

    Returns:
        AppConfig instance
    """
    if use_env:
        return AppConfig.from_env()
    return AppConfig.from_yaml(config_path)
