# VNBdigitaler Data Update Workflow System

Dieses System implementiert den **korrekten** Ansatz für die Integration von Daten:

- [ ] **BDEW Companies** Update (**BDEW-Code** = Unique ID eines Netzbetreibers) = Datenbasis
- [ ] **vnbdigital**-Datenintegration (verwendet auch BDEW-Codes als Unique ID)
- [ ] **BNetzA Smart Meter (iMSys) Rollout** Quoten (enthält auch reine Messstellenbetreiber)
- [ ] Integration der **Preisblätter Netzanschluss** jedes Netzbetreibers
- [ ] Integration der **Preisblätter Messtellenbetrieb** jedes Messstellenbetreibers
- [ ] Integration von **Energiepreisen** reiner Energieversorger

- **Fokus**: Rollout-Company-Management (nicht BDEW-Matching)
- **Workflow**: Version → Discover → Download → Convert → Company Management → Quota Updates
- **Architektur**: Saubere, step-basierte GitHub Actions mit JSON-State-Management

## Grundlegende Festlegungen

Alle temporären Files werden in `tmp` abgelegt.

Datenbank-Tabellen:

- `companies`: Tabelle mit Unternehmen aus der BDEW Liste mit `bdew_code`
  - Zusätzlich Integration der vnbdigital-Daten
- `rollout_companies`: Tabelle mit den Messtellenbetreibern aus der BNetzA-Liste
  - Enthält BDEW-Codes als Referenz zu `companies/bdew_code`
- `report_times`: Enthält doe verfügbaren Berichtszeitpunkte (üblicherweise jedes Quartal)
- `rolout_quotas`: Enthält die verfügbaren Rollout-Quoten zu jedem Berichtszeitpunkt zu
  jedem Messstellenbetreiber
- `rollout_update_logs`: Enthält Logs zu jedem Rollout-Update-Versuch mit neuen Daten
- `vnb_price_sheets`: Enthält die Preisblätter der Netzbetreiber
- `msb_price_sheets`: Enthält die Preisblätter der Messstellenbetreiber
- `energy_prices`: Enthält die Energiepreise reiner Energieversorger
  - Jeder Energieversorger kann mehrere Tarife festlegen (auch Haushalts, Gewerbe und Industriestrom)

## 📋 Workflow-Schritte

### BDEW Daten Update

### vnbdigital Daten Update

### Rollout-Daten Update

#### 0. Rollout-Update-Status

- Status Tracking über die Workflow-Steps hinweg in `rollout-update-status.json`
- JSON-File wird vollständig im ersten Schritt erstellt und von weiteren Steps aktualisiert
- Timing-Informationen für jeden Step werden erfasst
  - Timing-Informationen von komplexen Unterschritten werden erfasst

#### 1. Version/Release 🏷️

- Semantic Versioning mit paulhatch/semver
  - Major match: `/^(fix|feat|breaking|major):/`
  - Minor match: `/^(fix|feat|refactor|minor):/`
  - Bump on each commit erhöht Patch-Version
- Anlegen des `rollout-update-status.json`
- Erstellung eines Tags und Releases mit Quelldateien
- Generieren der Summary für diesen Schritt (in Actions-Übersicht + Release Notes)

#### 2. Discover/Document 🔍

- BNetzA-Website nach neuen Rollout-Reports scannen
- Excel-Discovery mit PDF-Screenshots dokumentieren
- Screenshot in Release-Files ablegen
- Aktualisieren des `rollout-update-status.json`

#### 3. Download 📥

- HEAD Request durchführen
- Wenn HEAD-Request-ETag = `DB:rollout_update_logs/excel_file_hash`
  - Download des Excel-Reports
  - Integrität-Checks und Metadaten-Erfassung
  - Prüfen der heruntergeladenen Datei
  - Excel-File in Release-Files ablegen
  - Unchanged in der `rollout-update-status.json` vermerken
  - Rollout-Update beenden
- Wenn neu,

#### 4. Convert 🔄

- Excel → CSV Konvertierung
- Datenvalidierung und -bereinigung

#### 5. Company Management 🏢

- **Neue Companies**: Tracking von neuen Rollout-Unternehmen
- **Fehlende Companies**: Erkennung von nicht mehr enthaltenen Unternehmen
- **Mögliche Matches**: Fuzzy-Matching für ähnliche Namen
- **Keine BDEW-Integration**: Fokus nur auf Rollout-Daten

#### 6. Quota Updates 📊

- Quota-Änderungen dokumentieren
- Historische Tracking von Rollout-Fortschritt

### Preisblätter VNB Daten Update

### Preisblätter MSB Daten Update

### Tarifdaten Update Energieversorger

## 🏗️ Neue Architektur

- Das komplette Datenupdate basiert auf Github Action Workflows
- Die Workflows sollen auch lokal (mit Act) getestet werden können
  - Github-Spezifische Schritte (Release-Erzeugung, Release-Dateien,...) sollen geskippt werden `${{ !env.ACT }}`
