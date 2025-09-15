# 🎯 VNB Digitaler - Qualitätsstandards & Entwicklungsrichtlinien

> **📋 Test-Anforderungen**: [TESTING_REQUIREMENTS.md](./TESTING_REQUIREMENTS.md) - Coverage & Test-Standards
> **🧪 Test-Dokumentation**: [TESTING.md](../specs/TESTING.md) - Umfassende Test-Strategien
> **⚙️ Technische Spezifikation**: [SPECIFICATION.md](../specs/SPECIFICATION.md) - Projekt-Architektur

## 📋 Inhaltsverzeichnis

1. [Code-Qualität Standards](#code-qualität-standards)
2. [Pre-commit Pipeline](#pre-commit-pipeline)
3. [Testing & Coverage](#testing--coverage)
4. [Entwicklungs-Workflow](#entwicklungs-workflow)
5. [CI/CD Integration](#cicd-integration)

---

## Code-Qualität Standards

### 🔧 Code Formatter & Linter

| Tool         | Zweck                    | Status   | Pre-commit Stage |
| ------------ | ------------------------ | -------- | ---------------- |
| **Black**    | Python Code Formatting   | ✅ Aktiv | pre-commit       |
| **isort**    | Import Sorting           | ✅ Aktiv | pre-commit       |
| **Ruff**     | Fast Python Linter       | ✅ Aktiv | pre-commit       |
| **Prettier** | Markdown/JSON Formatting | ✅ Aktiv | pre-commit       |

### 📝 Dokumentation Standards

| Tool             | Zweck                    | Status   | Pre-commit Stage |
| ---------------- | ------------------------ | -------- | ---------------- |
| **pydocstyle**   | Python Docstring Linting | ✅ Aktiv | pre-commit       |
| **markdownlint** | Markdown Linting         | ✅ Aktiv | pre-commit       |

### 🔒 Sicherheit & Compliance

| Tool               | Zweck                    | Status   | Pre-commit Stage |
| ------------------ | ------------------------ | -------- | ---------------- |
| **Bandit**         | Security Issue Detection | ✅ Aktiv | pre-commit       |
| **detect-secrets** | Secret Detection         | ✅ Aktiv | pre-commit       |

### 🧪 Testing & Coverage

| Tool               | Zweck                  | Status   | Pre-commit Stage |
| ------------------ | ---------------------- | -------- | ---------------- |
| **pytest**         | Unit/Integration Tests | ✅ Aktiv | pre-commit       |
| **pytest-cov**     | Coverage Measurement   | ✅ Aktiv | pre-commit       |
| **pytest-asyncio** | Async Test Support     | ✅ Aktiv | -                |

---

## Pre-commit Pipeline

### 🚦 Quality Gates

#### Pre-commit (bei jedem Commit)

```yaml
✅ Code Formatting (black, isort, prettier)
✅ Linting (ruff, pydocstyle, markdownlint)
✅ Security Checks (bandit, detect-secrets)
✅ File Checks (trailing whitespace, yaml/json syntax)
✅ Fast Tests (pytest, Coverage ≥ 60%)
```

#### Pre-push (vor jedem Push)

```yaml
✅ Alle Pre-commit Checks
✅ Full Test Suite (pytest, Coverage ≥ 50%)
✅ Integration Tests
```

### ⚙️ Hook-Konfiguration

```yaml
# .pre-commit-config.yaml
repos:
  # Standard Hooks
  - repo: https://github.com/pre-commit/pre-commit-hooks
  # Python Formatters
  - repo: https://github.com/psf/black
  - repo: https://github.com/pycqa/isort
  # Linters
  - repo: https://github.com/astral-sh/ruff-pre-commit
  - repo: https://github.com/PyCQA/pydocstyle
  # Security
  - repo: https://github.com/PyCQA/bandit
  - repo: https://github.com/Yelp/detect-secrets
  # Testing
  - repo: local
    hooks:
      - id: pytest-coverage
      - id: pytest-full-coverage
      - id: pytest-fast
```

---

## Testing & Coverage

### 📊 Coverage-Ziele

| Test-Kategorie   | Ziel-Coverage | Minimum (Pre-commit) | Minimum (CI/CD) |
| ---------------- | ------------- | -------------------- | --------------- |
| **Unit Tests**   | 85%           | 60%                  | 80%             |
| **Integration**  | 70%           | 50%                  | 65%             |
| **Gesamt-Suite** | 80%           | 50%                  | 75%             |

### 🏷️ Test-Kategorien

```python
# Pytest Marker
@pytest.mark.unit        # Schnelle Unit Tests
@pytest.mark.integration # Datenbank/API Tests
@pytest.mark.slow        # E2E/Performance Tests
```

### 🚀 Test-Execution

```bash
# Entwicklung: Schnelle Tests
pre-commit run pytest-fast --hook-stage manual

# Commit: Standard Test-Suite mit Coverage
pre-commit run pytest-coverage

# Push: Vollständige Test-Suite
pre-commit run pytest-full-coverage --hook-stage pre-push
```

---

## Entwicklungs-Workflow

### 🔄 Standard Development Flow

#### 1. Feature Development

```bash
# Setup
git checkout -b feature/new-feature
uv sync --dev

# Entwicklung mit kontinuierlichen Tests
pre-commit run pytest-fast --hook-stage manual

# Code-Änderungen
# ... entwickeln ...

# Vor Commit: Qualitätschecks
pre-commit run --all-files
```

#### 2. Quality Assurance

```bash
# Commit: Automatische Pre-commit Hooks
git commit -m "feat: implement new feature"

# Vor Push: Vollständige Test-Suite
pre-commit run pytest-full-coverage --hook-stage pre-push

# Push: Trigger CI/CD Pipeline
git push origin feature/new-feature
```

#### 3. Merge Process

```bash
# Pull Request: CI/CD Validation
# - Alle Pre-commit Hooks
# - Erweiterte Test-Suite
# - Coverage ≥ 75%
# - Sicherheits-Scans

# Merge: Protected Main Branch
# - Review erforderlich
# - Alle Checks bestanden
```

### 🛠️ Development Tools

#### lokale Coverage Reports

```bash
# HTML Coverage Report
uv run pytest --cov=src --cov-report=html
open htmlcov/index.html

# Terminal Coverage Report
uv run pytest --cov=src --cov-report=term-missing
```

#### Test-Performance Monitoring

```bash
# Test-Timing Analysis
uv run pytest --durations=10

# Memory Usage Analysis
uv run pytest --profile-svg
```

---

## CI/CD Integration

### 🔧 GitHub Actions Pipeline

#### Test Workflow (`.github/workflows/test.yml`)

```yaml
name: Tests & Quality
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3

      # Pre-commit Checks
      - name: Run pre-commit
        run: pre-commit run --all-files

      # Extended Testing
      - name: Run full test suite
        run: |
          uv run pytest --cov=src --cov-fail-under=75 \
                         --cov-report=xml --cov-report=term

      # Coverage Upload
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

#### Security Workflow (`.github/workflows/security.yml`)

```yaml
name: Security Scan
on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Dependency Vulnerability Scan
      - name: Run Bandit Security Lint
        run: uv run bandit -r src/

      # Secret Detection
      - name: Detect Secrets
        run: detect-secrets scan --all-files
```

### 📊 Quality Metrics Dashboard

#### Coverage Tracking

- **Codecov Integration**: Automatisches Coverage Tracking
- **Trend Analysis**: Coverage-Entwicklung über Zeit
- **PR Coverage**: Diff-Coverage für Pull Requests

#### Code Quality Metrics

- **Ruff Violations**: Code Quality Issues
- **Security Issues**: Bandit Findings
- **Test Performance**: Execution Time Trends

---

## 🎯 Qualitätsziele

### Kurze Ziele (nächsten 4 Wochen)

- [ ] **Coverage ≥ 70%**: Basis-Testabdeckung erreichen
- [ ] **Zero Security Issues**: Alle Bandit-Warnungen beheben
- [ ] **CI/CD Stabilität**: Alle Workflows grün
- [ ] **Documentation Complete**: Alle Module dokumentiert

### Mittelfristige Ziele (nächsten 3 Monate)

- [ ] **Coverage ≥ 85%**: Hohe Testabdeckung
- [ ] **Performance Benchmarks**: Automatisierte Performance-Tests
- [ ] **Load Testing**: Stress-Tests für API Endpoints
- [ ] **Security Hardening**: Advanced Security Scans

### Langfristige Ziele (nächsten 6 Monate)

- [ ] **100% Type Coverage**: Vollständige Type Annotations
- [ ] **Mutation Testing**: Advanced Test Quality Validation
- [ ] **Chaos Engineering**: Resilience Testing
- [ ] **Automated Security Updates**: Dependabot + Auto-merge

---

## 🚨 Eskalationspfade

### Quality Gate Failures

#### Pre-commit Failure

```bash
# Automatische Fixes versuchen
pre-commit run --all-files

# Manuelle Fixes für spezifische Issues
black src/        # Code formatting
isort src/        # Import sorting
ruff check --fix src/  # Auto-fixable issues
```

#### Coverage Drop

```bash
# Coverage Gap Analysis
uv run pytest --cov=src --cov-report=html
# Review htmlcov/index.html für Details

# Neue Tests hinzufügen
# Tests für uncovered code schreiben
# Coverage wieder über Minimum bringen
```

#### Security Issues

```bash
# Bandit Issues Review
uv run bandit -r src/ -f json

# Issue Classification:
# - High: Sofortige Behebung erforderlich
# - Medium: Behebung in nächstem Release
# - Low: Monitoring und Documentation
```

---

_Diese Dokumentation definiert die Qualitätsstandards und Entwicklungsrichtlinien für das VNB Digitaler Projekt._
