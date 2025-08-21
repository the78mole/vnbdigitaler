"""
Companies router for VNBdigitaler WebUI.
Handles company management, editing, and map visualization.
"""

import traceback
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db_session
from src.models import Company, RolloutCompany, RolloutQuota

# Initialize templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=templates_path)

router = APIRouter()


# Pydantic models for API requests
class CompanyUpdateRequest(BaseModel):
    rollout_report_name: str | None = None
    rollout_name_variations: list[str] | None = None
    manual_verification: bool | None = None


class CompanyFilterRequest(BaseModel):
    bdew_code: str | None = None
    name_filter: str | None = None
    manual_verification: bool | None = None
    has_rollout_name: bool | None = None


# Dependency to get database session is imported from src.database


@router.get("/", response_class=HTMLResponse)
async def companies_list(request: Request):
    """Main companies list page."""
    return templates.TemplateResponse(
        "companies_list.html",
        {
            "request": request,
            "title": "Companies Management",
            "active_page": "companies",
        },
    )


@router.get("/map", response_class=HTMLResponse)
async def companies_map(request: Request):
    """Companies map page showing Erlangen region."""
    return templates.TemplateResponse(
        "company_map.html",
        {
            "request": request,
            "title": "Companies Map",
            "active_page": "map",
        },
    )


@router.get("/map/{company_id}", response_class=HTMLResponse)
async def company_individual_map(request: Request, company_id: int):
    """Individual company map page (by database ID)."""
    return templates.TemplateResponse(
        "company_individual_map.html",
        {
            "request": request,
            "title": f"Company #{company_id} Map",
            "active_page": "companies",
            "company_id": company_id,
        },
    )


