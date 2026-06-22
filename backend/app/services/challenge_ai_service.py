"""
NeoFace Trust Engine — Challenge Response AI Service (Module 7)
Generates intelligent, non-repeating anti-spoof challenge sequences.

Rules:
  - Never repeat the same challenge type consecutively
  - Maintain per-session and per-user challenge history
  - Store challenge nonces for anti-replay protection
  - Challenges expire after 60 seconds

Challenge catalog:
  - smile_then_blink
  - look_left_then_smile
  - open_mouth_then_blink
  - raise_eyebrows_then_turn_right
  - blink_twice
  - turn_left_then_smile
  - look_up_then_smile
  - turn_right_then_open_mouth

Integrates with Redis for distributed challenge storage.
"""

from __future__ import annotations

import json
import random
import secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import logger

# ── Challenge catalog ─────────────────────────────────────────────────────────
CHALLENGES: list[dict[str, Any]] = [
    {
        "type": "smile_then_blink",
        "steps": ["smile", "blink"],
        "display": "Please smile, then blink",
        "difficulty": "easy",
    },
    {
        "type": "look_left_then_smile",
        "steps": ["turn_left", "smile"],
        "display": "Look left, then smile",
        "difficulty": "easy",
    },
    {
        "type": "open_mouth_then_blink",
        "steps": ["open_mouth", "blink"],
        "display": "Open your mouth, then blink",
        "difficulty": "easy",
    },
    {
        "type": "raise_eyebrows_then_turn_right",
        "steps": ["raise_eyebrows", "turn_right"],
        "display": "Raise your eyebrows, then turn right",
        "difficulty": "medium",
    },
    {
        "type": "blink_twice",
        "steps": ["blink", "blink"],
        "display": "Please blink twice",
        "difficulty": "easy",
    },
    {
        "type": "turn_left_then_smile",
        "steps": ["turn_left", "smile"],
        "display": "Turn left, then smile",
        "difficulty": "easy",
    },
    {
        "type": "look_up_then_smile",
        "steps": ["look_up", "smile"],
        "display": "Look up, then smile",
        "difficulty": "easy",
    },
    {
        "type": "turn_right_then_open_mouth",
        "steps": ["turn_right", "open_mouth"],
        "display": "Turn right, then open your mouth",
        "difficulty": "medium",
    },
    {
        "type": "look_down_then_blink",
        "steps": ["look_down", "blink"],
        "display": "Look down, then blink",
        "difficulty": "medium",
    },
    {
        "type": "raise_eyebrows_then_smile",
        "steps": ["raise_eyebrows", "smile"],
        "display": "Raise your eyebrows, then smile",
        "difficulty": "medium",
    },
]

# Challenge TTL in seconds
CHALLENGE_TTL = 60
# Max consecutive history to track per session
MAX_HISTORY = 5
# Redis key prefix
_CHALLENGE_PREFIX = "neoface:challenge:"
_HISTORY_PREFIX   = "neoface:challenge_history:"


@dataclass
class GeneratedChallenge:
    """A challenge ready to send to the client."""
    challenge_id: str
    challenge_type: str
    steps: list[str]
    display: str
    difficulty: str
    nonce: str
    expires_at: float
    created_at: float = field(default_factory=time.time)


