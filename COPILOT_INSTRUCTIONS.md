# VNB Digitaler - Copilot Instructions

> **📋 Projekt-Roadmap**: [ROADMAP.md](./docs/specs/ROADMAP.md) - Vollständige Phasen und Meilensteine
> **⚙️ Technische Spezifikation**: [SPECIFICATION.md](./docs/specs/SPECIFICATION.md) - API-Details und Architektur

## Generell

- Verwende `uv` für alle Python-Befehle
- Bevorzuge mermaid-Digramme ggü. ASCII-Art-Diagrammen in Markdown-Dateien
- Aktuelle Roadmap-Informationen: Siehe [ROADMAP.md](./docs/specs/ROADMAP.md)
- Technische Details: Siehe [SPECIFICATION.md](./docs/specs/SPECIFICATION.md)
- Synchronisiere alle drei Dokumente vor größeren Änderungen
- Erstelle mit der Implementierung (wo möglich) auch immer gleich Unit- und Integrations-Tests
- Code-Blöcke nicht in die SPECIFICATIONS.md, sondern in separate, spezifischere Dokumente.

## Anmerkungen

- Für die Nutzung der Datenintegrationspipeline sollen einfache Befehle zur Verfügung stehen
- **WICHTIG**: BDEW bietet eine umfassende Datenbasis ALLER Energiemarktakteure mit verschiedenen
  Rollen, nicht nur Verteilnetzbetreiber. Die Architektur muss auf alle Marktteilnehmer ausgelegt werden:
  <https://bdew-codes.de/Codenumbers/BDEWCodes/CodeOverview>
- **Rollen-Konzept**: Unternehmen können MEHRERE gleichberechtigte Rollen haben (z.B. gleichzeitig
  Stromnetzbetreiber UND Gasnetzbetreiber UND Energielieferant). Es gibt KEINE "primäre" Rolle.
- **Ziel**: vnbdigitaler als umfassende Plattform für alle deutschen Energiemarktakteure, nicht nur VNB

## 🎯 Projekt-Überblick

**VNB Digitaler** ist eine Transparenz-Plattform für den deutschen Energiemarkt, die interessierten Personen (Stromkunden, Vereine, Journalisten, Forscher) Zugang zu strukturierten und vergleichbaren Energiemarkt-Daten bietet.

**Hauptziel**: Markttransparenz und Vergleichbarkeit schaffen
**Zielgruppen**:

- 🏠 Stromkunden (Privat- und Gewerbekunden)
- 🏛️ Vereine und Verbraucherschutzorganisationen
- 📰 Journalisten und Medien
- 🎓 Forscher und Analysten
- 📊 Regulierungsbehörden und Politik

**Besonderer Fokus**:

- 🔌 **Steuerbare Verbrauchseinrichtungen** nach EnWG §14a
- 💰 **Variable Netzentgelte und Netzgebühren** für §14a-Anlagen
- 📊 **Preistransparenz** und Vergleichbarkeit der Netzbetreiber
- 🗺️ **Geografische Marktübersicht** und Zuständigkeitsgebiete

**Datenbasis**: Alle BDEW-registrierten Energiemarktakteure mit Spezialisierung auf Verteilnetzbetreiber-spezifische Daten (Rollout-Status, Netzentgelte, §14a-Regelungen).

## 🏗️ Architektur-Prinzipien

- **Transparenz**: Öffentlich zugängliche Energiemarkt-Informationen strukturiert aufbereiten
- **Vergleichbarkeit**: Standardisierte Darstellung für Preise, Konditionen und Regelungen
- **Benutzerfreundlichkeit**: Komplexe Energiemarkt-Daten für Laien verständlich machen
- **Datenintegrität**: Sichere und konsistente Verarbeitung offizieller Datenquellen
- **Offenheit**: Open-Data-Ansatz zur Förderung der Markttransparenz
- **Aktualität**: Regelmäßige Updates der Tarife und Regelungen
- **Neutralität**: Unabhängige, sachliche Darstellung ohne Interessenskonflikte

## 📊 Datenaktualisierung - Neuorganisation

