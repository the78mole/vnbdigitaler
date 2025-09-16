#!/usr/bin/env python3
"""
BDEW VNB Digitaler Admin Interface
==================================

A FastAPI-based admin dashboard for BDEW VNB Digitaler data.
This version uses templates and static files for clean separation of concerns.

The application provides a web interface to manage BDEW code registry data
including companies, codes, and market functions.

Author: AI Assistant
"""

import logging
from typing import Any

import psycopg2
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BDEW VNB Digitaler Admin", version="2.0.0")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": "5432",
    "database": "vnb_digitaler",
    "user": "vnb_admin",
    "password": "vnb_secure_password_2024",  # pragma: allowlist secret
}


# Pydantic models
class DashboardStats(BaseModel):
    total_companies: int
    total_codes: int
    total_functions: int
    last_sync: str | None


class Company(BaseModel):
    company_name: str
    total_codes: int


class CompanyDetails(BaseModel):
    company_name: str
    total_codes: int
    status: str
    codes: list[dict[str, Any]]


class BDEWCode(BaseModel):
    company_name: str
    bdew_code: str
    market_function: str | None
    status: str


class MarketFunction(BaseModel):
    function_name: str
    function_code: str
    description: str | None


def get_db_connection():
    """Get database connection."""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")


def clean_company_name(name: str) -> str:
    """Remove surrounding quotes from company names."""
    MIN_QUOTE_LENGTH = 2
    if (
        name
        and len(name) >= MIN_QUOTE_LENGTH
        and (
            (name.startswith('"') and name.endswith('"'))
            or (name.startswith("'") and name.endswith("'"))
        )
    ):
        return name[1:-1].strip()
    return name.strip() if name else name


# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main admin dashboard page."""
    return templates.TemplateResponse("admin_dashboard.html", {"request": request})


@app.get("/test", response_class=HTMLResponse)
async def test_page():
    """Simple test page to verify everything works."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 p-8">
        <h1 class="text-3xl font-bold text-blue-600">Test Page</h1>
        <p class="mt-4">Wenn Sie das sehen, funktioniert die Anwendung grundsätzlich.</p>
        <a href="/admin_dashboard" class="mt-4 inline-block bg-blue-500 text-white px-4 py-2 rounded">
            Zum Admin Dashboard
        </a>
    </body>
    </html>
    """


