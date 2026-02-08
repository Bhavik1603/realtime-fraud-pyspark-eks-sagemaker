# Sprint 1: Data Producer & Local Development Setup

## 🎯 Sprint Goals

By the end of Sprint 1, you will have:
1. ✅ A production-grade project structure
2. ✅ Synthetic transaction data generator with realistic fraud patterns
3. ✅ Kinesis producer that streams data to AWS or LocalStack
4. ✅ Local development environment using Docker
5. ✅ Unit tests and proper logging

## 📚 What You'll Learn

### Technical Skills
- **Python Best Practices:** Type hints, dataclasses, structured logging
- **AWS Kinesis:** Understanding streams, partitions, and batching
- **Configuration Management:** YAML configs, environment variables
- **Testing:** Unit testing with pytest, mocking AWS services
- **Local Development:** Using LocalStack to simulate AWS locally

### Architecture Patterns
- **Producer Pattern:** Generating and streaming data
- **Separation of Concerns:** Config, generation, and streaming as separate modules
- **Error Handling:** Retry logic, graceful degradation
- **Observability:** Structured logging, metrics collection

## 🚀 Step-by-Step Guide

### Step 1: Environment Setup (15 minutes)

1. **Install Python dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Start LocalStack:**
   ```powershell
   docker-compose up -d
   ```

3. **Verify LocalStack is running:**
   ```powershell
   docker ps
   ```
   You should see the `fraud-detection-localstack` container.

4. **Create AWS resources in LocalStack:**
   ```powershell
   python scripts/setup_localstack.py
   ```

### Step 2: Understanding the Code (30 minutes)

Read through these files in order:

1. **`config/config.yaml`** - Application configuration
2. **`producer/config.py`** - Configuration management with dataclasses
3. **`producer/data_generator.py`** - Synthetic data generation
4. **`producer/kinesis_producer.py`** - Kinesis client wrapper
5. **`producer/main.py`** - Main orchestration logic

**Key Concepts to Understand:**
- How dataclasses simplify configuration
- The fraud patterns in `TransactionGenerator`
- Batch processing in `KinesisProducer.put_records_batch()`
- Error handling and retry logic

### Step 3: Run the Producer (15 minutes)

1. **Run with default settings (100 transactions):**
   ```powershell
   python -m producer.main
   ```

2. **Run with custom parameters:**
   ```powershell
   python -m producer.main --num-transactions 500 --batch-size 20
   ```

3. **Check the output:**
   - You should see structured JSON logs
   - Batch statistics (fraud count, success/failure)
   - Final metrics (records sent, throughput, etc.)

### Step 4: Verify Data in Kinesis (10 minutes)

**Check stream status:**
```powershell
aws kinesis describe-stream --stream-name fraud-transactions --endpoint-url http://localhost:4566 --region us-east-1
```

**Get a shard iterator:**
```powershell
aws kinesis get-shard-iterator --stream-name fraud-transactions --shard-id shardId-000000000000 --shard-iterator-type TRIM_HORIZON --endpoint-url http://localhost:4566 --region us-east-1
```

**Read records (replace SHARD_ITERATOR with output from above):**
```powershell
aws kinesis get-records --shard-iterator "SHARD_ITERATOR" --endpoint-url http://localhost:4566 --region us-east-1
```

### Step 5: Run Tests (10 minutes)

1. **Run all tests:**
   ```powershell
   pytest tests/ -v
   ```

2. **Run with coverage:**
   ```powershell
   pytest tests/ -v --cov=producer --cov-report=html
   ```

3. **View coverage report:**
   ```powershell
   start htmlcov/index.html
   ```

### Step 6: Code Quality Checks (Optional, 10 minutes)

1. **Type checking with mypy:**
   ```powershell
   mypy producer/
   ```

2. **Code formatting with black:**
   ```powershell
   black producer/ tests/
   ```

3. **Import sorting:**
   ```powershell
   isort producer/ tests/
   ```

4. **Linting with flake8:**
   ```powershell
   flake8 producer/ tests/ --max-line-length=100
   ```

## 🧪 Experimentation Tasks

Try these to deepen your understanding:

### Task 1: Modify Fraud Patterns
Edit `producer/data_generator.py`:
- Change the fraud ratio to 10%
- Add a new fraud pattern (e.g., transactions from specific countries)
- Add a new transaction field (e.g., `device_type`)

### Task 2: Add Monitoring
Enhance `producer/main.py`:
- Add a progress bar using `tqdm`
- Export metrics to a JSON file
- Add a real-time dashboard (simple print statements showing current throughput)

### Task 3: Configuration Experiments
- Try loading config from environment variables instead of YAML
- Add a new configuration parameter (e.g., `max_amount_threshold`)
- Override config values via command-line arguments

### Task 4: AWS Integration (Optional)
If you have AWS credentials:
```powershell
python -m producer.main --use-aws --stream-name your-stream-name
```

## 📊 Sample Output

When you run the producer, you should see output like:
```json
{"event": "Starting fraud transaction producer", "stream_name": "fraud-transactions", "num_transactions": 100}
{"event": "Generated batch", "batch_number": 1, "fraud_count": 1, "fraud_percentage": 10.0}
{"event": "Batch sent to Kinesis", "total_sent": 10, "progress_pct": 10.0}
...
{"event": "Producer finished", "total_records": 100, "records_per_second": 45.2}
```

## 🎓 Learning Checkpoints

Before moving to Sprint 2, make sure you can answer:

1. **What is a partition key and why is it important in Kinesis?**
   - Answer: Determines which shard records go to, enables parallel processing

2. **Why do we use batching instead of sending one record at a time?**
   - Answer: Reduces API calls, increases throughput, is more cost-effective

3. **What are the fraud indicators in our synthetic data?**
   - Answer: High amounts, unusual hours, distance from home, rapid transactions

4. **How does LocalStack help in development?**
   - Answer: Simulates AWS locally, saves costs, enables offline development

5. **What is structured logging and why use it?**
   - Answer: JSON-formatted logs that are easier to parse and analyze at scale

## 🐛 Troubleshooting

### Issue: LocalStack not connecting
**Solution:**
```powershell
docker-compose down
docker-compose up -d
# Wait 10 seconds
python scripts/setup_localstack.py
```

### Issue: Import errors
**Solution:**
```powershell
# Make sure you're in the project root
cd d:\realtime-fraud-pyspark-eks-sagemaker
pip install -r requirements.txt
```

### Issue: Stream doesn't exist
**Solution:**
```powershell
python scripts/setup_localstack.py
```

## 📈 Next Steps: Sprint 2 Preview

In Sprint 2, you'll build:
- **PySpark Structured Streaming consumer**
- **Windowed aggregations** (e.g., total spend in last 10 minutes)
- **Watermarking** for handling late data
- **Stream-to-batch processing**

Get ready to level up your streaming skills! 🚀

## 💡 Resume Talking Points

After Sprint 1, you can discuss:
- "Built a production-grade data producer with retry logic and monitoring"
- "Implemented synthetic data generation with realistic fraud patterns"
- "Used LocalStack for cost-effective local AWS development"
- "Applied SOLID principles and type-safe Python development"
- "Achieved X% test coverage with pytest"

---

**Questions or Issues?** Review the code comments—they're your best documentation!
