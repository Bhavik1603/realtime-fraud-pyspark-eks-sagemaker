# Real-Time Fraud Detection System

A production-grade real-time fraud detection system using PySpark, AWS Kinesis, SageMaker, and EKS.

## 🏗️ Architecture Overview

```
Synthetic Data → AWS Kinesis → PySpark Streaming → ML Model (SageMaker) → DynamoDB (Alerts) + S3 (Raw Data)
```

## 📋 Project Status

**Current Sprint:** Sprint 1 - Data Producer & Local Development Setup

### Sprint Breakdown
- ✅ **Sprint 1:** Synthetic Data Producer + Kinesis Integration
- ⏳ **Sprint 2:** PySpark Structured Streaming Consumer
- ⏳ **Sprint 3:** ML Model Integration (SageMaker)
- ⏳ **Sprint 4:** Sinks (DynamoDB + S3)
- ⏳ **Sprint 5:** EKS Deployment + Infrastructure as Code

## 🚀 Quick Start (Sprint 1)

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- AWS CLI (optional, for real AWS)

### Local Development with LocalStack

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start LocalStack (simulates AWS locally):**
   ```bash
   docker-compose up -d
   ```

3. **Create Kinesis stream:**
   ```bash
   python scripts/setup_localstack.py
   ```

4. **Run the producer:**
   ```bash
   python -m producer.main --num-transactions 100 --batch-size 10
   ```

### Using Real AWS (Alternative)

1. **Configure AWS credentials:**
   ```bash
   aws configure
   ```

2. **Create Kinesis stream:**
   ```bash
   aws kinesis create-stream --stream-name fraud-transactions --shard-count 1
   ```

3. **Run producer with AWS:**
   ```bash
   python -m producer.main --use-aws --stream-name fraud-transactions
   ```

## 📁 Project Structure

```
realtime-fraud-pyspark-eks-sagemaker/
├── producer/                    # Sprint 1: Data generation & Kinesis producer
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   ├── data_generator.py       # Synthetic transaction generator
│   ├── kinesis_producer.py     # Kinesis client wrapper
│   └── config.py               # Configuration management
├── processor/                   # Sprint 2: PySpark streaming job
│   └── (TBD)
├── ml_model/                    # Sprint 3: ML model integration
│   └── (TBD)
├── infrastructure/              # Sprint 5: Terraform/K8s configs
│   └── (TBD)
├── tests/                       # Unit & integration tests
│   ├── __init__.py
│   └── test_producer.py
├── scripts/                     # Utility scripts
│   └── setup_localstack.py
├── config/                      # Configuration files
│   └── config.yaml
├── docker-compose.yml          # LocalStack setup
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Project metadata
└── README.md
```

## 🎯 Sprint 1 Learning Objectives

1. **Production-grade code structure:** Separation of concerns, modularity
2. **Type hints:** Using Python typing for better code quality
3. **Configuration management:** Externalized config using YAML
4. **AWS SDK:** Working with boto3 and Kinesis
5. **Local development:** Using LocalStack to avoid AWS costs
6. **Error handling & logging:** Proper exception handling and observability

## 📚 Next Steps

After completing Sprint 1, you'll have:
- ✅ A working synthetic data producer
- ✅ Data flowing to Kinesis (local or AWS)
- ✅ Foundation for the streaming processor

Move to Sprint 2 to build the PySpark consumer!