### Aktuelle Herausforderung

Die bestehenden Datenaktualisierungsschritte müssen von Grund auf neu organisiert werden.
Die WebUI ist schon zu großen Teilen korrekt und funktionsfähig.
Viele der archivierten Scripten enthalten schon Teile einer sehr guten Implementierung,
passen aber nicht ganz zu einem reibungslosen Workflow, der letztlich auch in GitHub
Actions Workflows integriert werden kann.

### Ziel-Architektur für Datenaktualisierung

```
📥 Datenquellen (Öffentlich verfügbar)
├── 🏢 BDEW (Alle Energiemarktakteure - Basis-Stammdaten)
│   ├── Verteilnetzbetreiber (Fokus: §14a-Regelungen)
│   ├── Stromnetzbetreiber
│   ├── Gasnetzbetreiber
│   ├── Energielieferanten
│   └── Messstellenbetreiber
├── 📊 BNetzA (Smart-Meter-Rollout-Berichte)
├── 💰 Netzbetreiber-Websites (§14a-Netzentgelte und Preisblätter)
└── 🗺️ VNB Digital (Netzgebiets-Territorien)
     ↓
🔄 Datenverarbeitung & Strukturierung
├── 📋 Multi-Source-Extraktion
├── 🏷️ Kategorisierung nach Zielgruppen-Relevanz
├── 💰 §14a-Preis-Extraktion und -Normalisierung
├── 🔍 Transparenz-orientierte Validierung
├── 🔀 Vergleichbarkeits-Transformation
└── 💾 Öffentlichkeits-zugänglicher Import
     ↓
🎯 Transparenz-Anwendung
├── 📱 Streamlit UI (Öffentlicher Zugang für Endverbraucher)
├── 🔍 Vergleichs-Tools (§14a-Preise, Netzentgelte)
├── 📊 Marktanalyse-Dashboard (für Journalisten/Forscher)
├── 🏗️ Installateurstools
│   ├── Einfacher Zugriff auf TABs, Formulare, Anträge
│   └── z.B. Antrag auf Eintragung in Installateursverzeichnis und Gasteintragung
└── 🔌 REST API (für Entwickler und Analysten)
```

### Prioritäten für Neuimplementierung

1. **Transparenz-orientierte Datenquellen**

   - Umfassende BDEW-Integration (öffentlich verfügbare Marktteilnehmer-Daten)
   - §14a-spezifische Preisdaten-Extraktion von Netzbetreiber-Websites
   - BNetzA-Rollout-Berichte für Smart-Meter-Transparenz
   - Robuste Fehlerbehandlung und Datenvalidierung

2. **Vergleichbarkeits-Pipeline**

   - Normalisierung unterschiedlicher Preisstrukturen
   - Standardisierte §14a-Netzentgelt-Formate
   - Cross-Validation zwischen verschiedenen Datenquellen
   - Historische Preisentwicklung und Trends

3. **Benutzerfreundliche Transparenz-Tools**
   - Postleitzahl-basierte Netzbetreiber-Suche
   - §14a-Preisvergleiche für Wärmepumpen, Wallboxen, etc.
   - Interaktive Karten der Netzgebiete
   - Einfacher Zugang zu Informationen/Formularen für Installateure
   - Download-Funktionen für Rohdaten (Open Data)

## 🛠️ Technische Guidelines

### Code-Organisation

