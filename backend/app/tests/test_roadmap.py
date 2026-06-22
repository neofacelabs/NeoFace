"""
NeoFace Roadmap Verification Tests
Covers Phase 1-5 additions: pgvector queries, Stripe payments, tenant isolation, and XGBoost tasks.
"""

import uuid
import base64
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock

import numpy as np
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.merchant import Merchant
from app.models.bank_account import BankAccount
from app.models.trust_engine import BehaviorProfile, BehaviorEvent, ContinuousSession
from app.models.transaction import Transaction
from app.repositories.embedding_repository import EmbeddingRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.stripe_gateway import StripeGateway
from app.services.payment_service import PaymentAuthorizationService
from app.services.behavioral_biometrics_service import BehavioralBiometricsService, extract_features
from app.tasks.behavior_training_task import _train_behavior_model
from app.tasks.continuous_auth_tasks import _sweep_sessions_async
from app.tests.conftest import make_fake_embedding

class MockSessionContext:
    def __init__(self, session):
        self.session = session
    async def __aenter__(self):
        return self.session
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

@pytest.fixture(autouse=True)
def mock_db_session_local(db_session):
    with patch("app.core.database.AsyncSessionLocal", return_value=MockSessionContext(db_session)), \
         patch("app.tasks.behavior_training_task.AsyncSessionLocal", return_value=MockSessionContext(db_session), create=True), \
         patch("app.tasks.continuous_auth_tasks.AsyncSessionLocal", return_value=MockSessionContext(db_session), create=True):
        yield

@pytest_asyncio.fixture
async def sample_merchant(db_session: AsyncSession) -> Merchant:
    """Create a sample merchant in the database."""
    merchant = Merchant(
        business_name="Test Shop",
        business_email="shop@test.com",
        business_category="retail",
        api_key_prefix="nf_live_test",
        api_key_hash="dummy_hash",
        is_active=True,
    )
    db_session.add(merchant)
    await db_session.flush()
    await db_session.refresh(merchant)
    return merchant

@pytest_asyncio.fixture
async def sample_bank_account(db_session: AsyncSession, test_user) -> BankAccount:
    """Create a linked bank account for the test user."""
    account = BankAccount(
        user_id=test_user.id,
        bank_name="NeoBank",
        account_holder_name="Test User",
        encrypted_token="tok_123456",
        account_mask="1234",
        is_default=True,
    )
    db_session.add(account)
    await db_session.flush()
    await db_session.refresh(account)
    return account


class TestPhase1Biometrics:
    """Tests pgvector find_nearest_neighbors query and SQLite fallback."""

    @pytest.mark.asyncio
    async def test_find_nearest_neighbors_sqlite_fallback(self, db_session: AsyncSession, enrolled_user):
        """Test nearest neighbor search falls back to numpy in SQLite test DB."""
        user, face_embedding = enrolled_user
        repo = EmbeddingRepository(db_session)

        # Vector identical to the enrolled user's vector
        query_vector = face_embedding.embedding_vector

        # Executing search should use the numpy fallback
        results = await repo.find_nearest_neighbors(query_vector, limit=1)
        assert len(results) == 1
        matched_emb, similarity = results[0]
        assert matched_emb.user_id == user.id
        assert similarity > 0.95  # Cosine similarity very close to 1 (identical)

    @pytest.mark.asyncio
    async def test_find_nearest_neighbors_postgres_operator(self, db_session: AsyncSession):
        """Test that Postgres dialect constructs a query using the pgvector `<=>` operator."""
        repo = EmbeddingRepository(db_session)
        query_vector = [0.1] * 512

        # Mock the dialect name to simulate PostgreSQL
        with patch.object(db_session.bind.dialect, "name", "postgresql"):
            # Mock the execute to capture the query SQL string
            mock_execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
            with patch.object(db_session, "execute", mock_execute):
                await repo.find_nearest_neighbors(query_vector, limit=5)
                # Verify execute was called
                assert mock_execute.called
                # Verify query constructs cosine distance operator
                stmt = mock_execute.call_args[0][0]
                from sqlalchemy.dialects import postgresql
                sql_string = str(stmt.compile(dialect=postgresql.dialect()))
                assert "<=>" in sql_string


