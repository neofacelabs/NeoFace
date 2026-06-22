"""
NeoFace Trust Engine — Continuous Authentication Service (Module 12)
Verifies user authenticity continuously after initial login.

Every 30 seconds performs:
  - Face Presence check
  - Eye Tracking validation
  - Device Trust verification
  - Behavioral Monitoring

If trust score drops below threshold:
  - Triggers re-authentication flow
  - Suspends session

Session lifecycle:
  active → suspended → reauth_required → active (after successful reauth)
  active → terminated (on logout or persistent failure)
"""

from __future__ import annotations

import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.logging import logger

# ── Check interval ────────────────────────────────────────────────────────────
DEFAULT_CHECK_INTERVAL_SECONDS = 30

# ── Trust thresholds ──────────────────────────────────────────────────────────
REAUTH_THRESHOLD   = 70.0   # Below this → trigger re-authentication
SUSPEND_THRESHOLD  = 50.0   # Below this → suspend session immediately
TERMINATE_THRESHOLD = 30.0  # Below this → terminate session

# ── Trust score decay ─────────────────────────────────────────────────────────
# If no check is performed in 2x the interval, decay score by 5 points per missed check
SCORE_DECAY_PER_MISSED_CHECK = 5.0
MAX_MISSED_CHECKS_BEFORE_SUSPEND = 3