@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get dashboard statistics."""
    with (
        get_db_connection() as conn,
        conn.cursor(cursor_factory=RealDictCursor) as cursor,
    ):
        # Get total companies
        cursor.execute(
            "SELECT COUNT(DISTINCT company_name) as total FROM vnb_digitaler.bdew_code_registry"
        )
        total_companies = cursor.fetchone()["total"]

        # Get total codes
        cursor.execute("SELECT COUNT(*) as total FROM vnb_digitaler.bdew_code_registry")
        total_codes = cursor.fetchone()["total"]

        # Get total functions
        cursor.execute("SELECT COUNT(*) as total FROM vnb_digitaler.market_functions")
        total_functions = cursor.fetchone()["total"]

        return DashboardStats(
            total_companies=total_companies,
            total_codes=total_codes,
            total_functions=total_functions,
            last_sync="Heute",
        )


@app.get("/api/companies")
async def get_companies(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(25, ge=1, le=1000, description="Page size"),
    search: str = Query("", description="Search term for company name"),
):
    """Get companies with DataTables-compatible pagination and filtering."""
    offset = (page - 1) * limit

    # Build WHERE clause for filtering
    where_conditions = []
    params = []

    if search.strip():
        where_conditions.append("LOWER(company_name) LIKE LOWER(%s)")
        params.append(f"%{search}%")

    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    with (
        get_db_connection() as conn,
        conn.cursor(cursor_factory=RealDictCursor) as cursor,
    ):
        # Get total count
        count_query = f"""
            SELECT COUNT(DISTINCT company_name) as total
            FROM vnb_digitaler.bdew_code_registry
            {where_clause}
        """
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()["total"]

        # Get paginated results
        query = f"""
            SELECT
                company_name as name,
                company_name as short_name,
                '' as postal_code,
                '' as city,
                COUNT(*) as code_count,
                MIN(bdew_code) as id
            FROM vnb_digitaler.bdew_code_registry
            {where_clause}
            GROUP BY company_name
            ORDER BY company_name
            LIMIT %s OFFSET %s
        """

        cursor.execute(query, [*params, limit, offset])

        items = []
        for row in cursor.fetchall():
            items.append(
                {
                    "id": str(row["id"]),
                    "name": clean_company_name(row["name"]),
                    "short_name": (
                        clean_company_name(row["short_name"])[:50]
                        if row["short_name"]
                        else ""
                    ),
                    "postal_code": row["postal_code"],
                    "city": row["city"],
                    "code_count": row["code_count"],
                }
            )

        return {
            "items": items,
            "total": total_count,
            "page": page,
            "limit": limit,
            "pages": (total_count + limit - 1) // limit,
        }


@app.get("/api/companies/{company_name}")
async def get_company_details(company_name: str):
    """Get detailed information about a specific company."""
    with (
        get_db_connection() as conn,
        conn.cursor(cursor_factory=RealDictCursor) as cursor,
    ):
        cursor.execute(
            """
                SELECT
                    b.company_name,
                    b.bdew_code,
                    m.name as market_function,
                    b.status
                FROM vnb_digitaler.bdew_code_registry b
                LEFT JOIN vnb_digitaler.market_functions m ON b.market_function_id = m.id
                WHERE b.company_name = %s
                ORDER BY b.bdew_code
            """,
            (company_name,),
        )

        codes = []
        company_name_clean = None

        for row in cursor.fetchall():
            if company_name_clean is None:
                company_name_clean = clean_company_name(row["company_name"])

            codes.append(
                {
                    "bdew_code": row["bdew_code"],
                    "market_function": row["market_function"],
                    "status": row["status"] or "active",
                }
            )

        if not codes:
            raise HTTPException(status_code=404, detail="Company not found")

        return CompanyDetails(
            company_name=company_name_clean,
            total_codes=len(codes),
            status="active",
            codes=codes,
        )


@app.get("/api/bdew-codes")
async def get_bdew_codes(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(25, ge=1, le=1000, description="Page size"),
    search: str = Query("", description="Search term for company name or BDEW code"),
    order_by: str = Query("code", description="Order by field"),
    order_dir: str = Query("asc", description="Order direction"),
):
    """Get BDEW codes with DataTables-compatible pagination and filtering."""
    offset = (page - 1) * limit

    # Build WHERE clause for filtering
    where_conditions = []
    params = []

    if search.strip():
        where_conditions.append(
            "(LOWER(b.company_name) LIKE LOWER(%s) OR b.bdew_code LIKE %s)"
        )
        search_param = f"%{search}%"
        params.extend([search_param, search_param])

    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    # Map frontend column names to database columns
    order_map = {
        "code": "b.bdew_code",
        "name": "b.company_name",
        "short_name": "b.company_name",
        "market_function_name": "m.name",
    }

    order_column = order_map.get(order_by, "b.bdew_code")
    order_direction = "DESC" if order_dir.lower() == "desc" else "ASC"

    with (
        get_db_connection() as conn,
        conn.cursor(cursor_factory=RealDictCursor) as cursor,
    ):
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM vnb_digitaler.bdew_code_registry b
            LEFT JOIN vnb_digitaler.market_functions m
                ON b.market_function_id = m.id
            {where_clause}
        """
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()["total"]

        # Get paginated results with proper JOIN
        query = f"""
            SELECT
                b.bdew_code as code,
                b.company_name as name,
                b.company_name as short_name,
                '' as postal_code,
                '' as city,
                COALESCE(m.name, '') as market_function_name,
                COALESCE(b.status, 'ACTIVE') as status
            FROM vnb_digitaler.bdew_code_registry b
            LEFT JOIN vnb_digitaler.market_functions m
                ON b.market_function_id = m.id
            {where_clause}
            ORDER BY {order_column} {order_direction}
            LIMIT %s OFFSET %s
        """

        cursor.execute(query, [*params, limit, offset])

        items = []
        for row in cursor.fetchall():
            items.append(
                {
                    "code": row["code"],
                    "name": clean_company_name(row["name"]),
                    "short_name": (
                        clean_company_name(row["short_name"])[:50]
                        if row["short_name"]
                        else ""
                    ),
                    "postal_code": row["postal_code"],
                    "city": row["city"],
                    "market_function_name": row["market_function_name"],
                    "status": row["status"],
                }
            )

        return {
            "items": items,
            "total": total_count,
            "page": page,
            "limit": limit,
            "pages": (total_count + limit - 1) // limit,
        }


