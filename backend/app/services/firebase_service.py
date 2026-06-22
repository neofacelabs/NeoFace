"""
NeoFace Firebase Service
Verifies Firebase ID tokens issued by the Google Auth frontend flow.

Uses firebase-admin to validate the token signature and extract the user's
email/uid without making round-trips to Google on every request.

Design:
- Initializes the firebase-admin app lazily (on first call).
- Falls back gracefully when FIREBASE_CREDENTIALS_JSON is not set (local dev).
- Thread/coroutine-safe: firebase_admin.initialize_app is idempotent.
"""

import json
import threading
from dataclasses import dataclass

import firebase_admin
from firebase_admin import auth as fb_auth
from firebase_admin import credentials

from app.core.config import settings
from app.core.logging import logger

_init_lock = threading.Lock()
_initialized = False


def _ensure_initialized() -> bool:
    """Initialize firebase-admin once. Returns True if available."""
    global _initialized

    if _initialized:
        return True

    with _init_lock:
        if _initialized:
            return True

        if not settings.FIREBASE_CREDENTIALS_JSON:
            logger.warning(
                "FIREBASE_CREDENTIALS_JSON is not set. "
                "Google Auth endpoint will be disabled."
            )
            return False

        try:
            cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
            cred = credentials.Certificate(cred_dict)
            # Guard against double-init in hot-reload scenarios
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            _initialized = True
            logger.info("Firebase Admin SDK initialized successfully")
            return True
        except Exception as exc:
            logger.error("Failed to initialize Firebase Admin SDK", error=str(exc))
            return False


@dataclass
class FirebaseTokenPayload:
    """Decoded, verified Firebase ID token data."""
    uid: str
    email: str
    name: str | None
    picture: str | None
    email_verified: bool


def verify_firebase_id_token(id_token: str) -> FirebaseTokenPayload | None:
    """
    Verify a Firebase ID token and return the decoded payload.

    Returns None if:
    - Firebase Admin SDK is not initialized (env var missing).
    - The token is invalid, expired, or revoked.

    Never raises — always returns None on failure (caller raises HTTPException).
    """
    if not _ensure_initialized():
        return None

    try:
        decoded = fb_auth.verify_id_token(id_token, check_revoked=True)
        return FirebaseTokenPayload(
            uid=decoded["uid"],
            email=decoded.get("email", ""),
            name=decoded.get("name"),
            picture=decoded.get("picture"),
            email_verified=decoded.get("email_verified", False),
        )
    except fb_auth.RevokedIdTokenError:
        logger.warning("Firebase token has been revoked")
        return None
    except fb_auth.ExpiredIdTokenError:
        logger.warning("Firebase token has expired")
        return None
    except fb_auth.InvalidIdTokenError as exc:
        logger.warning("Firebase token is invalid", error=str(exc))
        return None
    except Exception as exc:
        logger.error("Unexpected error verifying Firebase token", error=str(exc))
        return None
