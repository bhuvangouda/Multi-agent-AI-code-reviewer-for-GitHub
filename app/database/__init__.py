from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Async engine using the DSN from settings (default to async SQLite for local dev)
engine: AsyncEngine = create_async_engine(
    settings.POSTGRES_DSN,
    echo=settings.DEBUG,
    future=True,
)

# Session factory for async sessions
AsyncSessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_db() -> AsyncSession:
    """FastAPI dependency that provides an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session

# Base class for models
Base = declarative_base()
