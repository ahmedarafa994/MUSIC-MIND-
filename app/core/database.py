from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
import logging
from app.core.config import settings
import structlog

try:
    logger = structlog.get_logger(__name__)
except Exception:
    logger = logging.getLogger(__name__)
    if not logger.hasHandlers():
        logging.basicConfig(level=settings.LOG_LEVEL.upper() if hasattr(settings, 'LOG_LEVEL') else logging.INFO)

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {}
    if "sqlite+aiosqlite" not in str(settings.DATABASE_URL):
        logger.warning("SQLite DATABASE_URL does not specify aiosqlite, async operations might not work as expected. Consider 'sqlite+aiosqlite:///./your_db.db'")

    async_engine = create_async_engine(
        str(settings.DATABASE_URL),
        echo=settings.DB_ECHO_LOG if hasattr(settings, 'DB_ECHO_LOG') else settings.DEBUG, # Use DB_ECHO_LOG or fallback to DEBUG
        future=True
    )
else:
    async_engine = create_async_engine(
        str(settings.DATABASE_URL),
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        echo=settings.DB_ECHO_LOG if hasattr(settings, 'DB_ECHO_LOG') else settings.DEBUG,
        future=True
    )

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database dependency for FastAPI endpoints.
    """
    async with AsyncSessionLocal() as session:
        try:
            # await session.begin() # Removed begin here, individual CRUD methods can manage transactions
            yield session
            # await session.commit() # Removed commit here
        except Exception as e:
            logger.error(f"Database session error: {e}", exc_info=True)
            await session.rollback()
            raise
        finally:
            pass # Session closed by 'async with'

async def init_db():
    """
    Initialize database and create tables.
    """
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified successfully using async engine.")
    except Exception as e:
        logger.error(f"Error creating database tables with async engine: {e}", exc_info=True)
        raise

async def drop_tables_async():
    """
    Drop all database tables (use with caution) using async engine.
    """
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully using async engine.")
    except Exception as e:
        logger.error(f"Error dropping database tables with async engine: {e}", exc_info=True)
        raise

engine = async_engine # Export async_engine as engine for main.py

def get_db_info():
    """
    Get database connection information
    """
    return {
        "url": settings.DATABASE_URL,
        "engine": str(engine),
        "pool_size": engine.pool.size() if hasattr(engine.pool, 'size') else None,
        "checked_out": engine.pool.checkedout() if hasattr(engine.pool, 'checkedout') else None,
    }