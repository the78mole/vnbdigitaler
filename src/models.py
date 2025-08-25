"""Database models for VNBdigitaler application.

This module contains SQLAlchemy models for storing BNetzA Roll-Out report data,
BDEW grid operator information, and related metadata in a Neon PostgreSQL database.
"""

from datetime import datetime

from sqlalchemy import (
    ARRAY,
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

Base: DeclarativeMeta = declarative_base()


class Company(Base):  # type: ignore[valid-type,misc]
    """Model for storing electricity grid operator companies with BDEW as single source of truth."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # BDEW data (Single Source of Truth)
    bdew_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
        comment="Official BDEW operator code (authoritative)",
    )
    bdew_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Official BDEW company name (authoritative)",
    )
    bdew_name_normalized: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Normalized BDEW name for matching",
    )
    bdew_city: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True, comment="City from BDEW data"
    )

    # vnbdigital.de Stammdaten (strukturiert)
    vnbdigital_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Company name from vnbdigital.de (may differ from BDEW)",
    )
    vnbdigital_address: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Full address from vnbdigital.de"
    )
    vnbdigital_postcode: Mapped[str | None] = mapped_column(
        String(10), nullable=True, comment="Postal code from vnbdigital.de"
    )
    vnbdigital_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="City from vnbdigital.de (may differ from BDEW)",
    )
    vnbdigital_phone: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Phone number from vnbdigital.de"
    )
    vnbdigital_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Email contact from vnbdigital.de"
    )
    vnbdigital_website: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Website URL from vnbdigital.de"
    )
    vnbdigital_grid_types: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Grid voltage levels (e.g., Hochspannung, Mittelspannung, Niederspannung)",
    )

    # Geographic data
    network_territory_geojson: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="GeoJSON geometry for network territory boundaries from vnbdigital.de",
    )
    network_territory_layer_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="GeoServer layer URL for territory data (may require authentication)",
    )

    # Company headquarters location (WGS84 decimal degrees)
    company_latitude: Mapped[float | None] = mapped_column(
        Float,
        CheckConstraint(
            "company_latitude IS NULL OR (company_latitude >= -90 AND company_latitude <= 90)",
            name="chk_company_latitude",
        ),
        nullable=True,
        index=True,
        comment="Company headquarters latitude in WGS84 decimal degrees (-90 to 90)",
    )
    company_longitude: Mapped[float | None] = mapped_column(
        Float,
        CheckConstraint(
            "company_longitude IS NULL OR (company_longitude >= -180 AND company_longitude <= 180)",
            name="chk_company_longitude",
        ),
        nullable=True,
        index=True,
        comment="Company headquarters longitude in WGS84 decimal degrees (-180 to 180)",
    )

    # vnbdigital.de Zusatzdaten (JSONB für flexible Struktur)
    vnbdigital_extended_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional vnbdigital.de data: bbox, services, documents, regions, etc.",
    )

    # Integration Status und Metadaten
    vnbdigital_last_enriched: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful enrichment from vnbdigital.de",
    )
    vnbdigital_enrichment_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True, comment="Status: found, not_found, error"
    )

    # Roll-Out Report data (may contain variations)
    rollout_report_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="Company name as it appears in Roll-Out reports",
    )
    rollout_name_variations: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
        comment="Array of different name variations found in Roll-Out reports",
    )

    # Company classification
    company_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Type of company (e.g., Stadtwerk, Netzbetreiber, etc.)",
    )

    # Matching and verification metadata
    name_matching_confidence: Mapped[float | None] = mapped_column(
        Float,
        CheckConstraint(
            "name_matching_confidence IS NULL OR (name_matching_confidence >= 0.0 AND name_matching_confidence <= 1.0)",
            name="chk_matching_confidence_range",
        ),
        nullable=True,
        index=True,
        comment="AI confidence score for name matching (0.0-1.0)",
    )
    manual_verification: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether the matching has been manually verified",
    )
    verification_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Manual verification notes and comments"
    )

    # Metadata
    source_metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Raw source data and processing metadata"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Business rule constraints
    __table_args__ = (
        CheckConstraint(
            "bdew_code IS NOT NULL AND length(trim(bdew_code)) > 0",
            name="chk_bdew_code_required",
        ),
        CheckConstraint(
            "bdew_name IS NOT NULL AND length(trim(bdew_name)) > 0",
            name="chk_bdew_name_required",
        ),
        CheckConstraint(
            "length(trim(bdew_name_normalized)) > 0",
            name="chk_normalized_name_not_empty",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of Company."""
        return f"<Company(id={self.id}, bdew_code='{self.bdew_code}', bdew_name='{self.bdew_name}')>"


class RollOutReport(Base):  # type: ignore[valid-type,misc]
    """Model for storing BNetzA Roll-Out Quoten reports metadata."""

    __tablename__ = "rollout_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Report identification
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    quarter: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("quarter >= 1 AND quarter <= 4", name="quarter_range_check"),
        nullable=False,
        index=True,
    )  # 1, 2, 3, 4
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Analysis metadata
    confidence: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # high, medium, low
    method: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("method >= 0 AND method <= 2", name="method_range_check"),
        nullable=False,
        default=0,
        index=True,
    )  # 0=unknown, 1=ai_analysis, 2=fallback_pattern
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI analysis details
    ai_model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Download session information
    download_session_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    source_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Status tracking
    is_latest: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    is_processed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    def __repr__(self) -> str:
        """Return string representation of RollOutReport."""
        return f"<RollOutReport(id={self.id}, filename='{self.filename}', quarter='{self.quarter}', year={self.year})>"