class ContinuousAuthService:
    """
    Manages continuous authentication sessions.

    This service is stateless — it receives session data from the caller
    (which loads it from the DB) and returns updated session state + decisions.

    For the background worker (Celery), this service is called every
    CHECK_INTERVAL seconds with the latest sensor data.
    """

    # ── Session creation ──────────────────────────────────────────────────────

    @staticmethod
    def create_session(
        user_id: str | uuid.UUID,
        device_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        check_interval: int = DEFAULT_CHECK_INTERVAL_SECONDS,
    ) -> dict:
        """
        Create a new continuous authentication session.

        Returns a dict suitable for persisting to the continuous_sessions table.
        """
        session_token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)

        return {
            "user_id": str(user_id),
            "session_token": session_token,
            "status": "active",
            "current_trust_score": 100.0,
            "started_at": now.isoformat(),
            "last_verified_at": now.isoformat(),
            "reauth_count": 0,
            "check_interval_seconds": check_interval,
            "device_id": device_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

    # ── Check evaluation ──────────────────────────────────────────────────────

    def evaluate_check(
        self,
        session: dict,
        check_results: dict,
    ) -> dict:
        """
        Evaluate a continuous authentication check result and update session state.

        Args:
            session:       Current session dict (from DB).
            check_results: Latest sensor readings:
                {
                  "face_present": bool,
                  "face_confidence": float,      # 0–100
                  "eye_confidence": float,        # 0–100
                  "is_frozen_eyes": bool,
                  "device_trust_score": float,    # 0–100
                  "behavior_score": float,        # 0–100
                }

        Returns:
            Updated session dict + action recommendations.
        """
        now = datetime.now(timezone.utc)
        current_score = float(session.get("current_trust_score", 100.0))

        # ── Compute check score ───────────────────────────────────────────────
        check_score = self._compute_check_score(check_results)

        # ── Smooth score with EMA (don't crash on single bad frame) ──────────
        # New score = 70% existing + 30% new check
        updated_score = 0.70 * current_score + 0.30 * check_score
        updated_score = round(max(0.0, min(100.0, updated_score)), 2)

        # ── Determine action ──────────────────────────────────────────────────
        action, new_status, termination_reason = self._determine_action(
            updated_score,
            check_results,
            session,
        )

        updated_session = dict(session)
        updated_session["current_trust_score"] = updated_score
        updated_session["last_verified_at"] = now.isoformat()
        updated_session["status"] = new_status

        if termination_reason:
            updated_session["terminated_at"] = now.isoformat()
            updated_session["termination_reason"] = termination_reason

        if action == "reauth_required":
            updated_session["reauth_count"] = session.get("reauth_count", 0) + 1

        logger.info(
            "continuous_auth.evaluate_check",
            session_token=session.get("session_token", "")[:16],
            user_id=session.get("user_id"),
            prev_score=current_score,
            check_score=check_score,
            updated_score=updated_score,
            action=action,
            status=new_status,
        )

        return {
            "session": updated_session,
            "action": action,            # continue | reauth_required | suspend | terminate
            "trust_score": updated_score,
            "check_score": check_score,
            "evaluated_at": now.isoformat(),
            "next_check_in_seconds": session.get("check_interval_seconds", DEFAULT_CHECK_INTERVAL_SECONDS),
        }

    # ── Score computation ─────────────────────────────────────────────────────

    @staticmethod
    def _compute_check_score(check_results: dict) -> float:
        """
        Compute a 0–100 check score from the sensor readings.
        Weights: face_present=40%, eye=20%, device=25%, behavior=15%
        """
        score = 0.0
        total_weight = 0.0

        # Face presence (most important for continuous auth)
        face_present = check_results.get("face_present", None)
        face_conf    = check_results.get("face_confidence", None)
        if face_present is not None:
            face_score = float(face_conf) if face_conf is not None else (100.0 if face_present else 0.0)
            if not face_present:
                face_score = 0.0  # No face = fail
            score += face_score * 0.40
            total_weight += 0.40

        # Eye tracking (liveness micro-check)
        eye_conf   = check_results.get("eye_confidence", None)
        is_frozen  = check_results.get("is_frozen_eyes", False)
        if eye_conf is not None:
            eye_score = float(eye_conf)
            if is_frozen:
                eye_score *= 0.3   # Heavy penalty for frozen eyes
            score += eye_score * 0.20
            total_weight += 0.20

        # Device trust
        device_trust = check_results.get("device_trust_score", None)
        if device_trust is not None:
            score += float(device_trust) * 0.25
            total_weight += 0.25

        # Behavioral biometrics
        behavior = check_results.get("behavior_score", None)
        if behavior is not None:
            score += float(behavior) * 0.15
            total_weight += 0.15

        if total_weight < 1e-9:
            return 70.0  # Default neutral score if no data

        # Normalize for missing signals
        normalized = score / total_weight
        return round(min(100.0, max(0.0, normalized)), 2)

    # ── Action decision ───────────────────────────────────────────────────────

    @staticmethod
    def _determine_action(
        updated_score: float,
        check_results: dict,
        session: dict,
    ) -> tuple[str, str, str | None]:
        """
        Determine what action to take based on the updated trust score.

        Returns (action, new_status, termination_reason).
        """
        reauth_count = session.get("reauth_count", 0)

        # Terminate after 3 consecutive failed re-auths
        if reauth_count >= 3 and updated_score < SUSPEND_THRESHOLD:
            return "terminate", "terminated", "max_reauth_attempts_exceeded"

        # Critical drop — face gone or score extremely low
        if not check_results.get("face_present", True) and updated_score < TERMINATE_THRESHOLD:
            return "terminate", "terminated", "face_absent_critical"

        if updated_score < TERMINATE_THRESHOLD:
            return "terminate", "terminated", f"trust_score_critical:{updated_score:.0f}"

        if updated_score < SUSPEND_THRESHOLD:
            return "suspend", "suspended", None

        if updated_score < REAUTH_THRESHOLD:
            return "reauth_required", "reauth_required", None

        return "continue", "active", None

    # ── Session management helpers ────────────────────────────────────────────

    @staticmethod
    def should_check_now(session: dict) -> bool:
        """
        Return True if it's time for the next continuous auth check.

        Uses last_verified_at + check_interval_seconds to determine timing.
        """
        last_verified_str = session.get("last_verified_at")
        if not last_verified_str:
            return True

        try:
            last_verified = datetime.fromisoformat(last_verified_str)
            interval = float(session.get("check_interval_seconds", DEFAULT_CHECK_INTERVAL_SECONDS))
            now = datetime.now(timezone.utc)
            elapsed = (now - last_verified).total_seconds()
            return elapsed >= interval
        except Exception:
            return True

    @staticmethod
    def apply_score_decay(session: dict, active_user_typing: bool = False) -> dict:
        """
        Apply trust score decay for missed checks.
        Call this when the session is overdue for a check.
        If active_user_typing is True, decay rate is reduced to 1.0 (from 5.0) as keyboard input is present.
        """
        last_verified_str = session.get("last_verified_at")
        if not last_verified_str:
            return session

        try:
            last_verified = datetime.fromisoformat(last_verified_str)
            interval = float(session.get("check_interval_seconds", DEFAULT_CHECK_INTERVAL_SECONDS))
            elapsed = (datetime.now(timezone.utc) - last_verified).total_seconds()
            missed_checks = int(elapsed / interval) - 1
            if missed_checks > 0:
                decay_rate = 1.0 if active_user_typing else SCORE_DECAY_PER_MISSED_CHECK
                decay = min(decay_rate * missed_checks, 30.0)
                current_score = float(session.get("current_trust_score", 100.0))
                new_score = max(0.0, current_score - decay)
                updated = dict(session)
                updated["current_trust_score"] = round(new_score, 2)
                logger.debug(
                    "continuous_auth.decay",
                    missed_checks=missed_checks,
                    decay=decay,
                    new_score=new_score,
                    active_user_typing=active_user_typing,
                )
                return updated
        except Exception:
            pass
        return session
