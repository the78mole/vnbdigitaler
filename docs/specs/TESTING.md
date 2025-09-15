# 🧪 VNB Digitaler - Testing & Code Quality

> **📋 Projekt-Roadmap**: [ROADMAP.md](./ROADMAP.md) - Phasen und Meilensteine
> **⚙️ Technische Spezifikation**: [SPECIFICATION.md](./SPECIFICATION.md) - Architektur und API-Details
> **🚀 Deployment**: [DEPLOYMENT.md](./DEPLOYMENT.md) - Production Setup und CI/CD

## 📊 Testing-Strategie

### Test-Pyramide

```
    /\     E2E Tests (5%)
   /  \    API Integration Tests (15%)
  /____\   Unit Tests (80%)
```

Die Testing-Strategie folgt der klassischen Test-Pyramide mit Fokus auf:

- **Unit Tests (80%)**: Schnelle, isolierte Tests für Geschäftslogik
- **Integration Tests (15%)**: Datenbank- und API-Integration
- **End-to-End Tests (5%)**: Vollständige User-Journey-Tests

## 🔬 Unit Tests

### BDEW-Datenvalidierung

```python
# tests/test_bdew_validation.py
import pytest
from src.models.bdew import Company, RoleType
from src.validators.bdew import BDEWCodeValidator

class TestBDEWDataValidation:
    def test_company_code_validation(self):
        """BDEW-Code muss dem Standard entsprechen"""
        validator = BDEWCodeValidator()

        # Gültige 12-stellige BDEW-Codes
        assert validator.validate("123456789012") == True  # pragma: allowlist secret
        assert validator.validate("999999999999") == True  # pragma: allowlist secret

        # Invalide Codes
        assert validator.validate("12345") == False
        assert validator.validate("abc123456789") == False  # pragma: allowlist secret

    def test_multi_role_assignment(self):
        """Unternehmen können mehrere Rollen haben"""
        company = Company(code="123456789012", name="Test AG")  # pragma: allowlist secret

        company.add_role(RoleType.VNB, active=True)
        company.add_role(RoleType.MSB, active=True)

        assert len(company.roles) == 2
        assert company.has_role(RoleType.VNB) == True
        assert company.has_role(RoleType.MSB) == True

    def test_role_conflict_detection(self):
        """Prüfe auf Rollenkonflikte"""
        company = Company(code="123456789012", name="Test AG")  # pragma: allowlist secret

        # Bestimmte Rollen-Kombinationen sollten Warnungen erzeugen
        company.add_role(RoleType.VNB, active=True)
        company.add_role(RoleType.UNB, active=True)

        conflicts = company.check_role_conflicts()
        assert len(conflicts) > 0  # VNB + ÜNB ist ungewöhnlich
```

### Preisextraktion-Tests

```python
# tests/test_price_extraction.py
import pytest
from pathlib import Path
from src.extractors.price import PDFPriceExtractor

class TestPriceExtraction:
    def setup_method(self):
        self.extractor = PDFPriceExtractor()
        self.test_pdfs = Path("tests/fixtures/price_sheets")

    def test_14a_price_extraction(self):
        """Extraktion von §14a-Preisen aus PDF"""
        pdf_path = self.test_pdfs / "stadtwerke_beispiel_14a.pdf"

        extracted = self.extractor.extract_14a_prices(pdf_path)

        assert extracted.has_wallbox_tariff == True
        assert extracted.wallbox_price_reduction > 0
        assert extracted.heat_pump_price_reduction > 0
        assert extracted.base_price is not None

    def test_price_normalization(self):
        """Preisnormalisierung für Vergleichbarkeit"""
        raw_prices = {
            "wallbox": "15,50 ct/kWh",
            "wärmepumpe": "12.3 Cent je kWh",
            "grundpreis": "75€/Jahr"
        }

        normalized = self.extractor.normalize_prices(raw_prices)

        assert normalized["wallbox"] == 15.50  # Cent/kWh
        assert normalized["heat_pump"] == 12.30
        assert normalized["base_price"] == 75.00  # Euro/Jahr
```

### Geographic Data Tests