class DownloadSession(Base):  # type: ignore[valid-type,misc]
    """Model for tracking BNetzA download sessions."""

    __tablename__ = "download_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Session identification
    session_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    temp_directory: Mapped[str] = mapped_column(String(255), nullable=False)

    # Download statistics
    total_urls_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    excel_urls_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Session metadata
    user_agent: Mapped[str] = mapped_column(String(255), nullable=False)
    script_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running"
    )  # running, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw metadata
    session_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        """Return string representation of DownloadSession."""
        return f"<DownloadSession(id={self.id}, session_id='{self.session_id}', status='{self.status}')>"


class AnalysisSession(Base):  # type: ignore[valid-type,misc]
    """Model for tracking AI analysis sessions."""

    __tablename__ = "analysis_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Session identification
    download_session_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    # Analysis configuration
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Analysis results
    selected_report_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running"
    )  # running, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw analysis data
    analysis_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        """Return string representation of AnalysisSession."""
        return f"<AnalysisSession(id={self.id}, download_session_id='{self.download_session_id}', status='{self.status}')>"


class RolloutEntry(Base):  # type: ignore[valid-type,misc]
    """Model for storing individual entries from BNetzA Roll-Out CSV reports."""

    __tablename__ = "rollout_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # CSV data fields
    company_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Company name as it appears in the BNetzA Roll-Out CSV",
    )
    rollout_quota: Mapped[float] = mapped_column(
        Float,
        CheckConstraint(
            "rollout_quota >= 0.0 AND rollout_quota <= 1.0",
            name="chk_rollout_quota_range",
        ),
        nullable=False,
        index=True,
        comment="Roll-out quota (Ausstattungsquote) as decimal value 0.0-1.0",
    )
    reference_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Reference date (Stichtag) for the quota measurement",
    )

    # Source metadata
    source_file: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Source CSV filename"
    )
    csv_line_number: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Line number in the source CSV file"
    )

    # Matching status
    matched_company_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        comment="Foreign key to matched company in companies table",
    )
    matching_confidence: Mapped[float | None] = mapped_column(
        Float,
        CheckConstraint(
            "matching_confidence IS NULL OR (matching_confidence >= 0.0 AND matching_confidence <= 1.0)",
            name="chk_rollout_matching_confidence_range",
        ),
        nullable=True,
        index=True,
        comment="Confidence score for company matching (0.0-1.0)",
    )
    is_manual_match: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether the match was made manually",
    )
    match_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Notes about the matching process"
    )

    # Data processing metadata
    name_normalized: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Normalized company name for matching",
    )
    import_metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Metadata about the import process"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Business constraints
    __table_args__ = (
        CheckConstraint(
            "company_name IS NOT NULL AND length(trim(company_name)) > 0",
            name="chk_rollout_company_name_required",
        ),
        CheckConstraint(
            "source_file IS NOT NULL AND length(trim(source_file)) > 0",
            name="chk_rollout_source_file_required",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of RolloutEntry."""
        return f"<RolloutEntry(id={self.id}, company_name='{self.company_name}', rollout_quota={self.rollout_quota})>"


class RolloutCompany(Base):  # type: ignore[valid-type,misc]
    """Model for storing unique rollout companies with BDEW linking."""

    __tablename__ = "rollout_companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Company identification
    bnetza_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
        index=True,
        comment="Original company name as it appears in BNetzA Roll-Out reports",
    )
    normalized_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
        comment="Normalized company name for matching purposes",
    )

    # BDEW linking
    bdew_code: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("companies.bdew_code"),
        nullable=True,
        unique=True,
        index=True,
        comment="BDEW code referencing the matched BDEW company",
    )
    is_manually_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether the BDEW linking was manually verified",
    )
    verification_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Notes about the verification process"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Return string representation of RolloutCompany."""
        return f"<RolloutCompany(id={self.id}, bnetza_name='{self.bnetza_name}', bdew_code={self.bdew_code})>"


class RolloutQuota(Base):  # type: ignore[valid-type,misc]
    """Model for storing time-series rollout quota data."""

    __tablename__ = "rollout_quotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Company reference
    rollout_company_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("rollout_companies.id"),
        nullable=False,
        index=True,
        comment="Foreign key to rollout company",
    )

    # Quota data
    rollout_quota: Mapped[float] = mapped_column(
        Float,
        CheckConstraint(
            "rollout_quota >= 0.0 AND rollout_quota <= 1.0", name="chk_quota_range"
        ),
        nullable=False,
        index=True,
        comment="Roll-out quota (Ausstattungsquote) as decimal value 0.0-1.0",
    )
    reference_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Reference date (Stichtag) for the quota measurement",
    )

    # Report metadata
    report_quarter: Mapped[int | None] = mapped_column(
        Integer,
        CheckConstraint(
            "report_quarter IS NULL OR (report_quarter >= 1 AND report_quarter <= 4)",
            name="chk_report_quarter_valid",
        ),
        nullable=True,
        index=True,
        comment="Quarter number (1-4)",
    )
    report_year: Mapped[int | None] = mapped_column(
        Integer,
        CheckConstraint(
            "report_year IS NULL OR (report_year >= 2024 AND report_year <= 2030)",
            name="chk_report_year_valid",
        ),
        nullable=True,
        index=True,
        comment="Report year (2024-2030)",
    )
    source_file: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True, comment="Source CSV filename"
    )
    csv_line_number: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Line number in the source CSV file"
    )

    # Import metadata
    import_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="When this data was imported",
    )
    import_metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="Metadata about the import process"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Business constraints
    __table_args__ = (
        UniqueConstraint(
            "rollout_company_id",
            "reference_date",
            "report_quarter",
            "report_year",
            name="uq_rollout_quota_company_date_quarter_year",
        ),
        CheckConstraint(
            "rollout_quota >= 0.0 AND rollout_quota <= 1.0",
            name="chk_rollout_quota_valid_range",
        ),
    )

    def __repr__(self) -> str:
        """Return string representation of RolloutQuota."""
        return f"<RolloutQuota(id={self.id}, rollout_company_id={self.rollout_company_id}, quota={self.rollout_quota}, date={self.reference_date})>"


