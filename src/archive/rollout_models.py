"""VNBdigitaler Rollout Models.

Database models for rollout company and quota management.
Clean implementation focused on rollout data, not BDEW matching.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class RolloutCompany(Base):  # type: ignore[misc, valid-type]
    """Rollout Company Model.

    Tracks companies from BNetzA rollout reports.
    Focus: Companies that appear in rollout data, not BDEW matching.
    """

    __tablename__ = "rollout_companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    source = Column(String(100), nullable=False, default="bnetza_rollout_report")
    status = Column(String(50), nullable=False, default="active")

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now)
    first_seen_quarter = Column(String(20), nullable=True)
    last_seen_quarter = Column(String(20), nullable=True)

    # Optional fields for additional data
    website = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    verification_notes = Column(Text, nullable=True)

    # Relationships
    quotas = relationship("RolloutQuota", back_populates="company")

    def __repr__(self) -> str:
        return f"<RolloutCompany(id={self.id}, name='{self.name}', status='{self.status}')>"


class RolloutQuota(Base):  # type: ignore[misc, valid-type]
    """Rollout Quota Model.

    Tracks smart meter rollout quotas from BNetzA reports.
    """

    __tablename__ = "rollout_quotas"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("rollout_companies.id"), nullable=False)

    # Quarter and reporting information
    quarter = Column(String(20), nullable=False)  # e.g., "Q1_2025"
    report_date = Column(DateTime, nullable=True)

    # Quota data (exact fields depend on BNetzA report structure)
    total_rollout_target = Column(Integer, nullable=True)
    completed_rollouts = Column(Integer, nullable=True)
    pending_rollouts = Column(Integer, nullable=True)
    quota_percentage = Column(Float, nullable=True)

    # Status tracking
    status = Column(String(50), nullable=False, default="active")
    is_latest = Column(Boolean, nullable=False, default=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now)
    source_file = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    company = relationship("RolloutCompany", back_populates="quotas")

    def __repr__(self) -> str:
        return f"<RolloutQuota(id={self.id}, company_id={self.company_id}, quarter='{self.quarter}')>"


class RolloutReport(Base):  # type: ignore[misc, valid-type]
    """Rollout Report Model.

    Tracks processed BNetzA rollout reports.
    """

    __tablename__ = "rollout_reports"

    id = Column(Integer, primary_key=True)

    # Report identification
    quarter = Column(String(20), nullable=False, unique=True)  # e.g., "Q1_2025"
    filename = Column(String(255), nullable=False)
    source_url = Column(String(500), nullable=True)

    # Processing information
    downloaded_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    status = Column(
        String(50), nullable=False, default="discovered"
    )  # discovered, downloaded, processed, failed

    # Statistics
    companies_found = Column(Integer, nullable=True)
    quotas_processed = Column(Integer, nullable=True)
    new_companies_added = Column(Integer, nullable=True)

    # File information
    file_size = Column(Integer, nullable=True)
    file_hash = Column(String(64), nullable=True)  # SHA-256 hash

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now)
    notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<RolloutReport(id={self.id}, quarter='{self.quarter}', status='{self.status}')>"


class WorkflowExecution(Base):  # type: ignore[misc, valid-type]
    """Workflow Execution Model.

    Tracks rollout workflow executions for monitoring and debugging.
    """

    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True)

    # Execution identification
    workflow_id = Column(String(100), nullable=False, unique=True)
    quarter = Column(String(20), nullable=False)
    trigger = Column(String(50), nullable=False)  # manual, scheduled, api

    # Execution status
    status = Column(
        String(50), nullable=False, default="running"
    )  # running, completed, failed, cancelled
    current_step = Column(String(100), nullable=True)

    # Timing information
    started_at = Column(DateTime, nullable=False, default=datetime.now)
    completed_at = Column(DateTime, nullable=True)
    total_execution_time = Column(Float, nullable=True)  # seconds

    # Results
    companies_processed = Column(Integer, nullable=True)
    quotas_updated = Column(Integer, nullable=True)
    errors_count = Column(Integer, nullable=False, default=0)

    # Files and artifacts
    source_files = Column(Text, nullable=True)  # JSON list of files
    output_files = Column(Text, nullable=True)  # JSON list of files

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.now)
    notes = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<WorkflowExecution(id={self.id}, workflow_id='{self.workflow_id}', status='{self.status}')>"
