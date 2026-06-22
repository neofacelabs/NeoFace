"""
NeoFace Trust Engine — Enhanced Device Trust Engine (Module 9+)

Production-grade device integrity assessment with extended signal collection.

Signals:
  - Device seen before (low risk)
  - New device (medium risk)
  - Emulator/Virtual environment (high risk)
  - Rooted/Jailbroken device (high risk)
  - Browser fingerprint mismatch (elevated risk)
  - OS version mismatch (elevated risk)
  - Compromised indicators (high risk)

This service complements the existing device_trust_service.py by adding
advanced fingerprinting and behavioral signals.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.core.logging import logger


@dataclass
class BrowserFingerprint:
    """Browser/Device fingerprint from client."""
    
    user_agent: str | None
    accept_language: str | None
    accept_encoding: str | None
    screen_resolution: tuple[int, int] | None  # (width, height)
    timezone_offset: int | None  # minutes from UTC
    cpu_cores: int | None
    device_memory: int | None  # GB
    max_touch_points: int | None
    webgl_vendor: str | None
    webgl_renderer: str | None
    canvas_fingerprint: str | None  # Hash of canvas rendering
    fonts_available: set[str] | None
    hardware_concurrency: int | None


@dataclass
class DeviceProfile:
    """Known device profile from user's history."""
    
    device_id: str
    device_name: str | None
    first_seen: datetime
    last_seen: datetime
    os_type: str  # android | ios | macos | windows | linux | unknown
    os_version: str | None
    browser: str | None
    browser_version: str | None
    fingerprint_hash: str | None
    is_trusted: bool = False
    login_count: int = 0
    failed_auth_count: int = 0


@dataclass
class DeviceRiskResult:
    """Output from enhanced device trust calculation."""
    
    device_risk: float                # 0.0–1.0 (overall device risk)
    device_recognition: str           # known | new | high_risk
    fingerprint_mismatch: bool        # Fingerprint doesn't match recorded
    os_mismatch: bool                 # OS changed unexpectedly
    emulator_risk: float              # 0.0–1.0
    root_risk: float                  # 0.0–1.0
    automation_risk: float            # 0.0–1.0
    behavioral_anomalies: list[str]   # Suspicious patterns
    final_device_risk: float          # Weighted composite