- Die einzelnen Schritte sollen möglichst kleinteilig im Workflow ersichtlich sein
  - z.B. Generierung von Release-Notes, Release-Files in einem Schritt, Update im nächsten
  - Einzelschritte die länger als ca. 5 Sekunden laufen, sollen Laufzeit messen und im
    Summary ausweisen (es ist von 500 - 1000 Verteilnetzbetreibern auszugehen, die
    Neon-Datenbank hat relativ viel Latenz, da Standort USA)
- Es soll möglichst kein Inline-Code im Workflow-File enthalten sein, Scripten der
  Workflows sind in ./github/scripts/ auszulagern
- `uv` ist als Python Package Manager zu verwenden
- Es soll ein CLI-Interface für lokale Nutzung geben (z.B. `scripts/rollout_cli.sh`)

### Workflows

```text
000_central-data-update.yml
├── 010_update-bdew.yml
│   └── 110_bdew-companies-update.yml
├── 020_update-vnbdigital.yml
│   ├── 210_vnbdigital-company-basedata.yml
│   ├── 220_vnbdigital-company-geoposition.yml
│   └── 230_vnbdigital-company-geofeatures.yml
├── 030_update-bnetza.yml (simple delegator)
|   ├── 310_rollout-companies-updater.yml
|   └── 320_rollout-data-updater.yml (monolithic processor)
├── 040_vnb-update-data.yml
|   ├── 410_vnb-price-sheet-retriever.yml
|   ├── 420_vnb-price-sheet-analyzer.yml
|   └── 430_vnb-price-sheet-exporter.yml
├── 050_msb-update-data.yml
│   ├── 510_msb-price-sheet-retriever.yml
│   ├── 520_msb-price-sheet-analyzer.yml
│   └── 530_msb-price-sheet-exporter.yml
├── 060_evu_update-data.yml
|   ├── 610_evu-price-sheet-retriever.yml
|   ├── 620_evu-price-sheet-analyzer.yml
|   └── 630_evu-price-sheet-exporter.yml
├── 090_documentation_generator.yml
|   ├── 910_generate_github_pages.yml
|   └── 920_generate_api_docs.yml

```

### Database Models

```python
# TODO
```

## 🧹 Aufräumaktion Durchgeführt

Veile der alten Skiripen haben vor allem für die Anbindung an die diversen Dienste
(Neon, openRouter, cloudflare R2, vmbdigital,...) eine Relevanz.
Konkrete Implementierung von z.B. Prozessen oder rückschlüsse auf Architektur und Design
sind eben nicht sinnvoll, da sonst alles wieder ähnlich zerfasert wie auch schon
während der letzten Versuche.

- Archivierte Alte Scripts (`archive/old_scripts/`, `.github/scripts/archive/`)
- Archivierte Workflows (`archive/old_workflows/`)
- Archivierte Temp-Files (`archive/temp_files/`)

## 🎯 Verwendung

### GitHub Actions (Automatisch)

```yaml
# Manual trigger mit Parametern
# TODO
```

### Lokale CLI (Development)

Shell-Wrapper für Python Scripts

```bash
# TODO
scripts/vnbdigitaler.sh base COMMAND [...]        # company (BDEW) update
scripts/vnbdigitaler.sh vnbdigital COMMAND [...]  # BDEW enrichment von vnbdigital
scripts/vnbdigitaler.sh bnetza COMMAND [...]      # BNetzA Company Informationen
scripts/vnbdigitaler.sh rollout COMMAND []        # ... iMSys Rollout Quoten
scripts/vnbdigitaler.sh vnb COMMAND [...]         # VNB Preise
scripts/vnbdigitaler.sh msb COMMAND [...]         # MSB Preise
scripts/vnbdigitaler.sh evu COMMAND [...]         # EVU Preise

scripts/vnbdigitaler.sh stats [...]               # Statistikfunktionen
scripts/vnbdigitaler.sh verify [...]              # Datenkonsistenzprüfung
scripts/vnbdigitaler.sh databse COMMAND [...]     # Datenbankoperationen (branch, backup)
#...
```

## 🚦 Status & Features

### ✅ Implementiert

NOTE: TODO

### 🚧 In Entwicklung

NOTE: TODO

### 📋 Next Steps

NOTE: TODO

## 🔧 Technische Details

### Timing System

- `execute_and_time()` wrapper für alle Operations, die länger als ca. 5 Sekunden dauern
- JSON-State mit Execution-Times

### Error Handling

- Comprehensive Logging auf allen Ebenen
- Graceful Fallbacks bei Netzwerk-Fehlern
- Database-Transaction-Management

### File Management

- Strukturierte `data/` Directory
- Automatic Artifact Upload
- Release-Integration mit Source-Files und Dokumenten (Downloads, Conversion,...)

---

**🎉 Der Neubau ist bereit!**
