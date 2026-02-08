# PowerShell automation script for common tasks
# Sprint 1: Fraud Detection System

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host @"
Fraud Detection System - Development Commands

Usage: .\run.ps1 <command>

Available commands:

Setup & Environment:
  setup              Install all dependencies
  localstack-start   Start LocalStack (Docker)
  localstack-stop    Stop LocalStack
  localstack-setup   Initialize AWS resources in LocalStack
  clean              Remove generated files and caches

Development:
  producer           Run the producer (default: 100 transactions)
  producer-demo      Run producer with more transactions (1000)
  test               Run all tests
  test-cov           Run tests with coverage report
  lint               Run code quality checks (mypy, flake8, black)
  format             Auto-format code with black and isort

AWS Verification:
  verify-stream      Check Kinesis stream status
  read-stream        Read sample records from Kinesis

Help:
  help               Show this help message

Examples:
  .\run.ps1 setup
  .\run.ps1 localstack-start
  .\run.ps1 producer
  .\run.ps1 test-cov

"@
}

function Setup-Environment {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
    pip install -r requirements.txt
    Write-Host "✅ Dependencies installed!" -ForegroundColor Green
}

function Start-LocalStack {
    Write-Host "🐳 Starting LocalStack..." -ForegroundColor Cyan
    docker-compose up -d
    Write-Host "⏳ Waiting for LocalStack to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    Write-Host "✅ LocalStack started!" -ForegroundColor Green
}

function Stop-LocalStack {
    Write-Host "🛑 Stopping LocalStack..." -ForegroundColor Cyan
    docker-compose down
    Write-Host "✅ LocalStack stopped!" -ForegroundColor Green
}

function Setup-LocalStack {
    Write-Host "⚙️ Setting up LocalStack resources..." -ForegroundColor Cyan
    python scripts/setup_localstack.py
}

function Run-Producer {
    param([int]$NumTransactions = 100)
    Write-Host "🚀 Running producer ($NumTransactions transactions)..." -ForegroundColor Cyan
    python -m producer.main --num-transactions $NumTransactions --batch-size 10
}

function Run-Tests {
    Write-Host "🧪 Running tests..." -ForegroundColor Cyan
    pytest tests/ -v
}

function Run-TestsWithCoverage {
    Write-Host "🧪 Running tests with coverage..." -ForegroundColor Cyan
    pytest tests/ -v --cov=producer --cov-report=term-missing --cov-report=html
    Write-Host "📊 Coverage report generated at htmlcov/index.html" -ForegroundColor Green
}

function Run-Lint {
    Write-Host "🔍 Running code quality checks..." -ForegroundColor Cyan
    
    Write-Host "`n--- Type Checking (mypy) ---" -ForegroundColor Yellow
    mypy producer/
    
    Write-Host "`n--- Linting (flake8) ---" -ForegroundColor Yellow
    flake8 producer/ tests/ --max-line-length=100 --statistics
    
    Write-Host "`n--- Format Check (black) ---" -ForegroundColor Yellow
    black --check producer/ tests/
    
    Write-Host "✅ Linting complete!" -ForegroundColor Green
}

function Format-Code {
    Write-Host "✨ Formatting code..." -ForegroundColor Cyan
    black producer/ tests/
    isort producer/ tests/
    Write-Host "✅ Code formatted!" -ForegroundColor Green
}

function Verify-Stream {
    Write-Host "🔍 Checking Kinesis stream..." -ForegroundColor Cyan
    aws kinesis describe-stream --stream-name fraud-transactions --endpoint-url http://localhost:4566 --region us-east-1
}

function Read-Stream {
    Write-Host "📖 Reading from Kinesis stream..." -ForegroundColor Cyan
    
    # Get shard iterator
    $shardIterator = aws kinesis get-shard-iterator --stream-name fraud-transactions --shard-id shardId-000000000000 --shard-iterator-type TRIM_HORIZON --endpoint-url http://localhost:4566 --region us-east-1 --query 'ShardIterator' --output text
    
    if ($shardIterator) {
        Write-Host "Reading records..." -ForegroundColor Yellow
        aws kinesis get-records --shard-iterator $shardIterator --endpoint-url http://localhost:4566 --region us-east-1 --query 'Records[0:5]'
    }
}

function Clean-Project {
    Write-Host "🧹 Cleaning project..." -ForegroundColor Cyan
    
    # Remove Python cache
    Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
    Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
    Get-ChildItem -Recurse -Filter "*.pyo" | Remove-Item -Force
    
    # Remove test artifacts
    if (Test-Path ".pytest_cache") { Remove-Item -Recurse -Force ".pytest_cache" }
    if (Test-Path "htmlcov") { Remove-Item -Recurse -Force "htmlcov" }
    if (Test-Path ".coverage") { Remove-Item -Force ".coverage" }
    
    # Remove mypy cache
    if (Test-Path ".mypy_cache") { Remove-Item -Recurse -Force ".mypy_cache" }
    
    Write-Host "✅ Project cleaned!" -ForegroundColor Green
}

# Main command dispatcher
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "setup" { Setup-Environment }
    "localstack-start" { Start-LocalStack }
    "localstack-stop" { Stop-LocalStack }
    "localstack-setup" { Setup-LocalStack }
    "producer" { Run-Producer }
    "producer-demo" { Run-Producer -NumTransactions 1000 }
    "test" { Run-Tests }
    "test-cov" { Run-TestsWithCoverage }
    "lint" { Run-Lint }
    "format" { Format-Code }
    "verify-stream" { Verify-Stream }
    "read-stream" { Read-Stream }
    "clean" { Clean-Project }
    default {
        Write-Host "❌ Unknown command: $Command" -ForegroundColor Red
        Write-Host "Run '.\run.ps1 help' for available commands" -ForegroundColor Yellow
    }
}
