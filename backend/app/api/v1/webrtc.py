"""
NeoFace WebRTC Streaming API
Allows real-time video frame ingestion for continuous authentication and liveness check.
"""

import asyncio
import io
import time
from typing import Set
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.core.logging import logger

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
    from aiortc.contrib.media import MediaRelay
    import av
    AIORTC_AVAILABLE = True
except ImportError:
    AIORTC_AVAILABLE = False
    # Stub classes so code loads without error
    class RTCPeerConnection: pass
    class RTCSessionDescription: pass
    class MediaStreamTrack: pass

router = APIRouter(prefix="/webrtc", tags=["WebRTC"])

# Active connections track
_pcs: Set[RTCPeerConnection] = set()

class WebRTCOffer(BaseModel):
    sdp: str
    type: str

class WebRTCAnswer(BaseModel):
    sdp: str
    type: str

if AIORTC_AVAILABLE:
    class VideoReceiverTrack(MediaStreamTrack):
        kind = "video"

        def __init__(self, track):
            super().__init__()
            self.track = track
            self.last_process_time = 0.0

        async def recv(self):
            frame = await self.track.recv()
            
            # Process frames at 1 frame per second to not overload CPU
            now = time.time()
            if now - self.last_process_time >= 1.0:
                self.last_process_time = now
                asyncio.create_task(self._process_frame(frame))
                
            return frame

        async def _process_frame(self, frame):
            try:
                # Convert av.VideoFrame to JPEG bytes
                img = frame.to_image()
                buf = io.BytesIO()
                img.save(buf, format="JPEG")
                jpeg_bytes = buf.getvalue()

                # Run passive liveness detection
                from app.services.passive_liveness_service import PassiveLivenessService
                liveness_service = PassiveLivenessService.get_instance()
                result = liveness_service.predict_from_bytes(jpeg_bytes)
                
                logger.info(
                    "WebRTC frame processed",
                    is_live=result.is_live,
                    confidence=result.confidence,
                    attack_type=result.attack_type,
                )
            except Exception as e:
                logger.error("WebRTC frame processing failed", error=str(e))


@router.post(
    "/offer",
    response_model=WebRTCAnswer,
    summary="Establish a WebRTC connection via SDP offer",
)
async def webrtc_offer(offer: WebRTCOffer) -> WebRTCAnswer:
    """
    Establish WebRTC session.
    Receives SDP offer, configures local peer connection, and returns SDP answer.
    """
    if not AIORTC_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="WebRTC components (aiortc, av) are not installed or compiled on this platform."
        )

    pc = RTCPeerConnection()
    _pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        if pc.connectionState in ("failed", "closed"):
            await pc.close()
            _pcs.discard(pc)
            logger.info("WebRTC connection closed", state=pc.connectionState)

    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            pc.addTrack(VideoReceiverTrack(track))
            logger.info("WebRTC video track added")

    # Set remote description
    rd = RTCSessionDescription(sdp=offer.sdp, type=offer.type)
    await pc.setRemoteDescription(rd)

    # Generate SDP answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return WebRTCAnswer(sdp=pc.localDescription.sdp, type=pc.localDescription.type)
