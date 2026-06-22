"""
NeoFace Trust Engine — Behavioral Biometrics Service (Module 10)
Builds unique behavioral profiles and scores anomalies.

Collects:
  Mouse:    movement speed, curvature, hesitation rate
  Keyboard: typing speed (WPM), dwell time, flight time
  Touch:    swipe velocity, touch pressure, gesture rhythm

Models (Phase progression):
  Phase 1: Rule-Based (immediate, no training data required)
  Phase 2: Isolation Forest (unsupervised anomaly detection, 20+ events)
  Phase 3: XGBoost (supervised, 100+ labeled events — future)

Output:
  { "behavior_score": 93 }
"""

from __future__ import annotations

import math
import numpy as np
import statistics
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import logger

# Minimum events to establish baseline
_RULE_BASED_MIN_EVENTS = 1
_ISOLATION_FOREST_MIN  = 20

# Behavior score weights
_WEIGHTS = {
    "mouse":    0.35,
    "keyboard": 0.40,
    "touch":    0.25,
}

# Rule-based thresholds (typical human ranges)
_MOUSE_SPEED_MIN   = 50.0    # px/s
_MOUSE_SPEED_MAX   = 3000.0  # px/s
_TYPING_WPM_MIN    = 5.0
_TYPING_WPM_MAX    = 150.0
_DWELL_MS_MIN      = 30.0    # ms
_DWELL_MS_MAX      = 800.0   # ms
_FLIGHT_MS_MIN     = 20.0    # ms
_FLIGHT_MS_MAX     = 1500.0  # ms
_SWIPE_VEL_MIN     = 50.0    # px/s
_SWIPE_VEL_MAX     = 5000.0  # px/s


@dataclass
class BehaviorEventData:
    """Normalized behavioral event from the client SDK."""
    event_type: str         # mouse | keyboard | touch
    metrics: dict[str, Any]


@dataclass
class BehaviorScoreResult:
    """Output from the behavioral biometrics service."""
    behavior_score: float    # 0–100 (higher = more likely to be the genuine user)
    is_anomalous: bool
    anomaly_score: float     # IsolationForest raw score (negative = more anomalous)
    method: str              # rule_based | isolation_forest | xgboost
    component_scores: dict[str, float]   # Per-modality scores
    risk_flags: list[str]


@dataclass
class BehaviorProfile:
    """In-memory behavioral baseline for a user (mirrors the DB model)."""
    user_id: str
    total_events: int = 0
    is_baseline_established: bool = False

    # Mouse
    avg_mouse_speed: float | None = None
    avg_mouse_curvature: float | None = None
    avg_hesitation_rate: float | None = None

    # Keyboard
    avg_typing_speed_wpm: float | None = None
    avg_dwell_time_ms: float | None = None
    avg_flight_time_ms: float | None = None

    # Touch
    avg_swipe_velocity: float | None = None
    avg_touch_pressure: float | None = None
    avg_gesture_rhythm: float | None = None

    # IsolationForest model state (serializable)
    model_data: dict | None = None


