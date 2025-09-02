"""Repository layer for database operations.

This module provides high-level database operations through repository pattern,
handling Roll-Out reports, download sessions, and analysis sessions.
"""

from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db_session
from .models import AnalysisSession, DownloadSession, RollOutReport


class RollOutReportRepository:
    """Repository for managing RollOut report data."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def save_roll_out_report(
        self,
        filename: str,
        url: str,
        quarter: str,
        year: int,
        confidence: str,
        method: str,
        reasoning: str | None = None,
        ai_model_used: str | None = None,
        ai_tokens_used: int | None = None,
        ai_response: str | None = None,
        download_session_id: str | None = None,
        source_metadata: dict | None = None,
    ) -> RollOutReport:
        """Save a new Roll-Out report to the database."""
        # Check if this is the latest report for the quarter/year
        is_latest = await self._is_latest_report(quarter, year)

        report = RollOutReport(
            filename=filename,
            url=url,
            quarter=quarter,
            year=year,
            confidence=confidence,
            method=method,
            reasoning=reasoning,
            ai_model_used=ai_model_used,
            ai_tokens_used=ai_tokens_used,
            ai_response=ai_response,
            download_session_id=download_session_id,
            source_metadata=source_metadata,
            is_latest=is_latest,
        )

        self.session.add(report)
        await self.session.commit()
        await self.session.refresh(report)

        # If this is the latest, mark others as not latest
        if is_latest:
            await self._update_latest_flags(quarter, year, report.id)

        return report

    async def get_latest_report(
        self, quarter: str | None = None, year: int | None = None
    ) -> RollOutReport | None:
        """Get the latest Roll-Out report, optionally filtered by quarter/year."""
        query = select(RollOutReport).where(RollOutReport.is_latest)

        if quarter:
            query = query.where(RollOutReport.quarter == quarter)
        if year:
            query = query.where(RollOutReport.year == year)

        query = query.order_by(desc(RollOutReport.year), desc(RollOutReport.quarter))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_report_by_id(self, report_id: int) -> RollOutReport | None:
        """Get a specific report by ID."""
        query = select(RollOutReport).where(RollOutReport.id == report_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_reports_by_session(
        self, download_session_id: str
    ) -> list[RollOutReport]:
        """Get all reports from a specific download session."""
        query = (
            select(RollOutReport)
            .where(RollOutReport.download_session_id == download_session_id)
            .order_by(RollOutReport.created_at)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_recent_reports(self, limit: int = 10) -> list[RollOutReport]:
        """Get the most recent reports."""
        query = (
            select(RollOutReport).order_by(desc(RollOutReport.created_at)).limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def save_download_session(
        self,
        session_id: str,
        temp_directory: str,
        total_urls_found: int,
        excel_urls_found: int,
        user_agent: str,
        script_version: str,
        metadata: dict | None = None,
        status: str = "running",
    ) -> DownloadSession:
        """Save a download session to the database."""
        session_obj = DownloadSession(
            session_id=session_id,
            temp_directory=temp_directory,
            total_urls_found=total_urls_found,
            excel_urls_found=excel_urls_found,
            user_agent=user_agent,
            script_version=script_version,
            metadata=metadata,
            status=status,
        )

        self.session.add(session_obj)
        await self.session.commit()
        await self.session.refresh(session_obj)
        return session_obj

    async def update_download_session_status(
        self,
        session_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        """Update the status of a download session."""
        update_values = {
            "status": status,
            "completed_at": datetime.now(),
        }
        if error_message:
            update_values["error_message"] = error_message

        query = (
            update(DownloadSession)
            .where(DownloadSession.session_id == session_id)
            .values(**update_values)
        )
        await self.session.execute(query)
        await self.session.commit()

    async def save_analysis_session(
        self,
        download_session_id: str,
        model_used: str,
        dry_run: bool = False,
        selected_report_id: int | None = None,
        total_tokens_used: int | None = None,
        analysis_metadata: dict | None = None,
        status: str = "running",
    ) -> AnalysisSession:
        """Save an analysis session to the database."""
        analysis = AnalysisSession(
            download_session_id=download_session_id,
            model_used=model_used,
            dry_run=dry_run,
            selected_report_id=selected_report_id,
            total_tokens_used=total_tokens_used,
            analysis_metadata=analysis_metadata,
            status=status,
        )

        self.session.add(analysis)
        await self.session.commit()
        await self.session.refresh(analysis)
        return analysis

    async def update_analysis_session_status(
        self,
        session_id: int,
        status: str,
        error_message: str | None = None,
        selected_report_id: int | None = None,
        total_tokens_used: int | None = None,
    ) -> None:
        """Update the status of an analysis session."""
        update_values = {
            "status": status,
            "completed_at": datetime.now(),
        }
        if error_message:
            update_values["error_message"] = error_message
        if selected_report_id:
            update_values["selected_report_id"] = selected_report_id
        if total_tokens_used:
            update_values["total_tokens_used"] = total_tokens_used

        query = (
            update(AnalysisSession)
            .where(AnalysisSession.id == session_id)
            .values(**update_values)
        )
        await self.session.execute(query)
        await self.session.commit()

    async def _is_latest_report(self, quarter: str, year: int) -> bool:
        """Check if this would be the latest report for the given quarter/year."""
        query = select(RollOutReport).where(
            and_(
                RollOutReport.quarter == quarter,
                RollOutReport.year == year,
            )
        )
        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()
        return existing is None

    async def _update_latest_flags(
        self, quarter: str, year: int, current_id: int
    ) -> None:
        """Update is_latest flags for reports in the same quarter/year."""
        query = (
            update(RollOutReport)
            .where(
                and_(
                    RollOutReport.quarter == quarter,
                    RollOutReport.year == year,
                    RollOutReport.id != current_id,
                )
            )
            .values(is_latest=False)
        )
        await self.session.execute(query)


async def get_repository() -> AsyncGenerator[RollOutReportRepository, None]:
    """Get repository instance with database session."""
    async for session in get_db_session():
        yield RollOutReportRepository(session)
