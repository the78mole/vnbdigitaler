#!/usr/bin/env python3
"""
Minimal-Test für PostgreSQL-BDEW-Integration.

Testet nur die Kern-Funktionalität mit korrekten Feldnamen.
"""

import asyncio
import logging
import os
import sys
import traceback
from pathlib import Path

# Füge das src-Verzeichnis zum Python-Pfad hinzu
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Setze Umgebungsvariablen vor dem Import
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres@localhost:5432/vnbdigitaler"
)

from database import DatabaseManager  # noqa: E402
from repositories.bdew import BDEWRepository  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def minimal_test():
    """Minimal-Test der PostgreSQL-Integration."""

    logger.info("🧪 Starte Minimal-Test...")

    try:
        db_manager = DatabaseManager()

        # Teste Verbindung
        if not await db_manager.test_connection():
            logger.error("❌ Datenbankverbindung fehlgeschlagen!")
            return False

        logger.info("✅ Datenbankverbindung erfolgreich")

        async with db_manager.get_session() as session:
            repo = BDEWRepository(session)

            # Erstelle minimal-Unternehmen mit nur den nötigen Feldern
            company_data = {
                "company_name": "Test Stadtwerke GmbH",
                "company_name_normalized": "test stadtwerke",
                "postal_code": "80331",
                "city": "München",
                "is_active": True,
            }

            # Erstelle Unternehmen
            company = await repo.create_company(company_data)
            logger.info(
                f"✅ Unternehmen erstellt: {company.company_name} (ID: {company.id})"
            )

            # Teste einfache Suche
            companies = await repo.get_all_companies()
            logger.info(f"📊 Gefunden: {len(companies)} Unternehmen gesamt")

            # Teste Namenssuche
            search_results = await repo.search_companies_by_name("Test")
            logger.info(f"🔍 Namenssuche 'Test': {len(search_results)} Ergebnisse")

        logger.info("🎉 Minimal-Test erfolgreich abgeschlossen!")
        return True

    except Exception as e:
        logger.error(f"❌ Fehler beim Minimal-Test: {e}")
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = asyncio.run(minimal_test())
    sys.exit(0 if success else 1)
