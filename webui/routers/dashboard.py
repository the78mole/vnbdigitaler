"""
Dashboard router for VNBdigitaler WebUI.
Provides overview and navigation functionality.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session
from src.models import Company, RolloutCompany, RolloutQuota

# Initialize templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=templates_path)

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "title": "VNBdigitaler Admin Dashboard",
            "active_page": "dashboard",
        },
    )


@router.get("/api/dashboard/stats")
async def dashboard_stats_api(db: AsyncSession = Depends(get_db_session)):
    """API endpoint for dashboard statistics."""
    try:
        # Total companies
        total_companies_query = select(func.count()).select_from(Company)
        total_companies_result = await db.execute(total_companies_query)
        total_companies = total_companies_result.scalar() or 0

        # Companies with rollout names (matched) - using rollout_companies table
        matched_companies_query = (
            select(func.count(func.distinct(Company.id)))
            .select_from(Company)
            .join(RolloutCompany, Company.bdew_code == RolloutCompany.bdew_code)
        )
        matched_companies_result = await db.execute(matched_companies_query)
        matched_companies = matched_companies_result.scalar() or 0

        # Companies without rollout names (unmatched)
        unmatched_companies = total_companies - matched_companies

        # Rollout companies
        rollout_companies_query = select(func.count()).select_from(RolloutCompany)
        rollout_companies_result = await db.execute(rollout_companies_query)
        rollout_companies = rollout_companies_result.scalar() or 0

        # Rollout quotas
        rollout_quotas_query = select(func.count()).select_from(RolloutQuota)
        rollout_quotas_result = await db.execute(rollout_quotas_query)
        rollout_quotas = rollout_quotas_result.scalar() or 0

        # Companies with service areas
        service_areas_query = (
            select(func.count())
            .select_from(Company)
            .where(Company.network_territory_geojson.is_not(None))
        )
        service_areas_result = await db.execute(service_areas_query)
        service_areas = service_areas_result.scalar() or 0

        return {
            "total_companies": total_companies,
            "matched_companies": matched_companies,
            "unmatched_companies": unmatched_companies,
            "rollout_companies": rollout_companies,
            "rollout_quotas": rollout_quotas,
            "service_areas": service_areas,
            "match_rate": (
                round((matched_companies / total_companies * 100), 1)
                if total_companies > 0
                else 0.0
            ),
            "database_status": "connected",
            "last_updated": "now",
        }

    except Exception as e:
        print(f"Dashboard API error: {e}")
        return {
            "total_companies": 0,
            "matched_companies": 0,
            "unmatched_companies": 0,
            "rollout_companies": 0,
            "rollout_quotas": 0,
            "service_areas": 0,
            "match_rate": 0.0,
            "database_status": "error",
            "last_updated": "error",
            "error": str(e),
        }


@router.get("/stats", response_class=HTMLResponse)
async def stats(request: Request, db: AsyncSession = Depends(get_db_session)):
    """Statistics page with real database data."""
    try:
        # Total companies
        total_companies_query = select(func.count()).select_from(Company)
        total_companies_result = await db.execute(total_companies_query)
        total_companies = total_companies_result.scalar() or 0

        # Companies with rollout names (matched) - using rollout_companies table
        matched_companies_query = (
            select(func.count(func.distinct(Company.id)))
            .select_from(Company)
            .join(RolloutCompany, Company.bdew_code == RolloutCompany.bdew_code)
        )
        matched_companies_result = await db.execute(matched_companies_query)
        matched_companies = matched_companies_result.scalar() or 0

        # Companies without rollout names (unmatched)
        unmatched_companies = total_companies - matched_companies

        # Rollout companies (new normalized structure)
        rollout_companies_query = select(func.count()).select_from(RolloutCompany)
        rollout_companies_result = await db.execute(rollout_companies_query)
        rollout_companies = rollout_companies_result.scalar() or 0

        # Rollout companies matched to BDEW companies
        matched_rollout_query = (
            select(func.count())
            .select_from(RolloutCompany)
            .where(RolloutCompany.bdew_code.is_not(None))
        )
        matched_rollout_result = await db.execute(matched_rollout_query)
        matched_rollout = matched_rollout_result.scalar() or 0

        # Rollout quotas (individual quota entries)
        rollout_quotas_query = select(func.count()).select_from(RolloutQuota)
        rollout_quotas_result = await db.execute(rollout_quotas_query)
        rollout_quotas = rollout_quotas_result.scalar() or 0

        stats_data = {
            "total_companies": f"{total_companies:,}",
            "matched_companies": f"{matched_companies:,}",
            "unmatched_companies": f"{unmatched_companies:,}",
            "manual_verification_needed": f"{matched_rollout:,}",
            "rollout_companies": f"{rollout_companies:,}",
            "rollout_quotas": f"{rollout_quotas:,}",
            "match_rate": (
                f"{(matched_companies / total_companies * 100):.1f}%"
                if total_companies > 0
                else "0.0%"
            ),
            "rollout_match_rate": (
                f"{(matched_rollout / rollout_companies * 100):.1f}%"
                if rollout_companies > 0
                else "0.0%"
            ),
        }

    except Exception as e:
        # Fallback to loading state if database error
        print(f"Database error in stats: {e}")
        stats_data = {
            "total_companies": "Error",
            "matched_companies": "Error",
            "unmatched_companies": "Error",
            "manual_verification_needed": "Error",
            "rollout_companies": "Error",
            "rollout_quotas": "Error",
            "match_rate": "Error",
            "rollout_match_rate": "Error",
        }

    return templates.TemplateResponse(
        "stats.html",
        {
            "request": request,
            "title": "Database Statistics",
            "active_page": "stats",
            "stats": stats_data,
        },
    )