class ChallengeAIService:
    """
    Intelligent challenge generator with history-aware anti-repeat logic.

    Can operate with or without Redis — falls back to in-memory storage
    for single-process deployments.
    """

    def __init__(self, redis_client=None) -> None:
        self._redis = redis_client
        # In-memory fallback (not suitable for multi-process)
        self._memory_store: dict[str, dict] = {}
        self._history_store: dict[str, list[str]] = {}

    # ── Storage helpers ───────────────────────────────────────────────────────

    async def _store_challenge(self, challenge_id: str, data: dict) -> None:
        """Persist challenge data with TTL."""
        key = f"{_CHALLENGE_PREFIX}{challenge_id}"
        if self._redis:
            try:
                await self._redis.setex(key, CHALLENGE_TTL, json.dumps(data))
                return
            except Exception as exc:
                logger.warning("challenge_ai.store: Redis error", error=str(exc))
        self._memory_store[key] = data

    async def _load_challenge(self, challenge_id: str) -> dict | None:
        """Load challenge data by ID."""
        key = f"{_CHALLENGE_PREFIX}{challenge_id}"
        if self._redis:
            try:
                raw = await self._redis.get(key)
                return json.loads(raw) if raw else None
            except Exception as exc:
                logger.warning("challenge_ai.load: Redis error", error=str(exc))
        return self._memory_store.get(key)

    async def _delete_challenge(self, challenge_id: str) -> None:
        """Remove a consumed/expired challenge."""
        key = f"{_CHALLENGE_PREFIX}{challenge_id}"
        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception:
                pass
        self._memory_store.pop(key, None)

    async def _get_history(self, session_id: str) -> list[str]:
        """Get recent challenge history for a session."""
        key = f"{_HISTORY_PREFIX}{session_id}"
        if self._redis:
            try:
                raw = await self._redis.get(key)
                return json.loads(raw) if raw else []
            except Exception:
                pass
        return self._history_store.get(key, [])

    async def _append_history(self, session_id: str, challenge_type: str) -> None:
        """Add a challenge type to session history, keeping last MAX_HISTORY."""
        key = f"{_HISTORY_PREFIX}{session_id}"
        current = await self._get_history(session_id)
        current.append(challenge_type)
        current = current[-MAX_HISTORY:]  # Keep only recent history
        if self._redis:
            try:
                # History TTL: 10 minutes
                await self._redis.setex(key, 600, json.dumps(current))
                return
            except Exception:
                pass
        self._history_store[key] = current

    # ── Challenge selection ───────────────────────────────────────────────────

    async def generate(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> GeneratedChallenge:
        """
        Generate a new challenge, avoiding the last challenge in the session.

        Returns a GeneratedChallenge dict-compatible object.
        """
        session_id = session_id or str(uuid.uuid4())
        history = await self._get_history(session_id)

        # Get last challenge type to avoid
        last_type = history[-1] if history else None

        # Filter: exclude last challenge type (and possibly recent ones for stronger anti-repeat)
        recent_types = set(history[-2:]) if len(history) >= 2 else (set([last_type]) if last_type else set())
        available = [c for c in CHALLENGES if c["type"] not in recent_types]

        if not available:
            # All challenges recently used — reset and pick any
            available = CHALLENGES

        chosen = random.choice(available)
        challenge_id = secrets.token_urlsafe(16)
        nonce = secrets.token_hex(16)
        now = time.time()

        challenge_data = {
            "challenge_id": challenge_id,
            "challenge_type": chosen["type"],
            "steps": chosen["steps"],
            "display": chosen["display"],
            "difficulty": chosen["difficulty"],
            "nonce": nonce,
            "expires_at": now + CHALLENGE_TTL,
            "created_at": now,
            "session_id": session_id,
            "user_id": user_id,
        }

        await self._store_challenge(challenge_id, challenge_data)
        await self._append_history(session_id, chosen["type"])

        logger.debug(
            "challenge_ai.generate",
            challenge_id=challenge_id,
            type=chosen["type"],
            session_id=session_id,
            avoided=last_type,
        )

        return GeneratedChallenge(
            challenge_id=challenge_id,
            challenge_type=chosen["type"],
            steps=chosen["steps"],
            display=chosen["display"],
            difficulty=chosen["difficulty"],
            nonce=nonce,
            expires_at=now + CHALLENGE_TTL,
            created_at=now,
        )

    async def validate_and_consume(self, challenge_id: str, nonce: str) -> tuple[bool, dict | None]:
        """
        Validate a challenge by ID + nonce and mark it as consumed (one-time use).

        Returns (is_valid, challenge_data).
        """
        data = await self._load_challenge(challenge_id)
        if data is None:
            return False, None

        # Check nonce
        if data.get("nonce") != nonce:
            logger.warning("challenge_ai.validate: nonce mismatch", challenge_id=challenge_id)
            return False, None

        # Check expiry
        if time.time() > data.get("expires_at", 0):
            await self._delete_challenge(challenge_id)
            return False, None

        # Consume (delete) to prevent replay
        await self._delete_challenge(challenge_id)

        return True, data

    async def get_challenge(self, challenge_id: str) -> dict | None:
        """Load challenge data without consuming it (for multi-frame verification)."""
        return await self._load_challenge(challenge_id)
