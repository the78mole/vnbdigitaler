"""
SQLAlchemy Modelle für BDEW-Stammdaten.

Datenbank-Modelle für die Speicherung und Verwaltung
von BDEW Verteilnetzbetreiber-Stammdaten.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BDEWCompany(Base):
    """
    BDEW Verteilnetzbetreiber-Stammdaten.

    Speichert die Grundinformationen zu deutschen Verteilnetzbetreibern
    aus den BDEW-Datenquellen.
    """

    __tablename__ = "bdew_companies"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # BDEW Stammdaten
    company_name = Column(String(255), nullable=False, index=True)
    network_operator_id = Column(String(50), unique=True, index=True)
    marktlokations_id = Column(String(50), index=True)

    # Adress-Informationen
    postal_code = Column(String(10), index=True)
    city = Column(String(100), index=True)
    federal_state = Column(String(50), index=True)
    address_line = Column(String(255))

    # Kontakt-Informationen
    website = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))

    # Geo-Koordinaten (falls verfügbar)
    latitude = Column(String(20))
    longitude = Column(String(20))

    # Metadaten
    source_file = Column(String(255))  # Ursprungsdatei
    import_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_validated = Column(DateTime)
    is_active = Column(Boolean, default=True, nullable=False)

    # Zusätzliche Informationen
    notes = Column(Text)
    data_quality_score = Column(Integer)  # 0-100 Qualitätsbewertung

    # Indizes für Performance
    __table_args__ = (
        Index("idx_bdew_company_name_active", "company_name", "is_active"),
        Index("idx_bdew_location", "postal_code", "city", "federal_state"),
        Index("idx_bdew_import_date", "import_timestamp"),
    )

    def __repr__(self) -> str:
        return f"<BDEWCompany(name='{self.company_name}', id='{self.network_operator_id}')>"

    def to_dict(self) -> dict:
        """Konvertiere zu Dictionary für API-Ausgaben."""
        return {
            "id": str(self.id),
            "company_name": self.company_name,
            "network_operator_id": self.network_operator_id,
            "marktlokations_id": self.marktlokations_id,
            "postal_code": self.postal_code,
            "city": self.city,
            "federal_state": self.federal_state,
            "address_line": self.address_line,
            "website": self.website,
            "email": self.email,
            "phone": self.phone,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "import_timestamp": (
                self.import_timestamp.isoformat() if self.import_timestamp else None
            ),
            "last_validated": (
                self.last_validated.isoformat() if self.last_validated else None
            ),
            "is_active": self.is_active,
            "data_quality_score": self.data_quality_score,
        }


class BDEWImportLog(Base):
    """
    Log-Tabelle für BDEW-Import-Vorgänge.

    Verfolgt alle Import-Aktivitäten für Auditing und Debugging.
    """

    __tablename__ = "bdew_import_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Import-Details
    import_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    source_file = Column(String(255), nullable=False)
    file_size = Column(Integer)
    file_hash = Column(String(64))  # SHA-256 für Deduplizierung

    # Ergebnisse
    records_total = Column(Integer, nullable=False)
    records_imported = Column(Integer, nullable=False)
    records_updated = Column(Integer, nullable=False)
    records_skipped = Column(Integer, nullable=False)
    records_failed = Column(Integer, nullable=False)

    # Status und Metadaten
    import_status = Column(String(20), nullable=False)  # SUCCESS, FAILED, PARTIAL
    error_message = Column(Text)
    processing_time_seconds = Column(Integer)

    # Pipeline-Kontext
    pipeline_id = Column(String(100))
    user_id = Column(String(100))

    def __repr__(self) -> str:
        return (
            f"<BDEWImportLog(file='{self.source_file}', status='{self.import_status}')>"
        )


class BDEWValidationRule(Base):
    """
    Konfigurierbare Validierungsregeln für BDEW-Daten.

    Ermöglicht flexible Datenqualitätsprüfungen.
    """

    __tablename__ = "bdew_validation_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Regel-Definition
    rule_name = Column(String(100), nullable=False, unique=True)
    rule_description = Column(Text)
    field_name = Column(String(50), nullable=False)
    rule_type = Column(String(20), nullable=False)  # REQUIRED, FORMAT, RANGE, CUSTOM
    rule_config = Column(Text)  # JSON-Konfiguration

    # Regel-Status
    is_active = Column(Boolean, default=True, nullable=False)
    severity = Column(String(10), default="ERROR")  # ERROR, WARNING, INFO

    # Metadaten
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100))

    def __repr__(self) -> str:
        return (
            f"<BDEWValidationRule(name='{self.rule_name}', field='{self.field_name}')>"
        )
