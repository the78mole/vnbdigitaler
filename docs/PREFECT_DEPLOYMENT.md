# 🚀 VNB Digitaler - Prefect Deployment

> **📋 Hauptspezifikation**: [SPECIFICATION.md](../SPECIFICATION.md) - Gesamtarchitektur
> **🔄 Flow-Implementierungen**: [PREFECT_FLOWS.md](./PREFECT_FLOWS.md) - Code-Beispiele
> **🔧 Integration**: [PREFECT_INTEGRATION.md](./PREFECT_INTEGRATION.md) - Pipeline-Adapter

## 📋 Inhaltsverzeichnis

1. [Deployment-Konfigurationen](#deployment-konfigurationen)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Secrets & Environment Management](#secrets--environment-management)
4. [Scheduling & Automation](#scheduling--automation)
5. [Production Monitoring](#production-monitoring)

---

## Deployment-Konfigurationen

### Prefect Deployment YAML

```yaml
# deployments/bdew_import_deployment.yaml
name: "BDEW Company Import - Production"
version: "1.0.0"
description: "Täglicher Import von BDEW Energiemarktakteur-Daten"

# Flow Configuration
flow_name: "BDEW Company Data Import"
entrypoint: "src/prefect_flows/flows/bdew/company_import.py:bdew_company_import_flow"

# Infrastructure
work_pool:
  name: "vnb-digitaler-pool"
  work_queue_name: "data-import"

# Runtime Parameters
parameters:
  incremental: true
  dry_run: false

# Scheduling
schedule:
  cron: "0 6 * * *" # Täglich um 6:00 UTC
  timezone: "Europe/Berlin"

# Resource Limits
infrastructure:
  type: "docker-container"
  env:
    PYTHONPATH: "/app"
    LOG_LEVEL: "INFO"
  labels:
    environment: "production"
    team: "data-engineering"
    priority: "high"

---
# deployments/bnetza_rollout_deployment.yaml
name: "BNetzA Rollout Import - Quarterly"
version: "1.0.0"
description: "Quartalsweiser Import von Smart Meter Rollout-Daten"

flow_name: "BNetzA Smart Meter Rollout Import"
entrypoint: "src/prefect_flows/flows/bnetza/rollout_import.py:bnetza_rollout_import_flow"

work_pool:
  name: "vnb-digitaler-pool"
  work_queue_name: "quarterly-import"

# Quartalsweise Ausführung
schedule:
  cron: "0 8 1 1,4,7,10 *" # 1. Tag jedes Quartals um 8:00 UTC
  timezone: "Europe/Berlin"

parameters:
  quarter: null # Auto-detect latest
  force_download: false

infrastructure:
  type: "docker-container"
  env:
    PYTHONPATH: "/app"
    LOG_LEVEL: "INFO"
  labels:
    environment: "production"
    team: "data-engineering"
    priority: "medium"

---
# deployments/vnb_pricing_deployment.yaml
name: "VNB Price Sheet Processing - Weekly"
version: "1.0.0"
description: "Wöchentliche Verarbeitung von VNB-Preisblättern"

flow_name: "VNB Price Sheet Processing"
entrypoint: "src/prefect_flows/flows/pricing/vnb_price_sheets.py:vnb_price_sheet_flow"

work_pool:
  name: "vnb-digitaler-pool"
  work_queue_name: "price-processing"

# Wöchentlich am Montag
schedule:
  cron: "0 7 * * 1" # Montags um 7:00 UTC
  timezone: "Europe/Berlin"

parameters:
  vnb_codes: null # Alle VNB
  year: null # Aktuelles Jahr
  parallel_limit: 5

infrastructure:
  type: "docker-container"
  env:
    PYTHONPATH: "/app"
    LOG_LEVEL: "INFO"
    PDF_PROCESSING_TIMEOUT: "300"
  labels:
    environment: "production"
    team: "data-engineering"
    priority: "medium"
    resource_intensive: "true"
```

### Docker Infrastructure

```yaml
# infrastructure/docker-compose.prefect.yml
version: "3.8"

services:
  prefect-server:
    image: prefecthq/prefect:2.19.x-python3.11
    restart: unless-stopped
    volumes:
      - prefect:/root/.prefect
    environment:
      - PREFECT_SERVER_API_HOST=0.0.0.0
      - PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://prefect:${PREFECT_DB_PASSWORD}@postgres:5432/prefect
      - PREFECT_SERVER_ANALYTICS_ENABLED=false
    ports:
      - "4200:4200"
    depends_on:
      - postgres
    command: prefect server start
    networks:
      - vnb-network

  prefect-worker:
    image: vnb-digitaler/prefect-worker:latest
    restart: unless-stopped
    volumes:
      - ./src:/app/src
      - ./data:/app/data
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - PREFECT_API_URL=http://prefect-server:4200/api
      - PREFECT_WORKER_HEARTBEAT_SECONDS=30
      - PYTHONPATH=/app
    env_file:
      - .env.production
    depends_on:
      - prefect-server
    command: prefect worker start --pool vnb-digitaler-pool
    networks:
      - vnb-network

  postgres:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      - POSTGRES_USER=prefect
      - POSTGRES_PASSWORD=${PREFECT_DB_PASSWORD}
      - POSTGRES_DB=prefect
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - vnb-network

volumes:
  prefect:
  postgres_data:

networks:
  vnb-network:
    external: true
```

### Prefect Worker Dockerfile

```dockerfile
# infrastructure/Dockerfile.prefect
FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install UV for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# App setup
WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-cache

# Copy application code
COPY src/ src/
COPY migrations/ migrations/

# Create non-root user
RUN useradd --create-home --shell /bin/bash prefect
USER prefect

# Environment
ENV PYTHONPATH=/app
ENV PREFECT_LOGGING_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["uv", "run"]
```

---

## Infrastructure Setup

### Terraform Configuration

```hcl
# infrastructure/terraform/prefect.tf
resource "docker_network" "vnb_network" {
  name = "vnb-network"
}

resource "docker_volume" "prefect_data" {
  name = "prefect-data"
}

resource "docker_volume" "postgres_data" {
  name = "postgres-data"
}

# Prefect Server
resource "docker_container" "prefect_server" {
  name  = "vnb-prefect-server"
  image = "prefecthq/prefect:2.19.x-python3.11"

  restart = "unless-stopped"

  ports {
    internal = 4200
    external = 4200
  }

  volumes {
    volume_name    = docker_volume.prefect_data.name
    container_path = "/root/.prefect"
  }

  env = [
    "PREFECT_SERVER_API_HOST=0.0.0.0",
    "PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://prefect:${var.prefect_db_password}@vnb-postgres:5432/prefect",
    "PREFECT_SERVER_ANALYTICS_ENABLED=false"
  ]

  command = ["prefect", "server", "start"]

  networks_advanced {
    name = docker_network.vnb_network.name
  }

  depends_on = [docker_container.postgres]
}

# Prefect Worker
resource "docker_container" "prefect_worker" {
  name  = "vnb-prefect-worker"
  image = "vnb-digitaler/prefect-worker:latest"

  restart = "unless-stopped"

  volumes {
    host_path      = "/var/run/docker.sock"
    container_path = "/var/run/docker.sock"
  }

  volumes {
    host_path      = "${path.cwd}/src"
    container_path = "/app/src"
  }

  env = [
    "PREFECT_API_URL=http://vnb-prefect-server:4200/api",
    "PYTHONPATH=/app",
    "PREFECT_WORKER_HEARTBEAT_SECONDS=30"
  ]

  command = ["prefect", "worker", "start", "--pool", "vnb-digitaler-pool"]

  networks_advanced {
    name = docker_network.vnb_network.name
  }

  depends_on = [docker_container.prefect_server]
}

# Database for Prefect
resource "docker_container" "postgres" {
  name  = "vnb-postgres"
  image = "postgres:15-alpine"

  restart = "unless-stopped"

  volumes {
    volume_name    = docker_volume.postgres_data.name
    container_path = "/var/lib/postgresql/data"
  }

  env = [
    "POSTGRES_USER=prefect",
    "POSTGRES_PASSWORD=${var.prefect_db_password}",
    "POSTGRES_DB=prefect"
  ]

  networks_advanced {
    name = docker_network.vnb_network.name
  }
}

# Variables
variable "prefect_db_password" {
  description = "Password for Prefect PostgreSQL database"
  type        = string
  sensitive   = true
}

# Outputs
output "prefect_server_url" {
  value = "http://localhost:4200"
}
```

### Setup Scripts

```bash
#!/bin/bash
# scripts/setup_prefect.sh

set -e

echo "🚀 Setting up Prefect infrastructure for VNB Digitaler..."

# 1. Environment check
if [[ ! -f .env.production ]]; then
    echo "❌ .env.production file not found"
    exit 1
fi

source .env.production

# 2. Build Prefect Worker image
echo "📦 Building Prefect Worker image..."
docker build -f infrastructure/Dockerfile.prefect -t vnb-digitaler/prefect-worker:latest .

# 3. Start infrastructure
echo "🏗️ Starting Prefect infrastructure..."
docker-compose -f infrastructure/docker-compose.prefect.yml up -d

# 4. Wait for Prefect server to be ready
echo "⏳ Waiting for Prefect server..."
until curl -s http://localhost:4200/api/health > /dev/null; do
    echo "  Waiting for Prefect server..."
    sleep 5
done

# 5. Create work pool
echo "👷 Creating work pool..."
uv run prefect work-pool create vnb-digitaler-pool \
    --type docker-container \
    --base-job-template '{
        "job_configuration": {
            "image": "vnb-digitaler/prefect-worker:latest",
            "env": {
                "PYTHONPATH": "/app"
            },
            "labels": {
                "project": "vnb-digitaler"
            }
        }
    }'

# 6. Deploy flows
echo "🔄 Deploying flows..."
uv run prefect deploy deployments/bdew_import_deployment.yaml
uv run prefect deploy deployments/bnetza_rollout_deployment.yaml
uv run prefect deploy deployments/vnb_pricing_deployment.yaml

# 7. Setup monitoring
echo "📊 Setting up monitoring..."
./scripts/setup_prefect_monitoring.sh

echo "✅ Prefect setup completed!"
echo "🌐 Prefect UI: http://localhost:4200"
echo "📋 Check deployment status: prefect deployment ls"
```

```bash
#!/bin/bash
# scripts/setup_prefect_monitoring.sh

echo "📊 Setting up Prefect monitoring..."

# 1. Create monitoring deployment
cat > deployments/monitoring_deployment.yaml << EOF
name: "VNB Digitaler - Health Monitoring"
version: "1.0.0"
description: "Überwachung der VNB Digitaler Data Pipeline"

flow_name: "System Health Monitor"
entrypoint: "src/prefect_flows/monitoring/health_monitor.py:system_health_flow"

work_pool:
  name: "vnb-digitaler-pool"
  work_queue_name: "monitoring"

schedule:
  cron: "*/15 * * * *"  # Alle 15 Minuten
  timezone: "Europe/Berlin"

parameters:
  check_database: true
  check_external_apis: true
  create_alerts: true

infrastructure:
  type: "docker-container"
  env:
    PYTHONPATH: "/app"
    LOG_LEVEL: "INFO"
  labels:
    environment: "production"
    team: "monitoring"
    priority: "critical"
EOF

# 2. Deploy monitoring flow
uv run prefect deploy deployments/monitoring_deployment.yaml

# 3. Setup alerting (Webhook zu Slack/Teams)
uv run prefect block register-module prefect_slack
uv run prefect block register-module prefect_webhooks

echo "✅ Monitoring setup completed!"
```

---

## Secrets & Environment Management

### Prefect Blocks für Secrets

```python
# scripts/setup_secrets.py
"""Setup Prefect Blocks für Secrets Management."""

import asyncio
from prefect.blocks.system import Secret
from prefect.blocks.notifications import SlackWebhook

async def setup_production_secrets():
    """Erstelle Prefect Secret Blocks für Production."""

    # BDEW API Credentials
    bdew_api_secret = Secret(value="your-bdew-api-key")
    await bdew_api_secret.save("bdew-api-key")

    # Database Connection
    db_connection_secret = Secret(
        value="postgresql+asyncpg://user:password@localhost:5432/vnb_digitaler" # pragma: allowlist secret
    )
    await db_connection_secret.save("database-url")

    # Cloudflare R2 Credentials
    r2_access_key = Secret(value="your-r2-access-key")
    await r2_access_key.save("r2-access-key")

    r2_secret_key = Secret(value="your-r2-secret-key")
    await r2_secret_key.save("r2-secret-key")

    # Slack Webhook für Alerts
    slack_webhook = SlackWebhook(
        url="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
    )
    await slack_webhook.save("slack-alerts")

    print("✅ All secrets configured!")

if __name__ == "__main__":
    asyncio.run(setup_production_secrets())
```

### Environment-spezifische Konfiguration

```python
# src/prefect_flows/config/settings.py
from pydantic import BaseSettings
from typing import Optional

class PrefectSettings(BaseSettings):
    """Environment-spezifische Prefect Konfiguration."""

    # Prefect Server
    prefect_api_url: str = "http://localhost:4200/api"
    prefect_work_pool: str = "vnb-digitaler-pool"

    # Database
    database_url_secret: str = "database-url"

    # External APIs
    bdew_api_key_secret: str = "bdew-api-key"
    bdew_api_base_url: str = "https://api.bdew.de/v1"

    # Storage
    r2_access_key_secret: str = "r2-access-key"
    r2_secret_key_secret: str = "r2-secret-key"
    r2_bucket_name: str = "vnb-digitaler-documents"

    # Monitoring
    slack_webhook_secret: str = "slack-alerts"
    monitoring_enabled: bool = True

    # Performance
    max_concurrent_flows: int = 5
    task_timeout_seconds: int = 1800

    # Development overrides
    enable_debug_logging: bool = False
    dry_run_mode: bool = False

    class Config:
        env_prefix = "VNB_"
        env_file = ".env"

# Global settings instance
settings = PrefectSettings()
```

### Environment Files

```env
# .env.production
VNB_PREFECT_API_URL=http://prefect-server:4200/api
VNB_PREFECT_WORK_POOL=vnb-digitaler-pool

# Database
VNB_DATABASE_URL_SECRET=database-url

# External APIs
VNB_BDEW_API_KEY_SECRET=bdew-api-key
VNB_BDEW_API_BASE_URL=https://api.bdew.de/v1

# Storage
VNB_R2_ACCESS_KEY_SECRET=r2-access-key
VNB_R2_SECRET_KEY_SECRET=r2-secret-key
VNB_R2_BUCKET_NAME=vnb-digitaler-prod

# Monitoring
VNB_SLACK_WEBHOOK_SECRET=slack-alerts
VNB_MONITORING_ENABLED=true

# Performance
VNB_MAX_CONCURRENT_FLOWS=3
VNB_TASK_TIMEOUT_SECONDS=3600

# Production flags
VNB_ENABLE_DEBUG_LOGGING=false
VNB_DRY_RUN_MODE=false

# Infrastructure
PREFECT_DB_PASSWORD=your-secure-password
```

```env
# .env.development
VNB_PREFECT_API_URL=http://localhost:4200/api
VNB_PREFECT_WORK_POOL=vnb-digitaler-dev

# Development database
VNB_DATABASE_URL_SECRET=dev-database-url

# Mock APIs in development
VNB_BDEW_API_KEY_SECRET=dev-bdew-api-key
VNB_BDEW_API_BASE_URL=http://localhost:8001/mock/bdew

# Development storage
VNB_R2_BUCKET_NAME=vnb-digitaler-dev

# Development settings
VNB_MONITORING_ENABLED=false
VNB_ENABLE_DEBUG_LOGGING=true
VNB_DRY_RUN_MODE=true
VNB_MAX_CONCURRENT_FLOWS=2
```

---

## Scheduling & Automation

### Advanced Scheduling Patterns

```python
# src/prefect_flows/scheduling/advanced_schedules.py
from prefect.schedules import CronSchedule, IntervalSchedule
from prefect.automations import EventTrigger, Automation
from datetime import timedelta

# Business Hours Schedule (nur Werktage, 6-18 Uhr)
BUSINESS_HOURS_SCHEDULE = CronSchedule(
    cron="0 6-18/4 * * 1-5",  # Alle 4 Stunden von 6-18 Uhr, Mo-Fr
    timezone="Europe/Berlin"
)

# Quarter-End Processing (letzter Tag des Quartals)
QUARTER_END_SCHEDULE = CronSchedule(
    cron="0 20 31 3,6,9,12 *",  # 20:00 am letzten Tag des Quartals
    timezone="Europe/Berlin"
)

# Adaptive Schedule basierend auf Data Source Freshness
class AdaptiveDataSchedule:
    """Dynamische Scheduling basierend auf Datenquelle-Updates."""

    @staticmethod
    async def get_bdew_schedule() -> CronSchedule:
        """Bestimme BDEW Schedule basierend auf historischen Updates."""
        from ...database import get_async_session

        async with get_async_session() as session:
            # Analysiere historische Update-Patterns
            update_pattern = await analyze_bdew_update_pattern(session)

            if update_pattern["frequency"] == "daily":
                return CronSchedule(cron="0 6 * * *")  # Täglich 6:00
            elif update_pattern["frequency"] == "weekly":
                return CronSchedule(cron="0 6 * * 1")  # Montags 6:00
            else:
                return CronSchedule(cron="0 6 1 * *")  # Monatlich 1. Tag 6:00

# Event-driven Automation
async def setup_flow_automations():
    """Erstelle Event-basierte Automatisierungen."""

    # 1. Auto-retry bei API Failures
    api_failure_automation = Automation(
        name="Auto-retry on API Failure",
        trigger=EventTrigger(
            expect=["prefect.flow-run.Failed"],
            match={
                "prefect.tags": ["api-dependent"],
                "prefect.flow-run.message": "*API*"
            }
        ),
        actions=[
            {
                "type": "run-deployment",
                "deployment_id": "{{ event.related[0].deployment.id }}",
                "parameters": {"retry_mode": True}
            }
        ]
    )

    # 2. Downstream trigger bei erfolgreichem BDEW Import
    bdew_success_automation = Automation(
        name="Trigger Rollout Matching on BDEW Success",
        trigger=EventTrigger(
            expect=["prefect.flow-run.Completed"],
            match={
                "prefect.flow-run.name": "*BDEW*"
            }
        ),
        actions=[
            {
                "type": "run-deployment",
                "deployment_id": "bnetza-rollout-matching-deployment-id"
            }
        ]
    )

    # 3. Alert bei kritischen Fehlern
    critical_failure_automation = Automation(
        name="Alert on Critical Failure",
        trigger=EventTrigger(
            expect=["prefect.flow-run.Failed"],
            match={
                "prefect.tags": ["critical"],
                "prefect.flow-run.total-run-time": "> 3600"  # > 1 Stunde
            }
        ),
        actions=[
            {
                "type": "send-notification",
                "block_document_id": "slack-alerts-block-id",
                "message": "🚨 Critical flow failure: {{ event.resource.name }}"
            }
        ]
    )
```

### Conditional Flow Execution

```python
# src/prefect_flows/scheduling/conditional_flows.py
from prefect import flow, get_run_logger
from prefect.concurrency import concurrency

@flow(name="Smart Data Pipeline Orchestrator")
async def smart_orchestrator_flow() -> dict[str, Any]:
    """
    Intelligenter Orchestrator der Flows basierend auf Datenaktualität ausführt.
    """
    logger = get_run_logger()
    execution_plan = {}

    # 1. Prüfe Datenaktualität aller Quellen
    data_freshness = await check_all_data_freshness_task()

    # 2. Entscheide welche Flows ausgeführt werden müssen
    flows_to_run = []

    if data_freshness["bdew"]["needs_update"]:
        flows_to_run.append("bdew_import")
        logger.info("BDEW data is stale, scheduling import")

    if data_freshness["bnetza"]["needs_update"]:
        flows_to_run.append("bnetza_rollout")
        logger.info("BNetzA data is stale, scheduling import")

    if data_freshness["vnb_pricing"]["needs_update"]:
        flows_to_run.append("vnb_pricing")
        logger.info("VNB pricing data is stale, scheduling update")

    # 3. Parallele Ausführung mit Concurrency Control
    async with concurrency("data-pipeline", 2):  # Max 2 parallele Flows
        results = {}

        if "bdew_import" in flows_to_run:
            results["bdew"] = await bdew_company_import_flow()

        if "bnetza_rollout" in flows_to_run:
            results["bnetza"] = await bnetza_rollout_import_flow()

        if "vnb_pricing" in flows_to_run:
            results["vnb_pricing"] = await vnb_price_sheet_flow()

    # 4. Downstream Processing bei Erfolg
    successful_flows = [
        flow_name for flow_name, result in results.items()
        if result.get("status") == "success"
    ]

    if successful_flows:
        # Trigger Data Quality Checks
        quality_result = await run_data_quality_checks_task(successful_flows)
        execution_plan["quality_checks"] = quality_result

        # Update Analytics wenn alle kritischen Flows erfolgreich
        if "bdew" in successful_flows and "bnetza" in successful_flows:
            analytics_result = await update_analytics_views_task()
            execution_plan["analytics_update"] = analytics_result

    return {
        "executed_flows": flows_to_run,
        "results": results,
        "execution_plan": execution_plan,
        "next_run_needed": any(not result.get("status") == "success"
                              for result in results.values())
    }
```

---

## Production Monitoring

### Health Monitoring Flow

```python
# src/prefect_flows/monitoring/health_monitor.py
from prefect import flow, task, get_run_logger
from prefect.blocks.notifications import SlackWebhook
from prefect.artifacts import create_markdown_artifact

@flow(name="System Health Monitor")
async def system_health_flow(
    check_database: bool = True,
    check_external_apis: bool = True,
    create_alerts: bool = True
) -> dict[str, Any]:
    """
    Umfassende Gesundheitsprüfung des VNB Digitaler Systems.
    """
    logger = get_run_logger()
    health_status = {"overall": "healthy", "checks": {}}

    # 1. Database Health
    if check_database:
        db_health = await check_database_health_task()
        health_status["checks"]["database"] = db_health

        if not db_health["healthy"]:
            health_status["overall"] = "degraded"

    # 2. External API Health
    if check_external_apis:
        api_health = await check_external_apis_health_task()
        health_status["checks"]["external_apis"] = api_health

        if api_health["failed_apis"]:
            health_status["overall"] = "degraded"

    # 3. Data Freshness Check
    freshness_check = await check_data_freshness_health_task()
    health_status["checks"]["data_freshness"] = freshness_check

    if freshness_check["stale_sources"]:
        health_status["overall"] = "warning"

    # 4. System Resource Check
    resource_check = await check_system_resources_task()
    health_status["checks"]["resources"] = resource_check

    if resource_check["critical_resources"]:
        health_status["overall"] = "critical"

    # 5. Create Health Report Artifact
    await create_health_report_artifact(health_status)

    # 6. Send Alerts wenn nötig
    if create_alerts and health_status["overall"] in ["critical", "degraded"]:
        await send_health_alert_task(health_status)

    return health_status

@task(name="Check Database Health")
async def check_database_health_task() -> dict[str, Any]:
    """Prüfe Database Connectivity und Performance."""
    from ...database import get_async_session
    from sqlalchemy import text
    import time

    try:
        start_time = time.time()

        async with get_async_session() as session:
            # Connection Test
            await session.execute(text("SELECT 1"))

            # Performance Test
            await session.execute(text("""
                SELECT COUNT(*) FROM bdew_companies
                WHERE updated_at > NOW() - INTERVAL '24 hours'
            """))

        response_time = time.time() - start_time

        return {
            "healthy": True,
            "response_time_ms": round(response_time * 1000, 2),
            "status": "ok"
        }

    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "status": "failed"
        }

@task(name="Check External APIs Health")
async def check_external_apis_health_task() -> dict[str, Any]:
    """Prüfe Verfügbarkeit externer APIs."""
    import aiohttp

    apis_to_check = [
        {"name": "BDEW API", "url": "https://api.bdew.de/health"},
        {"name": "BNetzA Portal", "url": "https://www.bundesnetzagentur.de"},
    ]

    api_status = {}
    failed_apis = []

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        for api in apis_to_check:
            try:
                async with session.get(api["url"]) as response:
                    api_status[api["name"]] = {
                        "status_code": response.status,
                        "healthy": response.status < 400,
                        "response_time": response.headers.get("X-Response-Time", "unknown")
                    }

                    if response.status >= 400:
                        failed_apis.append(api["name"])

            except Exception as e:
                api_status[api["name"]] = {
                    "healthy": False,
                    "error": str(e)
                }
                failed_apis.append(api["name"])

    return {
        "api_status": api_status,
        "failed_apis": failed_apis,
        "overall_healthy": len(failed_apis) == 0
    }

async def create_health_report_artifact(health_status: dict[str, Any]):
    """Erstelle detaillierten Gesundheitsreport."""

    status_emoji = {
        "healthy": "✅",
        "warning": "⚠️",
        "degraded": "🟡",
        "critical": "🔴"
    }

    report_markdown = f"""
# VNB Digitaler - System Health Report

## Overall Status: {status_emoji[health_status["overall"]]} {health_status["overall"].upper()}

### Database Health
- **Status**: {status_emoji.get(health_status["checks"]["database"]["status"], "❓")}
- **Response Time**: {health_status["checks"]["database"].get("response_time_ms", "N/A")}ms

### External APIs
- **BDEW API**: {status_emoji.get("healthy" if health_status["checks"]["external_apis"]["api_status"].get("BDEW API", {}).get("healthy") else "failed", "❓")}
- **BNetzA Portal**: {status_emoji.get("healthy" if health_status["checks"]["external_apis"]["api_status"].get("BNetzA Portal", {}).get("healthy") else "failed", "❓")}

### Data Freshness
- **Stale Sources**: {len(health_status["checks"]["data_freshness"]["stale_sources"])}
- **Last BDEW Update**: {health_status["checks"]["data_freshness"].get("bdew_last_update", "Unknown")}
- **Last BNetzA Update**: {health_status["checks"]["data_freshness"].get("bnetza_last_update", "Unknown")}

### System Resources
- **Memory Usage**: {health_status["checks"]["resources"].get("memory_usage_percent", "N/A")}%
- **Disk Usage**: {health_status["checks"]["resources"].get("disk_usage_percent", "N/A")}%
- **CPU Load**: {health_status["checks"]["resources"].get("cpu_load_percent", "N/A")}%

---
*Report generated at {datetime.now().isoformat()}*
    """

    await create_markdown_artifact(
        key="system-health-report",
        markdown=report_markdown
    )

@task(name="Send Health Alert")
async def send_health_alert_task(health_status: dict[str, Any]):
    """Sende Gesundheitsalert über Slack."""

    slack_webhook = await SlackWebhook.load("slack-alerts")

    status_color = {
        "critical": "#FF0000",
        "degraded": "#FFA500",
        "warning": "#FFFF00"
    }

    message = {
        "attachments": [
            {
                "color": status_color[health_status["overall"]],
                "title": f"VNB Digitaler Health Alert - {health_status['overall'].upper()}",
                "fields": [
                    {
                        "title": "Database",
                        "value": "✅ Healthy" if health_status["checks"]["database"]["healthy"] else "❌ Failed",
                        "short": True
                    },
                    {
                        "title": "External APIs",
                        "value": f"{len(health_status['checks']['external_apis']['failed_apis'])} Failed",
                        "short": True
                    },
                    {
                        "title": "Data Freshness",
                        "value": f"{len(health_status['checks']['data_freshness']['stale_sources'])} Stale",
                        "short": True
                    }
                ],
                "footer": "VNB Digitaler Monitoring",
                "ts": int(datetime.now().timestamp())
            }
        ]
    }

    await slack_webhook.notify(message)
```

### Performance Monitoring

```python
# src/prefect_flows/monitoring/performance_monitor.py
from prefect import flow, task
from prefect.artifacts import create_table_artifact
import psutil
import asyncio

@flow(name="Performance Monitor")
async def performance_monitoring_flow() -> dict[str, Any]:
    """Sammle Performance-Metriken für System-Monitoring."""

    # System Metrics
    system_metrics = await collect_system_metrics_task()

    # Database Performance
    db_metrics = await collect_database_metrics_task()

    # Flow Performance History
    flow_metrics = await collect_flow_performance_task()

    # Erstelle Performance Dashboard
    await create_performance_dashboard_task({
        "system": system_metrics,
        "database": db_metrics,
        "flows": flow_metrics
    })

    return {
        "system_health_score": calculate_health_score(system_metrics),
        "database_performance_score": calculate_db_score(db_metrics),
        "flow_efficiency_score": calculate_flow_score(flow_metrics)
    }

@task(name="Collect System Metrics")
async def collect_system_metrics_task() -> dict[str, Any]:
    """Sammle System-Performance-Metriken."""

    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage_percent": psutil.disk_usage('/').percent,
        "network_io": psutil.net_io_counters()._asdict(),
        "process_count": len(psutil.pids()),
        "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
    }
```

---

_Diese Deployment-Konfigurationen ermöglichen eine robuste, skalierbare Prefect-Installation für VNB Digitaler in Production._
