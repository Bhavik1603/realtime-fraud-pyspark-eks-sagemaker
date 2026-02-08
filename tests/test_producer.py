"""Tests for the fraud detection producer module."""

import pytest

from producer.config import AppConfig, ProducerConfig
from producer.data_generator import TransactionGenerator


class TestTransactionGenerator:
    """Test cases for TransactionGenerator class."""

    def test_generator_initialization(self) -> None:
        """Test that generator initializes with correct parameters."""
        generator = TransactionGenerator(fraud_ratio=0.1, num_merchants=100, num_customers=200)

        assert generator.fraud_ratio == 0.1
        assert generator.num_merchants == 100
        assert generator.num_customers == 200
        assert len(generator.merchants) == 100
        assert len(generator.customers) == 200

    def test_invalid_fraud_ratio(self) -> None:
        """Test that invalid fraud ratio raises ValueError."""
        with pytest.raises(ValueError):
            TransactionGenerator(fraud_ratio=1.5)

        with pytest.raises(ValueError):
            TransactionGenerator(fraud_ratio=-0.1)

    def test_generate_transaction_structure(self) -> None:
        """Test that generated transaction has required fields."""
        generator = TransactionGenerator(seed=42)
        transaction = generator.generate_transaction()

        required_fields = [
            "transaction_id",
            "timestamp",
            "customer_id",
            "merchant_id",
            "merchant_name",
            "merchant_category",
            "amount",
            "currency",
            "is_fraud",
        ]

        for field in required_fields:
            assert field in transaction, f"Missing field: {field}"

    def test_generate_legitimate_transaction(self) -> None:
        """Test generation of legitimate transaction."""
        generator = TransactionGenerator(seed=42)
        transaction = generator.generate_transaction(is_fraud=False)

        assert transaction["is_fraud"] is False
        assert transaction["amount"] > 0
        assert transaction["currency"] == "USD"

    def test_generate_fraudulent_transaction(self) -> None:
        """Test generation of fraudulent transaction."""
        generator = TransactionGenerator(seed=42)
        transaction = generator.generate_transaction(is_fraud=True)

        assert transaction["is_fraud"] is True

    def test_generate_batch(self) -> None:
        """Test batch generation."""
        generator = TransactionGenerator(seed=42)
        batch = generator.generate_batch(batch_size=50)

        assert len(batch) == 50
        assert all(isinstance(t, dict) for t in batch)

    def test_fraud_ratio_in_batch(self) -> None:
        """Test that fraud ratio is approximately correct in large batch."""
        generator = TransactionGenerator(fraud_ratio=0.1, seed=42)
        batch = generator.generate_batch(batch_size=1000)

        fraud_count = sum(1 for t in batch if t["is_fraud"])
        fraud_percentage = fraud_count / len(batch)

        # Allow 5% tolerance for randomness
        assert 0.05 <= fraud_percentage <= 0.15

    def test_to_json(self) -> None:
        """Test JSON serialization."""
        generator = TransactionGenerator(seed=42)
        transaction = generator.generate_transaction()
        json_str = generator.to_json(transaction)

        assert isinstance(json_str, str)
        assert "transaction_id" in json_str
        assert "amount" in json_str

    def test_fraud_statistics(self) -> None:
        """Test fraud statistics calculation."""
        generator = TransactionGenerator(seed=42)
        transactions = [
            generator.generate_transaction(is_fraud=False) for _ in range(80)
        ] + [generator.generate_transaction(is_fraud=True) for _ in range(20)]

        stats = generator.get_fraud_statistics(transactions)

        assert stats["total_transactions"] == 100
        assert stats["fraud_count"] == 20
        assert stats["legitimate_count"] == 80
        assert stats["fraud_percentage"] == 20.0

    def test_reproducibility_with_seed(self) -> None:
        """Test that same seed produces same results."""
        gen1 = TransactionGenerator(seed=123)
        gen2 = TransactionGenerator(seed=123)

        trans1 = gen1.generate_transaction()
        trans2 = gen2.generate_transaction()

        assert trans1["merchant_id"] == trans2["merchant_id"]
        assert trans1["customer_id"] == trans2["customer_id"]


class TestProducerConfig:
    """Test cases for configuration management."""

    def test_config_defaults(self) -> None:
        """Test default configuration values."""
        config = ProducerConfig()

        assert config.stream_name == "fraud-transactions"
        assert config.batch_size == 10
        assert config.fraud_ratio == 0.05

    def test_config_from_yaml(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test loading configuration from YAML file."""
        # Create temporary config file
        config_file = tmp_path / "test_config.yaml"
        config_content = """
producer:
  stream_name: "test-stream"
  batch_size: 20
  fraud_ratio: 0.1

aws:
  region: "us-west-2"
  localstack:
    enabled: true

logging:
  level: "DEBUG"
"""
        config_file.write_text(config_content)

        # Load config
        app_config = AppConfig.from_yaml(config_file)

        assert app_config.producer.stream_name == "test-stream"
        assert app_config.producer.batch_size == 20
        assert app_config.producer.fraud_ratio == 0.1
        assert app_config.aws.region == "us-west-2"
        assert app_config.logging.level == "DEBUG"


# Add marker for integration tests (requires LocalStack)
@pytest.mark.integration
class TestKinesisProducerIntegration:
    """Integration tests for Kinesis producer (requires LocalStack)."""

    @pytest.mark.skip(reason="Requires LocalStack to be running")
    def test_kinesis_connection(self) -> None:
        """Test connection to LocalStack Kinesis."""
        from producer.kinesis_producer import KinesisProducer

        producer = KinesisProducer(
            stream_name="test-stream",
            endpoint_url="http://localhost:4566",
        )

        # This would require LocalStack to be running
        # producer.verify_stream_exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
