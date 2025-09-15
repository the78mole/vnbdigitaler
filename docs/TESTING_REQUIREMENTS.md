# 🧪 VNB Digitaler - Testing Requirements & Coverage Standards

> **🧪 Test-Dokumentation**: [TESTING.md](./specs/TESTING.md) - Umfassende Test-Strategien
> **⚙️ Technische Spezifikation**: [SPECIFICATION.md](./specs/SPECIFICATION.md) - Projekt-Architektur

## 📋 Inhaltsverzeichnis

1. [Coverage-Anforderungen](#coverage-anforderungen)
2. [Pre-commit Test-Hooks](#pre-commit-test-hooks)
3. [Test-Kategorien](#test-kategorien)
4. [Qualitätsstandards](#qualitätsstandards)

---

## Coverage-Anforderungen

### Mindest-Coverage-Standards

| Test-Typ              | Coverage-Ziel | Pre-commit Minimum | Beschreibung                          |
| --------------------- | ------------- | ------------------ | ------------------------------------- |
| **Unit Tests**        | 85%           | 60%                | Isolierte Komponenten-Tests           |
| **Integration Tests** | 70%           | 50%                | Service-übergreifende Tests           |
| **Full Test Suite**   | 80%           | 50%                | Alle Tests inklusive slow/integration |

### Coverage-Ausnahmen

Bestimmte Code-Bereiche sind von den Coverage-Anforderungen ausgenommen:

```python
# In pyproject.toml [tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "if settings.DEBUG",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod",
]
```

### Ausgeschlossene Verzeichnisse

```python
# In pyproject.toml [tool.coverage.run]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/__init__.py",
    "*/migrations/*",
    "*/archive/*",
    "tools/bak/*"
]
```

---

## Pre-commit Test-Hooks

### Aktivierte Test-Hooks

#### 1. pytest-coverage (pre-commit stage)

```yaml
- id: pytest-coverage
  name: pytest with coverage check
  entry: bash -c 'uv run pytest --cov=src --cov-fail-under=60 --cov-report=term-missing:skip-covered --cov-report=xml -m "not slow" || true'
  stages: [pre-commit]
```

**Zweck**: Schnelle Tests bei jedem Commit mit grundlegender Coverage

- **Coverage-Minimum**: 60%
- **Ausgeschlossen**: Tests mit `@pytest.mark.slow`
- **Ausgabe**: Terminal + XML Coverage Report

#### 2. pytest-full-coverage (pre-push stage)

```yaml
- id: pytest-full-coverage
  name: pytest full test suite with coverage
  entry: bash -c 'uv run pytest --cov=src --cov-fail-under=50 --cov-report=term-missing --cov-report=xml || true'
  stages: [pre-push]
```

**Zweck**: Vollständige Test-Suite vor Push

- **Coverage-Minimum**: 50%
- **Umfang**: Alle Tests inklusive Integration und slow tests
- **Ausgabe**: Detaillierter Coverage Report

#### 3. pytest-fast (manual stage)

```yaml
- id: pytest-fast
  name: pytest fast tests only
  entry: bash -c 'uv run pytest -m "not slow and not integration" --maxfail=5 || true'
  stages: [manual]
```

**Zweck**: Schnelle Unit Tests für Entwicklung

- **Ausführung**: `pre-commit run pytest-fast --hook-stage manual`
- **Ausgeschlossen**: `slow` und `integration` Tests
- **Fail-Fast**: Stoppt nach 5 Fehlern

---

## Test-Kategorien

### Pytest Marker

```python
# In pyproject.toml [tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]
```

### Marker-Verwendung

#### Unit Tests (Standard)

```python
def test_company_validation():
    """Fast unit test - keine Marker nötig"""
    pass
```

#### Integration Tests

```python
@pytest.mark.integration
def test_database_integration():
    """Test mit echter Datenbank-Verbindung"""
    pass
```

#### Slow Tests

```python
@pytest.mark.slow
def test_full_pipeline():
    """Langsamer End-to-End Test"""
    pass
```

#### Kombinierte Marker

```python
@pytest.mark.slow
@pytest.mark.integration
def test_complete_workflow():
    """Langsamer Integration Test"""
    pass
```

---

## Qualitätsstandards

### Code Quality Gates

1. **Pre-commit**: Alle Standard-Hooks + Fast Tests müssen bestehen
2. **Pre-push**: Vollständige Test-Suite + Coverage ≥ 50%
3. **CI/CD**: Erweiterte Tests + Coverage ≥ 80% (Ziel)

### Entwicklungs-Workflow

#### Lokale Entwicklung

```bash
# Schnelle Tests während Entwicklung
pre-commit run pytest-fast --hook-stage manual

# Vor Commit: Alle pre-commit Hooks
pre-commit run --all-files

# Vor Push: Vollständige Test-Suite
pre-commit run pytest-full-coverage --hook-stage pre-push
```

#### Coverage Reports

```bash
# Lokaler Coverage Report
uv run pytest --cov=src --cov-report=html
open htmlcov/index.html

# Coverage mit Details
uv run pytest --cov=src --cov-report=term-missing
```

### Kontinuierliche Verbesserung

#### Coverage-Monitoring

- **Wöchentlich**: Review der Coverage-Trends
- **Bei neuen Features**: Tests vor Implementation
- **Bei Refactoring**: Coverage darf nicht sinken

#### Test-Kategorien-Balance

```
    /\     E2E Tests (5%)
   /  \    Integration Tests (15%)
  /____\   Unit Tests (80%)
```

---

## 🚀 Integration mit CI/CD

### GitHub Actions Integration

Die Test-Hooks integrieren sich nahtlos mit der bestehenden CI/CD-Pipeline:

```yaml
# In .github/workflows/test.yml
- name: Run tests with coverage
  run: |
    uv run pytest --cov=src --cov-fail-under=80 --cov-report=xml

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

### Konfiguration anpassen

Coverage-Ziele können bei Bedarf angepasst werden:

```yaml
# Für strengere Standards in .pre-commit-config.yaml
entry: bash -c 'uv run pytest --cov=src --cov-fail-under=75 ...'

# Für Entwicklungsphase (weniger streng)
entry: bash -c 'uv run pytest --cov=src --cov-fail-under=50 ...'
```

---

_Diese Dokumentation definiert die Qualitätsstandards und Test-Anforderungen für das VNB Digitaler Projekt._