class RolloutUpdateLog(Base):  # type: ignore[valid-type,misc]
    """Model for tracking BNetzA rollout quota report downloads and updates."""

    __tablename__ = "rollout_update_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Report source information
    article_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="URL of the BNetzA article page containing the report",
    )
    excel_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename of the downloaded Excel file",
    )
    excel_file_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 hash of the Excel file content for change detection (set after processing)",
    )

    # Report metadata
    report_reference_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="The official reference date (Stichtag) of the report data",
    )
    report_quarter: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint(
            "report_quarter >= 1 AND report_quarter <= 4",
            name="chk_report_quarter_valid",
        ),
        nullable=False,
        index=True,
        comment="Quarter number (1-4)",
    )
    report_year: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint(
            "report_year >= 2020 AND report_year <= 2050", name="chk_report_year_valid"
        ),
        nullable=False,
        index=True,
        comment="Year of the report",
    )

    # Processing statistics
    total_entries_in_report: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint(
            "total_entries_in_report >= 0", name="chk_total_entries_positive"
        ),
        nullable=False,
        default=0,
        comment="Total number of entries found in the report",
    )
    entries_updated: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("entries_updated >= 0", name="chk_entries_updated_positive"),
        nullable=False,
        default=0,
        comment="Number of existing entries that were updated",
    )
    entries_added: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("entries_added >= 0", name="chk_entries_added_positive"),
        nullable=False,
        default=0,
        comment="Number of new entries that were added",
    )
    entries_with_wrong_reference_date: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint(
            "entries_with_wrong_reference_date >= 0",
            name="chk_wrong_date_entries_positive",
        ),
        nullable=False,
        default=0,
        comment="Number of entries with different reference dates than expected",
    )

    # Processing metadata
    download_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="When the Excel file was downloaded",
    )
    processing_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the processing started",
    )
    processing_duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        CheckConstraint(
            "processing_duration_seconds IS NULL OR processing_duration_seconds >= 0",
            name="chk_processing_duration_positive",
        ),
        nullable=True,
        comment="Duration of processing in seconds",
    )

    # Additional information
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Additional notes about the update process"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Error message if processing failed"
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "status IN ('discovered', 'downloaded', 'processing', 'completed', 'failed')",
            name="chk_status_valid",
        ),
        nullable=False,
        default="discovered",
        index=True,
        comment="Processing status: discovered, downloaded, processing, completed, failed",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Return string representation of RolloutUpdateLog."""
        return f"<RolloutUpdateLog(id={self.id}, quarter='{self.report_quarter}', status='{self.status}')>"
