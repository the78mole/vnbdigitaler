#!/usr/bin/env python3
"""
Rollout Router - BNetzA Roll-Out Data Management

Router for displaying and managing BNetzA Roll-Out data entries using the new
normalized table structure (rollout_companies + rollout_quotas).
Shows only companies that are NOT linked to BDEW data.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fuzzywuzzy import fuzz
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
    unmatched_only: bool = Query(False),  # Changed default to False to show all entries
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
    unmatched_only: bool = Query(False),  # Changed default to False to show all entries
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

    # Simplified approach: get companies first with their linked BDEW companies, then quota data separately
    # Build company query with JOIN to get linked BDEW company names
    company_query = select(
        RolloutCompany.id,
        RolloutCompany.bnetza_name,
        RolloutCompany.bdew_code,
        Company.bdew_name.label("linked_bdew_name"),
        Company.bdew_city.label("linked_bdew_city"),
    ).outerjoin(Company, RolloutCompany.bdew_code == Company.bdew_code)

    # Filter for unmatched companies (where bdew_code IS NULL)
    if unmatched_only:
        company_query = company_query.where(RolloutCompany.bdew_code.is_(None))

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
    company_rows = company_result.fetchall()

    # Get quota data for these companies
    entries = []
    for row in company_rows:
        company_id = row.id
        company_name = row.bnetza_name
        bdew_code = row.bdew_code
        linked_bdew_name = row.linked_bdew_name
        linked_bdew_city = row.linked_bdew_city

        if show_latest_only:
            # Get latest quota for this company
            quota_query = (
                select(RolloutQuota)
                .where(RolloutQuota.rollout_company_id == company_id)
                .order_by(RolloutQuota.reference_date.desc())
                .limit(1)
            )
            quota_result = await db.execute(quota_query)
            quota = quota_result.scalar_one_or_none()
        else:
            # For simplicity, also just get the latest (we can extend this later)
            quota_query = (
                select(RolloutQuota)
                .where(RolloutQuota.rollout_company_id == company_id)
                .order_by(RolloutQuota.reference_date.desc())
                .limit(1)
            )
            quota_result = await db.execute(quota_query)
            quota = quota_result.scalar_one_or_none()

        entries.append(
            {
                "id": company_id,
                "company_name": company_name,
                "linked_bdew_name": linked_bdew_name,
                "linked_bdew_city": linked_bdew_city,
                "rollout_quota": float(quota.rollout_quota * 100)
                if quota and quota.rollout_quota is not None
                else 0.0,
                "reference_date": quota.reference_date.isoformat()
                if quota and quota.reference_date
                else None,
                "report_quarter": quota.report_quarter if quota else None,
                "source_file": quota.source_file if quota else None,
                "is_matched": bdew_code is not None,
                "matched_company_id": bdew_code,
                "bdew_company_code": bdew_code,
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

    # Companies linked to BDEW (matched) - these have bdew_code
    matched_query = (
        select(func.count())
        .select_from(RolloutCompany)
        .where(RolloutCompany.bdew_code.is_not(None))
    )
    matched_result = await db.execute(matched_query)
    matched_companies = matched_result.scalar() or 0

    # Unmatched companies (not linked to BDEW) - these have NULL bdew_code
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
        query = query.where(RolloutCompany.bdew_code.is_(None))

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
                "bdew_code": company.bdew_code,
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
        "is_matched": company.bdew_code is not None,
        "matched_company_id": company.bdew_code,
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
        if company.bdew_code == bdew_id:
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
        company_query = company_query.where(RolloutCompany.bdew_code.is_(None))

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


@router.get("/api/bdew-companies/available")
async def get_available_bdew_companies(
    current_rollout_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
):
    """Get BDEW companies that are available for linking.

    Returns:
    - All unlinked BDEW companies sorted by fuzzy match score
    - The currently linked BDEW company (if any) for the given rollout company
    """

    # Get current rollout company name for fuzzy matching
    rollout_company_name = ""
    if current_rollout_id:
        rollout_query = select(RolloutCompany).where(
            RolloutCompany.id == current_rollout_id
        )
        rollout_result = await db.execute(rollout_query)
        rollout_company = rollout_result.scalar_one_or_none()
        if rollout_company:
            rollout_company_name = rollout_company.bnetza_name

    # Get BDEW companies that are NOT already linked to any rollout company
    unlinked_query = (
        select(Company)
        .outerjoin(RolloutCompany, Company.bdew_code == RolloutCompany.bdew_code)
        .where(RolloutCompany.bdew_code.is_(None))
        .where(Company.bdew_code.is_not(None))
    )

    unlinked_result = await db.execute(unlinked_query)
    unlinked_companies = unlinked_result.scalars().all()

    # Get currently linked company (if any)
    current_linked = None
    if current_rollout_id:
        current_query = (
            select(Company)
            .join(RolloutCompany, Company.bdew_code == RolloutCompany.bdew_code)
            .where(RolloutCompany.id == current_rollout_id)
        )
        current_result = await db.execute(current_query)
        current_linked = current_result.scalar_one_or_none()

    # Calculate fuzzy match scores and sort companies
    scored_companies = []
    for company in unlinked_companies:
        # Calculate fuzzy match score using multiple algorithms
        name_score = 0
        city_score = 0

        if rollout_company_name:
            # Score against BDEW company name
            name_score = max(
                fuzz.ratio(rollout_company_name.lower(), company.bdew_name.lower()),
                fuzz.partial_ratio(
                    rollout_company_name.lower(), company.bdew_name.lower()
                ),
                fuzz.token_sort_ratio(
                    rollout_company_name.lower(), company.bdew_name.lower()
                ),
                fuzz.token_set_ratio(
                    rollout_company_name.lower(), company.bdew_name.lower()
                ),
            )

            # Also score against city if available
            if company.bdew_city:
                city_score = fuzz.partial_ratio(
                    rollout_company_name.lower(), company.bdew_city.lower()
                )

        # Combined score (name is more important than city)
        combined_score = int(name_score * 0.8 + city_score * 0.2)

        scored_companies.append(
            {
                "company": company,
                "score": combined_score,
                "name_score": name_score,
                "city_score": city_score,
            }
        )

    # Sort by score (highest first)
    scored_companies.sort(key=lambda x: x["score"], reverse=True)

    # Combine results
    available_companies = []

    # Add currently linked company first (if exists)
    if current_linked:
        available_companies.append(
            {
                "bdew_code": current_linked.bdew_code,
                "bdew_name": current_linked.bdew_name,
                "bdew_city": current_linked.bdew_city or "",
                "is_current": True,
                "match_score": 100,  # Current link gets perfect score
            }
        )

    # Add scored unlinked companies
    for item in scored_companies:
        company = item["company"]
        available_companies.append(
            {
                "bdew_code": company.bdew_code,
                "bdew_name": company.bdew_name,
                "bdew_city": company.bdew_city or "",
                "is_current": False,
                "match_score": item["score"],
            }
        )

    return {
        "companies": available_companies,
        "current_linked_code": current_linked.bdew_code if current_linked else None,
        "rollout_company_name": rollout_company_name,
    }


@router.post("/api/bdew-companies/link")
async def link_bdew_company(
    rollout_company_id: int = Form(...),
    bdew_code: int | None = Form(None),
    db: AsyncSession = Depends(get_db_session),
):
    """Link a rollout company to a BDEW company or unlink it.

    Args:
        rollout_company_id: ID of the rollout company
        bdew_code: BDEW code to link to (None to unlink)
    """

    # Get the rollout company
    rollout_query = select(RolloutCompany).where(
        RolloutCompany.id == rollout_company_id
    )
    rollout_result = await db.execute(rollout_query)
    rollout_company = rollout_result.scalar_one_or_none()

    if not rollout_company:
        return {"success": False, "error": "Rollout company not found"}

    # Verify BDEW company exists (if linking)
    if bdew_code is not None:
        bdew_query = select(Company).where(Company.bdew_code == bdew_code)
        bdew_result = await db.execute(bdew_query)
        bdew_company = bdew_result.scalar_one_or_none()

        if not bdew_company:
            return {"success": False, "error": "BDEW company not found"}

        # Check if BDEW company is already linked to another rollout company
        existing_link_query = (
            select(RolloutCompany)
            .where(RolloutCompany.bdew_code == bdew_code)
            .where(RolloutCompany.id != rollout_company_id)
        )
        existing_link_result = await db.execute(existing_link_query)
        existing_link = existing_link_result.scalar_one_or_none()

        if existing_link:
            return {
                "success": False,
                "error": f"BDEW company already linked to '{existing_link.bnetza_name}'",
            }

    # Update the link
    rollout_company.bdew_code = bdew_code

    await db.commit()

    action = "linked" if bdew_code else "unlinked"
    bdew_name = ""

    if bdew_code:
        bdew_query = select(Company).where(Company.bdew_code == bdew_code)
        bdew_result = await db.execute(bdew_query)
        bdew_company = bdew_result.scalar_one_or_none()
        bdew_name = bdew_company.bdew_name if bdew_company else ""

    return {
        "success": True,
        "message": f"Company '{rollout_company.bnetza_name}' {action}",
        "rollout_company": rollout_company.bnetza_name,
        "bdew_company": bdew_name,
        "bdew_code": bdew_code,
    }
