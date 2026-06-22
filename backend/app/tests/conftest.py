"""
NeoFace Test Configuration
Pytest fixtures for async tests, test database, mock services, and test clients.
"""

import os
# Force single-threaded execution for numerical libraries to prevent segfaults on macOS/ARM
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import asyncio
import io
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock mediapipe submodules to prevent Python 3.14 import failures
mock_mp = MagicMock()
sys.modules["mediapipe"] = mock_mp
sys.modules["mediapipe.solutions"] = mock_mp
sys.modules["mediapipe.solutions.face_mesh"] = mock_mp
sys.modules["mediapipe.solutions.drawing_utils"] = mock_mp
sys.modules["mediapipe.solutions.drawing_styles"] = mock_mp

import numpy as np
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import TypeDecorator, Text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, JSONB as PG_JSONB, UUID as PG_UUID
import json

class SQLiteCompatibleARRAY(TypeDecorator):
    impl = Text
    cache_ok = True

    def __init__(self, *args, **kwargs):
        self.pg_array = PG_ARRAY(*args, **kwargs)
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(self.pg_array)
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        if value is not None:
            try:
                return json.loads(value)
            except Exception:
                return value
        return value

class SQLiteCompatibleJSONB(TypeDecorator):
    impl = Text
    cache_ok = True

    def __init__(self, *args, **kwargs):
        self.pg_jsonb = PG_JSONB(*args, **kwargs)
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(self.pg_jsonb)
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        if value is not None:
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if dialect.name == "postgresql":
            return value
        if value is not None:
            try:
                return json.loads(value)
            except Exception:
                return value
        return value

# Monkeypatch dialects.postgresql before models are loaded
import sqlalchemy.dialects.postgresql
sqlalchemy.dialects.postgresql.ARRAY = SQLiteCompatibleARRAY
sqlalchemy.dialects.postgresql.JSONB = SQLiteCompatibleJSONB

@compiles(PG_UUID, "sqlite")
def compile_uuid_sqlite(element, compiler, **kw):
    return "TEXT"

from app.core.database import Base, get_db
from app.core.security import JWTHandler, PasswordHasher
from app.main import app
from app.models.user import User
from app.models.face_embedding import FaceEmbedding
from app.models.auth_log import AuthLog
from app.services.face_detector import DetectedFace, DetectionResult, FaceDetectorService
from app.services.liveness_service import LivenessCheckResult, LivenessService

