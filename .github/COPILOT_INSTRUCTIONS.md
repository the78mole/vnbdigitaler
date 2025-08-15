# GitHub Copilot Instructions für VNBdigitaler

## Projektübersicht

VNBdigitaler ist eine Streamlit-basierte Web-Anwendung zur Vereinfachung des Zugangs zu Daten deutscher Verteilnetzbetreiber (VNB). Das Projekt automatisiert die Sammlung und Analyse von Smart Meter Rollout-Daten und Preisblättern der Netzbetreiber.

## Technologie-Stack

### Backend & Database
- **ORM**: SQLAlchemy
- **Database**: Neon Cloud PostgreSQL
- **Migrations**: Alembic
- **Object Storage**: Cloudflare R2 (S3-kompatibel)

### AI & Processing
- **AI Provider**: OpenRouter API
- **Models**: GPT-4, Claude (für PDF-Analyse und Datenvalidierung)
- **PDF Processing**: PyPDF2, pdfplumber, oder ähnliche Libraries

### Frontend & Deployment
- **Framework**: Streamlit
- **Deployment**: Streamlit Cloud
- **CI/CD**: GitHub Actions

### Development Tools
- **Package Manager**: uv
- **Testing**: pytest
- **Code Quality**: ruff, mypy
- **Documentation**: Sphinx oder MkDocs

## Code-Stil und Konventionen

### Python Coding Standards
```python
# Verwende Type Hints für alle Funktionen
def process_vnb_data(vnb_id: str, data: Dict[str, Any]) -> VNBData:
    pass

# Async/Await für Database Operations
async def get_vnb_by_id(db: AsyncSession, vnb_id: str) -> Optional[VNB]:
    pass

# Pydantic Models für Data Validation
from pydantic import BaseModel, Field

class VNBCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    operator_number: str = Field(..., regex=r"^\d{13}$")
```

### File Structure Patterns
```
src/
├── models/          # SQLAlchemy Models
├── schemas/         # Pydantic Schemas
├── services/        # Business Logic
├── repositories/    # Database Access Layer
├── api/            # API Clients (OpenRouter, R2)
├── utils/          # Helper Functions
└── config.py       # Configuration Management
```

### Database Models Beispiel
```python
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class VNB(Base):
    __tablename__ = "vnb"

    id = Column(Integer, primary_key=True)
    operator_number = Column(String(13), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    city = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

## Environment Variables und Configuration

### Required Environment Variables
```python
# Database
NEON_DATABASE_URL = "postgresql+asyncpg://user:pass@host/db"

# AI Services
OPENROUTER_API_KEY = "or-xxx"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Object Storage
CLOUDFLARE_R2_ACCESS_KEY = "xxx"
CLOUDFLARE_R2_SECRET_KEY = "xxx"
CLOUDFLARE_R2_BUCKET_NAME = "vnb-documents"
CLOUDFLARE_R2_ENDPOINT = "https://xxx.r2.cloudflarestorage.com"

# Application
STREAMLIT_SECRET_KEY = "xxx"
LOG_LEVEL = "INFO"
```

### Configuration Management
```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str
    openrouter_api_key: str
    r2_access_key: str

    class Config:
        env_file = ".env"

settings = Settings()
```

## API Integration Patterns

### OpenRouter Client
```python
import aiohttp
from typing import Dict, Any

class OpenRouterClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url

    async def analyze_pdf_content(self, text: str, model: str = "anthropic/claude-3-haiku") -> Dict[str, Any]:
        """Analysiere PDF-Inhalt mit KI"""
        prompt = f"""
        Analysiere das folgende Preisblatt eines Verteilnetzbetreibers.
        Extrahiere strukturierte Daten zu Tarifen und Preisen:

        {text}
        """
        # Implementation...
```

### R2 Storage Client
```python
import boto3
from botocore.config import Config

class R2StorageClient:
    def __init__(self, access_key: str, secret_key: str, endpoint: str, bucket: str):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint,
            config=Config(signature_version='s3v4')
        )
        self.bucket = bucket

    async def upload_document(self, file_path: str, key: str) -> str:
        """Upload document to R2 and return URL"""
        # Implementation...
```

## GitHub Actions Patterns

### Data Processing Workflow
```yaml
name: Update VNB Data
on:
  schedule:
    - cron: '0 6 * * 1'  # Weekly on Monday
  workflow_dispatch:

jobs:
  update-data:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v2
        with:
          version: "latest"
      - name: Set up Python
        run: uv python install 3.11
      - name: Install dependencies
        run: uv sync
      - name: Process VNB Data
        env:
          NEON_DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        run: |
          uv run python -m src.workflows.update_vnb_data
```

## Streamlit App Patterns

### Page Structure
```python
import streamlit as st
from src.services.vnb_service import VNBService

@st.cache_data(ttl=3600)
def load_vnb_data():
    """Cache VNB data for 1 hour"""
    return VNBService.get_all_vnbs()

def main():
    st.set_page_config(
        page_title="VNBdigitaler",
        page_icon="⚡",
        layout="wide"
    )

    st.title("VNBdigitaler - Verteilnetzbetreiber Daten")

    # Sidebar filters
    with st.sidebar:
        selected_state = st.selectbox("Bundesland", options=get_states())

    # Main content
    vnb_data = load_vnb_data()
    filtered_data = filter_by_state(vnb_data, selected_state)

    st.dataframe(filtered_data)
```

## Testing Patterns

### Database Tests
```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from src.models import Base, VNB

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session

@pytest.mark.asyncio
async def test_create_vnb(db_session):
    vnb = VNB(operator_number="1234567890123", name="Test VNB")
    db_session.add(vnb)
    await db_session.commit()

    assert vnb.id is not None
```

## Error Handling und Logging

### Standard Error Handling
```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def safe_api_call(func, *args, **kwargs) -> Optional[Any]:
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.error(f"API call failed: {e}", exc_info=True)
        return None
```

## Domain-Specific Knowledge

### VNB-spezifische Begriffe
- **VNB**: Verteilnetzbetreiber
- **Betreibernummer**: 13-stellige eindeutige Nummer
- **iMSys**: Intelligente Messsysteme (Smart Meter)
- **Rollout-Quote**: Prozentsatz installierter Smart Meter
- **Preisblatt**: Dokument mit Tarifen und Gebühren

### Typische Datenstrukturen
```python
class PriceSheetData(BaseModel):
    vnb_id: str
    document_date: datetime
    basic_price_monthly: Decimal
    working_price_per_kwh: Decimal
    meter_rental_monthly: Decimal
    smart_meter_surcharge: Optional[Decimal]
```

## Performance Guidelines

1. **Database Queries**: Verwende Bulk Operations für große Datenmengen
2. **Caching**: Implementiere Redis für häufig abgefragte Daten
3. **Async**: Alle I/O-Operationen sollten asynchron sein
4. **Monitoring**: Verwende strukturiertes Logging mit correlation IDs

## Security Best Practices

1. **API Keys**: Niemals in Code committen, nur über Environment Variables
2. **Database**: Verwende parameterisierte Queries (SQLAlchemy macht das automatisch)
3. **File Uploads**: Validiere Dateitypen und -größen
4. **Rate Limiting**: Implementiere für externe API-Calls

Folge diesen Richtlinien bei der Code-Generierung und stelle sicher, dass der generierte Code konsistent mit der bestehenden Projektstruktur ist.
