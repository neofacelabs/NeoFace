"""
NeoFace Trust Engine — Device Trust API (Module 9)

POST /api/v1/device/assess — Assess device integrity and return trust score
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TokenData, get_current_user
from app.core.logging import logger
from app.models.trust_engine import DeviceTrustLog
from app.services.device_trust_service import DeviceTrustService

router = APIRouter(prefix="/device", tags=["Device Trust"])

_device_svc = DeviceTrustService()


# ── Request/Response schemas ──────────────────────────────────────────────────

class DeviceSignalsRequest(BaseModel):
    """Device integrity signals from the client SDK."""

    platform: str = Field(..., description="android | ios | web")
    device_id: str | None = Field(default=None, description="Unique device identifier")
    device_model: str | None = Field(default=None, description="Android device model string")

    # Android
    is_rooted: bool = False
    magisk_detected: bool = False
    usb_debugging: bool = False
    is_emulator: bool = False
    root_files_found: list[str] = Field(default_factory=list)

    # iOS
    is_jailbroken: bool = False
    is_simulator: bool = False
    jailbreak_files_found: list[str] = Field(default_factory=list)
    debug_mode: bool = False

    # Web
    navigator_webdriver: bool | None = None
    chrome_runtime: bool | None = None
    webgl_vendor: str | None = None
    webgl_renderer: str | None = None
    camera_ids: list[dict] = Field(default_factory=list)

    # Session context
    session_id: str | None = None


class DeviceTrustResponse(BaseModel):
    device_trust: int          # 0–100
    platform: str
    rooted: bool
    jailbroken: bool
    emulator: bool
    usb_debugging: bool
    virtual_camera: bool
    headless_browser: bool
    automation_detected: bool
    risk_flags: list[str]


# ─────────────────────────────────────────────────────────────────────────────
# DEVICE TRUST ASSESSMENT
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/assess",
    response_model=DeviceTrustResponse,
    summary="Assess device integrity and generate trust score",
    status_code=status.HTTP_200_OK,
)
async def assess_device_trust(
    body: DeviceSignalsRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeviceTrustResponse:
    """
    Assess device integrity from client-collected signals.

    The client SDK (mobile app / browser extension) collects device signals
    locally and submits them here. The server scores them against known
    attack indicators.

    **Android detects:** root, Magisk, USB debugging, emulators
    **iOS detects:** jailbreak, Cydia, debug mode, simulator
    **Web detects:** virtual camera, Selenium/WebDriver, headless Chrome,
    Puppeteer, Playwright, software WebGL renderers

    Returns a trust score 0–100 where 100 is fully trusted.
    """
    user_agent = request.headers.get("user-agent", "")
    signals_dict = body.model_dump()

    result = _device_svc.assess(signals_dict, user_agent=user_agent)

    # Persist to device_trust_logs
    try:
        log = DeviceTrustLog(
            user_id=current_user.user_uuid,
            device_id=body.device_id,
            device_platform=result.platform,
            device_trust_score=result.device_trust_score,
            is_rooted=result.is_rooted,
            is_emulator=result.is_emulator,
            is_jailbroken=result.is_jailbroken,
            is_virtual_camera=result.is_virtual_camera,
            is_headless_browser=result.is_headless_browser,
            is_automation_detected=result.is_automation_detected,
            is_usb_debugging=result.is_usb_debugging,
            signals=result.signals,
            user_agent=user_agent[:500] if user_agent else None,
            ip_address=request.client.host if request.client else None,
        )
        db.add(log)
        await db.commit()
    except Exception as exc:
        logger.warning("device_trust.assess: log write failed", error=str(exc))

    return DeviceTrustResponse(
        device_trust=result.device_trust_score,
        platform=result.platform,
        rooted=result.is_rooted,
        jailbroken=result.is_jailbroken,
        emulator=result.is_emulator,
        usb_debugging=result.is_usb_debugging,
        virtual_camera=result.is_virtual_camera,
        headless_browser=result.is_headless_browser,
        automation_detected=result.is_automation_detected,
        risk_flags=result.risk_flags,
    )