```python
# tests/test_geographic.py
import pytest
from src.models.geographic import ServiceTerritory
from src.validators.geographic import CoordinateValidator

class TestGeographicData:
    def test_coordinate_validation(self):
        """Koordinaten-Validierung für Deutschland"""
        validator = CoordinateValidator()

        # Gültige deutsche Koordinaten
        assert validator.validate_de_coordinates(52.52, 13.405) == True  # Berlin
        assert validator.validate_de_coordinates(48.137, 11.576) == True  # München

        # Ungültige Koordinaten
        assert validator.validate_de_coordinates(0, 0) == False
        assert validator.validate_de_coordinates(90, 180) == False

    def test_postcode_territory_mapping(self):
        """Postleitzahl zu Netzgebiet-Zuordnung"""
        territory = ServiceTerritory.from_postcode("80331")

        assert territory is not None
        assert territory.city == "München"
        assert territory.vnb_code is not None
```

## 🔗 Integration Tests

### Pipeline Integration

```python
# tests/test_integration_pipeline.py
import pytest
from unittest.mock import patch
from src.pipelines.bdew_import import BDEWImportPipeline
from src.database import DatabaseManager

class TestDataPipelineIntegration:
    @pytest.mark.asyncio
    async def test_bdew_full_pipeline(self):
        """Vollständiger BDEW-Import-Test"""
        pipeline = BDEWImportPipeline()

        # Mock externe BDEW-API
        with patch('src.data_sources.bdew.BDEWClient.fetch_companies') as mock_fetch:
            mock_fetch.return_value = self.get_mock_bdew_data()

            result = await pipeline.run()

        assert result.status == 'success'
        assert result.records_processed > 0
        assert result.validation_errors == 0

    def get_mock_bdew_data(self):
        """Mock BDEW-Testdaten"""
        return [
            {
                "code": "123456789012",
                "name": "Test Stadtwerke GmbH",
                "city": "Teststadt",
                "roles": ["VNB", "EVU"]
            }
        ]
```

### API Integration Tests

```python
# tests/test_api_integration.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

class TestAPIIntegration:
    def setup_method(self):
        self.client = TestClient(app)

    def test_company_search_api(self):
        """Test der Unternehmensuche-API"""
        response = self.client.get("/api/v1/companies/search?q=stadtwerke")

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) > 0

    def test_price_comparison_api(self):
        """Test der Preisvergleichs-API"""
        response = self.client.get("/api/v1/prices/14a?postal_code=80331")

        assert response.status_code == 200
        data = response.json()
        assert "vnb_prices" in data
        assert "comparison" in data
```

### Database Integration

```python
# tests/test_database_integration.py
import pytest
from src.database import DatabaseManager
from src.repositories.bdew import BDEWRepository

class TestDatabaseIntegration:
    @pytest.fixture
    async def db_manager(self):
        """Test-Datenbank Setup"""
        manager = DatabaseManager(test_mode=True)
        await manager.initialize()
        yield manager
        await manager.cleanup()

    @pytest.mark.asyncio
    async def test_company_crud_operations(self, db_manager):
        """Test CRUD-Operationen für Unternehmen"""
        repo = BDEWRepository(db_manager)

        # Create
        company_data = {
            "code": "123456789012",
            "name": "Test Company",
            "city": "Teststadt"
        }
        company = await repo.create_company(company_data)
        assert company.id is not None

        # Read
        found = await repo.get_company(company.id)
        assert found.name == "Test Company"

        # Update
        await repo.update_company(company.id, {"name": "Updated Company"})
        updated = await repo.get_company(company.id)
        assert updated.name == "Updated Company"

        # Delete
        await repo.delete_company(company.id)
        deleted = await repo.get_company(company.id)
        assert deleted is None
```

## 🚀 Performance Tests

### Load Testing mit Locust

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import random

class VNBDigitalUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Setup vor Test-Session"""
        self.postal_codes = ["80331", "10117", "20095", "50667", "70173"]

    @task(3)
    def search_companies(self):
        """Unternehmensuche simulieren"""
        query = random.choice(["stadtwerke", "energie", "netz", "strom"])
        self.client.get(f"/api/v1/companies/search?q={query}")

    @task(2)
    def price_comparison(self):
        """Preisvergleich simulieren"""
        postal_code = random.choice(self.postal_codes)
        self.client.get(f"/api/v1/prices/14a?postal_code={postal_code}")

    @task(1)
    def view_territories(self):
        """Netzgebiete abrufen"""
        self.client.get("/api/v1/territories/geojson")

    @task(1)
    def admin_dashboard(self):
        """Admin-Dashboard (authentifiziert)"""
        # Simuliere Admin-Login
        login_response = self.client.post("/admin/auth/login", json={
            "username": "test_admin",
            "password": "test_password"  # pragma: allowlist secret
        })

        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            self.client.get("/admin/tables", headers={
                "Authorization": f"Bearer {token}"
            })
```

### Database Performance Tests

```python
# tests/performance/test_db_performance.py
import pytest
import time
from src.repositories.bdew import BDEWRepository

class TestDatabasePerformance:
    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self):
        """Test Bulk-Insert Performance"""
        repo = BDEWRepository()

        # Generiere 1000 Test-Unternehmen
        companies = []
        for i in range(1000):
            companies.append({
                "code": f"12345678{i:04d}",
                "name": f"Test Company {i}",
                "city": "Teststadt"
            })

        start_time = time.time()
        await repo.bulk_create_companies(companies)
        duration = time.time() - start_time

        # Sollte unter 5 Sekunden dauern
        assert duration < 5.0

    @pytest.mark.asyncio
    async def test_search_performance(self):
        """Test Suchperformance"""
        repo = BDEWRepository()

        start_time = time.time()
        results = await repo.search_companies("stadtwerke", limit=100)
        duration = time.time() - start_time

        # Suche sollte unter 1 Sekunde dauern
        assert duration < 1.0
        assert len(results) > 0
```

## 📏 Code Quality Standards

### Python Code Standards

```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  migrations
  | archive
)/
'''

[tool.isort]
profile = "black"
multi_line_output = 3
src_paths = ["src", "tests"]
known_first_party = ["src"]

[tool.mypy]
python_version = "3.11"
strict = true
disallow_untyped_defs = true
disallow_any_generics = true
warn_return_any = true
warn_unused_configs = true
exclude = ["migrations/", "archive/"]

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--cov=src",
    "--cov-report=html",
    "--cov-report=term-missing",
    "--cov-fail-under=95",
    "--strict-markers",
    "--disable-warnings"
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests"
]

[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/archive/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError"
]
```

### Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-merge-conflict
      - id: check-added-large-files
      - id: check-case-conflict

  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.3
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]

  - repo: https://github.com/pycqa/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]
```

### Ruff Configuration

```toml
# pyproject.toml
[tool.ruff]
target-version = "py311"
line-length = 88
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # Pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "ARG",  # flake8-unused-arguments
    "SIM",  # flake8-simplify
    "RUF",  # ruff-specific rules
]
ignore = [
    "E501",  # line too long (handled by black)
    "B008",  # do not perform function calls in argument defaults
]
exclude = [
    "migrations",
    "archive",
    ".venv",
    "venv",
]

[tool.ruff.per-file-ignores]
"tests/**/*.py" = ["ARG", "S101"]  # Allow unused args and asserts in tests
```

## 🎯 Test Execution

### Local Testing

```bash
# Alle Tests ausführen
uv run pytest

# Nur Unit Tests
uv run pytest tests/unit -m "not slow"

# Nur Integration Tests
uv run pytest tests/integration

# Performance Tests
uv run pytest tests/performance -m slow

# Mit Coverage Report
uv run pytest --cov-report=html
open htmlcov/index.html
```

### CI Testing

```bash
# Pre-commit Hooks lokal ausführen
pre-commit run --all-files

# Type Checking
uv run mypy src/

# Code Quality Check
uv run ruff check src/
uv run bandit -r src/

# Security Check
uv run detect-secrets scan --all-files
```

### Load Testing

```bash
# Locust Load Testing
uv run locust -f tests/performance/locustfile.py --host=http://localhost:8000

# Specific scenarios
uv run locust -f tests/performance/locustfile.py --users 100 --spawn-rate 10 -t 5m
```

## 📊 Quality Metrics

### Target Metrics

| Kategorie              | Zielwert | Aktuell | Status       |
| ---------------------- | -------- | ------- | ------------ |
| **Test Coverage**      | >95%     | 87%     | 🔄 In Arbeit |
| **Unit Tests**         | >500     | 234     | 🔄 In Arbeit |
| **API Response Time**  | <2s      | 1.2s    | ✅ Erreicht  |
| **Code Quality Score** | A        | B+      | 🔄 In Arbeit |
| **Security Issues**    | 0        | 0       | ✅ Erreicht  |

### Continuous Quality Monitoring

- **Daily**: Automatische Tests über GitHub Actions
- **Weekly**: Performance-Benchmarks und Regressionstests
- **Monthly**: Code Quality Review und Refactoring
- **Quarterly**: Security Audit und Dependency Updates

---

_Dieses Dokument wird kontinuierlich aktualisiert, um den sich entwickelnden Testing-Anforderungen des Projekts gerecht zu werden._