@router.get("/bdew/{bdew_code}/map", response_class=HTMLResponse)
async def company_map_by_bdew(
    request: Request,
    bdew_code: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Individual company map page (by BDEW code)."""
    try:
        # Get company by BDEW code
        query = select(Company.id, Company.bdew_name, Company.bdew_code).where(
            Company.bdew_code == bdew_code
        )
        result = await session.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(
                status_code=404, detail=f"Company with BDEW code {bdew_code} not found"
            )

        company_db_id, company_name, company_bdew = row

        return templates.TemplateResponse(
            "company_individual_map.html",
            {
                "request": request,
                "title": f"{company_name} (BDEW: {company_bdew}) - Map",
                "active_page": "companies",
                "company_id": company_db_id,
                "bdew_code": company_bdew,
                "company_name": company_name,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api", response_class=JSONResponse)
async def get_companies_api(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    name_filter: str | None = Query(None),
    manual_verification: bool | None = Query(None),
    has_rollout_name: bool | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    """API endpoint to get companies with pagination and filtering."""
    try:
        # Build base query with specific fields
        query = select(
            Company.id,
            Company.bdew_code,
            Company.bdew_name,
            Company.bdew_city,
            Company.rollout_report_name,
            Company.rollout_name_variations,
            Company.manual_verification,
            Company.network_territory_geojson,
        )

        # Apply filters
        if name_filter:
            query = query.where(Company.bdew_name.ilike(f"%{name_filter}%"))

        if manual_verification is not None:
            query = query.where(Company.manual_verification == manual_verification)

        if has_rollout_name is not None:
            if has_rollout_name:
                query = query.where(Company.rollout_report_name.is_not(None))
            else:
                query = query.where(Company.rollout_report_name.is_(None))

        # Add ordering and pagination
        query = query.order_by(Company.bdew_name)
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await session.execute(query)
        rows = result.fetchall()

        # Convert to list of dictionaries
        companies_data = []
        for row in rows:
            companies_data.append(
                {
                    "id": row.id,
                    "bdew_code": row.bdew_code,
                    "bdew_name": row.bdew_name,
                    "bdew_city": row.bdew_city,
                    "rollout_report_name": row.rollout_report_name,
                    "rollout_name_variations": row.rollout_name_variations or [],
                    "manual_verification": row.manual_verification or False,
                    "has_service_area": bool(row.network_territory_geojson),
                }
            )

        # Get total count for pagination
        count_query = select(Company.id)
        if name_filter:
            count_query = count_query.where(Company.bdew_name.ilike(f"%{name_filter}%"))
        if manual_verification is not None:
            count_query = count_query.where(
                Company.manual_verification == manual_verification
            )
        if has_rollout_name is not None:
            if has_rollout_name:
                count_query = count_query.where(
                    Company.rollout_report_name.is_not(None)
                )
            else:
                count_query = count_query.where(Company.rollout_report_name.is_(None))

        count_result = await session.execute(count_query)
        total_companies = len(count_result.fetchall())

        return {
            "companies": companies_data,
            "page": page,
            "page_size": page_size,
            "total": total_companies,
            "has_next": page * page_size < total_companies,
            "has_prev": page > 1,
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}")


@router.get("/edit/{company_id}", response_class=HTMLResponse)
async def edit_company(request: Request, company_id: int):
    """Company editing page."""
    return templates.TemplateResponse(
        "company_edit.html",
        {
            "request": request,
            "title": f"Edit Company #{company_id}",
            "active_page": "companies",
            "company_id": company_id,
        },
    )


@router.get("/api/{company_id}")
async def get_company_details(
    company_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    """Get detailed company information."""
    try:
        query = select(Company).where(Company.id == company_id)
        result = await session.execute(query)
        company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Get latest rollout quota if available via bdew_company_id relationship
        rollout_quota_info = None
        # Find the rollout company by bdew_company_id (direct FK relationship)
        rollout_query = select(RolloutCompany).where(
            RolloutCompany.bdew_company_id == company.id
        )
        rollout_result = await session.execute(rollout_query)
        rollout_company = rollout_result.scalar_one_or_none()

        if rollout_company:
            # Get the latest quota
            quota_query = (
                select(RolloutQuota)
                .where(RolloutQuota.rollout_company_id == rollout_company.id)
                .order_by(RolloutQuota.reference_date.desc())
                .limit(1)
            )
            quota_result = await session.execute(quota_query)
            latest_quota = quota_result.scalar_one_or_none()

            if latest_quota:
                rollout_quota_info = {
                    "quota": latest_quota.rollout_quota,
                    "reference_date": latest_quota.reference_date.isoformat(),
                    "quota_percentage": round(latest_quota.rollout_quota * 100, 1),
                    "rollout_company_id": rollout_company.id,
                    "bnetza_name": rollout_company.bnetza_name,
                }

        return {
            "id": company.id,
            "bdew_code": company.bdew_code,
            "bdew_name": company.bdew_name,
            "bdew_city": company.bdew_city,
            "bdew_name_normalized": company.bdew_name_normalized,
            "rollout_report_name": company.rollout_report_name,
            "rollout_name_variations": company.rollout_name_variations or [],
            "manual_verification": company.manual_verification or False,
            "name_matching_confidence": company.name_matching_confidence,
            "has_service_area": bool(company.network_territory_geojson),
            "rollout_quota": rollout_quota_info,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}")


@router.put("/api/{company_id}")
async def update_company(
    company_id: int,
    update_data: CompanyUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """Update company information."""
    try:
        # Check if company exists
        query = select(Company).where(Company.id == company_id)
        result = await session.execute(query)
        company = result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        # Build update data
        update_dict = {}
        if update_data.rollout_report_name is not None:
            update_dict["rollout_report_name"] = update_data.rollout_report_name
        if update_data.rollout_name_variations is not None:
            update_dict["rollout_name_variations"] = update_data.rollout_name_variations
        if update_data.manual_verification is not None:
            update_dict["manual_verification"] = update_data.manual_verification

        if update_dict:
            # Execute update
            stmt = update(Company).where(Company.id == company_id).values(**update_dict)
            await session.execute(stmt)
            await session.commit()

        return {
            "message": "Company updated successfully",
            "updated_fields": list(update_dict.keys()),
        }

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Update error: {e!s}")


@router.get("/api/{company_id}/geojson")
async def get_company_geojson(
    company_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    """Get company GeoJSON service area data."""
    try:
        query = select(
            Company.network_territory_geojson, Company.bdew_name, Company.bdew_city
        ).where(Company.id == company_id)
        result = await session.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(status_code=404, detail="Company not found")

        geojson_data, company_name, company_city = row

        if not geojson_data:
            return {
                "has_geojson": False,
                "message": "No GeoJSON data available for this company",
                "company_name": company_name,
                "company_city": company_city,
            }

        return {
            "has_geojson": True,
            "geojson": geojson_data,
            "company_name": company_name,
            "company_city": company_city,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GeoJSON error: {e!s}")


@router.get("/api/bdew/{bdew_code}/geojson")
async def get_company_geojson_by_bdew(
    bdew_code: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get company GeoJSON service area data by BDEW code."""
    try:
        query = select(
            Company.network_territory_geojson,
            Company.bdew_name,
            Company.bdew_city,
            Company.bdew_code,
        ).where(Company.bdew_code == bdew_code)
        result = await session.execute(query)
        row = result.first()

        if not row:
            raise HTTPException(
                status_code=404, detail=f"Company with BDEW code {bdew_code} not found"
            )

        geojson_data, company_name, company_city, company_bdew = row

        if not geojson_data:
            return {
                "has_geojson": False,
                "message": "No GeoJSON data available for this company",
                "company_name": company_name,
                "company_city": company_city,
                "bdew_code": company_bdew,
            }

        return {
            "has_geojson": True,
            "geojson": geojson_data,
            "company_name": company_name,
            "company_city": company_city,
            "bdew_code": company_bdew,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GeoJSON error: {e!s}")


@router.get("/dropdown", response_class=HTMLResponse)
async def company_dropdown(request: Request):
    """Company dropdown selection page."""
    return templates.TemplateResponse(
        "company_dropdown.html",
        {
            "request": request,
            "title": "Select Company",
            "active_page": "companies",
        },
    )


@router.get("/api-dropdown")
async def get_companies_dropdown(
    search: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
):
    """Get companies for dropdown selection."""
    try:
        query = select(
            Company.id, Company.bdew_code, Company.bdew_name, Company.bdew_city
        )

        if search:
            query = query.where(
                or_(
                    Company.bdew_name.ilike(f"%{search}%"),
                    Company.bdew_code.ilike(f"%{search}%"),
                )
            )

        query = query.order_by(Company.bdew_name).limit(100)

        result = await session.execute(query)
        companies = result.fetchall()

        companies_data = []
        for company in companies:
            display_name = f"{company.bdew_name}"
            if company.bdew_city:
                display_name += f" ({company.bdew_city})"
            display_name += f" [{company.bdew_code}]"

            companies_data.append(
                {
                    "id": company.id,
                    "bdew_code": company.bdew_code,
                    "display_name": display_name,
                }
            )

        return {"companies": companies_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}")


@router.get("/{company_id}", response_class=HTMLResponse)
async def company_detail(request: Request, company_id: int):
    """Company detail page with map if available."""
    return templates.TemplateResponse(
        "company_individual_map.html",
        {
            "request": request,
            "title": f"Company #{company_id} Details",
            "active_page": "companies",
            "company_id": company_id,
        },
    )


# Note: Administrative boundaries are now loaded directly in the frontend using overpass-frontend
# The /api/geodata/ endpoints have been removed to reduce backend complexity and improve performance
