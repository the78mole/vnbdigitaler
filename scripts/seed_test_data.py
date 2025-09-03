#!/usr/bin/env python3
"""
Test-Datensatz für PostgreSQL-Datenbank.

Dieses Skript fügt Beispiel-BDEW-Unternehmen in die Datenbank ein
für Entwicklung und Tests.
"""

import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Füge das src-Verzeichnis zum Python-Pfad hinzu
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Setze Umgebungsvariablen vor dem Import
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres@localhost:5432/vnbdigitaler"
)
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_DB", "vnbdigitaler")

from database import DatabaseManager  # noqa: E402
from repositories.bdew import BDEWRepository  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Beispiel-Unternehmensdaten
SAMPLE_COMPANIES = [
    {
        "network_operator_id": "9900000000001",
        "bdew_code": "9900000000001",
        "company_name": "Stadtwerke München GmbH",
        "company_name_normalized": "stadtwerke muenchen gmbh",
        "street": "Emmy-Noether-Str. 2",
        "postal_code": "80287",
        "city": "München",
        "federal_state": "Bayern",
        "latitude": 48.1351,
        "longitude": 11.5820,
        "email": "info@swm.de",
        "phone": "+49 89 2361-0",
        "website": "https://www.swm.de",
        "data_quality_score": 95,
        "service_territory": {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [11.4, 48.0],
                        [11.7, 48.0],
                        [11.7, 48.3],
                        [11.4, 48.3],
                        [11.4, 48.0],
                    ]
                ],
            },
            "properties": {"name": "München Stadtgebiet", "population": 1487708},
        },
        "additional_info": {
            "founded": 1998,
            "employees": 9000,
            "services": ["Strom", "Gas", "Wasser", "Fernwärme", "ÖPNV"],
        },
    },
    {
        "network_operator_id": "9900000000002",
        "bdew_code": "9900000000002",
        "company_name": "E.ON Bayern AG",
        "company_name_normalized": "eon bayern ag",
        "street": "Lilienthalstraße 7",
        "postal_code": "93049",
        "city": "Regensburg",
        "federal_state": "Bayern",
        "latitude": 49.0134,
        "longitude": 12.0991,
        "email": "service@eon.de",
        "phone": "+49 941 28000",
        "website": "https://www.eon.de",
        "data_quality_score": 88,
        "service_territory": {
            "type": "Feature",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [11.8, 48.8],
                            [12.3, 48.8],
                            [12.3, 49.2],
                            [11.8, 49.2],
                            [11.8, 48.8],
                        ]
                    ]
                ],
            },
            "properties": {"name": "Ostbayern", "area_km2": 2500},
        },
        "additional_info": {
            "founded": 2000,
            "employees": 3500,
            "services": ["Strom", "Gas", "Wärme"],
        },
    },
    {
        "network_operator_id": "9900000000003",
        "bdew_code": "9900000000003",
        "company_name": "Netze BW GmbH",
        "company_name_normalized": "netze bw gmbh",
        "street": "Schelmenwasenstraße 15",
        "postal_code": "70567",
        "city": "Stuttgart",
        "federal_state": "Baden-Württemberg",
        "latitude": 48.7758,
        "longitude": 9.1829,
        "email": "info@netze-bw.de",
        "phone": "+49 711 289-0",
        "website": "https://www.netze-bw.de",
        "data_quality_score": 92,
        "service_territory": {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[8.5, 47.5], [10.5, 47.5], [10.5, 49.8], [8.5, 49.8], [8.5, 47.5]]
                ],
            },
            "properties": {"name": "Baden-Württemberg", "population": 11100000},
        },
    },
    {
        "network_operator_id": "9900000000004",
        "company_name": "Stromnetz Hamburg GmbH",
        "company_name_normalized": "stromnetz hamburg gmbh",
        "street": "Bramfelder Chaussee 130",
        "postal_code": "22177",
        "city": "Hamburg",
        "federal_state": "Hamburg",
        "latitude": 53.5511,
        "longitude": 9.9937,
        "email": "info@stromnetz-hamburg.de",
        "phone": "+49 40 23666-0",
        "website": "https://www.stromnetz-hamburg.de",
        "data_quality_score": 89,
        "additional_info": {
            "founded": 2006,
            "employees": 1800,
            "services": ["Strom", "Fernwärme"],
        },
    },
    {
        "network_operator_id": "9900000000005",
        "company_name": "Bayernwerk Netz GmbH",
        "company_name_normalized": "bayernwerk netz gmbh",
        "street": "Lilienthalstraße 7",
        "postal_code": "93049",
        "city": "Regensburg",
        "federal_state": "Bayern",
        "latitude": 49.0134,
        "longitude": 12.0991,
        "email": "info@bayernwerk.de",
        "phone": "+49 941 201-0",
        "website": "https://www.bayernwerk.de",
        "data_quality_score": 85,
        "additional_info": {
            "parent_company": "E.ON",
            "network_length_km": 154000,
            "customers": 1300000,
        },
    },
]


