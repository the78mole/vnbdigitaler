# 🚀 VNB Digitaler - Deployment & Operations

> **📋 Projekt-Roadmap**: [ROADMAP.md](./ROADMAP.md) - Phasen und Meilensteine
> **⚙️ Technische Spezifikation**: [SPECIFICATION.md](./SPECIFICATION.md) - Architektur und API-Details
> **🧪 Testing & Quality**: [TESTING.md](./TESTING.md) - Tests und Code Quality

## 🏗️ Deployment-Architektur

### Übersicht

Das VNB Digitaler Projekt verwendet eine vereinfachte Cloud-native Architektur:

```mermaid
graph TD
    A[GitHub Actions<br/>CI/CD] --> D[Neon Database<br/>PostgreSQL]
    A -.->|deploys| B
    A -.->|deploys| C

    B[Streamlit Cloud<br/>Public Portal] --> D
    C[Docker Host<br/>VPS/Cloud<br/>Admin/Install] --> D
    C --> E[Cloudflare R2<br/>Object Storage<br/>PDF Documents]

    B -.->|reads from| E
    C -.->|uploads to| E

    style A fill:#24292e,stroke:#fff,stroke-width:2px,color:#fff
    style B fill:#ff4b4b,stroke:#fff,stroke-width:2px,color:#fff
    style C fill:#0066cc,stroke:#fff,stroke-width:2px,color:#fff
    style D fill:#336791,stroke:#fff,stroke-width:2px,color:#fff
    style E fill:#f38020,stroke:#fff,stroke-width:2px,color:#fff
```

### Deployment-Komponenten

| Komponente          | Hosting         | URL                          | Zweck                         |
| ------------------- | --------------- | ---------------------------- | ----------------------------- |
| **Public Portal**   | Streamlit Cloud | `vnbdigitaler.streamlit.app` | Öffentliche Datenansicht      |
| **Admin Interface** | Docker Host     | `admin.vnbdigitaler.de`      | Datenvalidierung & -kontrolle |
| **Installer API**   | Docker Host     | `installer.vnbdigitaler.de`  | Installateur-Services         |
| **Object Storage**  | Cloudflare R2   | `r2.vnbdigitaler.de`         | PDF-Dokumente & Backup        |
| **Database**        | Neon            | Managed PostgreSQL           | Zentrale Datenhaltung         |
| **CI/CD**           | GitHub Actions  | Workflows                    | Deployment-Automatisierung    |

## 🐳 Docker Setup

### Multi-Service Docker Compose

