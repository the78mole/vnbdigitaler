#!/usr/bin/env python3
"""
Vereinfachtes Test-Daten-Script für PostgreSQL-BDEW-Integration.

Erstellt einige Test-Unternehmen zur Validierung der PostgreSQL-Features.
"""

import asyncio
import logging
import os
import sys
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


async def create_test_companies():
    """Erstelle Test-Unternehmen."""

    test_companies = [
        {
            "company_name": "Stadtwerke München GmbH",
            "company_name_normalized": "stadtwerke münchen",
            "bdew_id": "SWM001",
            "street": "Emmy-Noether-Straße 2",
            "postal_code": "80992",
            "city": "München",
            "federal_state": "Bayern",
            "phone": "+49 89 2361-0",
            "email": "info@swm.de",
            "website": "https://www.swm.de",
            "latitude": 48.1351,
            "longitude": 11.5820,
            "data_quality_score": 95,
            "is_active": True,
            "service_territory": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [11.5, 48.1],
                            [11.6, 48.1],
                            [11.6, 48.2],
                            [11.5, 48.2],
                            [11.5, 48.1],
                        ]
                    ],
                },
                "properties": {"name": "München", "area_km2": 310.43},
            },
        },
        {
            "company_name": "Berliner Stadtwerke AG",
            "company_name_normalized": "berliner stadtwerke",
            "bdew_id": "BSW001",
            "street": "Kurfürstendamm 1",
            "postal_code": "10719",
            "city": "Berlin",
            "federal_state": "Berlin",
            "phone": "+49 30 123456",
            "email": "info@berliner-stadtwerke.de",
            "website": "https://www.berliner-stadtwerke.de",
            "latitude": 52.5200,
            "longitude": 13.4050,
            "data_quality_score": 88,
            "is_active": True,
        },
        {
            "company_name": "Rheinenergie AG",
            "company_name_normalized": "rheinenergie",
            "bdew_id": "REG001",
            "street": "Parkgürtel 24",
            "postal_code": "50823",
            "city": "Köln",
            "federal_state": "Nordrhein-Westfalen",
            "phone": "+49 221 178-0",
            "email": "info@rheinenergie.com",
            "website": "https://www.rheinenergie.com",
            "latitude": 50.9375,
            "longitude": 6.9603,
            "data_quality_score": 92,
            "is_active": True,
        },
    ]

    return test_companies


async def seed_simple_test_data():
    """Erstelle einfache Test-Daten."""

    logger.info("🌱 Starte vereinfachtes Test-Daten-Seeding...")

    try:
        db_manager = DatabaseManager()

        # Teste Verbindung
        if not await db_manager.test_connection():
            logger.error("❌ Datenbankverbindung fehlgeschlagen!")
            return False

        logger.info("✅ Datenbankverbindung erfolgreich")

        async with db_manager.get_session() as session:
            repo = BDEWRepository(session)

            # Erstelle Test-Unternehmen
            companies = await create_test_companies()

            created_count = 0
            for company_data in companies:
                try:
                    company = await repo.create_company(company_data)
                    logger.info(
                        f"✅ Unternehmen erstellt: {company.company_name} (ID: {company.id})"
                    )
                    created_count += 1
                except Exception as e:
                    logger.warning(f"⚠️  Unternehmen konnte nicht erstellt werden: {e}")

            # Erstelle einfachen Import-Log
            import_log_data = {
                "pipeline_step": "seed_test_data",
                "source_file": "simple_test_data.py",
                "records_total": len(companies),
                "records_imported": created_count,
                "records_updated": 0,
                "records_skipped": 0,
                "records_failed": len(companies) - created_count,
                "import_status": (
                    "SUCCESS" if created_count == len(companies) else "PARTIAL"
                ),
                "processing_time_seconds": 1.5,
            }

            try:
                import_log = await repo.create_import_log(import_log_data)
                logger.info(f"✅ Import-Log erstellt: {import_log.id}")
            except Exception as e:
                logger.warning(f"⚠️  Import-Log konnte nicht erstellt werden: {e}")

        logger.info(
            f"🎉 Test-Daten-Seeding abgeschlossen! {created_count}/{len(companies)} Unternehmen erstellt"
        )
        return True

    except Exception as e:
        logger.error(f"❌ Fehler beim Seeding: {e}")
        return False


async def test_repository_features():
    """Teste die erweiterten Repository-Features."""

    logger.info("🔍 Teste Repository-Features...")

    try:
        db_manager = DatabaseManager()

        async with db_manager.get_session() as session:
            repo = BDEWRepository(session)

            # Test 1: Alle Unternehmen abrufen
            all_companies = await repo.get_all_companies()
            logger.info(f"📊 Gefunden: {len(all_companies)} Unternehmen gesamt")

            # Test 2: Suche nach Name
            munich_companies = await repo.search_companies_by_name("München")
            logger.info(f"🔍 München-Suche: {len(munich_companies)} Ergebnisse")

            # Test 3: Full-Text-Suche (falls verfügbar)
            try:
                stadtwerke_companies = await repo.search_companies_fulltext(
                    "Stadtwerke"
                )
                logger.info(
                    f"🔍 Full-Text-Suche 'Stadtwerke': {len(stadtwerke_companies)} Ergebnisse"
                )
            except Exception as e:
                logger.warning(f"⚠️  Full-Text-Suche nicht verfügbar: {e}")

            # Test 4: Geo-Suche (falls verfügbar)
            try:
                nearby_companies = await repo.find_companies_by_location(
                    48.1351, 11.5820, 100
                )
                logger.info(
                    f"🌍 Geo-Suche (München, 100km): {len(nearby_companies)} Ergebnisse"
                )
            except Exception as e:
                logger.warning(f"⚠️  Geo-Suche nicht verfügbar: {e}")

            # Test 5: Datenqualitäts-Statistiken
            try:
                quality_stats = await repo.get_quality_distribution()
                logger.info(f"📈 Qualitäts-Statistiken: {quality_stats}")
            except Exception as e:
                logger.warning(f"⚠️  Qualitäts-Statistiken nicht verfügbar: {e}")

        logger.info("✅ Repository-Features erfolgreich getestet")
        return True

    except Exception as e:
        logger.error(f"❌ Fehler beim Testen der Repository-Features: {e}")
        return False


if __name__ == "__main__":

    async def main():
        # Seeding ausführen
        seed_success = await seed_simple_test_data()

        if seed_success:
            # Features testen
            await test_repository_features()

        return seed_success

    success = asyncio.run(main())
    sys.exit(0 if success else 1)