@app.get("/api/market-functions")
async def get_market_functions():
    """Get available market functions for filtering."""
    # For now, return a simple static list
    # This can be enhanced later with database queries
    return [
        {"value": "", "label": "Alle Marktfunktionen"},
        {"value": "lieferant", "label": "Lieferant"},
        {"value": "netzbetreiber", "label": "Netzbetreiber"},
        {"value": "messstellenbetreiber", "label": "Messstellenbetreiber"},
        {"value": "marktpartner", "label": "Marktpartner"},
    ]


@app.get("/api/functions")
async def get_functions(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(25, ge=1, le=1000, description="Page size"),
    search: str = Query("", description="Search term for function name"),
):
    """Get market functions with DataTables-compatible pagination and filtering."""
    offset = (page - 1) * limit

    # Build WHERE clause for filtering
    where_conditions = []
    params = []

    if search.strip():
        where_conditions.append("LOWER(name) LIKE LOWER(%s)")
        params.append(f"%{search}%")

    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)

    with (
        get_db_connection() as conn,
        conn.cursor(cursor_factory=RealDictCursor) as cursor,
    ):
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM vnb_digitaler.market_functions
            {where_clause}
        """
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()["total"]

        # Get paginated results
        query = f"""
            SELECT
                id as code,
                name,
                COALESCE(description, '') as description,
                TRUE as is_active,
                created_at
            FROM vnb_digitaler.market_functions
            {where_clause}
            ORDER BY name
            LIMIT %s OFFSET %s
        """

        cursor.execute(query, [*params, limit, offset])

        items = []
        for row in cursor.fetchall():
            items.append(
                {
                    "code": str(row["code"]),
                    "name": row["name"],
                    "description": row["description"],
                    "is_active": row["is_active"],
                    "created_at": (
                        row["created_at"].isoformat() if row["created_at"] else None
                    ),
                }
            )

        return {
            "items": items,
            "total": total_count,
            "page": page,
            "limit": limit,
            "pages": (total_count + limit - 1) // limit,
        }


@app.get("/api/debug/db-structure")
async def debug_db_structure():
    """Debug endpoint to check database structure."""
    with (
        get_db_connection() as conn,
        conn.cursor(cursor_factory=RealDictCursor) as cursor,
    ):
        # Check bdew_code_registry structure
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'vnb_digitaler'
            AND table_name = 'bdew_code_registry'
            ORDER BY ordinal_position
        """
        )
        bdew_columns = cursor.fetchall()

        # Check if market_functions table exists
        cursor.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'vnb_digitaler'
            AND table_name = 'market_functions'
            ORDER BY ordinal_position
        """
        )
        market_columns = cursor.fetchall()

        # Sample data with market_function_id
        cursor.execute(
            """
            SELECT company_name, bdew_code, market_function_id, status
            FROM vnb_digitaler.bdew_code_registry
            LIMIT 5
        """
        )
        sample_data = cursor.fetchall()

        return {
            "bdew_code_registry_columns": [dict(row) for row in bdew_columns],
            "market_functions_columns": [dict(row) for row in market_columns],
            "sample_data": [dict(row) for row in sample_data],
        }


# Companies API endpoints


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
