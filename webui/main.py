#!/usr/bin/env python3
"""
VNBdigitaler WebUI - FastAPI Admin Interface

A web-based administrative interface for managing the VNBdigitaler database
and company matching data.
"""

import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.config import get_settings
from webui.routers import companies, dashboard, rollout

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

# Initialize FastAPI app
app = FastAPI(
    title="VNBdigitaler Admin WebUI",
    description="Administrative interface for VNBdigitaler database management",
    version="1.0.0",
)

# Mount static files
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

# Initialize templates
templates_path = Path(__file__).parent / "templates"
templates_path.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=templates_path)

# Include routers
app.include_router(dashboard.router, prefix="", tags=["dashboard"])
app.include_router(companies.router, prefix="/companies", tags=["companies"])
app.include_router(rollout.router, prefix="/rollout", tags=["rollout"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint - redirect to dashboard."""
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "title": "VNBdigitaler Admin Dashboard",
            "active_page": "dashboard",
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "app": "VNBdigitaler WebUI",
        "database_configured": bool(settings.get_database_url()),
    }


if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("WEBUI_PORT", "8080"))
    host = os.getenv("WEBUI_HOST", "127.0.0.1")

    print(f"🚀 Starting VNBdigitaler WebUI on http://{host}:{port}")
    print("📊 Available endpoints:")
    print(f"  - Dashboard: http://{host}:{port}/")
    print(f"  - Companies: http://{host}:{port}/companies/")
    print(f"  - Roll-Out Data: http://{host}:{port}/rollout/")
    print(f"  - Health: http://{host}:{port}/health")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )
