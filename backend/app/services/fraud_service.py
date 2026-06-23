"""
NeoFace AaaS — Fraud Center Service
Aggregates threat intelligence from existing Trust Engine models:
  - DeepfakeLog  → deepfake detections
  - LivenessLog  → spoof/liveness failures
  - RiskScore    → high-risk sessions

Returns real values where Trust Engine data exists, mocked zeros where not.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trust_engine import DeepfakeLog, LivenessLog, RiskScore
from app.schemas.aaas import FraudEventResponse, FraudOverviewResponse, FraudTimelinePoint


class FraudService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_overview(self) -> FraudOverviewResponse:
        since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

        # Deepfake detections
        deepfake_count = await self._count_deepfakes(since_24h)

        # Spoof attempts (liveness failures)
        spoof_count = await self._count_spoof_attempts(since_24h)

        # High risk sessions (risk_score > 70)
        high_risk = await self._count_high_risk_sessions(since_24h)

        # Replay attacks: approximated as deepfakes with score < 0.3 (captured videos)
        replay_count = await self._count_replay_attacks(since_24h)

        return FraudOverviewResponse(
            spoof_attempts=spoof_count,
            deepfake_detections=deepfake_count,
            replay_attacks=replay_count,
            high_risk_sessions=high_risk,
            total_threat_events_24h=spoof_count + deepfake_count + high_risk,
            as_of=datetime.now(timezone.utc),
        )

    async def get_timeline(self, days: int = 14) -> list[FraudTimelinePoint]:
        points = []
        for i in range(days - 1, -1, -1):
            day = datetime.now(timezone.utc).date() - timedelta(days=i)
            day_start = datetime.combine(day, datetime.min.time()).replace(tzinfo=timezone.utc)
            day_end = datetime.combine(day, datetime.max.time()).replace(tzinfo=timezone.utc)

            spoof = await self._count_spoof_attempts_range(day_start, day_end)
            deepfakes = await self._count_deepfakes_range(day_start, day_end)
            high_risk = await self._count_high_risk_sessions_range(day_start, day_end)

            points.append(FraudTimelinePoint(
                date=day,
                spoof_attempts=spoof,
                deepfake_detections=deepfakes,
                high_risk_sessions=high_risk,
            ))
        return points

    async def get_events(
        self, page: int = 1, page_size: int = 50
    ) -> tuple[list[FraudEventResponse], int]:
        """Return recent high-risk and failed liveness events."""
        since_7d = datetime.now(timezone.utc) - timedelta(days=7)

        q = select(RiskScore).where(
            RiskScore.final_trust_score < 50,  # lower = higher risk
            RiskScore.created_at >= since_7d,
        ).order_by(RiskScore.created_at.desc())

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.offset((page - 1) * page_size).limit(page_size)
        scores = (await self.db.execute(q)).scalars().all()

        events = [
            FraudEventResponse(
                id=s.id,
                event_type="high_risk_session",
                risk_score=s.final_trust_score,
                confidence=None,
                ip_address=s.ip_address,
                created_at=s.created_at,
            )
            for s in scores
        ]
        return events, total

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _count_deepfakes(self, since: datetime) -> int:
        result = await self.db.execute(
            select(func.count(DeepfakeLog.id)).where(
                DeepfakeLog.is_deepfake == True,  # noqa: E712
                DeepfakeLog.created_at >= since,
            )
        )
        return result.scalar_one() or 0

    async def _count_deepfakes_range(self, start: datetime, end: datetime) -> int:
        result = await self.db.execute(
            select(func.count(DeepfakeLog.id)).where(
                DeepfakeLog.is_deepfake == True,  # noqa: E712
                DeepfakeLog.created_at >= start,
                DeepfakeLog.created_at <= end,
            )
        )
        return result.scalar_one() or 0

    async def _count_spoof_attempts(self, since: datetime) -> int:
        result = await self.db.execute(
            select(func.count(LivenessLog.id)).where(
                LivenessLog.is_live == False,  # noqa: E712
                LivenessLog.created_at >= since,
            )
        )
        return result.scalar_one() or 0

    async def _count_spoof_attempts_range(self, start: datetime, end: datetime) -> int:
        result = await self.db.execute(
            select(func.count(LivenessLog.id)).where(
                LivenessLog.is_live == False,  # noqa: E712
                LivenessLog.created_at >= start,
                LivenessLog.created_at <= end,
            )
        )
        return result.scalar_one() or 0

    async def _count_high_risk_sessions(self, since: datetime) -> int:
        result = await self.db.execute(
            select(func.count(RiskScore.id)).where(
                RiskScore.final_trust_score < 70,  # lower score = higher risk in trust engine
                RiskScore.created_at >= since,
            )
        )
        return result.scalar_one() or 0

    async def _count_high_risk_sessions_range(self, start: datetime, end: datetime) -> int:
        result = await self.db.execute(
            select(func.count(RiskScore.id)).where(
                RiskScore.final_trust_score < 70,  # lower = riskier
                RiskScore.created_at >= start,
                RiskScore.created_at <= end,
            )
        )
        return result.scalar_one() or 0

    async def _count_replay_attacks(self, since: datetime) -> int:
        # Replay = deepfakes flagged as deepfake_video attack category
        result = await self.db.execute(
            select(func.count(DeepfakeLog.id)).where(
                DeepfakeLog.is_deepfake == True,  # noqa: E712
                DeepfakeLog.deepfake_probability > 0.8,
                DeepfakeLog.attack_category == "deepfake_video",
                DeepfakeLog.created_at >= since,
            )
        )
        return result.scalar_one() or 0
