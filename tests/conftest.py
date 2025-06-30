import sys # Added import
import os # Added import
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import event
from sqlalchemy.orm import sessionmaker # Kept for possible sync test parts if any
from httpx import ASGITransport, AsyncClient # Changed import
import os

from app.main import app
from app.db.database import Base, get_async_db # Changed get_db to get_async_db
from app.core.config import settings

# Async Test Database
ASYNC_SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test_async.db"

async_engine = create_async_engine(
    ASYNC_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} # Specific to SQLite
)

AsyncTestingSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=async_engine, class_=AsyncSession
)

# Sync Test Database (if needed for some old tests or parts not yet migrated)
SYNC_SQLALCHEMY_DATABASE_URL = "sqlite:///./test_sync.db"
sync_engine = create_engine(
    SYNC_SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SyncTestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


async def override_get_async_db() -> AsyncSession:
    async with AsyncTestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_async_db] = override_get_async_db

# This event_loop fixture is often provided by pytest-asyncio.
# If pytest-asyncio is used, this might not be necessary or could conflict.
# For now, keeping it as it was, but it's a point of attention.
@pytest.fixture(scope="session")
def event_loop(request): # Changed to accept request for better compatibility
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def client() -> AsyncClient: # Changed to async and type hint
    """Create async test client"""
    # Ensure tables are created before running tests
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # Drop first for clean state
        await conn.run_sync(Base.metadata.create_all)

    # Use ASGITransport for FastAPI app
    transport = ASGITransport(app=app) # type: ignore
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Optional: Clean up DB file after tests if it's file-based like SQLite
    if os.path.exists("./test_async.db"):
        os.remove("./test_async.db")
    if os.path.exists("./test_sync.db"):
        os.remove("./test_sync.db")


@pytest.fixture()
async def async_db_session() -> AsyncSession: # Changed to async
    """Create async database session for testing"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session = AsyncTestingSessionLocal()
    try:
        yield session
    finally:
        await session.close()
        # Tables are dropped per client session or test run for cleaner state

# Fixture for synchronous sessions (if some tests still need it)
@pytest.fixture()
def sync_db_session():
    Base.metadata.create_all(bind=sync_engine)
    db = SyncTestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=sync_engine)


@pytest.fixture
def test_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123",
        "full_name": "Test User"
    }

@pytest.fixture
def test_audio_file():
    """Sample audio file data for testing"""
    return {
        "filename": "test_audio.wav",
        "file_size": 1024000,
        "mime_type": "audio/wav",
        "duration": 30.0,
        "sample_rate": 44100,
        "channels": 2
    }