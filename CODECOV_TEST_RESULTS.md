# Codecov Test Results Integration

## Übersicht

Diese Konfiguration implementiert die vollständige Codecov Test Results Integration für bessere Test-Transparenz und Fehlererkennung in Pull Requests.

## Implementierte Änderungen

### 1. JUnit XML Output (pytest Konfiguration)

In `pyproject.toml` wurde die pytest-Konfiguration erweitert:

```toml
addopts = [
    "--strict-markers",
    "--strict-config",
    "--verbose",
    "--tb=short",
    "--cov=src",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
    "--junitxml=junit.xml",          # ← NEU: JUnit XML generieren
    "-o", "junit_family=legacy",     # ← NEU: Legacy XML Format
]
```

Dies generiert eine `junit.xml` Datei mit detaillierten Testergebnissen.

### 2. Test Results Action (CI/CD Pipeline)

In `.github/workflows/ci.yml` wurde hinzugefügt:

```yaml
- name: Upload test results to Codecov
  if: ${{ !cancelled() }}
  uses: codecov/test-results-action@v1
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
```

Diese Action:

- ✅ Läuft auch bei gecancelten Jobs (`!cancelled()`)
- ✅ Lädt JUnit XML automatisch zu Codecov hoch
- ✅ Verwendet den bereits konfigurierten `CODECOV_TOKEN`

## Vorteile der Integration

### 📊 **Test Results Dashboard**

- Übersicht über alle Test-Läufe
- Historische Test-Trends
- Flaky Test Detection

### 🔍 **Pull Request Comments**

- Automatische Kommentare bei fehlgeschlagenen Tests
- Detaillierte Fehlerbeschreibungen
- Vergleich mit Base Branch

### 🎯 **Fehlgeschlagene Tests Dashboard**

- Zentrale Ansicht aller Failures
- Kategorisierung nach Test-Typen
- Performance-Metriken

## Generierte Dateien

Bei jedem Test-Lauf werden erstellt:

- **`junit.xml`**: Test-Ergebnisse im JUnit-Format
- **`coverage.xml`**: Code-Coverage-Report
- **`htmlcov/`**: HTML-Coverage-Report (lokal)

## Verwendung

### Lokale Tests

```bash
# Tests mit JUnit XML ausführen
uv run pytest

# Nur Coverage (ohne JUnit)
uv run pytest --cov=src --cov-report=xml
```

### CI/CD

Die Integration läuft automatisch bei:

- ✅ Push zu `main` oder `develop`
- ✅ Pull Requests zu `main`
- ✅ Renovate Dependency Updates

## Troubleshooting

### JUnit XML wird nicht generiert

```bash
# Überprüfung der pytest-Konfiguration
uv run pytest --help | grep junit

# Manueller Test
uv run pytest --junitxml=test-junit.xml
```

### Codecov Token Probleme

1. Repository Token in [codecov.io](https://codecov.io) überprüfen
2. GitHub Secret `CODECOV_TOKEN` validieren
3. Workflow-Logs auf Codecov-Errors prüfen

## Links

- [Codecov Test Results Docs](https://docs.codecov.com/docs/test-result-insights)
- [JUnit XML Format](https://llg.cubic.org/docs/junit/)
- [pytest JUnit Integration](https://docs.pytest.org/en/latest/how-to/output.html#creating-junitxml-format-files)