class BehavioralBiometricsService:
    """
    Behavioral biometrics service.

    Stateless — receives a BehaviorProfile (loaded from DB) and new event data,
    then computes a score and an updated profile.

    Phase 1 (Rule-Based): validates event values are within human ranges.
    Phase 2 (Isolation Forest): detects anomalies against established baseline.
    """

    # ── Phase 1: Rule-based scoring ───────────────────────────────────────────

    def _score_mouse_rule(self, metrics: dict) -> tuple[float, list[str]]:
        """Score mouse metrics against human-range rules. Returns (0–100, flags)."""
        flags: list[str] = []
        scores: list[float] = []

        speed = metrics.get("speed_pxps", metrics.get("speed"))
        if speed is not None:
            speed = float(speed)
            if speed < _MOUSE_SPEED_MIN or speed > _MOUSE_SPEED_MAX:
                flags.append(f"mouse_speed_abnormal:{speed:.0f}")
                scores.append(20.0)
            else:
                # Normalize within human range
                normalized = (speed - _MOUSE_SPEED_MIN) / (_MOUSE_SPEED_MAX - _MOUSE_SPEED_MIN)
                # Optimal around 300–800 px/s
                bell = 1.0 - abs(normalized - 0.25) * 2.0
                scores.append(max(50.0, bell * 100))

        curvature = metrics.get("curvature")
        if curvature is not None:
            curvature = float(curvature)
            if curvature < 0 or curvature > 2.0:
                flags.append(f"mouse_curvature_abnormal:{curvature:.2f}")
                scores.append(20.0)
            else:
                scores.append(80.0)  # Natural curvature range

        hesitation = metrics.get("hesitation_rate")
        if hesitation is not None:
            hesitation = float(hesitation)
            if hesitation > 0.8:
                flags.append(f"mouse_hesitation_high:{hesitation:.2f}")
                scores.append(40.0)
            else:
                scores.append(90.0)

        if not scores:
            return 75.0, flags
        return statistics.mean(scores), flags

    def _score_keyboard_rule(self, metrics: dict) -> tuple[float, list[str]]:
        """Score keyboard metrics. Returns (0–100, flags)."""
        flags: list[str] = []
        scores: list[float] = []

        wpm = metrics.get("typing_speed_wpm", metrics.get("wpm"))
        if wpm is not None:
            wpm = float(wpm)
            if wpm < _TYPING_WPM_MIN or wpm > _TYPING_WPM_MAX:
                flags.append(f"typing_speed_abnormal:{wpm:.0f}wpm")
                scores.append(10.0)
            else:
                scores.append(85.0)

        dwell = metrics.get("dwell_time_ms", metrics.get("dwell"))
        if dwell is not None:
            dwell = float(dwell)
            if dwell < _DWELL_MS_MIN or dwell > _DWELL_MS_MAX:
                flags.append(f"dwell_time_abnormal:{dwell:.0f}ms")
                scores.append(20.0)
            else:
                scores.append(88.0)

        flight = metrics.get("flight_time_ms", metrics.get("flight"))
        if flight is not None:
            flight = float(flight)
            if flight < _FLIGHT_MS_MIN or flight > _FLIGHT_MS_MAX:
                flags.append(f"flight_time_abnormal:{flight:.0f}ms")
                scores.append(20.0)
            else:
                scores.append(88.0)

        if not scores:
            return 75.0, flags
        return statistics.mean(scores), flags

    def _score_touch_rule(self, metrics: dict) -> tuple[float, list[str]]:
        """Score touch metrics. Returns (0–100, flags)."""
        flags: list[str] = []
        scores: list[float] = []

        velocity = metrics.get("swipe_velocity", metrics.get("velocity"))
        if velocity is not None:
            velocity = float(velocity)
            if velocity < _SWIPE_VEL_MIN or velocity > _SWIPE_VEL_MAX:
                flags.append(f"swipe_velocity_abnormal:{velocity:.0f}")
                scores.append(20.0)
            else:
                scores.append(85.0)

        pressure = metrics.get("touch_pressure", metrics.get("pressure"))
        if pressure is not None:
            pressure = float(pressure)
            if pressure < 0.01 or pressure > 1.0:
                flags.append(f"touch_pressure_abnormal:{pressure:.3f}")
                scores.append(20.0)
            elif pressure < 0.1:
                flags.append("touch_pressure_very_light")
                scores.append(50.0)
            else:
                scores.append(88.0)

        rhythm = metrics.get("gesture_rhythm")
        if rhythm is not None:
            rhythm = float(rhythm)
            if rhythm < 0.0 or rhythm > 10.0:
                flags.append(f"gesture_rhythm_abnormal:{rhythm:.2f}")
                scores.append(20.0)
            else:
                scores.append(85.0)

        if not scores:
            return 75.0, flags
        return statistics.mean(scores), flags

    # ── Phase 2: Isolation Forest ─────────────────────────────────────────────

    def _isolation_forest_score(
        self,
        new_metrics: dict,
        profile: BehaviorProfile,
        event_type: str,
    ) -> float | None:
        """
        Compare new metrics against the user's established baseline using
        a simple z-score anomaly method (Isolation Forest approximation).

        Returns anomaly score (-1 = outlier, 0 = normal) or None if not enough data.
        """
        if profile.total_events < _ISOLATION_FOREST_MIN:
            return None

        deviations: list[float] = []

        if event_type == "mouse" and profile.avg_mouse_speed is not None:
            speed = new_metrics.get("speed_pxps", new_metrics.get("speed"))
            if speed is not None:
                z = abs(float(speed) - profile.avg_mouse_speed) / (profile.avg_mouse_speed * 0.4 + 1e-9)
                deviations.append(z)

        elif event_type == "keyboard":
            if profile.avg_typing_speed_wpm is not None:
                wpm = new_metrics.get("typing_speed_wpm", new_metrics.get("wpm"))
                if wpm is not None:
                    z = abs(float(wpm) - profile.avg_typing_speed_wpm) / (profile.avg_typing_speed_wpm * 0.5 + 1e-9)
                    deviations.append(z)

            if profile.avg_dwell_time_ms is not None:
                dwell = new_metrics.get("dwell_time_ms", new_metrics.get("dwell"))
                if dwell is not None:
                    z = abs(float(dwell) - profile.avg_dwell_time_ms) / (profile.avg_dwell_time_ms * 0.5 + 1e-9)
                    deviations.append(z)

        elif event_type == "touch" and profile.avg_swipe_velocity is not None:
            vel = new_metrics.get("swipe_velocity", new_metrics.get("velocity"))
            if vel is not None:
                z = abs(float(vel) - profile.avg_swipe_velocity) / (profile.avg_swipe_velocity * 0.5 + 1e-9)
                deviations.append(z)

        if not deviations:
            return None

        avg_z = statistics.mean(deviations)
        # Map z-score to IsolationForest-like score: 0 = normal, -1 = extreme outlier
        anomaly_score = float(-min(avg_z / 3.0, 1.0))
        return round(anomaly_score, 4)

    # ── Profile update ────────────────────────────────────────────────────────

    def update_profile(self, profile: BehaviorProfile, events: list[BehaviorEventData]) -> BehaviorProfile:
        """
        Update the user's behavioral profile with new events using exponential moving average.
        Returns the updated profile (caller must persist to DB).
        """
        alpha = 0.1  # EMA smoothing factor (10% weight to new observations)

        for event in events:
            metrics = event.metrics
            profile.total_events += 1

            if event.event_type == "mouse":
                speed = metrics.get("speed_pxps", metrics.get("speed"))
                if speed is not None:
                    speed = float(speed)
                    if _MOUSE_SPEED_MIN <= speed <= _MOUSE_SPEED_MAX:
                        profile.avg_mouse_speed = _ema(profile.avg_mouse_speed, speed, alpha)

                curvature = metrics.get("curvature")
                if curvature is not None:
                    profile.avg_mouse_curvature = _ema(profile.avg_mouse_curvature, float(curvature), alpha)

                hes = metrics.get("hesitation_rate")
                if hes is not None:
                    profile.avg_hesitation_rate = _ema(profile.avg_hesitation_rate, float(hes), alpha)

            elif event.event_type == "keyboard":
                wpm = metrics.get("typing_speed_wpm", metrics.get("wpm"))
                if wpm is not None:
                    profile.avg_typing_speed_wpm = _ema(profile.avg_typing_speed_wpm, float(wpm), alpha)

                dwell = metrics.get("dwell_time_ms", metrics.get("dwell"))
                if dwell is not None:
                    profile.avg_dwell_time_ms = _ema(profile.avg_dwell_time_ms, float(dwell), alpha)

                flight = metrics.get("flight_time_ms", metrics.get("flight"))
                if flight is not None:
                    profile.avg_flight_time_ms = _ema(profile.avg_flight_time_ms, float(flight), alpha)

            elif event.event_type == "touch":
                vel = metrics.get("swipe_velocity", metrics.get("velocity"))
                if vel is not None:
                    profile.avg_swipe_velocity = _ema(profile.avg_swipe_velocity, float(vel), alpha)

                press = metrics.get("touch_pressure", metrics.get("pressure"))
                if press is not None:
                    profile.avg_touch_pressure = _ema(profile.avg_touch_pressure, float(press), alpha)

                rhythm = metrics.get("gesture_rhythm")
                if rhythm is not None:
                    profile.avg_gesture_rhythm = _ema(profile.avg_gesture_rhythm, float(rhythm), alpha)

        profile.is_baseline_established = profile.total_events >= _ISOLATION_FOREST_MIN
        return profile

    def _xgboost_score(
        self,
        new_metrics: dict,
        profile: BehaviorProfile,
        event_type: str,
    ) -> float | None:
        """
        Compare new metrics using the user's supervised XGBoost classifier.
        Returns genuine user probability (0.0 to 1.0) or None if model is unavailable.
        """
        if not profile.model_data or profile.model_data.get("algorithm") != "xgboost":
            return None

        model_bytes_b64 = profile.model_data.get("model_bytes")
        if not model_bytes_b64:
            return None

        try:
            import base64
            import xgboost as xgb
            import numpy as np

            # Extract features for the new event
            feats = extract_features(event_type, new_metrics)
            X = np.array([feats])

            # Load booster from Compact UBJ bytes
            raw_bytes = base64.b64decode(model_bytes_b64)
            bst = xgb.Booster()
            bst.load_model(bytearray(raw_bytes))

            dmatrix = xgb.DMatrix(X)
            prob = float(bst.predict(dmatrix)[0])
            return prob
        except Exception as exc:
            logger.warning("BehavioralBiometricsService: XGBoost prediction error", error=str(exc))
            return None

    # ── Main scoring ──────────────────────────────────────────────────────────

    def score(
        self,
        events: list[BehaviorEventData],
        profile: BehaviorProfile | None = None,
    ) -> BehaviorScoreResult:
        """
        Compute a behavioral trust score from a batch of behavioral events.

        Args:
            events:  New behavioral events from this session.
            profile: User's existing behavioral baseline (may be None for new users).

        Returns:
            BehaviorScoreResult with behavior_score 0–100.
        """
        if not events:
            return BehaviorScoreResult(
                behavior_score=75.0,    # Neutral for new users with no data
                is_anomalous=False,
                anomaly_score=0.0,
                method="no_data",
                component_scores={},
                risk_flags=[],
            )

        component_scores: dict[str, float] = {}
        all_flags: list[str] = []
        anomaly_scores: list[float] = []
        xgb_scores: list[float] = []
        method = "rule_based"

        mouse_scores:    list[float] = []
        keyboard_scores: list[float] = []
        touch_scores:    list[float] = []

        is_xgb_available = profile and profile.model_data and profile.model_data.get("algorithm") == "xgboost"

        for event in events:
            m = event.metrics

            if event.event_type == "mouse":
                s, flags = self._score_mouse_rule(m)
                mouse_scores.append(s)
                all_flags.extend(flags)
            elif event.event_type == "keyboard":
                s, flags = self._score_keyboard_rule(m)
                keyboard_scores.append(s)
                all_flags.extend(flags)
            elif event.event_type == "touch":
                s, flags = self._score_touch_rule(m)
                touch_scores.append(s)
                all_flags.extend(flags)

            # Phase 3: Supervised XGBoost model score
            if is_xgb_available:
                xgb_score = self._xgboost_score(m, profile, event.event_type)
                if xgb_score is not None:
                    xgb_scores.append(xgb_score)
                    method = "xgboost"
            # Phase 2: IsolationForest overlay
            elif profile and profile.is_baseline_established:
                iso_score = self._isolation_forest_score(m, profile, event.event_type)
                if iso_score is not None:
                    anomaly_scores.append(iso_score)
                    method = "isolation_forest"

        # Aggregate per-modality or use XGBoost directly
        if method == "xgboost" and xgb_scores:
            avg_xgb = statistics.mean(xgb_scores)
            final_score = avg_xgb * 100.0
            avg_anomaly = -float(1.0 - avg_xgb)
            if avg_xgb < 0.5:
                all_flags.append(f"xgboost_anomaly_probability:{avg_xgb:.3f}")
        else:
            if mouse_scores:
                component_scores["mouse"] = statistics.mean(mouse_scores)
            if keyboard_scores:
                component_scores["keyboard"] = statistics.mean(keyboard_scores)
            if touch_scores:
                component_scores["touch"] = statistics.mean(touch_scores)

            if not component_scores:
                final_score = 75.0
            else:
                # Weighted average across available modalities
                weights = {k: _WEIGHTS[k] for k in component_scores}
                total_w = sum(weights.values())
                final_score = sum(component_scores[k] * weights[k] / total_w for k in component_scores)

            # Apply IsolationForest adjustment
            avg_anomaly = statistics.mean(anomaly_scores) if anomaly_scores else 0.0
            if avg_anomaly < -0.5:
                # Significant anomaly detected — reduce score proportionally
                penalty = abs(avg_anomaly + 0.5) * 40.0
                final_score = max(0.0, final_score - penalty)
                all_flags.append(f"isolation_forest_anomaly:{avg_anomaly:.3f}")

        # Standard component scores for response payload reporting
        if mouse_scores:
            component_scores["mouse"] = statistics.mean(mouse_scores)
        if keyboard_scores:
            component_scores["keyboard"] = statistics.mean(keyboard_scores)
        if touch_scores:
            component_scores["touch"] = statistics.mean(touch_scores)

        final_score = round(min(100.0, max(0.0, final_score)), 1)
        is_anomalous = final_score < 60.0 or len([f for f in all_flags if "abnormal" in f]) >= 2

        logger.debug(
            "behavioral_biometrics.score",
            score=final_score, is_anomalous=is_anomalous,
            method=method, flags=all_flags[:5],
        )

        return BehaviorScoreResult(
            behavior_score=final_score,
            is_anomalous=is_anomalous,
            anomaly_score=round(avg_anomaly, 4),
            method=method,
            component_scores={k: round(v, 1) for k, v in component_scores.items()},
            risk_flags=all_flags,
        )


