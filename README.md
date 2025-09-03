# VNB Digitaler

[![Open in Coder](https://img.shields.io/badge/Open%20in-Coder-blue?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTIgMTJMMTIgMkwyMiAxMkwxMiAyMkwyIDEyWiIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+CjxwYXRoIGQ9Ik04IDEyTDE2IDEyIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K)](https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=vnbdigitaler&machine=basicLinux32gb&devcontainer_path=.devcontainer%2Fdevcontainer.json&location=WestEurope)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL 16+](https://img.shields.io/badge/postgresql-16+-blue.svg)](https://www.postgresql.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Security: bandit](https://img.shields.io/badge/security-bandit-green.svg)](https://github.com/PyCQA/bandit)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

Streamlit-Anwendung zur Verwaltung und Analyse von deutschen Verteilnetzbetreiber-Daten (VNB) mit PostgreSQL-Backend.

## 🚀 Quick Start

```bash
# Entwicklungsumgebung mit DevContainer starten
# Datenbank initialisieren
uv run python scripts/init_database.py

# Test-Daten einfügen (optional)
uv run python scripts/seed_test_data.py

# Anwendung starten
uv run streamlit run streamlit_app.py
```

## 📋 Überblick

Diese Anwendung ermöglicht die Verwaltung und Analyse von:

- VNB-Daten und -Territorien mit PostgreSQL-Backend
- Rollout-Quoten und -Berichte mit erweiterten Analytics
- Smart Meter Ausbaupläne mit Geo-Daten
- Geographische Visualisierungen mit JSONB-Service-Territorien
- Datenqualitäts-Tracking und Import-Logs

## 🛠️ Entwicklung

### Voraussetzungen

- Python 3.11+
- PostgreSQL 16+ (automatisch via DevContainer verfügbar)
- uv (Package Manager)
- Docker/DevContainer Support

### DevContainer Setup

Das Projekt nutzt einen DevContainer mit integrierten PostgreSQL und uv Features:

```bash
# DevContainer öffnen (VS Code)
# PostgreSQL läuft automatisch auf Port 5432
# Datenbank: vnbdigitaler
# User: postgres (ohne Passwort für Entwicklung)
```

### Manuelle Entwicklungsumgebung

```bash
# Repository klonen
git clone https://github.com/the78mole/vnbdigitaler.git
cd vnbdigitaler

# Dependencies installieren
uv sync

# PostgreSQL-Server starten (falls nicht via DevContainer)
# Umgebungsvariablen setzen
export DATABASE_URL="postgresql+asyncpg://postgres@localhost:5432/vnbdigitaler"
export POSTGRES_USER="postgres"
export POSTGRES_DB="vnbdigitaler"

# Datenbank initialisieren
uv run python scripts/init_database.py

# Entwicklungsserver starten
uv run streamlit run streamlit_app.py
```

## 🗄️ Datenbank-Schema

### PostgreSQL-Features

Das System nutzt erweiterte PostgreSQL-Features:

- **JSONB-Spalten**: Flexible Speicherung von Metadaten und GeoJSON-Territorien
- **Full-Text-Search**: Deutsche Volltextsuche in Unternehmensdaten
- **Trigram-Suche**: Ähnlichkeitssuche für Unternehmensnamen
- **Performance-Indices**: Optimierte Abfragen für große Datensätze
- **Change Tracking**: Vollständiges Auditing aller Datenänderungen

### Haupttabellen

- `bdew_companies`: BDEW-Unternehmensdaten mit JSONB-Territorien
- `bdew_import_logs`: Erweiterte Import-Logs mit Metadaten
- `bdew_validation_rules`: Flexible Validierungsregeln
- `bdew_data_history`: Change-Tracking für Auditing

### Datenbank-Operationen

```bash
# Datenbank zurücksetzen
uv run python scripts/init_database.py

# Test-Daten laden
uv run python scripts/seed_test_data.py

# Datenbank-Status prüfen
psql postgresql://postgres@localhost:5432/vnbdigitaler -c "\dt"
```

## 🏗️ Architektur

### Repository Pattern

Das System verwendet das Repository-Pattern für Datenzugriff:

```python
from database import DatabaseManager
from repositories.bdew import BDEWRepository

# Async Database Operations
async with DatabaseManager().get_session() as session:
    repo = BDEWRepository(session)
    companies = await repo.search_companies_fulltext("München")
```

### Async/Sync Support

- **Async**: Für Performance-kritische Operationen
- **Sync**: Für einfache Streamlit-Integration
- **Connection Pooling**: Automatische Verbindungsoptimierung

## 🔍 Erweiterte Features

### Full-Text-Suche

```python
# Deutsche Volltextsuche
companies = await repo.search_companies_fulltext(
    search_term="Stadtwerke München",
    min_quality_score=80
)
```

### Geo-Queries

```python
# Unternehmen in geografischer Nähe
nearby = await repo.find_companies_by_location(
    latitude=48.1351,
    longitude=11.5820,
    radius_km=50
)
```

### JSONB-Operationen

```python
# Service-Territory mit GeoJSON speichern
await repo.update_service_territory(
    company_id=company.id,
    geojson_data={
        "type": "Feature",
        "geometry": {...},
        "properties": {...}
    }
)
```

### Change Tracking

```python
# Datenänderungen verfolgen
await repo.track_data_change(
    company_id=company.id,
    change_type="UPDATE",
    old_values=old_data,
    new_values=new_data,
    changed_by="user@example.com"
)
```

## 📊 Datenqualität

### Qualitäts-Scoring

Das System berechnet automatisch Datenqualitäts-Scores basierend auf:

- Vollständigkeit der Pflichtfelder
- Validität von Email/Telefon/Website
- Verfügbarkeit von Geo-Koordinaten
- Konsistenz der Adressdaten

### Analytics

```python
# Qualitätsverteilung abrufen
stats = await repo.get_quality_distribution()
# {
#   "total_companies": 1500,
#   "average_quality_score": 85.2,
#   "high_quality_count": 1200,
#   "with_coordinates_count": 1350
# }
```

## 📚 Dokumentation

Die ausführliche Dokumentation befindet sich im [`docs/`](docs/) Verzeichnis.

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) Datei.

Helft also alle mit und steuert Daten über GitHub Pull-Requests bei.

Dieser Service basiert auf der kostenlosen Version von Streamlit.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://movies-dataset-template.streamlit.app/)

### Auf dem eigenen Rechner ausführen

1. uv installieren

   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. Dependencies installieren

   ```bash
   uv sync
   ```

3. App starten

   ```bash
   uv run streamlit run streamlit_app.py
   ```

## 🤖 BNetzA Smart Meter Tools

Das Projekt enthält automatisierte Tools zum Download und zur Analyse von BNetzA Smart Meter Daten:

### Tools Übersicht

1. **`01_download_bnetza_data.py`** - Lädt BNetzA Artikel-Seite herunter und extrahiert Excel-URLs
2. **`02_find_roll_out_report.py`** - Verwendet KI zur Identifikation von Roll-Out-Quoten-Berichten

### Automatisierte GitHub Actions Workflows

Das Projekt nutzt eine modulare GitHub Actions Architektur für automatisierte Datenaktualisierungen:

#### 🔄 Central Data Update

- **Zeitplan**: Täglich um 6:00 UTC (8:00 CEST)
- **Manuell**: Über GitHub Actions Workflow Dispatch
- **Orchestriert**: Alle automatisierten Datenaktualisierungen

#### 📊 Rollout Update System

Modulare Architektur mit spezialisierten Workflows:

- **`reusable-rollout-update.yml`** - Hauptkoordinator für BNetzA Rollout-Daten
  - **`reusable-rollout-company-update.yml`** - Company Matching & Management
  - **`reusable-rollout-quota-update.yml`** - Rollout-Quoten-Verarbeitung

#### 🛠️ Supporting Scripts

- **`.github/scripts/check_reports.py`** - BNetzA Report-Überprüfung
- **`.github/scripts/enhanced_update.py`** - Erweiterte Update-Verarbeitung
- **`.github/scripts/extract_stats.py`** - Statistik-Extraktion
- **`.github/scripts/format_companies.py`** - Company-Listen-Formatierung

#### 📋 Features

- ✅ **Automatische Datenaktualisierung** aus BNetzA Quellen
- ✅ **String-basiertes Company Matching** (in Entwicklung)
- ✅ **Detaillierte Berichterstattung** mit GitHub Actions Summaries
- ✅ **Fehlerbehandlung** mit automatischen Issue-Erstellungen
- ✅ **Modulare Architektur** für einfache Wartung und Tests
- ✅ **Semantic Versioning** mit automatischen Releases

#### 🏷️ Automatic Releases

Das System erstellt automatisch semantische Versionen basierend auf Commit-Messages:

- **Major Releases** (v1.x.x → v2.0.0): Breaking Changes mit `!` oder `BREAKING CHANGE`
- **Minor Releases** (v1.2.x → v1.3.0): Features mit `feat:`, `fix:`, `refactor:`
- **Patch Releases** (v1.2.3 → v1.2.4): Dokumentation, Wartung, Tests

**Release Contents:**

- 📊 Excel-Dateien (Original BNetzA-Berichte)
- 📄 CSV-Dateien (Konvertierte Daten für API-Integration)
- 📋 JSON-Zusammenfassungen (Metadaten und Statistiken)
- 📝 Automatische Release-Notes mit Update-Details

Siehe: [Semantic Versioning Guide](.github/SEMANTIC_VERSIONING.md)

Weitere Details: [GitHub Actions Architecture Documentation](docs/GITHUB_ACTIONS_ARCHITECTURE.md)

### Verwendung

```bash
# 1. BNetzA Daten herunterladen
uv run tools/01_download_bnetza_data.py

# 2. Roll-Out-Bericht mit KI identifizieren
uv run tools/02_find_roll_out_report.py

# Oder direkt mit Pipeline:
uv run tools/01_download_bnetza_data.py && uv run tools/02_find_roll_out_report.py
```

### Konfiguration

Die Tools verwenden das `tmp/` Verzeichnis im Workspace für temporäre Dateien:

- Downloads werden nach `tmp/bnetza_download_YYYYMMDD_HHMMSS/` gespeichert
- Automatische Erkennung der neuesten Download-Session
- Persistent und nachvollziehbar (nicht randomisiert wie system temp)

Für KI-Features siehe: [`docs/API_KEY_SETUP.md`](docs/API_KEY_SETUP.md)

## Datenherkunft

Die Daten stammen von der Bundesnetzagentur und den Preisblättern der einzelnen Netzbetreiber:

- [BNetzA iMSys Rollout Report](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/NetzzugangMesswesen/Mess-undZaehlwesen/iMSys/artikel.html).
- [Netzbetreibernummern](https://bdew-codes.de/Codenumbers/ElectricityGridOperatorCodes/ElectricityGridCodeNumbers)

# Datenimport

## Verteilnetzbetreiber

Der Datenimport der Netzbetreibernummern erfolgt einfach über den Download des Excel-Files (siehe Netzbetreibernummern oben), Copy-Paste in eine Textdate (Tabulator-separiert) und dann ein ausführen des Helfer Skripts:

```bash
python tools/convert_vnbtsv_to_pgsql.py "tab-seperated-file" > tmp_out.pgsql
```

Den Text dann einfach als Statement in PostgreSQL ausführen (z.B. im SQL-Editor im Neon-Projekt). Sollten sich die Daten einer Verteilnetzbetreibernummer ändern, werden diese aktualisiert. Bei gleichen Betreibern für verschiedene Betreibernummern erfolgt eine Warnung bei der Konvertierung. Doppelte VNB-Nummern werden ignoriert und ebenfalls eine Warnung ausgegeben.

## Rollout-Quoten

Die Rollout-Quoten werden automatisch über GitHub Actions verwaltet:

### 🤖 Automatisierte Verarbeitung

- **Entdeckung**: Neue BNetzA-Berichte werden automatisch erkannt und heruntergeladen
- **Verarbeitung**: Excel-Dateien werden zu CSV konvertiert und in die Datenbank importiert
- **Company-Matching**: BNetzA-Unternehmen werden automatisch mit BDEW-Einträgen abgeglichen
- **Aktualisierung**: Quartalsweise Aktualisierung der Rollout-Quoten in der Datenbank

### 📊 Status-Kategorien

Nach der Verarbeitung werden Unternehmen in folgende Kategorien eingeordnet:

- **Up-to-date**: Unternehmen mit aktuellen Daten (keine Änderung gegenüber vorherigem Lauf)
- **Updated**: Unternehmen mit geänderten Rollout-Quoten
- **New**: Neu hinzugekommene Unternehmen in den BNetzA-Berichten
- **Not in current report**: Unternehmen, die im aktuellen Bericht nicht mehr enthalten sind

### � Workflow-Konfiguration

Die Automatisierung läuft über GitHub Actions Workflows in `.github/workflows/`:

- `reusable-rollout-update.yml` - Hauptkoordinator
- `reusable-rollout-quota-update.yml` - Rollout-Quoten-Verarbeitung
- `reusable-rollout-company-update.yml` - Company-Matching

Manuelle Ausführung über die GitHub Actions Weboberfläche möglich.

## 🏭 BDEW-Integration (Phase 2)

Die BDEW-Integration ermöglicht die automatisierte Verarbeitung und Verwaltung von BDEW-Unternehmensdaten mit vollständiger Pipeline-Unterstützung.

### 📊 Verfügbare Module

- **Database Models**: SQLAlchemy-basierte Datenbankmodelle für BDEW-Daten
- **Repository Pattern**: Strukturierte Datenzugriffsmuster mit CRUD-Operationen
- **Import Pipeline**: 4-stufige Verarbeitungspipeline für BDEW-Datenimporte
- **Validierung**: Umfassende Datenvalidierung und Qualitätsprüfung

### 🛠️ Manuelle Verwendung

#### 1. Python-Umgebung vorbereiten

```bash
# Dependencies installieren und Shell aktivieren
uv sync
uv shell
```

#### 2. BDEW-Pipeline ausführen

```python
import asyncio
from src.pipelines.core import PipelineManager
from src.pipelines.bdew_import import BDEWImportPipeline

async def run_bdew_import():
    """BDEW-Daten importieren und verarbeiten"""

    # Pipeline-Manager initialisieren
    manager = PipelineManager()

    # BDEW-Import-Pipeline erstellen
    pipeline = BDEWImportPipeline()

    # Pipeline ausführen
    context = {
        'source_file': 'data/bdew_companies.csv',  # Pfad zur BDEW-Datei
        'validation_rules': {
            'require_name': True,
            'require_location': True,
            'max_name_length': 200
        }
    }

    result = await manager.execute_pipeline(pipeline, context)

    if result.success:
        print(f"✅ Import erfolgreich: {result.metadata}")
    else:
        print(f"❌ Import fehlgeschlagen: {result.error}")

# Pipeline ausführen
asyncio.run(run_bdew_import())
```

#### 3. Repository für Datenzugriff verwenden

```python
from src.repositories.bdew import BDEWRepository
from src.database import get_session

def search_companies():
    """BDEW-Unternehmen durchsuchen"""

    with get_session() as session:
        repo = BDEWRepository(session)

        # Alle Unternehmen abrufen
        all_companies = repo.get_all()
        print(f"Gefunden: {len(all_companies)} Unternehmen")

        # Nach Namen suchen
        search_results = repo.search_by_name("Stadtwerke")
        print(f"Stadtwerke gefunden: {len(search_results)}")

        # Nach PLZ filtern
        regional_companies = repo.get_by_postal_code("80333")
        print(f"München (80333): {len(regional_companies)} Unternehmen")

        # Datenqualität prüfen
        quality_stats = repo.get_data_quality_stats()
        print(f"Qualität: {quality_stats}")

search_companies()
```

#### 4. Direkte Datenbankoperationen

```python
from src.models.bdew import BDEWCompany
from src.database import get_session

def manual_data_operations():
    """Manuelle Datenbankoperationen"""

    with get_session() as session:
        # Neues Unternehmen erstellen
        new_company = BDEWCompany(
            name="Beispiel Stadtwerke GmbH",
            bdew_id="12345",
            street="Musterstraße 1",
            postal_code="12345",
            city="Musterstadt",
            phone="+49 123 456789",
            email="info@beispiel-stadtwerke.de",
            website="https://www.beispiel-stadtwerke.de"
        )

        session.add(new_company)
        session.commit()
        print(f"✅ Unternehmen erstellt: {new_company.id}")

        # Unternehmen suchen und aktualisieren
        company = session.query(BDEWCompany).filter_by(bdew_id="12345").first()
        if company:
            company.phone = "+49 123 456790"  # Telefonnummer aktualisieren
            session.commit()
            print(f"✅ Unternehmen aktualisiert: {company.name}")

        # Batch-Operations
        companies_in_berlin = session.query(BDEWCompany).filter(
            BDEWCompany.city.ilike("%Berlin%")
        ).all()
        print(f"Berlin: {len(companies_in_berlin)} Unternehmen")

manual_data_operations()
```

#### 5. Datenvalidierung und -bereinigung

```python
from src.pipelines.bdew_import import BDEWValidationStep
from src.models.bdew import BDEWValidationRule

def validate_data():
    """Datenvalidierung durchführen"""

    # Validierungsregeln definieren
    rules = [
        BDEWValidationRule(
            field_name="name",
            rule_type="required",
            rule_value="true"
        ),
        BDEWValidationRule(
            field_name="email",
            rule_type="format",
            rule_value="email"
        )
    ]

    # Validierung ausführen
    validator = BDEWValidationStep()

    sample_data = {
        'name': 'Test Stadtwerke',
        'email': 'invalid-email',  # Ungültiges Format
        'city': 'Teststadt'
    }

    is_valid, errors = validator.validate_record(sample_data, rules)

    if is_valid:
        print("✅ Daten sind valide")
    else:
        print(f"❌ Validierungsfehler: {errors}")

validate_data()
```

#### 6. Import-Logs und Monitoring

```python
from src.models.bdew import BDEWImportLog
from src.database import get_session
from datetime import datetime, timedelta

def check_import_status():
    """Import-Status und -Logs überprüfen"""

    with get_session() as session:
        # Letzte Imports anzeigen
        recent_imports = session.query(BDEWImportLog).filter(
            BDEWImportLog.timestamp >= datetime.now() - timedelta(days=7)
        ).order_by(BDEWImportLog.timestamp.desc()).all()

        print(f"Imports der letzten 7 Tage: {len(recent_imports)}")

        for import_log in recent_imports[:5]:  # Top 5 anzeigen
            status = "✅" if import_log.success else "❌"
            print(f"{status} {import_log.timestamp}: {import_log.records_processed} Datensätze")
            if import_log.error_message:
                print(f"   Fehler: {import_log.error_message}")

        # Erfolgsstatistiken
        total_imports = len(recent_imports)
        successful_imports = len([log for log in recent_imports if log.success])
        success_rate = (successful_imports / total_imports * 100) if total_imports > 0 else 0

        print(f"Erfolgsrate: {success_rate:.1f}% ({successful_imports}/{total_imports})")

check_import_status()
```

### 🧪 Tests ausführen

```bash
# Alle BDEW-Tests ausführen
uv run python -m pytest tests/test_bdew_integration.py -v

# Spezifische Test-Kategorien
uv run python -m pytest tests/test_bdew_integration.py::TestBDEWRepository -v
uv run python -m pytest tests/test_bdew_integration.py::TestBDEWSearch -v

# Mit Coverage-Report
uv run python -m pytest tests/test_bdew_integration.py --cov=src.repositories.bdew --cov=src.models.bdew
```

### 📁 Verzeichnisstruktur

```
src/
├── models/
│   └── bdew.py              # SQLAlchemy-Datenbankmodelle
├── repositories/
│   └── bdew.py              # Repository-Pattern für Datenzugriff
└── pipelines/
    └── bdew_import.py       # 4-stufige Import-Pipeline

tests/
└── test_bdew_integration.py # Umfassende Test-Suite
```

### 🔧 Konfiguration

Die BDEW-Integration nutzt die Standard-Datenbankverbindung:

```python
# In src/database.py konfiguriert
DATABASE_URL = "postgresql://user:password@localhost/vnbdigitaler"
```

Für lokale Entwicklung wird automatisch SQLite verwendet (siehe Tests).

````
