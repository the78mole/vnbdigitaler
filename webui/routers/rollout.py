#!/usr/bin/env python3
"""
Rollout Router - BNetzA Roll-Out Data Management

Router for displaying and managing BNetzA Roll-Out data entries using the new
normalized table structure (rollout_companies + rollout_quotas).
Shows only companies that are NOT linked to BDEW data.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session
from src.models import Company, RolloutCompany, RolloutQuota

# Initialize templates
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")

# Create router
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def rollout_list(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    unmatched_only: bool = Query(True),
    search: str | None = Query(None),
    show_latest_only: bool = Query(True),
    highlight: str | None = Query(None),
    highlight_bdew_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    """Display BNetzA Roll-Out entries with pagination and filtering."""

    # If highlighting a specific company, disable unmatched_only filter to ensure visibility
    if highlight or highlight_bdew_id:
        unmatched_only = False
        if highlight:
            search = highlight  # Also set search to the highlighted company

        # Find the correct page for the highlighted company
        if highlight_bdew_id:
            page = await find_page_for_bdew_id(
                highlight_bdew_id, page_size, unmatched_only, search, db
            )
        elif highlight:
            page = await find_page_for_company_name(
                highlight, page_size, unmatched_only, search, db
            )

    return templates.TemplateResponse(
        "rollout_list.html",
        {
            "request": request,
            "title": "BNetzA Roll-Out Data",
            "active_page": "rollout",
            "page": page,
            "page_size": page_size,
            "unmatched_only": unmatched_only,
            "search": search,
            "show_latest_only": show_latest_only,
            "highlight": highlight,
            "highlight_bdew_id": highlight_bdew_id,
        },
    )


@router.get("/unmatched", response_class=HTMLResponse)
async def rollout_unmatched(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    show_latest_only: bool = Query(True),
):
    """Display unmatched BNetzA Roll-Out entries (convenience endpoint)."""
    return templates.TemplateResponse(
        "rollout_list.html",
        {
            "request": request,
            "title": "Unmatched Roll-Out Data",
            "active_page": "rollout",
            "page": page,
            "page_size": page_size,
            "unmatched_only": True,  # Force unmatched_only to True
            "search": search,
            "show_latest_only": show_latest_only,
        },
    )


@router.get("/api")
async def get_rollout_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    unmatched_only: bool = Query(True),  # Default back to True
    search: str | None = Query(None),
    show_latest_only: bool = Query(True),
    highlight: str | None = Query(None),
    highlight_bdew_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    """API endpoint to get rollout entries with pagination and filtering."""

    # If highlighting a specific company, disable unmatched_only filter to ensure visibility
    if highlight or highlight_bdew_id:
        unmatched_only = False
        if highlight:
            search = highlight  # Also set search to the highlighted company

        # Find the correct page for the highlighted company
        if highlight_bdew_id:
            page = await find_page_for_bdew_id(
                highlight_bdew_id, page_size, unmatched_only, search, db
            )
        elif highlight:
            page = await find_page_for_company_name(
                highlight, page_size, unmatched_only, search, db
            )

    # Simplified approach: get companies first, then their quota data separately
    # Build company query first
    company_query = select(RolloutCompany)

    # Filter for unmatched companies (where bdew_company_id IS NULL)
    if unmatched_only:
        company_query = company_query.where(RolloutCompany.bdew_company_id.is_(None))

    # Add search filter
    if search:
        search_term = f"%{search.lower()}%"
        company_query = company_query.where(
            func.lower(RolloutCompany.bnetza_name).like(search_term)
        )

    # Count total companies
    count_query = select(func.count()).select_from(company_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Add pagination to company query
    offset = (page - 1) * page_size
    company_query = (
        company_query.offset(offset)
        .limit(page_size)
        .order_by(RolloutCompany.bnetza_name)
    )

    # Execute company query
    company_result = await db.execute(company_query)
    companies = company_result.scalars().all()

    # Get quota data for these companies
    entries = []
    for company in companies:
        if show_latest_only:
            # Get latest quota for this company
            quota_query = (
                select(RolloutQuota)
                .where(RolloutQuota.rollout_company_id == company.id)
                .order_by(RolloutQuota.reference_date.desc())
                .limit(1)
            )
            quota_result = await db.execute(quota_query)
            quota = quota_result.scalar_one_or_none()
        else:
            # For simplicity, also just get the latest (we can extend this later)
            quota_query = (
                select(RolloutQuota)
                .where(RolloutQuota.rollout_company_id == company.id)
                .order_by(RolloutQuota.reference_date.desc())
                .limit(1)
            )
            quota_result = await db.execute(quota_query)
            quota = quota_result.scalar_one_or_none()

        entries.append(
            {
                "id": company.id,
                "company_name": company.bnetza_name,
                "rollout_quota": float(quota.rollout_quota * 100)
                if quota and quota.rollout_quota is not None
                else 0.0,
                "reference_date": quota.reference_date.isoformat()
                if quota and quota.reference_date
                else None,
                "report_quarter": quota.report_quarter if quota else None,
                "source_file": quota.source_file if quota else None,
                "is_matched": company.bdew_company_id is not None,
                "matched_company_id": company.bdew_company_id,
                "bdew_company_code": None,  # Will be filled below if matched
                "created_at": quota.created_at.isoformat()
                if quota and quota.created_at
                else None,
                "updated_at": None,  # We don't track updates in quota table
            }
        )

    # Get BDEW codes for matched companies
    matched_company_ids = [
        entry["matched_company_id"] for entry in entries if entry["matched_company_id"]
    ]
    bdew_codes_map = {}

    if matched_company_ids:
        bdew_query = select(Company.id, Company.bdew_code).where(
            Company.id.in_(matched_company_ids)
        )
        bdew_result = await db.execute(bdew_query)
        bdew_codes_map = {row.id: row.bdew_code for row in bdew_result.fetchall()}

    # Update entries with BDEW codes
    for entry in entries:
        if (
            entry["matched_company_id"]
            and entry["matched_company_id"] in bdew_codes_map
        ):
            entry["bdew_company_code"] = bdew_codes_map[entry["matched_company_id"]]

    # Calculate pagination info
    total_pages = (total + page_size - 1) // page_size
    has_next = page < total_pages
    has_prev = page > 1

    return {
        "entries": entries,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
        },
    }


@router.get("/stats")
async def get_rollout_stats(
    db: AsyncSession = Depends(get_db_session),
):
    """Get statistics about rollout entries."""

    # Total companies
    total_query = select(func.count()).select_from(RolloutCompany)
    total_result = await db.execute(total_query)
    total_companies = total_result.scalar() or 0

    # Companies linked to BDEW (matched) - these have bdew_company_id
    matched_query = (
        select(func.count())
        .select_from(RolloutCompany)
        .where(RolloutCompany.bdew_company_id.is_not(None))
    )
    matched_result = await db.execute(matched_query)
    matched_companies = matched_result.scalar() or 0

    # Unmatched companies (not linked to BDEW) - these have NULL bdew_company_id
    unmatched_companies = total_companies - matched_companies

    # Total quota entries
    quota_entries_query = select(func.count()).select_from(RolloutQuota)
    quota_result = await db.execute(quota_entries_query)
    total_quota_entries = quota_result.scalar() or 0

    # Get all quotas > 0 (simplified approach)
    companies_with_quota_query = select(
        func.count(func.distinct(RolloutQuota.rollout_company_id))
    ).where(RolloutQuota.rollout_quota > 0)
    quota_count_result = await db.execute(companies_with_quota_query)
    companies_with_quota = quota_count_result.scalar() or 0

    # Calculate average quota for all quotas > 0 (simplified)
    avg_quota_query = select(func.avg(RolloutQuota.rollout_quota)).where(
        RolloutQuota.rollout_quota > 0
    )
    avg_result = await db.execute(avg_quota_query)
    avg_quota = avg_result.scalar() or 0.0

    return {
        "total_entries": total_companies,
        "matched_entries": matched_companies,
        "unmatched_entries": unmatched_companies,
        "match_rate": (matched_companies / total_companies * 100)
        if total_companies > 0
        else 0,
        "total_quota_entries": total_quota_entries,
        "entries_with_quota": companies_with_quota,
        "avg_quota": float(avg_quota) if avg_quota else 0.0,
    }


@router.get("/companies")
async def get_rollout_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    unmatched_only: bool = Query(False),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    """API endpoint to get rollout companies (without quota data)."""

    # Build query for companies
    query = select(RolloutCompany)

    # Filter for unmatched companies
    if unmatched_only:
        query = query.where(RolloutCompany.bdew_company_id.is_(None))

    # Add search filter
    if search:
        search_term = f"%{search.lower()}%"
        query = query.where(func.lower(RolloutCompany.bnetza_name).like(search_term))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Add pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Order by company name
    query = query.order_by(RolloutCompany.bnetza_name)

    # Execute query
    result = await db.execute(query)
    companies = result.scalars().all()

    # Calculate pagination info
    total_pages = (total + page_size - 1) // page_size
    has_next = page < total_pages
    has_prev = page > 1

    return {
        "companies": [
            {
                "id": company.id,
                "bnetza_name": company.bnetza_name,
                "normalized_name": company.normalized_name,
                "bdew_company_id": company.bdew_company_id,
                "is_manually_verified": company.is_manually_verified,
                "verification_notes": company.verification_notes,
                "created_at": company.created_at.isoformat(),
                "updated_at": company.updated_at.isoformat(),
            }
            for company in companies
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev,
        },
    }


@router.get("/api/{entry_id}")
async def get_rollout_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    """API endpoint to get a single rollout entry by ID."""

    # Get the company
    company_query = select(RolloutCompany).where(RolloutCompany.id == entry_id)
    company_result = await db.execute(company_query)
    company = company_result.scalar_one_or_none()

    if not company:
        return {"detail": "Entry not found"}

    # Get the latest quota for this company
    quota_query = (
        select(RolloutQuota)
        .where(RolloutQuota.rollout_company_id == company.id)
        .order_by(RolloutQuota.reference_date.desc())
        .limit(1)
    )
    quota_result = await db.execute(quota_query)
    quota = quota_result.scalar_one_or_none()

    return {
        "id": company.id,
        "company_name": company.bnetza_name,
        "normalized_company_name": company.normalized_name,
        "rollout_quota": float(quota.rollout_quota * 100)
        if quota and quota.rollout_quota is not None
        else 0.0,
        "reference_date": quota.reference_date.isoformat()
        if quota and quota.reference_date
        else None,
        "report_quarter": quota.report_quarter if quota else None,
        "source_file": quota.source_file if quota else None,
        "is_matched": company.bdew_company_id is not None,
        "matched_company_id": company.bdew_company_id,
        "is_manually_verified": company.is_manually_verified,
        "verification_notes": company.verification_notes,
        "created_at": quota.created_at.isoformat()
        if quota and quota.created_at
        else company.created_at.isoformat(),
    }


async def find_page_for_bdew_id(
    bdew_id: int,
    page_size: int,
    unmatched_only: bool,
    search: str | None,
    db: AsyncSession,
) -> int:
    """Find the page number where a company with given BDEW ID appears."""

    # Build the same query as in get_rollout_entries to maintain consistency
    company_query = select(RolloutCompany)

    # Apply the same filters
    if unmatched_only:
        company_query = company_query.where(RolloutCompany.bdew_company_id.is_(None))

    if search:
        search_term = f"%{search.lower()}%"
        company_query = company_query.where(
            func.lower(RolloutCompany.bnetza_name).like(search_term)
        )

    # Order by same criteria and get all relevant company IDs in order
    company_query = company_query.order_by(RolloutCompany.bnetza_name)

    # Execute query to get all company IDs that match the filter
    result = await db.execute(company_query)
    companies = result.scalars().all()

    # Find the position of our target company
    for i, company in enumerate(companies):
        if company.bdew_company_id == bdew_id:
            position = i + 1  # 1-indexed position
            page = ((position - 1) // page_size) + 1
            return page

    return 1  # Not found, default to page 1


async def find_page_for_company_name(
    company_name: str,
    page_size: int,
    unmatched_only: bool,
    search: str | None,
    db: AsyncSession,
) -> int:
    """Find the page number where a company with given name appears."""

    # Build the same query as in get_rollout_entries to maintain consistency
    company_query = select(RolloutCompany)

    # Apply the same filters
    if unmatched_only:
        company_query = company_query.where(RolloutCompany.bdew_company_id.is_(None))

    if search:
        search_term = f"%{search.lower()}%"
        company_query = company_query.where(
            func.lower(RolloutCompany.bnetza_name).like(search_term)
        )

    # Order by same criteria and get all relevant companies in order
    company_query = company_query.order_by(RolloutCompany.bnetza_name)

    # Execute query to get all companies that match the filter
    result = await db.execute(company_query)
    companies = result.scalars().all()

    # Find the position of our target company
    for i, company in enumerate(companies):
        if company.bnetza_name == company_name:
            position = i + 1  # 1-indexed position
            page = ((position - 1) // page_size) + 1
            return page

    return 1  # Not found, default to page 1