# ── EMA helper ────────────────────────────────────────────────────────────────

def _ema(current: float | None, new_value: float, alpha: float) -> float:
    """Exponential moving average update."""
    if current is None:
        return new_value
    return float(alpha * new_value + (1.0 - alpha) * current)


def extract_features(event_type: str, metrics: dict) -> list[float]:
    """
    Extract a flat 12-dimensional feature vector from a behavioral event.
    Missing fields are populated with np.nan for XGBoost compatibility.
    """
    features = [np.nan] * 12

    # One-hot encode event_type
    if event_type == "mouse":
        features[0] = 1.0
        features[1] = 0.0
        features[2] = 0.0
        features[3] = float(metrics.get("speed_pxps", metrics.get("speed", np.nan)))
        features[4] = float(metrics.get("curvature", np.nan))
        features[5] = float(metrics.get("hesitation_rate", np.nan))
    elif event_type == "keyboard":
        features[0] = 0.0
        features[1] = 1.0
        features[2] = 0.0
        features[6] = float(metrics.get("typing_speed_wpm", metrics.get("wpm", np.nan)))
        features[7] = float(metrics.get("dwell_time_ms", metrics.get("dwell", np.nan)))
        features[8] = float(metrics.get("flight_time_ms", metrics.get("flight", np.nan)))
    elif event_type == "touch":
        features[0] = 0.0
        features[1] = 0.0
        features[2] = 1.0
        features[9] = float(metrics.get("swipe_velocity", metrics.get("velocity", np.nan)))
        features[10] = float(metrics.get("touch_pressure", metrics.get("pressure", np.nan)))
        features[11] = float(metrics.get("gesture_rhythm", np.nan))

    return features
