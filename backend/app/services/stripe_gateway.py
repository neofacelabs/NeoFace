"""
NeoFace Stripe Gateway
Mock settlement gateway communicating with a simulated Stripe/Plaid API.
"""

import uuid
from app.core.logging import logger

class StripeGateway:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def process_bank_transfer(
        self,
        amount: float,
        currency: str,
        bank_token: str,
        account_holder: str | None = None,
    ) -> dict:
        """
        Mock bank account settlement via Stripe.
        Simulates payment outcomes based on the provided token.
        """
        logger.info(
            "StripeGateway: processing bank settlement transfer",
            amount=amount,
            currency=currency,
            token_prefix=bank_token[:8] if bank_token else "none",
        )

        # Generate a simulated gateway reference ID
        charge_id = f"ch_{uuid.uuid4().hex[:24]}"

        # Simulated failure cases via specific tokens
        if bank_token and "fail" in bank_token.lower():
            return {
                "success": False,
                "charge_id": charge_id,
                "error": "insufficient_funds",
                "status": "failed",
            }

        return {
            "success": True,
            "charge_id": charge_id,
            "error": None,
            "status": "succeeded",
        }