# ── Test database ─────────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create in-memory SQLite engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    """Provide a transactional test session that rolls back after each test."""
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        async def mock_commit():
            await session.flush()
        session.commit = mock_commit
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession, mock_face_detector) -> AsyncClient:
    """
    Async HTTP client with overridden database dependency and mocked face detector.
    Use this for API integration tests.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    from app.utils.dependencies import get_face_detector, get_storage
    app.dependency_overrides[get_face_detector] = lambda: mock_face_detector

    mock_storage = AsyncMock()
    mock_storage.save_face_image.return_value = "faces/test/image.jpg"
    mock_storage.delete_face_image.return_value = True
    app.dependency_overrides[get_storage] = lambda: mock_storage

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ── Mock AI services ──────────────────────────────────────────────────────────

def make_fake_embedding(seed: int = 42) -> np.ndarray:
    """Generate a deterministic fake 512-d embedding."""
    rng = np.random.RandomState(seed)
    emb = rng.randn(512).astype(np.float32)
    return emb / np.linalg.norm(emb)


def make_fake_detected_face(seed: int = 42) -> DetectedFace:
    """Create a fake DetectedFace with a real embedding."""
    return DetectedFace(
        bbox=(50, 50, 200, 200),
        landmarks=np.zeros((5, 2)),
        embedding=make_fake_embedding(seed),
        detection_score=0.98,
        quality_score=85.0,
        face_crop=np.zeros((112, 112, 3), dtype=np.uint8),
    )


def make_fake_detection_result(
    success: bool = True,
    face_count: int = 1,
    seed: int = 42,
) -> DetectionResult:
    """Create a fake DetectionResult."""
    faces = [make_fake_detected_face(seed)] if success and face_count == 1 else []
    return DetectionResult(
        success=success,
        face_count=face_count,
        faces=faces,
        image_width=640,
        image_height=480,
        blur_score=250.0,
    )


@pytest.fixture
def mock_face_detector():
    """Mock FaceDetectorService that returns successful detections."""
    mock = MagicMock(spec=FaceDetectorService)
    mock.detect_single.return_value = (
        make_fake_detection_result(success=True),
        make_fake_detected_face(),
    )
    mock.detect.return_value = make_fake_detection_result(success=True)
    mock._initialized = True
    return mock


@pytest.fixture
def mock_liveness_pass():
    """Mock LivenessService that always passes."""
    result = LivenessCheckResult(
        is_live=True,
        score=85.0,
        blink_detected=True,
        head_turn_detected=True,
        smile_detected=True,
        ear_value=0.25,
        mouth_ratio=0.15,
        yaw_angle=20.0,
        checks_passed=3,
    )
    mock = MagicMock(spec=LivenessService)
    mock.analyze.return_value = result
    return mock


@pytest.fixture
def mock_liveness_fail():
    """Mock LivenessService that always fails."""
    result = LivenessCheckResult(
        is_live=False,
        score=25.0,
        blink_detected=False,
        head_turn_detected=False,
        smile_detected=False,
        ear_value=0.30,
        mouth_ratio=0.05,
        yaw_angle=2.0,
        checks_passed=0,
        failure_reason="Blink not detected",
    )
    mock = MagicMock(spec=LivenessService)
    mock.analyze.return_value = result
    return mock


# ── Test data factories ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a standard test user in the database."""
    user = User(
        name="Test User",
        email="testuser@example.com",
        hashed_password=PasswordHasher.hash("TestPass123!"),
        role="user",
        is_active=True,
        is_enrolled=False,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test admin user in the database."""
    admin = User(
        name="Test Admin",
        email="testadmin@example.com",
        hashed_password=PasswordHasher.hash("AdminPass123!"),
        role="admin",
        is_active=True,
        is_enrolled=False,
    )
    db_session.add(admin)
    await db_session.flush()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def enrolled_user(db_session: AsyncSession) -> tuple[User, FaceEmbedding]:
    """Create a test user with a face embedding."""
    user = User(
        name="Enrolled User",
        email="enrolled@example.com",
        hashed_password=PasswordHasher.hash("TestPass123!"),
        role="user",
        is_active=True,
        is_enrolled=True,
    )
    db_session.add(user)
    await db_session.flush()

    embedding = FaceEmbedding(
        user_id=user.id,
        embedding_vector=make_fake_embedding(seed=99).tolist(),
        embedding_version="arcface_r100_v1",
        embedding_dimension=512,
        quality_score=85.0,
    )
    db_session.add(embedding)
    await db_session.flush()
    await db_session.refresh(user)
    await db_session.refresh(embedding)
    return user, embedding


def make_admin_token(user_id: str, email: str = "admin@test.com") -> str:
    """Generate a valid admin JWT for tests."""
    return JWTHandler.create_access_token(
        user_id=user_id, email=email, role="admin"
    )


def make_user_token(user_id: str, email: str = "user@test.com") -> str:
    """Generate a valid user JWT for tests."""
    return JWTHandler.create_access_token(
        user_id=user_id, email=email, role="user"
    )


def make_test_image_bytes() -> bytes:
    """Generate a minimal valid JPEG image for tests."""
    try:
        import cv2
        img = np.ones((224, 224, 3), dtype=np.uint8) * 128
        _, buffer = cv2.imencode(".jpg", img)
        return buffer.tobytes()
    except ImportError:
        # Fallback: tiny valid JPEG bytes
        return (
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
            b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
            b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
            b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f"
            b"\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00"
            b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01"
            b"\x00\x00?\x00\xf5\x0a\xff\xd9"
        )