```yaml
# docker-compose.prod.yml
version: "3.8"

services:
  # Data Admin UI (FastAPI)
  admin-api:
    build:
      context: .
      dockerfile: Dockerfile.admin
    ports:
      - "8081:8081"
    environment:
      - ENV=production
      - DATABASE_URL=${NEON_DATABASE_URL}
      - ADMIN_SECRET_KEY=${ADMIN_SECRET_KEY}
      - ALLOWED_HOSTS=admin.vnbdigitaler.de
      # Cloudflare R2 Configuration
      - CLOUDFLARE_R2_ACCESS_KEY=${CLOUDFLARE_R2_ACCESS_KEY}
      - CLOUDFLARE_R2_SECRET_KEY=${CLOUDFLARE_R2_SECRET_KEY}
      - CLOUDFLARE_R2_ACCOUNT_ID=${CLOUDFLARE_R2_ACCOUNT_ID}
      - CLOUDFLARE_R2_BUCKET_NAME=vnbdigitaler
      - CLOUDFLARE_R2_ENDPOINT_URL=https://${CLOUDFLARE_R2_ACCOUNT_ID}.r2.cloudflarestorage.com
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Installateur Web-App (FastAPI + React)
  installer-api:
    build:
      context: .
      dockerfile: Dockerfile.installer
    ports:
      - "8080:8080"
    environment:
      - ENV=production
      - DATABASE_URL=${NEON_DATABASE_URL}
      - OAUTH_CLIENT_ID=${OAUTH_CLIENT_ID}
      - OAUTH_CLIENT_SECRET=${OAUTH_CLIENT_SECRET}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ALLOWED_HOSTS=installer.vnbdigitaler.de
      # Cloudflare R2 Configuration
      - CLOUDFLARE_R2_ACCESS_KEY=${CLOUDFLARE_R2_ACCESS_KEY}
      - CLOUDFLARE_R2_SECRET_KEY=${CLOUDFLARE_R2_SECRET_KEY}
      - CLOUDFLARE_R2_ACCOUNT_ID=${CLOUDFLARE_R2_ACCOUNT_ID}
      - CLOUDFLARE_R2_BUCKET_NAME=vnbdigitaler
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

    environment:
      - PREFECT_API_URL=http://localhost:4200/api
      - DATABASE_URL=${NEON_DATABASE_URL}
      - BDEW_API_KEY=${BDEW_API_KEY}
      - VNB_DIGITAL_API_KEY=${VNB_DIGITAL_API_KEY}
      # Cloudflare R2 Configuration for document processing
      - CLOUDFLARE_R2_ACCESS_KEY=${CLOUDFLARE_R2_ACCESS_KEY}
      - CLOUDFLARE_R2_SECRET_KEY=${CLOUDFLARE_R2_SECRET_KEY}
      - CLOUDFLARE_R2_ACCOUNT_ID=${CLOUDFLARE_R2_ACCOUNT_ID}
      - CLOUDFLARE_R2_BUCKET_NAME=vnbdigitaler
    volumes:
      - ./flows:/app/flows
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped

  # Nginx für HTTPS/SSL-Termination und Routing
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./nginx/logs:/var/log/nginx
    depends_on:
      - admin-api
      - installer-api
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Log Aggregation (Optional)
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml:ro
      - loki-data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    restart: unless-stopped

  # Cloudflare R2 Management Service (Optional Web Interface)
  r2-manager:
    build:
      context: .
      dockerfile: Dockerfile.r2-manager
    ports:
      - "8082:8082"
    environment:
      - CLOUDFLARE_R2_ACCESS_KEY=${CLOUDFLARE_R2_ACCESS_KEY}
      - CLOUDFLARE_R2_SECRET_KEY=${CLOUDFLARE_R2_SECRET_KEY}
      - CLOUDFLARE_R2_ACCOUNT_ID=${CLOUDFLARE_R2_ACCOUNT_ID}
      - CLOUDFLARE_R2_BUCKET_NAME=vnbdigitaler
      - ADMIN_SECRET_KEY=${ADMIN_SECRET_KEY}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    depends_on:
      - admin-api
    profiles:
      - "management"  # Optional service, enable with --profile management

volumes:
  loki-data:

networks:
  default:
    name: vnbdigitaler-network
```

### Dockerfiles

#### Admin Interface

```dockerfile
# Dockerfile.admin
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies (including boto3 for R2 integration)
RUN uv add "boto3>=1.28.0" "botocore>=1.31.0"
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/
COPY admin/ ./admin/

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

EXPOSE 8081

CMD ["uv", "run", "uvicorn", "admin.main:app", "--host", "0.0.0.0", "--port", "8081"]
```

#### Installer API

```dockerfile
# Dockerfile.installer
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./
COPY installer/package.json installer/package-lock.json ./installer/

# Install Python dependencies (including boto3 for R2 integration)
RUN uv add "boto3>=1.28.0" "botocore>=1.31.0" "Pillow>=10.0.0"
RUN uv sync --frozen --no-dev

# Install Node.js dependencies and build frontend
WORKDIR /app/installer
RUN npm ci --only=production && npm run build

# Copy application code
WORKDIR /app
COPY src/ ./src/
COPY installer/ ./installer/

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "installer.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

#### R2 Manager (Optional)

```dockerfile
# Dockerfile.r2-manager
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies for R2 management
RUN uv add "fastapi>=0.100.0" "uvicorn>=0.22.0" "boto3>=1.28.0" "streamlit>=1.25.0"
RUN uv sync --frozen --no-dev

# Copy R2 management application
COPY src/ ./src/
COPY r2-manager/ ./r2-manager/

# Create non-root user
RUN useradd --create-home --shell /bin/bash r2user && chown -R r2user:r2user /app
USER r2user

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8082/health || exit 1

EXPOSE 8082

