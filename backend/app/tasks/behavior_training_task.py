"""
NeoFace Trust Engine — Behavioral Biometrics XGBoost Model Training
Trains a supervised XGBoost classification model to detect user typing anomalies.
"""

from __future__ import annotations

import asyncio
import base64
import uuid
import random
from datetime import datetime, timezone

import numpy as np
import xgboost as xgb
from sqlalchemy import select

from app.core.logging import logger
from app.tasks.celery_app import celery_app
from app.services.behavioral_biometrics_service import extract_features

@celery_app.task(
    name="app.tasks.behavior_training_task.train_behavior_model_async",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def train_behavior_model_async(self, user_id: str) -> dict:
    """
    Celery task wrapper to execute XGBoost model training asynchronously.
    """
    logger.info(
        "Behavior model training task started",
        task_id=self.request.id,
        user_id=user_id,
    )
    try:
        result = asyncio.run(_train_behavior_model(user_id))
        logger.info(
            "Behavior model training task completed successfully",
            task_id=self.request.id,
            user_id=user_id,
            result=result,
        )
        return result
    except Exception as exc:
        logger.error(
            "Behavior model training task failed",
            task_id=self.request.id,
            user_id=user_id,
            error=str(exc),
            exc_info=True,
        )
        raise self.retry(exc=exc)

async def _train_behavior_model(user_id: str) -> dict:
    """
    Inner async method: loads events, trains XGBoost, saves to user's profile.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.trust_engine import BehaviorProfile as BehaviorProfileModel, BehaviorEvent

    user_uuid = uuid.UUID(user_id)

    async with AsyncSessionLocal() as db:
        # Load user behavior events
        user_events_q = select(BehaviorEvent).where(BehaviorEvent.user_id == user_uuid)
        user_events_res = await db.execute(user_events_q)
        user_events = user_events_res.scalars().all()

        if len(user_events) < 200:
            logger.info(
                "Training skipped: insufficient events",
                user_id=user_id,
                events_count=len(user_events),
            )
            return {"status": "skipped", "reason": f"Insufficient events ({len(user_events)} < 200)"}

        # Load other users' events as background negative class (limit to 200)
        other_events_q = select(BehaviorEvent).where(BehaviorEvent.user_id != user_uuid).limit(200)
        other_events_res = await db.execute(other_events_q)
        other_events = other_events_res.scalars().all()

        # Generate synthetic negative samples if other users' data is scarce (e.g. local dev / testing)
        synthetic_features = []
        if len(other_events) < 100:
            needed = 200 - len(other_events)
            for _ in range(needed):
                base_event = random.choice(user_events)
                base_feats = extract_features(base_event.event_type, base_event.metrics)
                # Perturb features heavily to simulate abnormal patterns
                perturbed = list(base_feats)
                for idx in range(3, 12):
                    if not np.isnan(perturbed[idx]):
                        scale = random.choice([random.uniform(0.1, 0.4), random.uniform(2.5, 5.0)])
                        perturbed[idx] *= scale
                synthetic_features.append(perturbed)

        # Build training dataset
        X = []
        y = []

        # Positive class (label = 1)
        for e in user_events:
            X.append(extract_features(e.event_type, e.metrics))
            y.append(1)

        # Negative class (label = 0)
        for e in other_events:
            X.append(extract_features(e.event_type, e.metrics))
            y.append(0)

        for feats in synthetic_features:
            X.append(feats)
            y.append(0)

        X = np.array(X)
        y = np.array(y)

        # Train supervised XGBoost classifier
        model = xgb.XGBClassifier(
            max_depth=3,
            n_estimators=50,
            learning_rate=0.1,
            random_state=42,
            verbosity=0,
            n_jobs=1
        )
        model.fit(X, y)

        # Serialize model using Compact UBJ format
        booster = model.get_booster()
        raw_model_bytes = booster.save_raw()
        serialized_model = base64.b64encode(raw_model_bytes).decode("utf-8")

        # Save to BehaviorProfile
        profile_q = select(BehaviorProfileModel).where(BehaviorProfileModel.user_id == user_uuid)
        profile_res = await db.execute(profile_q)
        profile = profile_res.scalar_one_or_none()

        if profile is None:
            profile = BehaviorProfileModel(user_id=user_uuid)
            db.add(profile)
            await db.flush()

        profile.model_data = {
            "algorithm": "xgboost",
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "events_count": len(user_events),
            "model_bytes": serialized_model,
        }
        profile.profile_version += 1
        await db.commit()

        return {
            "status": "trained",
            "events_count": len(user_events),
            "negative_samples": len(other_events) + len(synthetic_features),
            "trained_at": profile.model_data["trained_at"],
        }
