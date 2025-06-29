from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session, Mapped, mapped_column
from sqlalchemy.pool import StaticPool
import os
from typing import Generator, AsyncGenerator
import logging
from datetime import datetime # Added for Mapped types

from app.core.config import settings

logger = logging.getLogger(__name__)

# Database URL from settings
SYNC_DATABASE_URL = settings.DATABASE_URL
ASYNC_DATABASE_URL = SYNC_DATABASE_URL

if SYNC_DATABASE_URL.startswith("postgresql"):
    ASYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif SYNC_DATABASE_URL.startswith("sqlite"):
    ASYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")


# Synchronous engine (kept for potential existing sync operations or tools)
if SYNC_DATABASE_URL.startswith("sqlite"):
    sync_engine = create_engine(
        SYNC_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG
    )
else:
    sync_engine = create_engine(
        SYNC_DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE, # Assuming DB_POOL_SIZE and DB_MAX_OVERFLOW are in settings
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
        echo=settings.DEBUG
    )

# Asynchronous engine
if ASYNC_DATABASE_URL.startswith("sqlite+aiosqlite"):
    async_engine = create_async_engine(
        ASYNC_DATABASE_URL,
        connect_args={"check_same_thread": False}, # For aiosqlite, check_same_thread is managed differently or not needed.
                                                 # It's generally for the standard library's sqlite3 module.
                                                 # We'll keep it for consistency if settings.DEBUG is on.
        echo=settings.DEBUG
    )
else:
    async_engine = create_async_engine(
        ASYNC_DATABASE_URL,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=True,
        echo=settings.DEBUG
    )


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

from sqlalchemy import func as sqlalchemy_func # For server_default
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # For PostgreSQL UUID type
import uuid # For default factory

class Base(DeclarativeBase):
    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, server_default=sqlalchemy_func.now())
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow, server_default=sqlalchemy_func.now())


def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI endpoints (Synchronous)
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database dependency for FastAPI endpoints (Asynchronous)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"Async database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

def create_tables():
    """
    Create all database tables
    """
    try:
        # Import all models to ensure they are registered
        from app.models import user, audio_file, agent_session, api_key
        
        Base.metadata.create_all(bind=sync_engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def drop_tables():
    """
    Drop all database tables (use with caution)
    """
    try:
        Base.metadata.drop_all(bind=sync_engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise

def init_db():
    """
    Initialize database with tables
    """
    create_tables()

def reset_db():
    """
    Reset database by dropping and creating tables
    """
    logger.warning("Resetting database - all data will be lost!")
    drop_tables()
    create_tables()