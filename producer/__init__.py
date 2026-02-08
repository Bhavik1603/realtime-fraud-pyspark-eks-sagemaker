"""
Fraud Detection System - Data Producer Package

This package contains modules for generating synthetic credit card transaction data
and streaming it to AWS Kinesis (or LocalStack for local development).

Modules:
    - config: Configuration management and validation
    - data_generator: Synthetic transaction data generation
    - kinesis_producer: AWS Kinesis producer client wrapper
    - main: Entry point for running the producer
"""

__version__ = "0.1.0"
__author__ = "Your Name"

from producer.config import ProducerConfig
from producer.data_generator import TransactionGenerator
from producer.kinesis_producer import KinesisProducer

__all__ = ["ProducerConfig", "TransactionGenerator", "KinesisProducer"]
