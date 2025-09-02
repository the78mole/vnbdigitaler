# VNB Digitaler

Streamlit-Anwendung zur Verwaltung und Analyse von deutschen Verteilnetzbetreiber-Daten (VNB).

## 🚀 Quick Start

```bash
# Mit uv (empfohlen)
uv run streamlit run streamlit_app.py

# Oder mit pip
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 📋 Überblick

Diese Anwendung ermöglicht die Verwaltung und Analyse von:

- VNB-Daten und -Territorien
- Rollout-Quoten und -Berichte
- Smart Meter Ausbaupläne
- Geographische Visualisierungen

## 🛠️ Entwicklung

### Voraussetzungen

- Python 3.11+
- PostgreSQL (für Produktionsdatenbank)
- uv (Package Manager)

### Setup

```bash
# Repository klonen
git clone https://github.com/the78mole/vnbdigitaler.git
cd vnbdigitaler

# Dependencies installieren
uv sync

# Entwicklungsserver starten
uv run streamlit run streamlit_app.py
```

## 📚 Dokumentation

Die ausführliche Dokumentation befindet sich im [`docs/`](docs/) Verzeichnis.

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) Datei.

Helft also alle mit und steuert Daten über GitHub Pull-Requests bei.

Dieser Service basiert auf der kostenlosen Version von Streamlit.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://movies-dataset-template.streamlit.app/)

### Auf dem eigenen Rechner ausführen

1. uv installieren (empfohlen)

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

#### Alternative mit pip

1. Python Virtual Environment erstellen

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # oder
   venv\Scripts\activate     # Windows
   ```

2. Dependencies installieren

   ```bash
   pip install -e ".[dev]"
   ```

3. App starten

   ```bash
   streamlit run streamlit_app.py
   ```

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
