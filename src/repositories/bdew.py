"""
BDEW Repository für PostgreSQL-Datenbankzugriff.

Repository-Pattern für BDEW-Datenoperationen mit erweiterten PostgreSQL-Features
wie JSONB-Abfragen, Full-Text-Search und Geo-Queries.
"""

import hashlib
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import and_, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.bdew import (
    BDEWCompany,
    BDEWDataHistory,
    BDEWImportLog,
)


class BDEWRepository:
    """Repository für BDEW-Datenbankoperationen mit PostgreSQL-Features."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Company Operations

    async def get_all_companies(self, limit: int = 100) -> list[BDEWCompany]:
        """
        Hole alle BDEW-Unternehmen.

        Args:
            limit: Maximale Anzahl der Ergebnisse

        Returns:
            list[BDEWCompany]: Liste aller Unternehmen
        """
        result = await self.session.execute(
            select(BDEWCompany)
            .where(BDEWCompany.is_active)
            .order_by(BDEWCompany.company_name)
            .limit(limit)
        )
        return result.scalars().all()

    async def search_companies_by_name(self, name: str) -> list[BDEWCompany]:
        """
        Suche Unternehmen nach Namen.

        Args:
            name: Suchbegriff für Unternehmensname

        Returns:
            list[BDEWCompany]: Gefundene Unternehmen
        """
        result = await self.session.execute(
            select(BDEWCompany)
            .where(
                and_(BDEWCompany.is_active, BDEWCompany.company_name.ilike(f"%{name}%"))
            )
            .order_by(BDEWCompany.company_name)
        )
        return result.scalars().all()

    async def create_company(self, company_data: dict[str, Any]) -> BDEWCompany:
        """
        Erstelle neuen BDEW-Unternehmensdatensatz.

        Args:
            company_data: Unternehmensdaten

        Returns:
            BDEWCompany: Erstellter Datensatz
        """
        # Normalisiere Firmennamen automatisch
        if (
            "company_name" in company_data
            and "company_name_normalized" not in company_data
        ):
            company_data["company_name_normalized"] = (
                BDEWCompany.normalize_company_name(company_data["company_name"])
            )

        company = BDEWCompany(**company_data)
        self.session.add(company)
        await self._commit_with_rollback()
        return company

    async def upsert_company(
        self, company_data: dict[str, Any]
    ) -> tuple[BDEWCompany, bool]:
        """
        Upsert (Insert oder Update) eines Unternehmens.

        Args:
            company_data: Unternehmensdaten

        Returns:
            Tuple[BDEWCompany, bool]: (Unternehmen, wurde_erstellt)
        """
        # PostgreSQL UPSERT mit ON CONFLICT
        stmt = insert(BDEWCompany).values(**company_data)

        # Bei Konflikt mit network_operator_id oder bdew_code: Update
        conflict_cols = ["network_operator_id"]
        if company_data.get("bdew_code"):
            conflict_cols.append("bdew_code")

        # Werte für Update (exklusive Timestamps)
        update_values = {
            k: v for k, v in company_data.items() if k not in ["id", "created_at"]
        }
        update_values["updated_at"] = func.now()

        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_cols, set_=update_values
        ).returning(BDEWCompany)

        result = await self.session.execute(stmt)
        company = result.scalar_one()
        await self._commit_with_rollback()

        # Check if newly created by comparing timestamps
        was_created = (
            getattr(company, "created_at", None) == getattr(company, "updated_at", None)
            if hasattr(company, "created_at") and hasattr(company, "updated_at")
            else False
        )

        return company, was_created

    async def find_company_by_operator_id(self, operator_id: str) -> BDEWCompany | None:
        """
        Finde Unternehmen anhand der Betreiber-ID.

        Args:
            operator_id: Betreiber-ID

        Returns:
            BDEWCompany: Gefundenes Unternehmen oder None
        """
        result = await self.session.execute(
            select(BDEWCompany).where(
                and_(
                    BDEWCompany.network_operator_id == operator_id,
                    BDEWCompany.is_active,
                )
            )
        )
        return result.scalars().first()

    async def find_companies_by_location(
        self, latitude: float, longitude: float, radius_km: float = 50
    ) -> list[BDEWCompany]:
        """
        Finde Unternehmen in geografischer Nähe.

        Args:
            latitude: Breitengrad
            longitude: Längengrad
            radius_km: Suchradius in Kilometern

        Returns:
            List[BDEWCompany]: Unternehmen in der Nähe
        """
        # PostGIS-ähnliche Entfernungsberechnung (vereinfacht)
        result = await self.session.execute(
            text("""
                SELECT *,
                       (6371 * acos(cos(radians(:lat)) * cos(radians(latitude))
                                  * cos(radians(longitude) - radians(:lng))
                                  + sin(radians(:lat)) * sin(radians(latitude)))) AS distance
                FROM bdew_companies
                WHERE latitude IS NOT NULL
                  AND longitude IS NOT NULL
                  AND is_active = true
                  AND (6371 * acos(cos(radians(:lat)) * cos(radians(latitude))
                                 * cos(radians(longitude) - radians(:lng))
                                 + sin(radians(:lat)) * sin(radians(latitude)))) <= :radius
                ORDER BY distance
            """),
            {"lat": latitude, "lng": longitude, "radius": radius_km},
        )
        return [BDEWCompany(**row) for row in result.mappings()]

    async def search_companies_fulltext(
        self, search_term: str, limit: int = 50, min_quality_score: int | None = None
    ) -> list[BDEWCompany]:
        """
        Full-Text-Suche in Unternehmensdaten.

        Args:
            search_term: Suchbegriff
            limit: Maximale Anzahl Ergebnisse
            min_quality_score: Minimaler Qualitätsscore

        Returns:
            List[BDEWCompany]: Gefundene Unternehmen
        """
        # PostgreSQL Full-Text-Search mit rohen SQL
        sql_query = """
            SELECT *,
                   ts_rank(
                       to_tsvector('german',
                           COALESCE(company_name, '') || ' ' ||
                           COALESCE(city, '') || ' ' ||
                           COALESCE(federal_state, '')
                       ),
                       plainto_tsquery('german', :search_term)
                   ) as relevance_score
            FROM bdew_companies
            WHERE is_active = true
              AND to_tsvector('german',
                      COALESCE(company_name, '') || ' ' ||
                      COALESCE(city, '') || ' ' ||
                      COALESCE(federal_state, '')
                  ) @@ plainto_tsquery('german', :search_term)
        """

        params: dict[str, Any] = {"search_term": search_term}

        if min_quality_score:
            sql_query += " AND data_quality_score >= :min_quality_score"
            params["min_quality_score"] = min_quality_score

        sql_query += (
            " ORDER BY relevance_score DESC, data_quality_score DESC LIMIT :limit"
        )
        params["limit"] = limit

        result = await self.session.execute(text(sql_query), params)
        return [BDEWCompany(**row) for row in result.mappings()]

    async def find_similar_companies(
        self, company_name: str, threshold: float = 0.7
    ) -> list[BDEWCompany]:
        """
        Finde ähnliche Unternehmen basierend auf Namens-Similarity.

        Args:
            company_name: Unternehmensname
            threshold: Ähnlichkeits-Schwellenwert (0-1)

        Returns:
            List[BDEWCompany]: Ähnliche Unternehmen
        """
        normalized_name = BDEWCompany.normalize_company_name(company_name)

        # PostgreSQL similarity() Funktion (falls pg_trgm aktiviert)
        result = await self.session.execute(
            text("""
                SELECT *, similarity(company_name_normalized, :name) as sim_score
                FROM bdew_companies
                WHERE similarity(company_name_normalized, :name) > :threshold
                  AND is_active = true
                ORDER BY sim_score DESC
                LIMIT 20
            """),
            {"name": normalized_name, "threshold": threshold},
        )
        return [BDEWCompany(**row) for row in result.mappings()]

    # Advanced Analytics

    async def get_companies_by_federal_state(self) -> dict[str, int]:
        """
        Gruppiere Unternehmen nach Bundesländern.

        Returns:
            Dict[str, int]: {Bundesland: Anzahl}
        """
        result = await self.session.execute(text("""
                SELECT federal_state, COUNT(*) as count
                FROM bdew_companies
                WHERE is_active = true AND federal_state IS NOT NULL
                GROUP BY federal_state
                ORDER BY count DESC
            """))
        return {
            str(getattr(row, "federal_state", "")): int(getattr(row, "count", 0))
            for row in result
        }

    async def get_quality_distribution(self) -> dict[str, Any]:
        """
        Analyse der Datenqualitäts-Verteilung.

        Returns:
            Dict[str, Any]: Qualitätsstatistiken
        """
        result = await self.session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    AVG(data_quality_score) as avg_score,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY data_quality_score) as median_score,
                    COUNT(*) FILTER (WHERE data_quality_score >= 80) as high_quality,
                    COUNT(*) FILTER (WHERE data_quality_score < 50) as low_quality,
                    COUNT(*) FILTER (WHERE latitude IS NOT NULL AND longitude IS NOT NULL) as with_coordinates
                FROM bdew_companies
                WHERE is_active = true
            """))

        row = result.first()
        if not row:
            return {
                "total_companies": 0,
                "average_quality_score": 0.0,
                "median_quality_score": 0.0,
                "high_quality_count": 0,
                "low_quality_count": 0,
                "with_coordinates_count": 0,
                "coordinate_coverage_percent": 0.0,
            }

        return {
            "total_companies": int(getattr(row, "total", 0)),
            "average_quality_score": float(getattr(row, "avg_score", 0) or 0),
            "median_quality_score": float(getattr(row, "median_score", 0) or 0),
            "high_quality_count": int(getattr(row, "high_quality", 0)),
            "low_quality_count": int(getattr(row, "low_quality", 0)),
            "with_coordinates_count": int(getattr(row, "with_coordinates", 0)),
            "coordinate_coverage_percent": (
                (getattr(row, "with_coordinates", 0) / getattr(row, "total", 1) * 100)
                if getattr(row, "total", 0) > 0
                else 0.0
            ),
        }

    # JSONB Operations

    async def update_service_territory(
        self, company_id: uuid.UUID, geojson_data: dict[str, Any]
    ) -> bool:
        """
        Aktualisiere Service-Territorium mit GeoJSON-Daten.

        Args:
            company_id: Unternehmens-ID
            geojson_data: GeoJSON-Daten

        Returns:
            bool: True wenn erfolgreich
        """
        result = await self.session.execute(
            text("""
                UPDATE bdew_companies
                SET service_territory = :geojson,
                    updated_at = NOW()
                WHERE id = :company_id
                RETURNING id
            """),
            {"company_id": company_id, "geojson": geojson_data},
        )

        await self._commit_with_rollback()
        return result.first() is not None

    async def find_companies_with_service_area(self) -> list[BDEWCompany]:
        """
        Finde alle Unternehmen mit definierten Service-Gebieten.

        Returns:
            List[BDEWCompany]: Unternehmen mit Service-Territorien
        """
        result = await self.session.execute(text("""
                SELECT * FROM bdew_companies
                WHERE service_territory IS NOT NULL
                  AND service_territory != 'null'::jsonb
                  AND is_active = true
                ORDER BY company_name
            """))
        return [BDEWCompany(**row) for row in result.mappings()]

    # Change Tracking

    async def track_data_change(
        self,
        company_id: uuid.UUID,
        change_type: str,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        changed_by: str | None = None,
        import_log_id: uuid.UUID | None = None,
    ) -> BDEWDataHistory:
        """
        Verfolge Datenänderungen für Auditing.

        Args:
            company_id: Unternehmens-ID
            change_type: Art der Änderung (INSERT, UPDATE, DELETE)
            old_values: Alte Werte
            new_values: Neue Werte
            changed_by: Wer hat geändert
            import_log_id: Referenz zum Import-Log

        Returns:
            BDEWDataHistory: Historien-Eintrag
        """
        # Ermittle geänderte Felder
        changed_fields = []
        if old_values and new_values:
            changed_fields = [
                field
                for field in new_values
                if old_values.get(field) != new_values.get(field)
            ]

        history_entry = BDEWDataHistory(
            company_id=company_id,
            change_type=change_type,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            changed_by=changed_by,
            import_log_id=import_log_id,
        )

        self.session.add(history_entry)
        await self._commit_with_rollback()
        return history_entry

    # Import Logs with Enhanced Features

    async def create_import_log(self, log_data: dict[str, Any]) -> BDEWImportLog:
        """
        Erstelle erweiterten Import-Log-Eintrag.

        Args:
            log_data: Log-Daten

        Returns:
            BDEWImportLog: Erstellter Log-Eintrag
        """
        import_log = BDEWImportLog(**log_data)
        self.session.add(import_log)
        await self._commit_with_rollback()
        return import_log

    async def get_import_statistics(self, days: int = 30) -> dict[str, Any]:
        """
        Hole Import-Statistiken der letzten Tage.

        Args:
            days: Anzahl Tage zurück

        Returns:
            Dict[str, Any]: Import-Statistiken
        """
        result = await self.session.execute(
            text("""
                SELECT
                    COUNT(*) as total_imports,
                    COUNT(*) FILTER (WHERE import_status = 'SUCCESS') as successful_imports,
                    SUM(records_imported) as total_records,
                    AVG(processing_time_seconds) as avg_processing_time,
                    SUM(file_size_bytes) as total_data_processed
                FROM bdew_import_logs
                WHERE import_timestamp >= NOW() - INTERVAL ':days days'
            """),
            {"days": days},
        )

        row = result.first()
        if not row:
            return {
                "total_imports": 0,
                "successful_imports": 0,
                "success_rate": 0.0,
                "total_records_imported": 0,
                "average_processing_time": 0.0,
                "total_data_processed_mb": 0.0,
            }

        return {
            "total_imports": int(getattr(row, "total_imports", 0)),
            "successful_imports": int(getattr(row, "successful_imports", 0)),
            "success_rate": (
                (
                    getattr(row, "successful_imports", 0)
                    / getattr(row, "total_imports", 1)
                    * 100
                )
                if getattr(row, "total_imports", 0) > 0
                else 0.0
            ),
            "total_records_imported": int(getattr(row, "total_records", 0) or 0),
            "average_processing_time": float(
                getattr(row, "avg_processing_time", 0) or 0
            ),
            "total_data_processed_mb": float(
                getattr(row, "total_data_processed", 0) or 0
            )
            / (1024 * 1024),
        }

    # Utility Methods

    async def _commit_with_rollback(self):
        """Commit mit automatischem Rollback bei Fehlern."""
        try:
            await self.session.commit()
        except SQLAlchemyError:
            await self.session.rollback()
            raise

    @staticmethod
    def calculate_file_hash(file_path: str | Path) -> str:
        """
        Berechne SHA-256 Hash einer Datei.

        Args:
            file_path: Dateipfad

        Returns:
            str: SHA-256 Hash
        """
        hash_sha256 = hashlib.sha256()
        with Path(file_path).open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    # Health Checks

    async def health_check(self) -> dict[str, Any]:
        """
        Gesundheitsprüfung der Datenbank und Daten.

        Returns:
            Dict[str, Any]: Gesundheitsstatus
        """
        try:
            # Basis-Verbindungstest
            await self.session.execute(text("SELECT 1"))

            # Datenqualitätsprüfungen
            quality_stats = await self.get_quality_distribution()

            # Letzte Import-Aktivität
            last_import = await self.session.execute(text("""
                    SELECT import_timestamp, import_status
                    FROM bdew_import_logs
                    ORDER BY import_timestamp DESC
                    LIMIT 1
                """))
            last_import_row = last_import.first()

            return {
                "database_connection": "healthy",
                "total_companies": quality_stats["total_companies"],
                "average_quality_score": quality_stats["average_quality_score"],
                "last_import": {
                    "timestamp": (
                        last_import_row.import_timestamp.isoformat()
                        if last_import_row
                        else None
                    ),
                    "status": (
                        last_import_row.import_status if last_import_row else None
                    ),
                },
                "status": "healthy",
            }

        except Exception as e:
            return {
                "database_connection": "unhealthy",
                "error": str(e),
                "status": "unhealthy",
            }

    # Test-Support Methoden für die Test-Suite

    async def bulk_insert_companies(self, companies_data: list[dict[str, Any]]) -> int:
        """
        Bulk-Insert für mehrere Unternehmen.

        Args:
            companies_data: Liste von Company-Dictionaries

        Returns:
            int: Anzahl eingefügter Unternehmen
        """
        if not companies_data:
            return 0

        try:
            count = 0
            for company_data in companies_data:
                await self.create_company(company_data)
                count += 1
            return count
        except Exception as e:
            await self.session.rollback()
            raise SQLAlchemyError(f"Bulk insert failed: {e}")

    async def get_companies_count(self) -> int:
        """
        Anzahl aller aktiven Unternehmen.

        Returns:
            int: Anzahl Unternehmen
        """
        result = await self.session.execute(
            select(func.count(BDEWCompany.id)).where(BDEWCompany.is_active)
        )
        return result.scalar() or 0

    async def search_companies(
        self,
        query: str | None = None,
        federal_state: str | None = None,
        postal_code: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BDEWCompany]:
        """
        Allgemeine Suchfunktion für Unternehmen.

        Args:
            query: Suchbegriff für Namen
            federal_state: Filter nach Bundesland
            postal_code: Filter nach PLZ
            limit: Maximale Anzahl Ergebnisse
            offset: Offset für Paginierung

        Returns:
            list[BDEWCompany]: Gefundene Unternehmen
        """
        # Build query conditions
        conditions = [BDEWCompany.is_active]

        if query:
            conditions.append(BDEWCompany.company_name.ilike(f"%{query}%"))

        if federal_state:
            conditions.append(BDEWCompany.federal_state == federal_state)

        if postal_code:
            conditions.append(BDEWCompany.postal_code == postal_code)

        stmt = (
            select(BDEWCompany)
            .where(and_(*conditions))
            .order_by(BDEWCompany.company_name)
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_data_quality_stats(self) -> dict[str, Any]:
        """
        Erstelle Datenqualitäts-Statistiken.

        Returns:
            dict: Statistiken über Datenqualität
        """
        # Gesamtanzahl
        total_result = await self.session.execute(
            select(func.count(BDEWCompany.id)).where(BDEWCompany.is_active)
        )
        total_companies = total_result.scalar() or 0

        # Durchschnittlicher Quality Score
        avg_result = await self.session.execute(
            select(func.avg(BDEWCompany.data_quality_score)).where(
                and_(BDEWCompany.is_active, BDEWCompany.data_quality_score.is_not(None))
            )
        )
        avg_quality = avg_result.scalar() or 0

        return {
            "total_companies": total_companies,
            "average_quality_score": float(avg_quality) if avg_quality else 0.0,
        }
