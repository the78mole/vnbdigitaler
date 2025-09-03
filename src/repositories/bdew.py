"""
BDEW Repository für Datenbankzugriff.

Repository-Pattern für BDEW-Datenoperationen mit SQLAlchemy.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import desc, func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models.bdew import BDEWCompany, BDEWImportLog, BDEWValidationRule


class BDEWRepository:
    """Repository für BDEW-Datenbankoperationen."""

    def __init__(self, session: Session):
        self.session = session

    # Company Operations

    def create_company(self, company_data: dict[str, Any]) -> BDEWCompany:
        """
        Erstelle neuen BDEW-Unternehmensdatensatz.

        Args:
            company_data: Unternehmensdaten

        Returns:
            BDEWCompany: Erstellter Datensatz
        """
        company = BDEWCompany(**company_data)
        self.session.add(company)
        self._commit_with_rollback()
        return company

    def update_company(
        self, company_id: str, updates: dict[str, Any]
    ) -> BDEWCompany | None:
        """
        Aktualisiere BDEW-Unternehmensdatensatz.

        Args:
            company_id: Unternehmens-ID
            updates: Zu aktualisierende Felder

        Returns:
            BDEWCompany: Aktualisierter Datensatz oder None
        """
        company = (
            self.session.query(BDEWCompany).filter(BDEWCompany.id == company_id).first()
        )

        if not company:
            return None

        for key, value in updates.items():
            if hasattr(company, key):
                setattr(company, key, value)

        company.last_validated = datetime.utcnow()
        self._commit_with_rollback()
        return company

    def find_company_by_operator_id(self, operator_id: str) -> BDEWCompany | None:
        """
        Finde Unternehmen anhand der Betreiber-ID.

        Args:
            operator_id: Netzbetreiber-ID

        Returns:
            BDEWCompany: Gefundenes Unternehmen oder None
        """
        return (
            self.session.query(BDEWCompany)
            .filter(
                BDEWCompany.network_operator_id == operator_id,
                BDEWCompany.is_active,
            )
            .first()
        )

    def search_companies(
        self,
        query: str | None = None,
        federal_state: str | None = None,
        postal_code: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BDEWCompany]:
        """
        Suche Unternehmen mit Filtern.

        Args:
            query: Suchtext für Unternehmensname
            federal_state: Bundesland-Filter
            postal_code: Postleitzahl-Filter
            limit: Maximale Anzahl Ergebnisse
            offset: Ergebnisse überspringen

        Returns:
            List[BDEWCompany]: Gefundene Unternehmen
        """
        query_obj = self.session.query(BDEWCompany).filter(BDEWCompany.is_active)

        if query:
            query_obj = query_obj.filter(BDEWCompany.company_name.ilike(f"%{query}%"))

        if federal_state:
            query_obj = query_obj.filter(BDEWCompany.federal_state == federal_state)

        if postal_code:
            query_obj = query_obj.filter(
                BDEWCompany.postal_code.like(f"{postal_code}%")
            )

        return query_obj.offset(offset).limit(limit).all()

    def get_companies_count(self) -> int:
        """Gesamtanzahl aktiver Unternehmen."""
        return (
            self.session.query(func.count(BDEWCompany.id))
            .filter(BDEWCompany.is_active)
            .scalar()
        )

    def get_companies_by_location(
        self, postal_codes: list[str] | None = None, cities: list[str] | None = None
    ) -> list[BDEWCompany]:
        """
        Hole Unternehmen nach Standorten.

        Args:
            postal_codes: Liste von Postleitzahlen
            cities: Liste von Städten

        Returns:
            List[BDEWCompany]: Unternehmen an den Standorten
        """
        query_obj = self.session.query(BDEWCompany).filter(BDEWCompany.is_active)

        conditions = []

        if postal_codes:
            conditions.append(BDEWCompany.postal_code.in_(postal_codes))

        if cities:
            conditions.append(BDEWCompany.city.in_(cities))

        if conditions:
            query_obj = query_obj.filter(or_(*conditions))

        return query_obj.all()

    # Bulk Operations

    def bulk_insert_companies(self, companies_data: list[dict[str, Any]]) -> int:
        """
        Bulk-Insert für Unternehmensdaten.

        Args:
            companies_data: Liste von Unternehmensdaten

        Returns:
            int: Anzahl eingefügter Datensätze
        """
        companies = [BDEWCompany(**data) for data in companies_data]
        self.session.bulk_save_objects(companies, return_defaults=True)
        self._commit_with_rollback()
        return len(companies)

    def deactivate_old_companies(self, import_timestamp: datetime) -> int:
        """
        Deaktiviere Unternehmen, die vor einem bestimmten Zeitpunkt importiert wurden.

        Args:
            import_timestamp: Zeitstempel-Grenze

        Returns:
            int: Anzahl deaktivierter Datensätze
        """
        count = (
            self.session.query(BDEWCompany)
            .filter(
                BDEWCompany.import_timestamp < import_timestamp,
                BDEWCompany.is_active,
            )
            .update({"is_active": False})
        )

        self._commit_with_rollback()
        return count

    # Import Log Operations

    def create_import_log(self, log_data: dict[str, Any]) -> BDEWImportLog:
        """
        Erstelle Import-Log-Eintrag.

        Args:
            log_data: Log-Daten

        Returns:
            BDEWImportLog: Erstellter Log-Eintrag
        """
        import_log = BDEWImportLog(**log_data)
        self.session.add(import_log)
        self._commit_with_rollback()
        return import_log

    def get_recent_imports(self, limit: int = 10) -> list[BDEWImportLog]:
        """
        Hole letzte Import-Logs.

        Args:
            limit: Maximale Anzahl Logs

        Returns:
            List[BDEWImportLog]: Import-Logs
        """
        return (
            self.session.query(BDEWImportLog)
            .order_by(desc(BDEWImportLog.import_timestamp))
            .limit(limit)
            .all()
        )

    def check_file_already_imported(self, file_hash: str) -> BDEWImportLog | None:
        """
        Prüfe ob Datei bereits importiert wurde.

        Args:
            file_hash: SHA-256 Hash der Datei

        Returns:
            BDEWImportLog: Existierender Import oder None
        """
        return (
            self.session.query(BDEWImportLog)
            .filter(
                BDEWImportLog.file_hash == file_hash,
                BDEWImportLog.import_status == "SUCCESS",
            )
            .first()
        )

    # Validation Rules

    def get_active_validation_rules(self) -> list[BDEWValidationRule]:
        """Hole alle aktiven Validierungsregeln."""
        return (
            self.session.query(BDEWValidationRule)
            .filter(BDEWValidationRule.is_active)
            .all()
        )

    def create_validation_rule(self, rule_data: dict[str, Any]) -> BDEWValidationRule:
        """
        Erstelle neue Validierungsregel.

        Args:
            rule_data: Regel-Daten

        Returns:
            BDEWValidationRule: Erstellte Regel
        """
        rule = BDEWValidationRule(**rule_data)
        self.session.add(rule)
        self._commit_with_rollback()
        return rule

    # Utility Methods

    def _commit_with_rollback(self):
        """Commit mit automatischem Rollback bei Fehlern."""
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
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

    def get_data_quality_stats(self) -> dict[str, Any]:
        """
        Hole Datenqualitäts-Statistiken.

        Returns:
            Dict[str, Any]: Qualitätsstats
        """
        total_companies = self.get_companies_count()

        # Unternehmen mit vollständigen Adressdaten
        complete_address = (
            self.session.query(func.count(BDEWCompany.id))
            .filter(
                BDEWCompany.is_active,
                BDEWCompany.postal_code.isnot(None),
                BDEWCompany.city.isnot(None),
                BDEWCompany.federal_state.isnot(None),
            )
            .scalar()
        )

        # Unternehmen mit Kontaktdaten
        with_contact = (
            self.session.query(func.count(BDEWCompany.id))
            .filter(
                BDEWCompany.is_active,
                or_(
                    BDEWCompany.email.isnot(None),
                    BDEWCompany.phone.isnot(None),
                    BDEWCompany.website.isnot(None),
                ),
            )
            .scalar()
        )

        # Durchschnittlicher Qualitätsscore
        avg_quality = (
            self.session.query(func.avg(BDEWCompany.data_quality_score))
            .filter(
                BDEWCompany.is_active,
                BDEWCompany.data_quality_score.isnot(None),
            )
            .scalar()
        )

        return {
            "total_companies": total_companies,
            "complete_address_percentage": (
                (complete_address / total_companies * 100) if total_companies > 0 else 0
            ),
            "with_contact_percentage": (
                (with_contact / total_companies * 100) if total_companies > 0 else 0
            ),
            "average_quality_score": float(avg_quality) if avg_quality else 0,
        }
