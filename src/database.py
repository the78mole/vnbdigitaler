"""Database connection and session management for Neon PostgreSQL.

This module provides async database connections, session management,
and initialization utilities for the VNBdigitaler application.
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


class DatabaseManager:
    """Manages database connections and sessions for Neon PostgreSQL."""

    def __init__(self, database_url: str | None = None):
        """Initialize database manager with connection URL."""
        self.database_url = database_url or self._get_database_url()

        # Create async engine for async operations
        self.async_engine = create_async_engine(
            self.database_url,
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        # Create sync engine for migrations and initial setup
        sync_url = self.database_url.replace("+asyncpg", "").replace(
            "postgresql://", "postgresql+psycopg2://"
        )
        self.sync_engine = create_engine(
            sync_url,
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        # Create session makers
        self.async_session_maker = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        self.sync_session_maker = sessionmaker(
            bind=self.sync_engine,
            expire_on_commit=False,
        )

    def _get_database_url(self) -> str:
        """Get database URL from environment variables."""
        # Try the main database URL first
        database_url = os.getenv("NEON_DATABASE_URL")
        if database_url:
            # Ensure we use asyncpg for async operations
            if not database_url.startswith("postgresql+asyncpg://"):
                database_url = database_url.replace(
                    "postgresql://", "postgresql+asyncpg://"
                )
            return database_url

        # Build URL from individual components
        user = os.getenv("NEON_USER")
        password = os.getenv("NEON_PASSWORD")
        host = os.getenv("NEON_HOST")
        port = os.getenv("NEON_PORT", "5432")
        database = os.getenv("NEON_DATABASE")

        if not all([user, password, host, database]):
            raise ValueError(
                "Database connection not configured. Set NEON_DATABASE_URL or "
                "individual environment variables (NEON_USER, NEON_PASSWORD, NEON_HOST, NEON_DATABASE)"
            )

        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session."""
        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    def get_sync_session(self) -> Session:
        """Get sync database session (for migrations and setup)."""
        return self.sync_session_maker()

    async def create_tables(self) -> None:
        """Create all database tables."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all database tables (use with caution!)."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def test_connection(self) -> bool:
        """Test database connection."""
        try:
            async with self.async_engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            print(f"Database connection test failed: {e}")
            return False

    async def close(self) -> None:
        """Close all database connections."""
        await self.async_engine.dispose()
        self.sync_engine.dispose()


# Global database manager instance
db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance."""
    global db_manager  # noqa: PLW0603
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session in FastAPI/async contexts."""
    db = get_db_manager()
    async for session in db.get_async_session():
        yield session
