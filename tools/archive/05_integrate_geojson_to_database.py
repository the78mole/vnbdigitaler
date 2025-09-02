#!/usr/bin/env python3
"""
Integration von extrahierten GeoJSON-Daten in die Neon PostgreSQL Datenbank.

Dieses Skript:
1. Lädt die extrahierten GeoJSON-Daten aus complete_territories_geojson.json
2. Matched sie mit den Operatoren in der Datenbank über BDEW-Codes
3. Aktualisiert das network_territory_geojson JSON-Feld in der Datenbank

Author: VNBdigitaler Team
Date: 2025-08-21
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import asyncpg
from dotenv import load_dotenv

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Basis-Verzeichnis
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# .env laden
load_dotenv()


class GeoJSONDatabaseIntegrator:
    """Integriert GeoJSON-Daten in die Neon PostgreSQL Datenbank."""

    def __init__(self):
        """Initialisiert den Integrator mit Datenbankverbindung."""
        # Neon Database URL aus Umgebungsvariablen
        self.database_url = os.getenv("NEON_DATABASE_URL")
        if not self.database_url:
            raise ValueError("NEON_DATABASE_URL nicht gefunden in Umgebungsvariablen")

        # SSL Parameter für asyncpg konvertieren
        if "sslmode=require" in self.database_url:
            self.database_url = self.database_url.replace(
                "sslmode=require", "ssl=require"
            )

        self.connection = None

    async def connect(self):
        """Stellt Verbindung zur Datenbank her."""
        try:
            self.connection = await asyncpg.connect(self.database_url)
            logger.info("✅ Erfolgreich mit Neon PostgreSQL verbunden")
        except Exception as e:
            logger.error(f"❌ Fehler bei Datenbankverbindung: {e}")
            raise

    async def disconnect(self):
        """Schließt die Datenbankverbindung."""
        if self.connection:
            await self.connection.close()
            logger.info("🔌 Datenbankverbindung geschlossen")

    async def load_geojson_data(self) -> dict[str, Any]:
        """Lädt die extrahierten GeoJSON-Daten."""
        geojson_file = DATA_DIR / "complete_territories_geojson.json"

        if not geojson_file.exists():
            raise FileNotFoundError(f"GeoJSON-Datei nicht gefunden: {geojson_file}")

        with geojson_file.open(encoding="utf-8") as f:
            data = json.load(f)

        geojson_data = data.get("geojson_data", {})
        logger.info(f"📄 GeoJSON-Daten geladen: {len(geojson_data)} Operatoren")
        logger.info(
            f"📊 Erfolgreiche Extraktionen: {data.get('successful_extractions', 0)}"
        )
        return data

    async def get_operators_from_database(self) -> list[dict[str, Any]]:
        """Holt alle Operatoren aus der Datenbank."""
        query = """
        SELECT id, bdew_code, bdew_name, vnbdigital_name
        FROM companies
        WHERE bdew_code IS NOT NULL
        ORDER BY bdew_code
        """

        rows = await self.connection.fetch(query)
        operators = [dict(row) for row in rows]

        logger.info(f"🏢 {len(operators)} Operatoren aus Datenbank geladen")
        return operators

    async def update_operator_geojson(
        self, operator_id: int, bdew_code: str, geojson_data: dict[str, Any]
    ) -> bool:
        """Aktualisiert das GeoJSON-Feld für einen Operator."""
        try:
            # JSON-Daten für PostgreSQL vorbereiten
            geojson_json = json.dumps(geojson_data, ensure_ascii=False)

            query = """
            UPDATE companies
            SET network_territory_geojson = $1,
                manual_verification = false
            WHERE id = $2
            """

            await self.connection.execute(query, geojson_json, operator_id)
            return True

        except Exception as e:
            logger.error(f"❌ Fehler beim Update von Operator {bdew_code}: {e}")
            return False

    async def integrate_geojson_data(self):
        """Hauptfunktion für die GeoJSON-Integration."""
        logger.info("🚀 Starte GeoJSON-Datenbank-Integration...")

        # GeoJSON-Daten laden
        data = await self.load_geojson_data()
        geojson_data = data.get("geojson_data", {})

        # Operatoren aus Datenbank laden
        operators = await self.get_operators_from_database()

        # Statistiken
        updated_count = 0
        failed_count = 0
        not_found_count = 0

        for operator in operators:
            operator_id = operator["id"]
            bdew_code = str(operator["bdew_code"])  # Ensure string for comparison
            company_name = (
                operator["bdew_name"]
                or operator["vnbdigital_name"]
                or f"Operator {bdew_code}"
            )

            logger.info(f"🔄 Verarbeite {company_name} (BDEW: {bdew_code})...")

            # Prüfe, ob GeoJSON-Daten für diesen Operator vorhanden sind
            if bdew_code in geojson_data:
                territory_data = geojson_data[bdew_code]

                # Verwende direkt das GeoJSON aus den Daten
                geojson = territory_data.get("geojson", {})

                # Füge Metadaten hinzu
                if "metadata" not in geojson:
                    geojson["metadata"] = {}

                geojson["metadata"].update(
                    {
                        "bdew_code": bdew_code,
                        "company_name": company_name,
                        "operator_name": territory_data.get("operator_name"),
                        "vnbdigital_name": operator.get("vnbdigital_name"),
                        "extraction_date": data.get("extraction_timestamp"),
                        "feature_count": territory_data.get("features_count", 0),
                    }
                )

                # In Datenbank aktualisieren
                success = await self.update_operator_geojson(
                    operator_id, bdew_code, geojson
                )

                if success:
                    feature_count = territory_data.get("features_count", 0)
                    logger.info(
                        f"✅ {company_name}: {feature_count} GeoJSON-Features integriert"
                    )
                    updated_count += 1
                else:
                    logger.error(f"❌ {company_name}: Integration fehlgeschlagen")
                    failed_count += 1
            else:
                logger.warning(f"⚠️ {company_name}: Keine GeoJSON-Daten gefunden")
                not_found_count += 1

        # Abschlussbericht
        logger.info("=" * 60)
        logger.info("📊 GeoJSON-Integration abgeschlossen:")
        logger.info(f"   ✅ Erfolgreich integriert: {updated_count}")
        logger.info(f"   ❌ Fehlgeschlagen: {failed_count}")
        logger.info(f"   ⚠️ Nicht gefunden: {not_found_count}")
        logger.info(f"   📈 Gesamte Operatoren: {len(operators)}")

        success_rate = (updated_count / len(operators)) * 100 if operators else 0
        logger.info(f"   🎯 Erfolgsrate: {success_rate:.1f}%")
        logger.info("=" * 60)

    async def verify_integration(self) -> dict[str, int]:
        """Verifiziert die Integration durch Abfrage der Datenbank."""
        logger.info("🔍 Verifiziere GeoJSON-Integration...")

        # Zähle Operatoren mit GeoJSON-Daten
        query_with_geojson = """
        SELECT COUNT(*) as count
        FROM companies
        WHERE network_territory_geojson IS NOT NULL
        """

        # Zähle Operatoren ohne GeoJSON-Daten
        query_without_geojson = """
        SELECT COUNT(*) as count
        FROM companies
        WHERE network_territory_geojson IS NULL
        """

        # Zähle Gesamtzahl der Operatoren
        query_total = """
        SELECT COUNT(*) as count
        FROM companies
        """

        with_geojson = await self.connection.fetchval(query_with_geojson)
        without_geojson = await self.connection.fetchval(query_without_geojson)
        total = await self.connection.fetchval(query_total)

        logger.info("📊 Verifikationsergebnisse:")
        logger.info(f"   🗺️ Mit GeoJSON-Daten: {with_geojson}")
        logger.info(f"   ❌ Ohne GeoJSON-Daten: {without_geojson}")
        logger.info(f"   📈 Gesamt: {total}")

        coverage = (with_geojson / total) * 100 if total > 0 else 0
        logger.info(f"   🎯 Abdeckung: {coverage:.1f}%")

        return {
            "with_geojson": with_geojson,
            "without_geojson": without_geojson,
            "total": total,
            "coverage_percent": coverage,
        }


async def main():
    """Hauptfunktion für die GeoJSON-Datenbank-Integration."""
    integrator = GeoJSONDatabaseIntegrator()

    try:
        # Datenbankverbindung herstellen
        await integrator.connect()

        # GeoJSON-Daten integrieren
        await integrator.integrate_geojson_data()

        # Integration verifizieren
        await integrator.verify_integration()

    except Exception as e:
        logger.error(f"❌ Fehler in main(): {e}")
        raise
    finally:
        # Verbindung schließen
        await integrator.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
