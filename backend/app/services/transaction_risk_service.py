"""
NeoFace Trust Engine — Transaction Risk Scoring (Module 3.5)

Computes transaction-specific risk factors:
  - Amount risk (smooth logarithmic scoring based on user profile)
  - Historical spending patterns (comparison vs average/median/max)
  - Velocity risk (transaction frequency anomalies)
  - First large transaction detection

Production-grade fraud detection optimized for fintech use cases.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.core.logging import logger

# Transaction amount constants
MAX_AMOUNT_RISK_FACTOR = 100000.0  # ₹100k — amounts beyond treated equivalently
MIN_VELOCITY_INTERVAL = 1.0  # minutes
MAX_HISTORICAL_TRANSACTIONS = 500  # sample size for statistics


@dataclass
class SpendingProfile:
    """User's historical spending statistics."""
    
    average_transaction: float     # Mean historical transaction amount
    median_transaction: float      # Median historical transaction amount
    max_transaction: float         # Maximum historical transaction amount
    transaction_count_7d: int      # Transactions in last 7 days
    transaction_count_30d: int     # Transactions in last 30 days
    total_spent_30d: float         # Total amount spent in last 30 days
    is_new_user: bool              # Account age < 30 days


@dataclass
class AmountRiskResult:
    """Output from amount risk calculation."""
    
    amount_risk: float             # 0.0–1.0 (normalized logarithmic)
    velocity_risk: float           # 0.0–1.0 (frequency anomaly)
    historical_risk: float         # 0.0–1.0 (deviation from user average)
    first_large_transaction: bool  # First time exceeding user's max
    final_amount_risk: float       # Weighted composite


@dataclass
class VelocityEvent:
    """A single transaction for velocity analysis."""
    
    timestamp: datetime
    amount: float
    transaction_id: str


