"""
NeoFace AaaS — Infrastructure Monitoring Service
Collects real-time metrics from all system components.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.aaas import InfraMetrics, ServiceHealth


class InfraService:
    """
    Collects system metrics using psutil and async probes.
    GPU metrics require pynvml (nvidia-ml-py) — fails gracefully if absent.
    """

    async def get_metrics(self) -> InfraMetrics:
        import time
        services = []

        # ── Database ──────────────────────────────────────────────────────────
        db_health = await self._check_db()
        services.append(db_health)

        # ── Redis ─────────────────────────────────────────────────────────────
        redis_health = await self._check_redis()
        services.append(redis_health)

        # ── Celery queue ──────────────────────────────────────────────────────
        queue_depth = await self._get_queue_depth()
        services.append(ServiceHealth(
            name="celery_queue",
            status="ok" if queue_depth < 1000 else "degraded",
            detail=f"depth={queue_depth}",
        ))

        # ── CPU / Memory ──────────────────────────────────────────────────────
        cpu_pct, mem_pct, mem_used_gb, mem_total_gb = self._get_system_stats()

        # ── GPU ───────────────────────────────────────────────────────────────
        gpu_available, gpu_util = self._get_gpu_stats()

        return InfraMetrics(
            cpu_percent=cpu_pct,
            memory_percent=mem_pct,
            memory_used_gb=mem_used_gb,
            memory_total_gb=mem_total_gb,
            gpu_available=gpu_available,
            gpu_utilization=gpu_util,
            queue_depth=queue_depth,
            services=services,
            as_of=datetime.now(timezone.utc),
        )

    async def get_services(self) -> list[ServiceHealth]:
        db = await self._check_db()
        redis = await self._check_redis()
        queue_depth = await self._get_queue_depth()
        return [
            db,
            redis,
            ServiceHealth(
                name="celery_queue",
                status="ok" if queue_depth < 1000 else "degraded",
                detail=f"depth={queue_depth}",
            ),
        ]

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _check_db(self) -> ServiceHealth:
        import time
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import text
        t0 = time.perf_counter()
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            latency = (time.perf_counter() - t0) * 1000
            return ServiceHealth(name="postgresql", status="ok", latency_ms=round(latency, 2))
        except Exception as exc:
            return ServiceHealth(name="postgresql", status="error", detail=str(exc))

    async def _check_redis(self) -> ServiceHealth:
        import time
        from app.core.config import settings
        t0 = time.perf_counter()
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
            await r.ping()
            await r.aclose()
            latency = (time.perf_counter() - t0) * 1000
            return ServiceHealth(name="redis", status="ok", latency_ms=round(latency, 2))
        except Exception as exc:
            return ServiceHealth(name="redis", status="error", detail=str(exc))

    async def _get_queue_depth(self) -> int:
        from app.core.config import settings
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.REDIS_URL)
            depth = await r.llen("celery")
            await r.aclose()
            return int(depth or 0)
        except Exception:
            return 0

    def _get_system_stats(self) -> tuple[float, float, float, float]:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            return (
                round(cpu, 1),
                round(mem.percent, 1),
                round(mem.used / 1024 ** 3, 2),
                round(mem.total / 1024 ** 3, 2),
            )
        except ImportError:
            return 0.0, 0.0, 0.0, 0.0

    def _get_gpu_stats(self) -> tuple[bool, float | None]:
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            return True, float(util.gpu)
        except Exception:
            return False, None