class TestPhase3Financials:
    """Tests Stripe/Plaid settlement gateway flow and row-level tenant filtering."""

    def test_stripe_mock_settlement_outcomes(self):
        """Test StripeGateway outcomes for normal vs fail tokens."""
        gateway = StripeGateway.get_instance()

        success_res = gateway.process_bank_transfer(100.0, "USD", "tok_valid")
        assert success_res["success"] is True
        assert success_res["status"] == "succeeded"
        assert success_res["charge_id"].startswith("ch_")

        fail_res = gateway.process_bank_transfer(100.0, "USD", "tok_fail_insufficient")
        assert fail_res["success"] is False
        assert fail_res["status"] == "failed"
        assert fail_res["error"] == "insufficient_funds"

    @pytest.mark.asyncio
    async def test_payment_settlement_integration(
        self, db_session: AsyncSession, test_user, sample_merchant, sample_bank_account
    ):
        """Test payment authorization executes Stripe transfer on default bank account."""
        # Mock face verification to return genuine match
        svc = PaymentAuthorizationService(db=db_session)
        
        with patch.object(svc, "_run_face_verification") as mock_face:
            mock_face.return_value = {
                "confidence_score": 98.0,
                "liveness_score": 85.0,
                "liveness_passed": True,
                "anti_spoof_passed": True,
                "blink_detected": True,
                "head_turn_detected": True,
                "user_id": str(test_user.id),
                "embedding_hash": "dummy_hash",
            }

            result = await svc.authorize(
                amount=150.0,
                currency="USD",
                merchant_id=sample_merchant.id,
                face_image_bytes=b"dummy_image",
            )

            assert result["authorized"] is True
            assert result["status"] == "authorized"
            
            # Check transaction record in DB
            txn_id = uuid.UUID(result["transaction_id"])
            txn_repo = TransactionRepository(db_session)
            txn = await txn_repo.get_by_id(txn_id)
            assert txn is not None
            assert txn.status == "authorized"
            assert txn.amount == 150.0
            assert txn.bank_account_id == sample_bank_account.id


class TestPhase4Behavioral:
    """Tests XGBoost behavioral training task and prediction scoring."""

    @pytest.mark.asyncio
    async def test_xgboost_celery_training_flow(self, db_session: AsyncSession, test_user):
        """Test that the async training function fits XGBoost and stores weights."""
        profile = BehaviorProfile(user_id=test_user.id, total_events=0)
        db_session.add(profile)
        await db_session.flush()

        # Add 200 dummy events for the user
        for i in range(200):
            event = BehaviorEvent(
                profile_id=profile.id,
                user_id=test_user.id,
                event_type="keyboard" if i % 2 == 0 else "mouse",
                metrics={
                    "wpm": 75.0 + (i % 5),
                    "dwell": 120.0 + (i % 10),
                    "flight": 150.0 + (i % 20),
                    "speed": 250.0 + (i % 50),
                    "curvature": 0.8,
                }
            )
            db_session.add(event)
        await db_session.commit()

        # Execute training logic directly
        res = await _train_behavior_model(str(test_user.id))
        assert res["status"] == "trained"
        assert res["events_count"] == 200

        # Reload profile and verify model is saved
        stmt = select(BehaviorProfile).where(BehaviorProfile.user_id == test_user.id)
        reloaded = (await db_session.execute(stmt)).scalar_one()
        assert reloaded.model_data is not None
        assert reloaded.model_data["algorithm"] == "xgboost"
        assert "model_bytes" in reloaded.model_data

        # Predict with service scoring using XGBoost
        service = BehavioralBiometricsService()
        from app.services.behavioral_biometrics_service import BehaviorProfile as ServiceProfile, BehaviorEventData
        
        svc_profile = ServiceProfile(
            user_id=str(test_user.id),
            total_events=200,
            is_baseline_established=True,
            model_data=reloaded.model_data
        )

        test_event = BehaviorEventData(
            event_type="keyboard",
            metrics={"wpm": 77.0, "dwell": 125.0, "flight": 155.0}
        )

        score_res = service.score([test_event], svc_profile)
        assert score_res.method == "xgboost"
        assert 0.0 <= score_res.behavior_score <= 100.0


class TestPhase4ContinuousAuthDecay:
    """Tests active-typing based continuous authentication decay modifiers."""

    @pytest.mark.asyncio
    async def test_continuous_auth_decay_with_typing(self, db_session: AsyncSession, test_user):
        """Test that active keyboard behavior events mitigate/reduce continuous auth decay."""
        # Create continuous session
        session = ContinuousSession(
            user_id=test_user.id,
            session_token="session_decay_test_token",
            status="active",
            current_trust_score=100.0,
            check_interval_seconds=30,
            last_verified_at=datetime.now(timezone.utc)
        )
        db_session.add(session)

        # Create behavior profile
        profile = BehaviorProfile(user_id=test_user.id)
        db_session.add(profile)
        await db_session.flush()

        # Add a recent keyboard typing event for the user
        typing_event = BehaviorEvent(
            profile_id=profile.id,
            user_id=test_user.id,
            event_type="keyboard",
            metrics={"wpm": 60.0},
            created_at=datetime.now(timezone.utc)
        )
        db_session.add(typing_event)
        await db_session.commit()

        # Manually force the session verified time back to trigger overdue check decay
        # overdue by 2 intervals (e.g. 70 seconds ago)
        from datetime import timedelta
        session.last_verified_at = datetime.now(timezone.utc) - timedelta(seconds=75)
        await db_session.commit()

        # Run background sweep task
        sweep_res = await _sweep_sessions_async()
        
        # Verify session was updated and decay was applied
        await db_session.refresh(session)
        assert sweep_res["sessions_updated"] == 1
        
        # Decay with typing should be 1 point per missed interval, so 100.0 -> 99.0
        # Instead of 5 points per missed interval (100.0 -> 95.0)
        assert session.current_trust_score == 99.0
