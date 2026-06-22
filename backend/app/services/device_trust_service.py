"""
NeoFace Trust Engine — Device Integrity Service (Module 9)
Computes a trust score for the requesting device.

Detects on Android:
  - Root / SuperSU / Magisk
  - USB Debugging enabled
  - Emulator

Detects on iOS:
  - Jailbreak (Cydia, file system anomalies)
  - Debug mode

Detects on Web:
  - Virtual / spoofed camera
  - Selenium / WebDriver automation
  - Headless browser (Puppeteer, Playwright)
  - Browser automation frameworks

Output:
  { "device_trust": 91, "rooted": false, "emulator": false }
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.logging import logger

# Trust score deductions per flag (out of 100)
_DEDUCTIONS = {
    "is_rooted":              40,
    "is_jailbroken":          40,
    "is_emulator":            35,
    "is_usb_debugging":       15,
    "is_virtual_camera":      30,
    "is_headless_browser":    35,
    "is_automation_detected": 30,
    "unknown_platform":       10,
    "no_device_id":           5,
}

# Browser automation fingerprints (User-Agent strings)
_AUTOMATION_UA_PATTERNS = [
    r"HeadlessChrome",
    r"PhantomJS",
    r"Selenium",
    r"WebDriver",
    r"Playwright",
    r"Puppeteer",
    r"cypress",
    r"nightwatch",
]

# Virtual camera indicators in device info
_VIRTUAL_CAMERA_KEYWORDS = [
    "manycam",
    "obs-virtual",
    "obs virtual",
    "droidcam",
    "ivcam",
    "virtualcam",
    "reincubate",
    "camo",
    "ecamm",
    "xsplit",
]

# Android emulator fingerprints
_ANDROID_EMULATOR_PATTERNS = [
    r"sdk_gphone",
    r"generic_x86",
    r"emulator",
    r"android sdk",
    r"goldfish",
    r"vbox86",
    r"generic.*86",
    r"nox",
    r"bluestacks",
    r"genymotion",
]

# iOS jailbreak filesystem paths (sent by client-side SDK)
_JAILBREAK_FILES = [
    "/Applications/Cydia.app",
    "/Library/MobileSubstrate/MobileSubstrate.dylib",
    "/bin/bash",
    "/usr/sbin/sshd",
    "/etc/apt",
    "/usr/bin/ssh",
    "/private/var/lib/apt/",
    "/private/var/tmp/cydia.log",
    "/private/var/stash",
    "/usr/libexec/cydia/",
    "/Applications/RockApp.app",
    "/Applications/Icy.app",
    "/Applications/WinterBoard.app",
]

# Rooted Android file paths
_ROOT_FILES = [
    "/system/app/Superuser.apk",
    "/sbin/su",
    "/system/bin/su",
    "/system/xbin/su",
    "/data/local/xbin/su",
    "/data/local/bin/su",
    "/system/sd/xbin/su",
    "/system/bin/failsafe/su",
    "/data/local/su",
    "/system/xbin/busybox",
    "/data/data/com.noshufou.android.su",
    "/data/data/com.thirdparty.superuser",
    "/data/data/com.yellowes.su",
]


@dataclass
class DeviceTrustResult:
    """Structured output from the device trust service."""
    device_trust_score: int       # 0–100
    platform: str                 # android | ios | web | unknown
    is_rooted: bool = False
    is_jailbroken: bool = False
    is_emulator: bool = False
    is_usb_debugging: bool = False
    is_virtual_camera: bool = False
    is_headless_browser: bool = False
    is_automation_detected: bool = False
    risk_flags: list[str] = field(default_factory=list)
    signals: dict = field(default_factory=dict)


class DeviceTrustService:
    """
    Stateless device integrity assessment service.

    Accepts device signals from the client SDK (JSON payload) and
    computes a trust score. The client SDK must send signals it collected
    locally — the server cannot directly inspect the device.

    Signal payload schema (from client SDK):
    {
      "platform": "android" | "ios" | "web",
      "user_agent": "...",
      "device_id": "...",
      "device_model": "...",         # Android
      "is_rooted": bool,             # Android
      "magisk_detected": bool,       # Android
      "usb_debugging": bool,         # Android
      "is_emulator": bool,           # Android / iOS
      "root_files_found": [...],     # Android
      "jailbreak_files_found": [...],# iOS
      "camera_ids": [...],           # Web: camera device IDs
      "webgl_vendor": "...",         # Web
      "webgl_renderer": "...",       # Web
      "navigator_webdriver": bool,   # Web
      "chrome_runtime": bool,        # Web: headless Chrome detection
    }
    """

    def assess(self, signals: dict, user_agent: str = "") -> DeviceTrustResult:
        """
        Assess device trust from client-provided signals.

        Args:
            signals:    Device signal dict from client SDK.
            user_agent: HTTP User-Agent header string.

        Returns:
            DeviceTrustResult with trust score and boolean flags.
        """
        platform = str(signals.get("platform", "unknown")).lower()
        risk_flags: list[str] = []
        flags: dict[str, bool] = {
            "is_rooted": False,
            "is_jailbroken": False,
            "is_emulator": False,
            "is_usb_debugging": False,
            "is_virtual_camera": False,
            "is_headless_browser": False,
            "is_automation_detected": False,
        }

        if platform == "android":
            self._assess_android(signals, flags, risk_flags)
        elif platform == "ios":
            self._assess_ios(signals, flags, risk_flags)
        elif platform == "web":
            self._assess_web(signals, flags, risk_flags, user_agent)
        else:
            risk_flags.append("unknown_platform")

        if not signals.get("device_id"):
            risk_flags.append("no_device_id")

        # Also check User-Agent for automation regardless of platform
        if platform != "web" and user_agent:
            ua_lower = user_agent.lower()
            for pattern in _AUTOMATION_UA_PATTERNS:
                if re.search(pattern, ua_lower, re.IGNORECASE):
                    flags["is_automation_detected"] = True
                    risk_flags.append(f"automation_ua:{pattern.lower()}")
                    break

        # Compute trust score
        trust_score = 100
        for flag, deduction in _DEDUCTIONS.items():
            if flags.get(flag) or flag in risk_flags:
                trust_score -= deduction
        trust_score = max(0, trust_score)

        logger.debug(
            "device_trust.assess",
            platform=platform,
            trust_score=trust_score,
            flags=flags,
            risk_flags=risk_flags,
        )

        return DeviceTrustResult(
            device_trust_score=trust_score,
            platform=platform,
            is_rooted=flags["is_rooted"],
            is_jailbroken=flags["is_jailbroken"],
            is_emulator=flags["is_emulator"],
            is_usb_debugging=flags["is_usb_debugging"],
            is_virtual_camera=flags["is_virtual_camera"],
            is_headless_browser=flags["is_headless_browser"],
            is_automation_detected=flags["is_automation_detected"],
            risk_flags=risk_flags,
            signals={
                "platform": platform,
                "device_id": signals.get("device_id"),
                "user_agent_truncated": user_agent[:120] if user_agent else None,
            },
        )

    # ── Android ───────────────────────────────────────────────────────────────

    def _assess_android(self, signals: dict, flags: dict, risk_flags: list) -> None:
        """Assess Android-specific risk signals."""
        # Direct client flags
        if signals.get("is_rooted") or signals.get("magisk_detected"):
            flags["is_rooted"] = True
            risk_flags.append("android_root")

        if signals.get("usb_debugging"):
            flags["is_usb_debugging"] = True
            risk_flags.append("android_usb_debugging")

        if signals.get("is_emulator"):
            flags["is_emulator"] = True
            risk_flags.append("android_emulator")

        # Check root file list from client
        found_root = signals.get("root_files_found", [])
        if isinstance(found_root, list) and any(p in _ROOT_FILES for p in found_root):
            flags["is_rooted"] = True
            risk_flags.append("android_root_files")

        # Device model emulator detection
        model = str(signals.get("device_model", "")).lower()
        for pattern in _ANDROID_EMULATOR_PATTERNS:
            if re.search(pattern, model, re.IGNORECASE):
                flags["is_emulator"] = True
                risk_flags.append(f"android_emulator_model:{model[:30]}")
                break

    # ── iOS ───────────────────────────────────────────────────────────────────

    def _assess_ios(self, signals: dict, flags: dict, risk_flags: list) -> None:
        """Assess iOS-specific risk signals."""
        if signals.get("is_jailbroken"):
            flags["is_jailbroken"] = True
            risk_flags.append("ios_jailbreak")

        if signals.get("is_emulator") or signals.get("is_simulator"):
            flags["is_emulator"] = True
            risk_flags.append("ios_simulator")

        # Check jailbreak file list
        found_jb = signals.get("jailbreak_files_found", [])
        if isinstance(found_jb, list) and any(p in _JAILBREAK_FILES for p in found_jb):
            flags["is_jailbroken"] = True
            risk_flags.append("ios_jailbreak_files")

        if signals.get("debug_mode"):
            risk_flags.append("ios_debug_mode")

    # ── Web ───────────────────────────────────────────────────────────────────

    def _assess_web(self, signals: dict, flags: dict, risk_flags: list, user_agent: str) -> None:
        """Assess Web browser-specific risk signals."""
        ua_lower = user_agent.lower()

        # Headless / automation User-Agent
        for pattern in _AUTOMATION_UA_PATTERNS:
            if re.search(pattern, ua_lower, re.IGNORECASE):
                flags["is_headless_browser"] = True
                flags["is_automation_detected"] = True
                risk_flags.append(f"web_automation_ua:{pattern.lower()}")
                break

        # navigator.webdriver flag (set by Selenium/Playwright)
        if signals.get("navigator_webdriver"):
            flags["is_automation_detected"] = True
            flags["is_headless_browser"] = True
            risk_flags.append("web_webdriver_flag")

        # Headless Chrome detection
        if signals.get("chrome_runtime") is False and "chrome" in ua_lower:
            flags["is_headless_browser"] = True
            risk_flags.append("web_headless_chrome")

        # Virtual camera detection from camera device IDs
        camera_ids = signals.get("camera_ids", [])
        camera_labels = [str(c.get("label", "")).lower() for c in camera_ids] if isinstance(camera_ids, list) else []
        all_labels = " ".join(camera_labels)
        for kw in _VIRTUAL_CAMERA_KEYWORDS:
            if kw in all_labels:
                flags["is_virtual_camera"] = True
                risk_flags.append(f"web_virtual_camera:{kw}")
                break

        # WebGL renderer check (headless environments use software renderers)
        renderer = str(signals.get("webgl_renderer", "")).lower()
        if any(kw in renderer for kw in ["swiftshader", "llvmpipe", "software", "mesa"]):
            flags["is_headless_browser"] = True
            risk_flags.append(f"web_software_renderer:{renderer[:40]}")