class TransactionRiskService:
    """
    Computes fraud risk signals from transaction characteristics.
    
    Stateless service — call methods independently for each transaction.
    All inputs should come from user profile / transaction repository.
    """

    # Velocity thresholds (events per time window)
    VELOCITY_CRITICAL = [
        (5, 1),      # 5 transactions in 1 minute
        (10, 5),     # 10 transactions in 5 minutes
        (20, 30),    # 20 transactions in 30 minutes
    ]

    @staticmethod
    def calculate_amount_risk(
        amount: float,
        profile: SpendingProfile,
    ) -> AmountRiskResult:
        """
        Calculate smooth, logarithmic amount risk based on user profile.
        
        Args:
            amount: Transaction amount in base currency (₹, $, €, etc.)
            profile: User's spending profile with historical statistics.
            
        Returns:
            AmountRiskResult with amount_risk, velocity_risk, etc.
        """
        if amount < 0:
            amount = 0.0

        # ── 1. Amount Risk: Smooth logarithmic scoring ────────────────────────
        # No hard thresholds like "if amount > 1000: score = 5"
        # Instead: log-based, continuous scale
        
        if amount == 0:
            amount_risk = 0.0
        else:
            # Normalize amount to 0–1 using logarithmic scaling
            # log1p(x) = ln(1 + x), handles small amounts well
            normalized = math.log1p(amount) / math.log1p(MAX_AMOUNT_RISK_FACTOR)
            amount_risk = min(max(normalized, 0.0), 1.0)

        # ── 2. Historical Risk: Deviation from user's profile ─────────────────
        historical_risk = TransactionRiskService._calculate_historical_risk(
            amount, profile
        )

        # ── 3. First Large Transaction ─────────────────────────────────────────
        first_large = (
            amount > profile.max_transaction * 1.5  # 50% above previous max
            and not profile.is_new_user
        )

        # ── 4. Velocity Risk ───────────────────────────────────────────────────
        # NOTE: Velocity requires transaction history; calculate separately
        # using calculate_velocity_risk() method
        velocity_risk = 0.0

        # ── Composite amount risk (weighted) ────────────────────────────────────
        # amount_risk (0.4) + historical_risk (0.5) + first_large bonus (0.1)
        final_amount_risk = (
            0.40 * amount_risk +
            0.50 * historical_risk +
            (0.10 if first_large else 0.0)
        )
        final_amount_risk = min(max(final_amount_risk, 0.0), 1.0)

        logger.debug(
            "transaction_risk.amount",
            amount=round(amount, 2),
            amount_risk=round(amount_risk, 3),
            historical_risk=round(historical_risk, 3),
            first_large=first_large,
            final_amount_risk=round(final_amount_risk, 3),
        )

        return AmountRiskResult(
            amount_risk=amount_risk,
            velocity_risk=velocity_risk,
            historical_risk=historical_risk,
            first_large_transaction=first_large,
            final_amount_risk=final_amount_risk,
        )

    @staticmethod
    def _calculate_historical_risk(
        amount: float,
        profile: SpendingProfile,
    ) -> float:
        """
        Compare transaction amount against user's historical spending.
        
        Returns 0.0–1.0 indicating deviation from normal pattern.
        """
        if profile.average_transaction <= 0:
            # New user or insufficient history
            return 0.1 if profile.is_new_user else 0.05

        # Ratio of current to average
        ratio = amount / profile.average_transaction

        if ratio <= 1.0:
            # Amount ≤ average — low risk
            return 0.0
        elif ratio <= 2.0:
            # 1–2x average — moderate risk (log scale)
            return 0.2 * math.log(ratio) / math.log(2.0)
        elif ratio <= 5.0:
            # 2–5x average — elevated risk
            return 0.2 + 0.4 * (ratio - 2.0) / 3.0
        else:
            # 5x+ average — high risk
            return min(0.6 + 0.4 * math.log(ratio / 5.0) / math.log(10.0), 1.0)

    @staticmethod
    def calculate_velocity_risk(
        recent_transactions: list[VelocityEvent],
        current_timestamp: datetime | None = None,
    ) -> float:
        """
        Detect suspicious transaction frequency patterns.
        
        Checks for:
          - 5 transactions in 1 minute
          - 10 transactions in 5 minutes
          - 20 transactions in 30 minutes
        
        Args:
            recent_transactions: Recent transactions with timestamps.
            current_timestamp: Reference time (default: now).
            
        Returns:
            velocity_risk: 0.0–1.0 (0 = normal, 1 = highly suspicious).
        """
        if current_timestamp is None:
            current_timestamp = datetime.utcnow()

        if not recent_transactions:
            return 0.0

        # Sort by timestamp (newest first)
        sorted_txns = sorted(
            recent_transactions,
            key=lambda t: t.timestamp,
            reverse=True,
        )

        max_velocity_violation = 0.0

        # Check each threshold
        for threshold_count, threshold_minutes in TransactionRiskService.VELOCITY_CRITICAL:
            window = timedelta(minutes=threshold_minutes)
            window_start = current_timestamp - window
            
            in_window = [
                t for t in sorted_txns
                if t.timestamp >= window_start and t.timestamp <= current_timestamp
            ]
            
            txn_count = len(in_window)
            
            if txn_count >= threshold_count:
                # Violation score scales from threshold to 1.0 max
                violation_ratio = min(txn_count / threshold_count, 5.0)
                violation_score = min(violation_ratio / 5.0, 1.0)
                max_velocity_violation = max(max_velocity_violation, violation_score)

                logger.warning(
                    "transaction_risk.velocity_violation",
                    threshold_count=threshold_count,
                    threshold_minutes=threshold_minutes,
                    actual_count=txn_count,
                    violation_score=round(violation_score, 3),
                )

        return float(min(max(max_velocity_violation, 0.0), 1.0))

    @staticmethod
    def merge_amount_and_velocity_risk(
        amount_risk_result: AmountRiskResult,
        velocity_risk: float,
    ) -> float:
        """
        Merge amount risk and velocity risk into a final transaction risk score.
        
        Args:
            amount_risk_result: Result from calculate_amount_risk().
            velocity_risk: Result from calculate_velocity_risk().
            
        Returns:
            transaction_risk: 0.0–1.0 (0 = safe, 1 = highly risky).
        """
        # Weighted average: amount (60%) + velocity (40%)
        final_risk = (
            0.60 * amount_risk_result.final_amount_risk +
            0.40 * velocity_risk
        )
        return min(max(final_risk, 0.0), 1.0)

    @staticmethod
    def generate_flags(
        amount: float,
        amount_risk_result: AmountRiskResult,
        velocity_risk: float,
        profile: SpendingProfile,
    ) -> list[str]:
        """Generate human-readable risk flags for logging/UI."""
        flags = []

        if amount_risk_result.first_large_transaction:
            flags.append(f"first_large_transaction:{amount:.0f}")

        if amount_risk_result.amount_risk > 0.7:
            flags.append(f"high_amount_risk:{amount_risk_result.amount_risk:.2f}")

        if amount_risk_result.historical_risk > 0.6:
            ratio = amount / max(profile.average_transaction, 1.0)
            flags.append(f"unusual_amount_ratio:{ratio:.1f}x")

        if velocity_risk > 0.5:
            flags.append(f"velocity_anomaly:{velocity_risk:.2f}")

        if profile.is_new_user:
            flags.append("new_user_account")

        return flags