async def seed_test_data():
    """Füge Test-Daten in die Datenbank ein."""

    logger.info("🌱 Starte Test-Daten-Seeding...")

    try:
        # Erstelle DatabaseManager und Repository
        db_manager = DatabaseManager()

        if not await db_manager.test_connection():
            logger.error("❌ Datenbankverbindung fehlgeschlagen!")
            return False

        async with db_manager.get_session() as session:
            repo = BDEWRepository(session)

            # Füge Import-Log hinzu
            import_log_data = {
                "source_file": "test_seed_data.py",
                "file_hash_sha256": "test_hash_123",
                "import_timestamp": datetime.utcnow(),
                "import_status": "SUCCESS",
                "records_imported": len(SAMPLE_COMPANIES),
                "processing_time_seconds": 1.5,
                "file_size_bytes": 4096,
                "import_metadata": {
                    "source": "manual_seed",
                    "version": "1.0",
                    "description": "Test-Daten für Entwicklung",
                },
            }

            import_log = await repo.create_import_log(import_log_data)
            logger.info(f"📝 Import-Log erstellt: {import_log.id}")

            # Füge Unternehmen hinzu
            created_count = 0
            updated_count = 0

            for company_data in SAMPLE_COMPANIES:
                company_data["import_timestamp"] = datetime.utcnow()
                company_data["import_log_id"] = import_log.id

                try:
                    company, was_created = await repo.upsert_company(company_data)

                    if was_created:
                        created_count += 1
                        logger.info(f"✅ Unternehmen erstellt: {company.company_name}")

                        # Verfolge Datenänderung
                        await repo.track_data_change(
                            company_id=company.id,
                            change_type="INSERT",
                            new_values=company_data,
                            changed_by="seed_script",
                            import_log_id=import_log.id,
                        )
                    else:
                        updated_count += 1
                        logger.info(
                            f"🔄 Unternehmen aktualisiert: {company.company_name}"
                        )

                except Exception as e:
                    logger.error(
                        f"❌ Fehler bei Unternehmen {company_data['company_name']}: {e}"
                    )

            logger.info(
                f"✅ {created_count} Unternehmen erstellt, {updated_count} aktualisiert"
            )

            # Zeige Datenbank-Statistiken
            await show_statistics(repo)

        logger.info("🎉 Test-Daten erfolgreich eingefügt!")
        return True

    except Exception as e:
        logger.error(f"❌ Fehler beim Seeding: {e}")
        logger.error(traceback.format_exc())
        return False


async def show_statistics(repo: BDEWRepository):
    """Zeige Datenbank-Statistiken nach dem Seeding."""

    try:
        # Qualitätsverteilung
        quality_stats = await repo.get_quality_distribution()
        logger.info("📊 Qualitäts-Statistiken:")
        logger.info(f"   - Gesamt-Unternehmen: {quality_stats['total_companies']}")
        logger.info(
            f"   - Durchschnittliche Qualität: {quality_stats['average_quality_score']:.1f}"
        )
        logger.info(f"   - Hohe Qualität (>=80): {quality_stats['high_quality_count']}")
        logger.info(f"   - Mit Koordinaten: {quality_stats['with_coordinates_count']}")

        # Bundesländer-Verteilung
        federal_states = await repo.get_companies_by_federal_state()
        logger.info("🗺️  Bundesländer-Verteilung:")
        for state, count in federal_states.items():
            logger.info(f"   - {state}: {count}")

        # Import-Statistiken
        import_stats = await repo.get_import_statistics(days=1)
        logger.info("📈 Import-Statistiken (letzter Tag):")
        logger.info(f"   - Imports: {import_stats['total_imports']}")
        logger.info(f"   - Erfolgsrate: {import_stats['success_rate']:.1f}%")
        logger.info(
            f"   - Importierte Datensätze: {import_stats['total_records_imported']}"
        )

    except Exception as e:
        logger.warning(f"⚠️  Konnte Statistiken nicht abrufen: {e}")


if __name__ == "__main__":
    success = asyncio.run(seed_test_data())
    sys.exit(0 if success else 1)