class EnhancedDeviceTrustEngine:
    """
    Advanced device trust scoring with fingerprinting and behavioral analysis.
    
    Stateless service — device history should be fetched from repository.
    """

    # Risk scoring weights
    KNOWN_DEVICE_RISK = 0.05
    NEW_DEVICE_RISK = 0.30
    HIGH_RISK_DEVICE = 0.85

    # Component thresholds
    EMULATOR_HIGH_RISK = 0.75
    ROOT_HIGH_RISK = 0.75
    AUTOMATION_HIGH_RISK = 0.85

    @staticmethod
    def calculate_device_risk(
        current_fingerprint: BrowserFingerprint,
        known_device_profile: DeviceProfile | None,
        trust_signals: dict,
    ) -> DeviceRiskResult:
        """
        Assess device risk from fingerprint, recognition, and trust signals.
        
        Args:
            current_fingerprint: Current browser/device fingerprint.
            known_device_profile: Previously seen device (from database).
            trust_signals: Platform-specific signals (rooted, emulator, etc).
            
        Returns:
            DeviceRiskResult with device_risk and behavioral flags.
        """
        anomalies: list[str] = []
        
        # ── 1. Device Recognition ────────────────────────────────────────────
        if known_device_profile is not None:
            device_recognition = "known"
            device_recognition_risk = EnhancedDeviceTrustEngine.KNOWN_DEVICE_RISK
        else:
            device_recognition = "new"
            device_recognition_risk = EnhancedDeviceTrustEngine.NEW_DEVICE_RISK
            anomalies.append("new_device")

        # ── 2. Fingerprint Mismatch ──────────────────────────────────────────
        fingerprint_mismatch = False
        if known_device_profile is not None:
            current_hash = EnhancedDeviceTrustEngine._fingerprint_hash(current_fingerprint)
            if (known_device_profile.fingerprint_hash and
                known_device_profile.fingerprint_hash != current_hash):
                fingerprint_mismatch = True
                anomalies.append("fingerprint_mismatch")
                logger.warning(
                    "device_trust.fingerprint_mismatch",
                    device_id=known_device_profile.device_id,
                )

        # ── 3. OS Version Mismatch ──────────────────────────────────────────
        os_mismatch = False
        if known_device_profile is not None:
            if (known_device_profile.os_version and
                trust_signals.get("os_version") and
                known_device_profile.os_version != trust_signals.get("os_version")):
                os_mismatch = True
                anomalies.append("os_version_mismatch")
                logger.info(
                    "device_trust.os_version_mismatch",
                    device_id=known_device_profile.device_id,
                    previous=known_device_profile.os_version,
                    current=trust_signals.get("os_version"),
                )

        # ── 4. Emulator/Virtual Environment Detection ─────────────────────────
        is_emulator = trust_signals.get("is_emulator", False)
        emulator_risk = EnhancedDeviceTrustEngine.EMULATOR_HIGH_RISK if is_emulator else 0.0
        if is_emulator:
            anomalies.append("emulator_detected")

        # ── 5. Root/Jailbreak Detection ──────────────────────────────────────
        is_rooted = (
            trust_signals.get("is_rooted") or
            trust_signals.get("is_jailbroken")
        )
        root_risk = EnhancedDeviceTrustEngine.ROOT_HIGH_RISK if is_rooted else 0.0
        if is_rooted:
            jailbreak_type = "jailbroken" if trust_signals.get("is_jailbroken") else "rooted"
            anomalies.append(f"device_{jailbreak_type}")

        # ── 6. Browser Automation Detection ──────────────────────────────────
        is_automation = trust_signals.get("is_automation_detected", False)
        automation_risk = EnhancedDeviceTrustEngine.AUTOMATION_HIGH_RISK if is_automation else 0.0
        if is_automation:
            anomalies.append("automation_framework_detected")

        # ── 7. Screen Resolution Anomaly ────────────────────────────────────
        if (known_device_profile is not None and
            current_fingerprint.screen_resolution):
            # Resolution shouldn't change between sessions
            if (trust_signals.get("previous_resolution") and
                trust_signals.get("previous_resolution") != str(current_fingerprint.screen_resolution)):
                anomalies.append("screen_resolution_changed")

        # ── 8. Timezone Mismatch (could indicate location spoofing) ─────────
        if (known_device_profile is not None and
            trust_signals.get("previous_timezone") and
            current_fingerprint.timezone_offset):
            if trust_signals.get("previous_timezone") != current_fingerprint.timezone_offset:
                # Timezone can legitimately change, but flag for analysis
                # Only flag if in known location but timezone is radically different
                if abs(trust_signals.get("previous_timezone", 0) - current_fingerprint.timezone_offset) > 180:
                    anomalies.append("timezone_anomaly")

        # ── 9. Repeated Failed Authentications ───────────────────────────────
        if (known_device_profile is not None and
            known_device_profile.failed_auth_count >= 5):
            anomalies.append(f"repeated_failures:{known_device_profile.failed_auth_count}")

        # ── Composite device risk ─────────────────────────────────────────────
        # Weights: device_recognition (50%) + emulator (15%) + root (15%) + automation (10%) + fingerprint (10%)
        final_device_risk = (
            0.50 * device_recognition_risk +
            0.15 * emulator_risk +
            0.15 * root_risk +
            0.10 * automation_risk +
            0.10 * (1.0 if fingerprint_mismatch else 0.0)
        )
        final_device_risk = min(max(final_device_risk, 0.0), 1.0)

        logger.debug(
            "device_trust.enhanced",
            device_recognition=device_recognition,
            fingerprint_mismatch=fingerprint_mismatch,
            os_mismatch=os_mismatch,
            is_emulator=is_emulator,
            is_rooted=is_rooted,
            is_automation=is_automation,
            anomalies=anomalies,
            final_device_risk=round(final_device_risk, 3),
        )

        return DeviceRiskResult(
            device_risk=device_recognition_risk,
            device_recognition=device_recognition,
            fingerprint_mismatch=fingerprint_mismatch,
            os_mismatch=os_mismatch,
            emulator_risk=emulator_risk,
            root_risk=root_risk,
            automation_risk=automation_risk,
            behavioral_anomalies=anomalies,
            final_device_risk=final_device_risk,
        )

    @staticmethod
    def _fingerprint_hash(fingerprint: BrowserFingerprint) -> str:
        """
        Generate a deterministic hash of the device fingerprint.
        
        Used to detect if the same device is connecting with a different fingerprint.
        """
        components = [
            fingerprint.user_agent or "",
            str(fingerprint.screen_resolution or ""),
            str(fingerprint.timezone_offset or ""),
            fingerprint.webgl_renderer or "",
            str(fingerprint.cpu_cores or ""),
            str(fingerprint.max_touch_points or ""),
        ]
        combined = "|".join(components)
        return hashlib.sha256(combined.encode()).hexdigest()

    @staticmethod
    def create_or_update_profile(
        device_id: str,
        fingerprint: BrowserFingerprint,
        trust_signals: dict,
        existing_profile: DeviceProfile | None = None,
    ) -> DeviceProfile:
        """
        Create or update a device profile for storage.
        
        Args:
            device_id: Unique device identifier.
            fingerprint: Current browser fingerprint.
            trust_signals: Platform-specific signals.
            existing_profile: Previous profile (if updating).
            
        Returns:
            Updated DeviceProfile ready for persistence.
        """
        now = datetime.utcnow()

        if existing_profile is not None:
            return DeviceProfile(
                device_id=device_id,
                device_name=existing_profile.device_name,
                first_seen=existing_profile.first_seen,
                last_seen=now,
                os_type=trust_signals.get("os_type", existing_profile.os_type),
                os_version=trust_signals.get("os_version", existing_profile.os_version),
                browser=fingerprint.user_agent,
                browser_version=trust_signals.get("browser_version"),
                fingerprint_hash=EnhancedDeviceTrustEngine._fingerprint_hash(fingerprint),
                is_trusted=existing_profile.is_trusted,
                login_count=existing_profile.login_count + 1,
                failed_auth_count=existing_profile.failed_auth_count,
            )
        else:
            return DeviceProfile(
                device_id=device_id,
                device_name=trust_signals.get("device_name"),
                first_seen=now,
                last_seen=now,
                os_type=trust_signals.get("os_type", "unknown"),
                os_version=trust_signals.get("os_version"),
                browser=fingerprint.user_agent,
                browser_version=trust_signals.get("browser_version"),
                fingerprint_hash=EnhancedDeviceTrustEngine._fingerprint_hash(fingerprint),
                is_trusted=False,
                login_count=1,
                failed_auth_count=0,
            )

    @staticmethod
    def mark_authentication_failed(profile: DeviceProfile) -> DeviceProfile:
        """Update device profile after failed authentication."""
        profile.failed_auth_count += 1
        return profile

    @staticmethod
    def mark_trusted(profile: DeviceProfile) -> DeviceProfile:
        """Mark device as trusted by user."""
        profile.is_trusted = True
        profile.failed_auth_count = 0
        return profile
