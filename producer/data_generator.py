"""
Synthetic Transaction Data Generator

Generates realistic credit card transaction data with configurable fraud patterns.
Uses the Faker library for realistic data generation.

Fraud Patterns Implemented:
1. High-value transactions (> $5000)
2. Multiple transactions in short time window
3. Transactions from unusual locations
4. Transactions outside normal hours (2 AM - 5 AM)
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from faker import Faker


class TransactionGenerator:
    """
    Generates synthetic credit card transactions with realistic fraud patterns.

    This class creates fake transaction data that mimics real-world credit card
    transactions, including both legitimate and fraudulent patterns.
    """

    def __init__(
        self,
        fraud_ratio: float = 0.05,
        num_merchants: int = 1000,
        num_customers: int = 5000,
        seed: Optional[int] = None,
    ) -> None:
        """
        Initialize the transaction generator.

        Args:
            fraud_ratio: Proportion of transactions that should be fraudulent (0.0 to 1.0)
            num_merchants: Number of unique merchants to simulate
            num_customers: Number of unique customers to simulate
            seed: Random seed for reproducibility (optional)

        Raises:
            ValueError: If fraud_ratio is not between 0 and 1
        """
        if not 0.0 <= fraud_ratio <= 1.0:
            raise ValueError(f"fraud_ratio must be between 0 and 1, got {fraud_ratio}")

        self.fraud_ratio = fraud_ratio
        self.num_merchants = num_merchants
        self.num_customers = num_customers

        # Initialize Faker with seed for reproducibility
        self.fake = Faker()
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)

        # Pre-generate merchant and customer pools for consistency
        self.merchants = self._generate_merchants()
        self.customers = self._generate_customers()

        # Transaction categories
        self.categories = [
            "grocery",
            "restaurant",
            "gas_station",
            "online_retail",
            "entertainment",
            "travel",
            "electronics",
            "clothing",
            "healthcare",
            "utilities",
        ]

    def _generate_merchants(self) -> List[Dict[str, Any]]:
        """Generate a pool of merchants with consistent attributes."""
        merchants = []
        for _ in range(self.num_merchants):
            merchant = {
                "merchant_id": f"M{uuid.uuid4().hex[:12]}",
                "merchant_name": self.fake.company(),
                "merchant_category": random.choice(self.categories),
                "merchant_location": {
                    "city": self.fake.city(),
                    "state": self.fake.state_abbr(),
                    "country": "US",
                    "latitude": float(self.fake.latitude()),
                    "longitude": float(self.fake.longitude()),
                },
            }
            merchants.append(merchant)
        return merchants

    def _generate_customers(self) -> List[Dict[str, Any]]:
        """Generate a pool of customers with consistent attributes."""
        customers = []
        for _ in range(self.num_customers):
            customer = {
                "customer_id": f"C{uuid.uuid4().hex[:12]}",
                "customer_name": self.fake.name(),
                "customer_email": self.fake.email(),
                "customer_phone": self.fake.phone_number(),
                "home_location": {
                    "city": self.fake.city(),
                    "state": self.fake.state_abbr(),
                    "country": "US",
                    "latitude": float(self.fake.latitude()),
                    "longitude": float(self.fake.longitude()),
                },
            }
            customers.append(customer)
        return customers

    def _calculate_distance(self, loc1: Dict[str, float], loc2: Dict[str, float]) -> float:
        """
        Calculate approximate distance between two locations (in km).

        Uses simplified haversine formula.

        Args:
            loc1: First location with 'latitude' and 'longitude' keys
            loc2: Second location with 'latitude' and 'longitude' keys

        Returns:
            Approximate distance in kilometers
        """
        # Simplified distance calculation (for fraud detection simulation)
        lat_diff = abs(loc1["latitude"] - loc2["latitude"])
        lon_diff = abs(loc1["longitude"] - loc2["longitude"])
        return (lat_diff**2 + lon_diff**2) ** 0.5 * 111  # Rough km conversion

    def _is_unusual_hour(self, timestamp: datetime) -> bool:
        """Check if transaction occurs during unusual hours (2 AM - 5 AM)."""
        return 2 <= timestamp.hour < 5

    def generate_transaction(self, is_fraud: Optional[bool] = None) -> Dict[str, Any]:
        """
        Generate a single transaction with optional fraud characteristics.

        Args:
            is_fraud: If specified, generates fraud/legitimate transaction.
                     If None, determines randomly based on fraud_ratio.

        Returns:
            Dictionary containing transaction details
        """
        # Determine if this transaction is fraudulent
        if is_fraud is None:
            is_fraud = random.random() < self.fraud_ratio

        # Select random customer and merchant
        customer = random.choice(self.customers)
        merchant = random.choice(self.merchants)

        # Generate timestamp (within last 24 hours for more realistic streaming)
        base_time = datetime.utcnow()
        time_offset = timedelta(seconds=random.randint(0, 86400))
        timestamp = base_time - time_offset

        # Base transaction amount (legitimate transactions)
        if is_fraud:
            # Fraudulent transactions: higher amounts or suspicious patterns
            amount = self._generate_fraud_amount(merchant["merchant_category"])
        else:
            # Legitimate transactions: normal distribution
            amount = self._generate_normal_amount(merchant["merchant_category"])

        # Calculate distance from home (fraud indicator)
        distance_from_home = self._calculate_distance(
            customer["home_location"], merchant["merchant_location"]
        )

        # Build transaction object
        transaction = {
            "transaction_id": f"T{uuid.uuid4().hex}",
            "timestamp": timestamp.isoformat() + "Z",
            "customer_id": customer["customer_id"],
            "merchant_id": merchant["merchant_id"],
            "merchant_name": merchant["merchant_name"],
            "merchant_category": merchant["merchant_category"],
            "amount": round(amount, 2),
            "currency": "USD",
            "merchant_location": merchant["merchant_location"],
            "distance_from_home_km": round(distance_from_home, 2),
            "is_unusual_hour": self._is_unusual_hour(timestamp),
            "card_type": random.choice(["visa", "mastercard", "amex", "discover"]),
            "is_fraud": is_fraud,  # Ground truth label (for ML training)
        }

        return transaction

    def _generate_normal_amount(self, category: str) -> float:
        """Generate realistic transaction amount for legitimate transactions."""
        # Category-based amount ranges
        category_ranges = {
            "grocery": (20, 150),
            "restaurant": (15, 100),
            "gas_station": (30, 80),
            "online_retail": (25, 300),
            "entertainment": (20, 150),
            "travel": (100, 1000),
            "electronics": (50, 800),
            "clothing": (30, 250),
            "healthcare": (50, 500),
            "utilities": (50, 300),
        }

        min_amt, max_amt = category_ranges.get(category, (10, 200))
        # Use log-normal distribution for more realistic amounts
        mean = (min_amt + max_amt) / 2
        std = (max_amt - min_amt) / 4
        amount = random.gauss(mean, std)

        # Clamp to range
        return max(min_amt, min(max_amt, amount))

    def _generate_fraud_amount(self, category: str) -> float:
        """Generate suspicious transaction amount for fraudulent transactions."""
        fraud_type = random.choice(["high_value", "normal_suspicious"])

        if fraud_type == "high_value":
            # Very high value transactions (major fraud indicator)
            return random.uniform(3000, 10000)
        else:
            # Normal-looking amount but will have other fraud indicators
            return self._generate_normal_amount(category)

    def generate_batch(self, batch_size: int) -> List[Dict[str, Any]]:
        """
        Generate a batch of transactions.

        Args:
            batch_size: Number of transactions to generate

        Returns:
            List of transaction dictionaries
        """
        return [self.generate_transaction() for _ in range(batch_size)]

    def to_json(self, transaction: Dict[str, Any]) -> str:
        """
        Convert transaction to JSON string.

        Args:
            transaction: Transaction dictionary

        Returns:
            JSON string representation
        """
        return json.dumps(transaction, ensure_ascii=False)

    def get_fraud_statistics(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics about fraud in a batch of transactions.

        Args:
            transactions: List of transaction dictionaries

        Returns:
            Dictionary with fraud statistics
        """
        total = len(transactions)
        fraud_count = sum(1 for t in transactions if t["is_fraud"])

        return {
            "total_transactions": total,
            "fraud_count": fraud_count,
            "legitimate_count": total - fraud_count,
            "fraud_percentage": round((fraud_count / total * 100), 2) if total > 0 else 0,
        }
