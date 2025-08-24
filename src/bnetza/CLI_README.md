# BNetzA Rollout Report Updater CLI

Dieses Tool automatisiert das Herunterladen und Verarbeiten von BNetzA Roll-out Quoten Berichten.

## Installation

Das Tool ist bereits als Teil des vnbdigitaler Projekts installiert.

## Verwendung

### Grundlegende Syntax

```bash
uv run python -m src.bnetza.rollout_report_updater [Optionen]
```

### Verfügbare Optionen

- `--check-update`: Nur prüfen, ob Updates verfügbar sind (keine Datenbankupdates)
- `--dry-run`: Zeigen, was aktualisiert würde (ohne Datenbankänderungen)
- `--force-update`: Erzwinge Update auch wenn Dateien nicht geändert wurden
- `--download-dir=<dir>`: Verzeichnis für heruntergeladene Dateien (Standard: tmp)
- `--verbose`: Ausführliches Logging aktivieren
- `--help`: Hilfe anzeigen

### Beispiele

#### 1. Prüfen auf neue Berichte

```bash
uv run python -m src.bnetza.rollout_report_updater --check-update
```

#### 2. Dry-Run (zeigt was passieren würde)

```bash
uv run python -m src.bnetza.rollout_report_updater --dry-run
```

#### 3. Normales Update (lädt neue Daten herunter und importiert sie)

```bash
uv run python -m src.bnetza.rollout_report_updater
```

#### 4. Erzwungenes Update mit ausführlichem Logging

```bash
uv run python -m src.bnetza.rollout_report_updater --force-update --verbose
```

#### 5. Update mit spezifischem Download-Verzeichnis

```bash
uv run python -m src.bnetza.rollout_report_updater --download-dir=/path/to/downloads
```

## Workflow

Das Tool führt automatisch folgende Schritte aus:

1. **Discovery**: Überprüft die BNetzA-Website auf neue Rollout-Berichte
2. **Download**: Lädt Excel-Dateien herunter (nur wenn sich Inhalte geändert haben)
3. **Conversion**: Konvertiert Excel-Dateien zu sauberen CSV-Formaten
4. **Import**: Importiert Daten in die PostgreSQL-Datenbank

## Ausgabe

### Erfolgreiche Ausführung

```
🔄 BNetzA Rollout Report Updater
==================================================

🔄 Running regular update...
✅ Update completed successfully!
📊 Final state: Report: Roll-out-Quoten_Q1_2025.xlsx, ETag: e320bfe71b58974b..., Local: Roll-out-Quoten_Q1_2025.xlsx
📊 Imported 518 company quota records
```

### Check-Update Modus

```
🔄 BNetzA Rollout Report Updater
==================================================

🔍 Checking for new reports...
✅ New reports are available
📊 Current state: RolloutReportUpdater (no current report)
```

### Dry-Run Modus

```
🔄 BNetzA Rollout Report Updater
==================================================

🔍 Dry run: Checking what would be updated...
📥 Would discover and download:
✅ Would download:
    Report: Roll-out-Quoten_Q1_2025.xlsx,
    ETag: e320bfe71b58974b...,
    Local: Roll-out-Quoten_Q1_2025.xlsx
🔄 Would convert to: tmp/Roll-out-Quoten_Q1_2025.csv
📊 Would import 518 company quota records
📋 Sample data that would be imported:
   1. Albstadtwerke GmbH: 0.0% (Date: 2025-03-31)
   2. Albwerk GmbH & Co. KG: 0.7% (Date: 2025-03-31)
   3. AllgäuNetz GmbH & Co. KG: 2.1% (Date: 2025-03-31)

🔍 Dry run completed - no changes made to database
```

## Exit Codes

- `0`: Erfolgreiche Ausführung
- `1`: Fehler oder keine neuen Berichte verfügbar (bei --check-update)

## Automatisierung

Das Tool kann problemlos in Cron-Jobs oder anderen Automatisierungssystemen verwendet werden:

```bash
# Täglich um 08:00 nach neuen Berichten suchen und importieren
0 8 * * * cd /path/to/vnbdigitaler && uv run python -m src.bnetza.rollout_report_updater
```

## Datenbanktabellen

Das Tool aktualisiert folgende Tabellen:

- `rollout_companies`: Unternehmensstammdaten
- `rollout_quotas`: Zeitreihen der Ausstattungsquoten
- `rollout_reports`: Metadaten der verarbeiteten Berichte

## Konfiguration

Die Datenbankverbindung wird über Umgebungsvariablen konfiguriert. Siehe `.env` Datei für Details.
