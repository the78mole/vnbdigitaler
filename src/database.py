"""PostgreSQL-Datenbankverbindung und Session-Management.

Zentrale Datenbank-Infrastruktur für die BDEW-Anwendung mit
PostgreSQL-spezifischen Features wie JSONB, Full-Text-Search und
Performance-Optimierungen.
"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

# Importiere alle Modelle für Tabellenerstellung
import models.bdew

Base = models.bdew.Base

# Standardkonfiguration für lokale Entwicklung
DEFAULT_DATABASE_URL = "postgresql://postgres@localhost:5432/vnbdigitaler"


def get_database_url() -> str:
    """
    Datenbankverbindung für lokale Entwicklung und Produktion.

    Priorität:
    1. DATABASE_URL Environment Variable
    2. Lokale PostgreSQL (Standard für DevContainer)

    Returns:
        str: PostgreSQL Verbindungs-URL
    """
    # Prüfe Environment Variable
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    # Für lokale Entwicklung: Verwende Container-PostgreSQL
    return DEFAULT_DATABASE_URL


def get_async_database_url() -> str:
    """
    Async-kompatible Datenbankverbindung.

    Returns:
        str: Async PostgreSQL Verbindungs-URL mit asyncpg
    """
    url = get_database_url()

    # Konvertiere zu asyncpg für async Operationen
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return url


class DatabaseManager:
    """
    Verwaltet Datenbankverbindungen für synchrone und asynchrone Operationen.

    Unterstützt:
    - Lokale PostgreSQL-Entwicklung im DevContainer
    - Produktionsumgebungen mit Environment-Konfiguration
    - Automatische Session-Verwaltung
    - Tabellenerstellung und Migrationen
    """

    def __init__(self, database_url: str | None = None):
        """
        Initialisiert DatabaseManager.

        Args:
            database_url: Optional - Überschreibt automatische URL-Erkennung
        """
        self.database_url = database_url or get_database_url()
        self.async_database_url = database_url or get_async_database_url()

        # Async Engine für normale Operationen
        self.async_engine = create_async_engine(
            self.async_database_url,
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        # Sync Engine für Migrationen und Setup
        self.sync_engine = create_engine(
            self.database_url,
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        # Session Factories
        self.async_session_factory = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        self.sync_session_factory = sessionmaker(
            bind=self.sync_engine,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Async Context Manager für Datenbank-Sessions.

        Yields:
            AsyncSession: Datenbank-Session
        """
        async with self.async_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    def get_sync_session(self) -> Session:
        """
        Sync Datenbank-Session für Migrationen und Setup.

        Returns:
            Session: SQLAlchemy sync session
        """
        return self.sync_session_factory()

    async def create_database_if_not_exists(
        self, database_name: str = "vnbdigitaler"
    ) -> None:
        """
        Erstellt Datenbank falls sie nicht existiert.

        Args:
            database_name: Name der zu erstellenden Datenbank
        """
        # Verbinde zu postgres Database für Datenbankerstellung
        postgres_url = self.database_url.replace(f"/{database_name}", "/postgres")

        temp_engine = create_engine(postgres_url)

        with temp_engine.connect() as conn:
            # Prüfe ob Datenbank existiert
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                {"db_name": database_name},
            )

            if not result.fetchone():
                # Datenbank erstellen
                conn.execute(text("COMMIT"))  # Ende aktuelle Transaction
                conn.execute(text(f"CREATE DATABASE {database_name}"))
                print(f"✅ Datenbank '{database_name}' erstellt")
            else:
                print(f"Info: Datenbank '{database_name}' existiert bereits")

        temp_engine.dispose()

    async def create_tables(self) -> None:
        """Erstellt alle Datenbanktabellen."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Datenbanktabellen erstellt")

    def create_tables_sync(self) -> None:
        """Erstellt alle Datenbanktabellen (synchron)."""
        Base.metadata.create_all(self.sync_engine)
        print("✅ Datenbanktabellen erstellt")

    async def drop_tables(self) -> None:
        """Löscht alle Datenbanktabellen (Vorsicht!)."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("⚠️  Alle Datenbanktabellen gelöscht")

    async def test_connection(self) -> bool:
        """
        Testet Datenbankverbindung.

        Returns:
            bool: True wenn Verbindung erfolgreich
        """
        try:
            async with self.async_engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            print(f"❌ Datenbankverbindung fehlgeschlagen: {e}")
            return False

    def test_connection_sync(self) -> bool:
        """
        Testet Datenbankverbindung (synchron).

        Returns:
            bool: True wenn Verbindung erfolgreich
        """
        try:
            with self.sync_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            print(f"❌ Datenbankverbindung fehlgeschlagen: {e}")
            return False

    async def close(self) -> None:
        """Schließt alle Datenbankverbindungen."""
        await self.async_engine.dispose()
        self.sync_engine.dispose()


# Globale Database Manager Instanz
_db_manager: DatabaseManager | None = None


def get_database_manager() -> DatabaseManager:
    """
    Hole globale DatabaseManager Instanz (Singleton Pattern).

    Returns:
        DatabaseManager: Globale DatabaseManager Instanz
    """
    # Verwende lokale Variable statt global
    if not hasattr(get_database_manager, "_db_manager"):
        get_database_manager._db_manager = DatabaseManager()
    return get_database_manager._db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency für async Database Session.

    Verwendung in FastAPI oder anderen async Kontexten:

    ```python
    async def my_function(db: AsyncSession = Depends(get_db_session)):
        # Datenbankoperationen hier
        pass
    ```

    Yields:
        AsyncSession: SQLAlchemy async session
    """
    db_manager = get_database_manager()
    async with db_manager.get_session() as session:
        yield session


async def init_database() -> None:
    """
    Initialisiert Datenbank für Entwicklung.

    - Erstellt Datenbank falls notwendig
    - Erstellt alle Tabellen
    - Testet Verbindung
    """
    print("🔧 Initialisiere lokale PostgreSQL-Datenbank...")

    db_manager = get_database_manager()

    # Datenbank erstellen falls notwendig
    await db_manager.create_database_if_not_exists()

    # Verbindung testen
    if not await db_manager.test_connection():
        raise RuntimeError("❌ Datenbankverbindung fehlgeschlagen")

    print("✅ Datenbankverbindung erfolgreich")

    # Tabellen erstellen
    await db_manager.create_tables()

    print("🎉 Datenbank erfolgreich initialisiert!")


if __name__ == "__main__":
    import asyncio

    print(f"📊 Database URL: {get_database_url()}")
    print(f"🔄 Async URL: {get_async_database_url()}")

    # Test der Verbindung
    async def test():
        """Test der Datenbankverbindung und -initialisierung."""
        await init_database()

        db_manager = get_database_manager()
        if await db_manager.test_connection():
            print("✅ Datenbanktest erfolgreich")
        else:
            print("❌ Datenbanktest fehlgeschlagen")

    asyncio.run(test())
