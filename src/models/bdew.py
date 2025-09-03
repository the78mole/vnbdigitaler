"""
SQLAlchemy Modelle für BDEW-Stammdaten.

Datenbank-Modelle für die Speicherung und Verwaltung
von BDEW Verteilnetzbetreiber-Stammdaten mit PostgreSQL-Optimierungen.
"""

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class BDEWCompany(Base):
    """
    BDEW Verteilnetzbetreiber-Stammdaten.

    Speichert die Grundinformationen zu deutschen Verteilnetzbetreibern
    aus den BDEW-Datenquellen mit PostgreSQL-spezifischen Features.
    """

    __tablename__ = "bdew_companies"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # BDEW Stammdaten (Authoritative Source)
    company_name = Column(String(255), nullable=False, index=True)
    company_name_normalized = Column(String(255), nullable=False, index=True)
    network_operator_id = Column(String(50), unique=True, index=True)
    marktlokations_id = Column(String(50), index=True)
    bdew_code = Column(String(20), unique=True, index=True)

    # Adress-Informationen
    postal_code = Column(String(10), index=True)
    city = Column(String(100), index=True)
    federal_state = Column(String(50), index=True)
    address_line = Column(String(255))

    # Geo-Koordinaten mit Constraints
    latitude = Column(
        Float,
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="chk_latitude_range",
        ),
        index=True,
    )
    longitude = Column(
        Float,
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="chk_longitude_range",
        ),
        index=True,
    )

    # Kontakt-Informationen
    website = Column(String(500))
    email = Column(String(255))
    phone = Column(String(50))

    # Geschäftsdaten
    company_type = Column(String(50), index=True)  # Stadtwerk, Regional, etc.
    grid_areas = Column(String(255))  # Netzgebiete
    service_territory = Column(JSONB)  # GeoJSON für Servicegebiet

    # Qualitäts- und Metadaten
    data_quality_score = Column(
        Integer,
        CheckConstraint(
            "data_quality_score IS NULL OR (data_quality_score >= 0 AND data_quality_score <= 100)",
            name="chk_quality_score_range",
        ),
    )
    source_file = Column(String(255))
    import_metadata = Column(JSONB)  # Flexible Import-Metadaten

    # Status und Lifecycle
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    verification_status = Column(
        String(20), default="pending"
    )  # pending, verified, rejected
    verification_notes = Column(Text)

    # Automatische Timestamps
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_validated = Column(DateTime(timezone=True))

    # Performance-Indizes
    __table_args__ = (
        Index("idx_bdew_company_search", "company_name", "city", "postal_code"),
        Index("idx_bdew_quality_active", "data_quality_score", "is_active"),
        Index("idx_bdew_location", "latitude", "longitude"),
        Index("idx_bdew_updated", "updated_at"),
        Index("idx_bdew_verification", "verification_status", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<BDEWCompany(name='{self.company_name}', id='{self.network_operator_id}')>"

    def to_dict(self) -> dict[str, Any]:
        """Konvertiere zu Dictionary für API-Ausgaben."""
        return {
            "id": str(self.id),
            "company_name": self.company_name,
            "company_name_normalized": self.company_name_normalized,
            "network_operator_id": self.network_operator_id,
            "marktlokations_id": self.marktlokations_id,
            "bdew_code": self.bdew_code,
            "postal_code": self.postal_code,
            "city": self.city,
            "federal_state": self.federal_state,
            "address_line": self.address_line,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "website": self.website,
            "email": self.email,
            "phone": self.phone,
            "company_type": self.company_type,
            "grid_areas": self.grid_areas,
            "service_territory": self.service_territory,
            "data_quality_score": self.data_quality_score,
            "is_active": self.is_active,
            "verification_status": self.verification_status,
        }

    @classmethod
    def normalize_company_name(cls, name: str) -> str:
        """Normalisiert Firmennamen für besseres Matching."""
        if not name:
            return ""

        # Grundlegende Normalisierung
        normalized = name.lower().strip()

        # Entferne häufige Rechtsformen
        replacements = [
            (" gmbh", ""),
            (" ag", ""),
            (" kg", ""),
            (" ohg", ""),
            (" mbh", ""),
            (" co", ""),
            (" und", " &"),
            ("  ", " "),
        ]

        for old, new in replacements:
            normalized = normalized.replace(old, new)

        return normalized.strip()


class BDEWImportLog(Base):
    """
    Erweiterte Log-Tabelle für BDEW-Import-Vorgänge.

    Verfolgt alle Import-Aktivitäten mit detailliertem Status und Metriken.
    """

    __tablename__ = "bdew_import_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Import-Kontext
    import_timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    pipeline_execution_id = Column(String(100), index=True)
    pipeline_step = Column(
        String(50), nullable=False
    )  # download, validate, persist, log

    # Quell-Informationen
    source_file = Column(String(255), nullable=False)
    source_url = Column(String(500))
    file_size_bytes = Column(Integer)
    file_hash_sha256 = Column(String(64), index=True)  # Für Deduplizierung

    # Import-Statistiken
    records_total = Column(Integer, nullable=False, default=0)
    records_imported = Column(Integer, nullable=False, default=0)
    records_updated = Column(Integer, nullable=False, default=0)
    records_skipped = Column(Integer, nullable=False, default=0)
    records_failed = Column(Integer, nullable=False, default=0)

    # Performance-Metriken
    processing_time_seconds = Column(Float)
    memory_usage_mb = Column(Float)
    cpu_usage_percent = Column(Float)

    # Status und Fehlerbehandlung
    import_status = Column(
        String(20), nullable=False, index=True
    )  # SUCCESS, FAILED, PARTIAL, RUNNING, CANCELLED
    error_message = Column(Text)
    error_details = Column(JSONB)  # Strukturierte Fehlerinformationen
    warnings = Column(JSONB)  # Array von Warnungen

    # Validierungs-Ergebnisse
    validation_results = Column(JSONB)  # Detaillierte Validierungsergebnisse
    data_quality_metrics = Column(JSONB)  # Qualitätsmetriken

    # System-Kontext
    system_info = Column(JSONB)  # Systemversion, Python-Version, etc.
    user_context = Column(String(100))

    def __repr__(self) -> str:
        return (
            f"<BDEWImportLog(file='{self.source_file}', "
            f"status='{self.import_status}', records={self.records_imported})>"
        )

    def get_success_rate(self) -> float:
        """Berechnet Erfolgsquote des Imports."""
        total = getattr(self, "records_total", 0) or 0
        imported = getattr(self, "records_imported", 0) or 0
        updated = getattr(self, "records_updated", 0) or 0

        if total == 0:
            return 0.0
        return (imported + updated) / total * 100


class BDEWValidationRule(Base):
    """
    Konfigurierbare Validierungsregeln für BDEW-Daten.

    Ermöglicht flexible, datengetriebene Datenqualitätsprüfungen.
    """

    __tablename__ = "bdew_validation_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Regel-Definition
    rule_name = Column(String(100), nullable=False, unique=True, index=True)
    rule_description = Column(Text)
    field_name = Column(String(50), nullable=False, index=True)
    rule_type = Column(
        Enum(
            "REQUIRED",
            "FORMAT",
            "RANGE",
            "CUSTOM",
            "REGEX",
            "LENGTH",
            name="validation_rule_type",
        ),
        nullable=False,
    )

    rule_config = Column(JSONB, nullable=False)

    # Regel-Status und Priorität
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    severity = Column(
        String(10), default="ERROR", nullable=False
    )  # ERROR, WARNING, INFO
    priority = Column(Integer, default=100)  # Ausführungsreihenfolge

    # Regel-Metriken
    execution_count = Column(Integer, default=0)
    violation_count = Column(Integer, default=0)
    last_executed = Column(DateTime(timezone=True))

    # Metadaten
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by = Column(String(100))
    category = Column(String(50), index=True)  # business, technical, compliance

    def __repr__(self) -> str:
        return (
            f"<BDEWValidationRule(name='{self.rule_name}', "
            f"field='{self.field_name}', active={self.is_active})>"
        )

    def get_violation_rate(self) -> float:
        """Berechnet Verletzungsrate der Regel."""
        execution_count = getattr(self, "execution_count", 0) or 0
        violation_count = getattr(self, "violation_count", 0) or 0

        if execution_count == 0:
            return 0.0
        return violation_count / execution_count * 100


class BDEWDataHistory(Base):
    """
    Change-Tracking für BDEW-Unternehmensdaten.

    Speichert historische Änderungen für Auditing und Rollback.
    """

    __tablename__ = "bdew_data_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Referenz zum ursprünglichen Datensatz
    company_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Change-Tracking
    change_timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    change_type = Column(String(20), nullable=False)  # INSERT, UPDATE, DELETE
    changed_by = Column(String(100))
    change_reason = Column(String(255))

    # Daten vor der Änderung
    old_values = Column(JSONB)
    # Daten nach der Änderung
    new_values = Column(JSONB)
    # Geänderte Felder
    changed_fields = Column(JSONB)  # Array von Feldnamen

    # Import-Kontext
    import_log_id = Column(UUID(as_uuid=True), index=True)

    __table_args__ = (
        Index("idx_history_company_time", "company_id", "change_timestamp"),
        Index("idx_history_change_type", "change_type", "change_timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<BDEWDataHistory(company_id='{self.company_id}', "
            f"type='{self.change_type}', timestamp='{self.change_timestamp}')>"
        )