```
src/
├── data_sources/          # Öffentliche Datenquellen-Adapter
│   ├── bdew/             # BDEW Multi-Role Integration
│   │   ├── base.py       # Basis-BDEW-Adapter
│   │   ├── web.py        # Multi-Endpoint Web Data Source
│   │   └── roles.py      # Marktakteur-spezifische Verarbeitung
│   ├── bnetza.py         # BNetzA-Rollout-Berichte
│   ├── vnb_digital.py    # VNB Digital API (Netzgebiete)
│   └── price_extractors/ # §14a-Preisdaten von Netzbetreiber-Websites
│       ├── base.py       # Basis-Preisextraktor
│       ├── pdf_parser.py # PDF-Preisblatt-Parser
│       └── web_scraper.py # Website-Preisdaten-Extraktor
├── processors/           # Transparenz-orientierte Datenverarbeitung
│   ├── extractors/       # Multi-Source Daten-Extraktion
│   ├── validators/       # Transparenz-Validierung
│   ├── normalizers/      # Preisdaten-Normalisierung
│   └── comparators/      # Vergleichbarkeits-Tools
├── pipelines/            # Transparenz-Pipelines
│   ├── bdew_transparency.py   # BDEW-Markttransparenz
│   ├── price_comparison.py    # §14a-Preisvergleiche
│   └── market_analysis.py     # Marktanalyse für Öffentlichkeit
└── models/               # Transparenz-Datenmodelle
    ├── market_participants/   # Marktakteur-Modelle
    ├── pricing/              # §14a-Preismodelle
    └── transparency/         # Transparenz-spezifische Modelle
```

### Entwicklungs-Workflow

1. **Datenquelle analysieren** → Adapter entwickeln
2. **Verarbeitung definieren** → Pipeline implementieren
3. **Validierung sicherstellen** → Tests schreiben
4. **Integration testen** → End-to-End Tests

### Code-Standards

- **Type Hints**: Verwende Python Type Hints für alle Funktionen
- **Error Handling**: Explizite Exception-Behandlung
- **Logging**: Strukturiertes Logging für alle Verarbeitungsschritte
- **Documentation**: Docstrings für alle öffentlichen Funktionen

## 🔄 Datenaktualisierung - Implementierungsplan

> **📋 Detaillierte Roadmap**: Siehe [ROADMAP.md](./docs/specs/ROADMAP.md) für vollständige Phasen, Meilensteine und Checklisten

### Aktueller Status (September 2025)

**Phase 2**: Core Data Integration (🔄 In Entwicklung)

### Technische Implementierung

Die Implementierung folgt einem phasenweisen Ansatz mit klarer Trennung der Verantwortlichkeiten:

#### Aktuell abgeschlossen ✅

- **Foundation**: Pipeline-Architektur, PostgreSQL-Integration, DevContainer-Setup
- **BDEW-Basis**: Stromnetzbetreiber-Import, Datenmodelle, Repository-Pattern

#### In Entwicklung 🔄

- **Multi-Role-BDEW**: Alle Marktteilnehmer-Kategorien, Many-to-Many-Rollen-Modell
- **BNetzA-Integration**: Smart-Meter-Rollout-Daten, Quartalsweise Updates
- **Data-Admin-WebUI**: FastAPI-Backend, Validierungs-Interface

#### Geplant 📋

- **Price Transparency**: PDF-Extraktion, Preisvergleiche, Historische Daten
- **Public Portal**: Streamlit-Interface, Interaktive Karten, API
- **Installer Services**: OAuth2, Automatisierung, Dashboard

## 🧪 Testing-Strategie

### Unit Tests ✅ Implementiert

- Jeder Adapter hat eigene Tests
- Mock externe Datenquellen
- Validierung der Datenverarbeitung

### Integration Tests ✅ Implementiert

- End-to-End Pipeline-Tests
- Datenbank-Integration
- API-Endpoint-Tests

### Data Quality Tests ✅ Implementiert

- Datenvalidierung und -konsistenz
- Historische Datenvergleiche
- Performance-Benchmarks

**Aktuelle Test-Struktur:**

- `tests/test_bdew_integration.py` - 18 BDEW-Tests (Haupt-Datei)
- `tests/test_pipeline_architecture.py` - 5 Pipeline-Tests
- Alle redundanten Test-Dateien entfernt und geschützt
- 100% Test Success Rate (23/23 Tests)

## 📝 Entwicklungs-Guidelines für Copilot

### Bei Datenaktualisierung

1. **Immer zuerst fragen**: "Welche Datenquelle und welche Rolle wird aktualisiert?"
2. **Rollen-bewusst denken**: Ein Unternehmen kann MEHRERE gleichberechtigte Rollen haben
3. **Validierung priorisieren**: Cross-Role-Validation sicherstellen
4. **Transaktional denken**: Atomare Operationen für Multi-Role-Datenänderungen
5. **Logging hinzufügen**: Jeder Verarbeitungsschritt soll geloggt werden
6. **VNB-spezifisch**: Rollout-relevante Daten nur für Verteilnetzbetreiber anreichern