CMD ["uv", "run", "uvicorn", "r2_manager.main:app", "--host", "0.0.0.0", "--port", "8082"]
```

## 🌐 Nginx Configuration

### Main Configuration

```nginx
# nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                   '$status $body_bytes_sent "$http_referer" '
                   '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;

    # Performance
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 100M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=admin:10m rate=5r/s;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Admin Interface
    server {
        listen 443 ssl http2;
        server_name admin.vnbdigitaler.de;

        ssl_certificate /etc/nginx/ssl/admin.crt;
        ssl_certificate_key /etc/nginx/ssl/admin.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # Rate limiting for admin
        limit_req zone=admin burst=20 nodelay;

        location / {
            proxy_pass http://admin-api:8081;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }

    # Installer Interface
    server {
        listen 443 ssl http2;
        server_name installer.vnbdigitaler.de;

        ssl_certificate /etc/nginx/ssl/installer.crt;
        ssl_certificate_key /etc/nginx/ssl/installer.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # Rate limiting for API
        limit_req zone=api burst=50 nodelay;

        location / {
            proxy_pass http://installer-api:8080;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Static files caching
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }

    # HTTP redirect to HTTPS
    server {
        listen 80;
        server_name admin.vnbdigitaler.de installer.vnbdigitaler.de;
        return 301 https://$server_name$request_uri;
    }
}
```

## ⚙️ GitHub Actions CI/CD

### Main Deployment Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy VNB Digitaler

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python + uv
        uses: astral-sh/setup-uv@v1
        with:
          version: "latest"

      - name: Install dependencies
        run: uv sync

      - name: Run tests
        run: |
          uv run pytest --cov=src --cov-report=xml
          uv run mypy src/
          uv run ruff check src/

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    strategy:
      matrix:
        service: [admin, installer]

    steps:
      - uses: actions/checkout@v4

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-${{ matrix.service }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=sha

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.${{ matrix.service }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}

  deploy-streamlit:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Streamlit Cloud
        run: |
          # Streamlit Cloud deployment wird automatisch getriggert
          # durch Repository-Updates (Webhook-basiert)
          echo "Streamlit deployment triggered automatically"

  deploy-docker-host:
    needs: [build-and-push]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Docker Host
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.DOCKER_HOST }}
          username: ${{ secrets.DOCKER_USER }}
          key: ${{ secrets.DOCKER_SSH_KEY }}
          script: |
            # Navigate to project directory
            cd /opt/vnbdigitaler

            # Pull latest images
            docker-compose -f docker-compose.prod.yml pull

            # Update services (zero-downtime deployment)
            docker-compose -f docker-compose.prod.yml up -d --remove-orphans

            # Cleanup old images
            docker image prune -f

  data-pipeline:
    needs: deploy-docker-host
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python + uv
        uses: astral-sh/setup-uv@v1

      - name: Run BDEW data sync
        run: uv run python -m src.pipelines.bdew_import
        env:
          DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}

      - name: Run price extraction
        run: uv run python -m src.pipelines.price_extraction
        env:
          DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}
```

### Data Pipeline Workflow

```yaml
# .github/workflows/data-pipeline.yml
name: Daily Data Pipeline

on:
  schedule:
    - cron: "0 2 * * *" # Täglich um 2:00 UTC
  workflow_dispatch:

jobs:
  bdew-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python + uv
        uses: astral-sh/setup-uv@v1

      - name: Run BDEW data sync
        run: |
          uv run python -m src.pipelines.bdew_import \
            --update-mode incremental \
            --validate-data \
            --log-level INFO
        env:
          DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}
          BDEW_API_KEY: ${{ secrets.BDEW_API_KEY }}

      - name: Upload sync report
        uses: actions/upload-artifact@v3
        with:
          name: bdew-sync-report
          path: logs/bdew_import_*.json

  bnetza-sync:
    runs-on: ubuntu-latest
    needs: bdew-sync
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python + uv
        uses: astral-sh/setup-uv@v1

      - name: Run BNetzA rollout data sync
        run: |
          uv run python -m src.pipelines.bnetza_import \
            --quarter Q4-2025 \
            --validate-data
        env:
          DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}

  price-extraction:
    runs-on: ubuntu-latest
    needs: [bdew-sync, bnetza-sync]
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python + uv
        uses: astral-sh/setup-uv@v1

      - name: Extract VNB price sheets
        run: |
          uv run python -m src.pipelines.price_extraction \
            --target-vnbs 50 \
            --extract-14a-prices \
            --update-historical
        env:
          DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}

  data-validation:
    runs-on: ubuntu-latest
    needs: [bdew-sync, bnetza-sync, price-extraction]
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python + uv
        uses: astral-sh/setup-uv@v1

      - name: Run data quality checks
        run: |
          uv run python -m src.validation.data_quality \
            --full-validation \
            --generate-report
        env:
          DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}

      - name: Upload validation report
        uses: actions/upload-artifact@v3
        with:
          name: data-quality-report
          path: reports/data_quality_*.html
```

## 🗄️ Database Setup (Neon)

### Connection Configuration

```python
# src/database/neon.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
import os

# Neon Database Configuration
DATABASE_URL = os.getenv("NEON_DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("NEON_DATABASE_URL environment variable is required")

# Connection string format:
# postgresql://username:password@ep-xyz.us-east-1.aws.neon.tech/vnbdigitaler?sslmode=require  # pragma: allowlist secret

# Connection Pool Setup for Neon
engine = create_engine(
    DATABASE_URL,
    # Neon-optimized settings
    poolclass=QueuePool,
    pool_size=5,          # Small pool for cost efficiency
    max_overflow=10,      # Burst capacity
    pool_pre_ping=True,   # Validate connections
    pool_recycle=3600,    # Recycle connections every hour
    echo=False,           # Disable SQL logging in production

    # Connection arguments
    connect_args={
        "sslmode": "require",
        "connect_timeout": 10,
        "application_name": "vnbdigitaler"
    }
)

# Async engine for FastAPI
from sqlalchemy.ext.asyncio import create_async_engine

async_engine = create_async_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)
```

### Migration Management

```python
# migrations/env.py (Alembic configuration)
from alembic import context
from sqlalchemy import engine_from_config, pool
from src.models import Base
import os

# Database URL from environment
config = context.config
database_url = os.getenv("NEON_DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata

def run_migrations_online():
    """Run migrations in 'online' mode for Neon"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True
        )

        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
```

### Backup Strategy

```bash
#!/bin/bash
# scripts/backup_neon_db.sh

# Neon Database Backup Script
BACKUP_DIR="/opt/backups/vnbdigitaler"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/vnbdigitaler_${TIMESTAMP}.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database dump
pg_dump $NEON_DATABASE_URL > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Upload to Cloudflare R2 backup folder
if [ -n "$CLOUDFLARE_R2_BUCKET_NAME" ]; then
    aws s3 cp "${BACKUP_FILE}.gz" "s3://${CLOUDFLARE_R2_BUCKET_NAME}/backups/database/" \
        --endpoint-url $CLOUDFLARE_R2_ENDPOINT_URL
fi

# Cleanup old backups (keep last 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Database backup completed: ${BACKUP_FILE}.gz"
```

### R2 Object Storage Backup

```bash
#!/bin/bash
# scripts/backup_r2_objects.sh

# Cloudflare R2 Object Backup Script
BACKUP_DIR="/opt/backups/vnbdigitaler/r2-objects"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Sync critical documents to local backup
aws s3 sync "s3://${CLOUDFLARE_R2_BUCKET_NAME}/documents/" "${BACKUP_DIR}/${TIMESTAMP}/" \
    --endpoint-url $CLOUDFLARE_R2_ENDPOINT_URL

# Create integrity report
aws s3 ls "s3://${CLOUDFLARE_R2_BUCKET_NAME}/documents/" --recursive \
    --endpoint-url $CLOUDFLARE_R2_ENDPOINT_URL > "${BACKUP_DIR}/${TIMESTAMP}/object_list.txt"

# Calculate checksums for verification
find "${BACKUP_DIR}/${TIMESTAMP}" -type f -name "*.pdf" -exec sha256sum {} \; > "${BACKUP_DIR}/${TIMESTAMP}/checksums.txt"

# Optional: Create archive for long-term storage
tar -czf "${BACKUP_DIR}/r2_backup_${TIMESTAMP}.tar.gz" -C "${BACKUP_DIR}" "${TIMESTAMP}/"

echo "R2 object backup completed: ${BACKUP_DIR}/r2_backup_${TIMESTAMP}.tar.gz"
```

## 📊 Monitoring & Health Checks

### Application Health Checks

```python
# src/health.py
from fastapi import APIRouter, status, HTTPException
from sqlalchemy import text
from src.database import get_db_session
from datetime import datetime
import psycopg2

router = APIRouter()

@router.get("/health")
async def health_check():
    """Umfassende Gesundheitsprüfung"""
    checks = {
        "timestamp": datetime.utcnow().isoformat(),
        "status": "healthy",
        "services": {}
    }

    # Database connectivity
    try:
        async with get_db_session() as session:
            result = await session.execute(text("SELECT 1"))
            checks["services"]["database"] = {
                "status": "healthy",
                "response_time_ms": 0  # TODO: Measure actual time
            }
    except Exception as e:
        checks["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        checks["status"] = "unhealthy"

    # API responsiveness
    checks["services"]["api"] = {
        "status": "healthy",
        "version": "1.0.0"
    }

    # Return appropriate status code
    status_code = status.HTTP_200_OK if checks["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE

    return checks

@router.get("/ready")
async def readiness_check():
    """Kubernetes-style readiness probe"""
    # Check if application is ready to serve traffic
    return {"status": "ready", "timestamp": datetime.utcnow()}

@router.get("/live")
async def liveness_check():
    """Kubernetes-style liveness probe"""
    # Basic liveness check
    return {"status": "alive", "timestamp": datetime.utcnow()}
```

### GitHub Actions Health Monitoring

```yaml
# .github/workflows/health-check.yml
name: System Health Check

on:
  schedule:
    - cron: "*/30 * * * *" # Alle 30 Minuten
  workflow_dispatch:

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - name: Check Streamlit App
        run: |
          response=$(curl -s -o /dev/null -w "%{http_code}" https://vnbdigitaler.streamlit.app/)
          if [ $response -ne 200 ]; then
            echo "Streamlit app health check failed with status $response"
            exit 1
          fi
          echo "Streamlit app is healthy"

      - name: Check Admin Interface
        run: |
          response=$(curl -s -o /dev/null -w "%{http_code}" https://admin.vnbdigitaler.de/health)
          if [ $response -ne 200 ]; then
            echo "Admin interface health check failed with status $response"
            exit 1
          fi
          echo "Admin interface is healthy"

      - name: Check Installer API
        run: |
          response=$(curl -s -o /dev/null -w "%{http_code}" https://installer.vnbdigitaler.de/health)
          if [ $response -ne 200 ]; then
            echo "Installer API health check failed with status $response"
            exit 1
          fi
          echo "Installer API is healthy"

      - name: Check Database Connection
        run: |
          python3 -c "
          import psycopg2
          import os
          try:
              conn = psycopg2.connect(os.environ['NEON_DATABASE_URL'])
              print('Database connection successful')
              conn.close()
          except Exception as e:
              print(f'Database connection failed: {e}')
              exit(1)
          "
        env:
          NEON_DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}

      - name: Send notification on failure
        if: failure()
        uses: 8398a7/action-slack@v3
        with:
          status: failure
          text: "VNB Digitaler health check failed!"
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

## 🔐 Security & Secrets Management

### Environment Variables

```bash
# .env.production (Example - use GitHub Secrets in production)

# Database
NEON_DATABASE_URL=postgresql://user:pass@host/db?sslmode=require  # pragma: allowlist secret

# Admin Interface
ADMIN_SECRET_KEY=your-super-secret-admin-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=bcrypt-hashed-password

# Installer API
OAUTH_CLIENT_ID=google-oauth-client-id
OAUTH_CLIENT_SECRET=google-oauth-client-secret
JWT_SECRET_KEY=jwt-signing-secret

# External APIs
BDEW_API_KEY=bdew-api-access-key
VNB_DIGITAL_API_KEY=vnb-digital-graphql-key

# Cloudflare R2 Object Storage
CLOUDFLARE_R2_ACCESS_KEY=your-r2-access-key
CLOUDFLARE_R2_SECRET_KEY=your-r2-secret-key  # pragma: allowlist secret
CLOUDFLARE_R2_ACCOUNT_ID=your-cloudflare-account-id
CLOUDFLARE_R2_BUCKET_NAME=vnbdigitaler
CLOUDFLARE_R2_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
CLOUDFLARE_R2_PUBLIC_URL=https://r2.vnbdigitaler.de

# Prefect Configuration
PREFECT_API_URL=http://prefect-server:4200/api
PREFECT_SERVER_API_HOST=0.0.0.0
PREFECT_SERVER_API_PORT=4200
PREFECT_API_DATABASE_CONNECTION_URL=postgresql://${NEON_USER}:${NEON_PASSWORD}@${NEON_HOST}/vnbdigitaler
PREFECT_LOGGING_LEVEL=INFO
PREFECT_WORKER_POOL=default-pool

# Monitoring
SLACK_WEBHOOK_URL=slack-webhook-for-alerts
SENTRY_DSN=sentry-error-tracking-dsn

# SSL/TLS
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem
```

### Docker Secrets

```yaml
# docker-compose.prod.yml (secrets section)
secrets:
  admin_secret_key:
    external: true
  oauth_client_secret:
    external: true
  jwt_secret_key:
    external: true
  ssl_cert:
    external: true
  ssl_key:
    external: true

services:
  admin-api:
    secrets:
      - admin_secret_key
      - jwt_secret_key
    environment:
      - ADMIN_SECRET_KEY_FILE=/run/secrets/admin_secret_key

  installer-api:
    secrets:
      - oauth_client_secret
      - jwt_secret_key
    environment:
      - OAUTH_CLIENT_SECRET_FILE=/run/secrets/oauth_client_secret
```

## 📈 Scaling & Performance

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
version: "3.8"

services:
  admin-api:
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
        reservations:
          cpus: "0.25"
          memory: 256M

  installer-api:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "1.0"
          memory: 1G
        reservations:
          cpus: "0.5"
          memory: 512M
```

### Load Balancing

```nginx
# nginx/upstream.conf
upstream admin_backend {
    least_conn;
    server admin-api-1:8081 max_fails=3 fail_timeout=30s;
    server admin-api-2:8081 max_fails=3 fail_timeout=30s;
}

upstream installer_backend {
    least_conn;
    server installer-api-1:8080 max_fails=3 fail_timeout=30s;
    server installer-api-2:8080 max_fails=3 fail_timeout=30s;
    server installer-api-3:8080 max_fails=3 fail_timeout=30s;
}
```

## 🚨 Disaster Recovery

### Disaster Recovery Backup Strategy

```bash
#!/bin/bash
# scripts/disaster_recovery.sh

# Automated backup and recovery procedures

# 1. Database Backup
echo "Creating database backup..."
pg_dump $NEON_DATABASE_URL | gzip > "backup_$(date +%Y%m%d_%H%M%S).sql.gz"

# 2. Application State Backup
echo "Backing up application state..."
docker-compose -f docker-compose.prod.yml exec admin-api tar -czf /tmp/admin_data.tar.gz /app/data
docker-compose -f docker-compose.prod.yml exec installer-api tar -czf /tmp/installer_uploads.tar.gz /app/uploads

# 3. Configuration Backup
echo "Backing up configurations..."
tar -czf "config_backup_$(date +%Y%m%d_%H%M%S).tar.gz" nginx/ docker-compose.prod.yml

# 4. Upload to cloud storage
if [ -n "$AWS_S3_BUCKET" ]; then
    aws s3 sync . "s3://${AWS_S3_BUCKET}/disaster-recovery/" --exclude "*" --include "*.tar.gz" --include "*.sql.gz"
fi

echo "Disaster recovery backup completed"
```

### Recovery Procedures

```bash
#!/bin/bash
# scripts/restore_from_backup.sh

BACKUP_DATE=$1
if [ -z "$BACKUP_DATE" ]; then
    echo "Usage: $0 <backup_date> (format: YYYYMMDD_HHMMSS)"
    exit 1
fi

# 1. Stop services
echo "Stopping services..."
docker-compose -f docker-compose.prod.yml down

# 2. Restore database
echo "Restoring database from backup_${BACKUP_DATE}.sql.gz..."
gunzip -c "backup_${BACKUP_DATE}.sql.gz" | psql $NEON_DATABASE_URL

# 3. Restore application data
echo "Restoring application data..."
# ... restoration commands ...

# 4. Restart services
echo "Restarting services..."
docker-compose -f docker-compose.prod.yml up -d

echo "Recovery completed from backup: $BACKUP_DATE"
```

---

_Dieses Deployment-Handbuch wird kontinuierlich aktualisiert, um den sich entwickelnden Infrastruktur-Anforderungen des Projekts gerecht zu werden._
