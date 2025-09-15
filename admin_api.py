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
from fastapi import FastAPI, HTTPException, Request
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


@app.get("/api/companies", response_model=list[Company])
async def get_companies():
    """Get all companies with their code counts."""
    with (
        get_db_connection() as conn,
        conn.cursor(cursor_factory=RealDictCursor) as cursor,
    ):
        cursor.execute(
            """
                SELECT
                    company_name,
                    COUNT(*) as total_codes
                FROM vnb_digitaler.bdew_code_registry
                GROUP BY company_name
                ORDER BY company_name
            """
        )

        companies = []
        for row in cursor.fetchall():
            companies.append(
                Company(
                    company_name=clean_company_name(row["company_name"]),
                    total_codes=row["total_codes"],
                )
            )

        return companies


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


@app.get("/api/bdew-codes", response_model=list[BDEWCode])
async def get_bdew_codes():
    """Get all BDEW codes."""
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
                ORDER BY b.company_name, b.bdew_code
            """
        )

        codes = []
        for row in cursor.fetchall():
            codes.append(
                BDEWCode(
                    company_name=clean_company_name(row["company_name"]),
                    bdew_code=row["bdew_code"],
                    market_function=row["market_function"],
                    status=row["status"] or "active",
                )
            )

        return codes


@app.get("/api/market-functions", response_model=list[MarketFunction])
async def get_market_functions():
    """Get all market functions."""
    with (
        get_db_connection() as conn,
        conn.cursor(cursor_factory=RealDictCursor) as cursor,
    ):
        cursor.execute(
            """
                SELECT
                    name as function_name,
                    id::text as function_code,
                    description
                FROM vnb_digitaler.market_functions
                ORDER BY name
            """
        )

        functions = []
        for row in cursor.fetchall():
            functions.append(
                MarketFunction(
                    function_name=row["function_name"],
                    function_code=row["function_code"],
                    description=row["description"],
                )
            )

        return functions


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