### Code-Stil

- Verwende aussagekräftige Funktions- und Variablennamen
- Kleine, fokussierte Funktionen (max. 20-30 Zeilen)
- Explicit ist besser als implicit
- Dokumentiere komplexe Geschäftslogik

### Fehlerbehandlung

- Verwende spezifische Exception-Typen
- Logge Fehler mit Kontext-Informationen
- Graceful Degradation wo möglich
- Nie silent failures

## 🎯 Ziele für die Neuorganisation

1. **Klarheit**: Verständliche Datenflüsse
2. **Zuverlässigkeit**: Robuste Fehlerbehandlung
3. **Wartbarkeit**: Modularer, testbarer Code
4. **Performance**: Effiziente Datenverarbeitung
5. **Monitoring**: Vollständige Observability

## ✅ Implementierungsstatus

> **📋 Aktuelle Roadmap**: Siehe [ROADMAP.md](./docs/specs/ROADMAP.md) für detaillierte Phasen und Meilensteine

### Status-Übersicht (September 2025)

#### Phase 1 & 2 - Erfolgreich Abgeschlossen ✅

**Pipeline-Architektur:**

- `src/pipelines/base.py` - Basis-Pipeline mit Step-System
- `src/pipelines/bdew_import.py` - 4-stufige BDEW-Import-Pipeline

**PostgreSQL-Integration (Phase 2):**

- `src/database.py` - PostgreSQL DatabaseManager mit async/sync Support
- `src/models/bdew.py` - PostgreSQL-optimierte Modelle mit JSONB, UUID, Constraints
- `src/repositories/bdew.py` - Repository-Pattern mit erweiterten PostgreSQL-Features
- `.devcontainer/` - DevContainer mit automatischem PostgreSQL 16 Setup
- `scripts/init_database.py` - Automatische Schema-Initialisierung
- Extensions: pg_trgm, unaccent, uuid-ossp erfolgreich installiert
- Performance-Indices: 7 spezialisierte Indices für optimierte Abfragen

**BDEW-Integration:**

- `src/models/bdew.py` - Vollständige PostgreSQL-Datenmodelle (Company, ImportLog, ValidationRule)
- `src/repositories/bdew.py` - Repository-Pattern mit CRUD + PostgreSQL-Features
- `src/data_sources/bdew.py` - BDEW-Datenquellen-Adapter

**Test-Coverage:**

- `tests/test_bdew_integration.py` - 18 umfassende BDEW-Tests (100% Success Rate)
- `tests/test_pipeline_architecture.py` - 5 Pipeline-Tests

**Features implementiert:**

- ✅ Bulk-Import von BDEW-Stromnetzbetreiber-Daten (Basis für Multi-Role-Erweiterung)
- ✅ Erweiterte PostgreSQL-Suchfunktionen (Full-Text, Trigram, Geo-Proximity)
- ✅ JSONB-Service-Territory-Support für flexible Geodaten
- ✅ Datenqualitäts-Scoring und Statistiken
- ✅ Vollständiges Audit-Logging mit PostgreSQL-Optimierung
- ✅ Repository-Pattern mit transaktionaler Sicherheit
- ✅ Pipeline-Steps mit Fehlerbehandlung
- ✅ PostgreSQL-optimierte Datenmodelle mit UUID-Keys und Performance-Indices
- ✅ DevContainer mit automatischem PostgreSQL-Setup
- ✅ Streamlit-Integration mit PostgreSQL-Backend getestet
- 🔄 **Nächste Phase**: Multi-Role BDEW-Architektur (Endpoint-Discovery, Rollen-Modelle)

### Phase 3 bereit: Umfassende BDEW-Integration (alle Marktteilnehmer)

---

_Diese Anweisungen sind ein lebendiges Dokument und sollen bei Bedarf aktualisiert werden._
