"""Database models for VNBdigitaler application.

This module contains SQLAlchemy models for storing BNetzA Roll-Out report data
and related metadata in a Neon PostgreSQL database.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

Base: DeclarativeMeta = declarative_base()


class RollOutReport(Base):  # type: ignore[valid-type,misc]
    """Model for storing BNetzA Roll-Out Quoten reports metadata."""

    __tablename__ = "rollout_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Report identification
    filename: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    quarter: Mapped[str] = mapped_column(
        String(2), nullable=False, index=True
    )  # Q1, Q2, Q3, Q4
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Analysis metadata
    confidence: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # high, medium, low
    method: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # ai_analysis, fallback_pattern
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
    metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

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
