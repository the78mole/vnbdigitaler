# VNB Digitaler - Projektspezifikation

> **📋 Projekt-Roadmap**: [ROADMAP.md](./ROADMAP.md) - Phasen, Meilensteine und aktuelle Checklisten
> **👨‍💻 Entwicklungsrichtlinien**: [COPILOT_INSTRUCTIONS.md](../../COPILOT_INSTRUCTIONS.md) - Guidelines und technische Implementierung

## 📋 Inhaltsverzeichnis

1. [Projektüberblick](#-projektüberblick)
2. [Geschäftsziele](#-geschäftsziele)
3. [Funktionale Anforderungen](#️-funktionale-anforderungen)
4. [Technische Architektur](#️-technische-architektur)
5. [Datenmodell](#️-datenmodell)
6. [API-Spezifikation](#-api-spezifikation)
7. [Benutzeroberfläche](#️-benutzeroberfläche)
8. [Datenintegration](#-datenintegration)
9. [Qualitätssicherung](#-qualitätssicherung)
10. [Betrieb und Wartung](#-betrieb-und-wartung)
11. [Implementierungsplan](#-implementierungsplan)

---

## 🎯 Projektüberblick

### Vision

**VNB Digitaler** ist eine umfassende Transparenz-Plattform für den deutschen Energiemarkt, die strukturierte und vergleichbare Energiemarkt-Daten für alle Interessensgruppen zugänglich macht.

### Mission

Schaffen von Markttransparenz und Vergleichbarkeit im deutschen Energiesektor mit besonderem Fokus auf steuerbare Verbrauchseinrichtungen nach EnWG §14a.

### Kernwerte

- **Transparenz**: Öffentlich zugängliche Informationen strukturiert aufbereiten
- **Neutralität**: Unabhängige, sachliche Darstellung ohne Interessenskonflikte
- **Offenheit**: Open-Data-Ansatz zur Förderung der Markttransparenz
- **Benutzerfreundlichkeit**: Komplexe Daten für Laien verständlich aufbereiten

---

## 🎯 Geschäftsziele

### Primäre Zielgruppen

| Zielgruppe               | Bedürfnisse                                       | Nutzen                                    |
| ------------------------ | ------------------------------------------------- | ----------------------------------------- |
| 🏠 **Stromkunden**       | §14a-Preisvergleiche, Netzbetreiber-Informationen | Kostentransparenz, bessere Entscheidungen |
| 🔧 **Installateure**     | TAB-Unterlagen, Anmeldeformulare, Gasteintragung  | Vereinfachte Prozesse, Automatisierung    |
| 📰 **Journalisten**      | Marktdaten, Preisentwicklungen, Vergleiche        | Fundierte Berichterstattung               |
| 🎓 **Forscher**          | Strukturierte Daten, historische Trends           | Wissenschaftliche Analysen                |
| 🏛️ **Verbraucherschutz** | Marktübersicht, Preisvergleiche                   | Verbraucherschutz, Beratung               |

### Geschäftsziele

1. **Markttransparenz erhöhen**

   - Zentrale Anlaufstelle für Energiemarkt-Informationen
   - Vergleichbare Darstellung von Preisen und Konditionen
   - Geografische Marktübersicht

2. **§14a-Transparenz schaffen**

   - Vergleich der Netzentgelte für steuerbare Verbrauchseinrichtungen
   - Übersicht über Regelungen und Bedingungen
   - Unterstützung bei der Anbieterwahl

3. **Installateurprozesse digitalisieren**
   - Automatisierte Gasteintragung
   - Zentrale Formularverwaltung
   - Erinnerungssystem für Fristen

---

## ⚙️ Funktionale Anforderungen

### Core Features

#### 1. Marktakteur-Management

- **FR-001**: Verwaltung aller BDEW-registrierten Energiemarktakteure
- **FR-002**: Multi-Rollen-Support (Ein Unternehmen kann mehrere Rollen haben)
- **FR-003**: Automatische Synchronisation mit BDEW-Datenbank
- **FR-004**: Geografische Zuordnung von Netzgebieten

#### 2. Preistransparenz

- **FR-010**: §14a-Netzentgelt-Vergleiche
- **FR-011**: Historische Preisentwicklung
- **FR-012**: Postleitzahl-basierte Netzbetreiber-Suche
- **FR-013**: Preisblatt-Extraktion aus PDF-Dokumenten
- **FR-014**: Tarifregler-Integration

#### 3. Installateurservices

- **FR-020**: Benutzerauthentifizierung (OAuth2)
- **FR-021**: Automatische Gasteintragung bei Netzbetreibern
- **FR-022**: TAB-Dokumentenverwaltung
- **FR-023**: Antragsformular-Management
- **FR-024**: Fristenerinnerungen
- **FR-025**: Installateur-Dashboard

#### 4. Datenintegration

- **FR-030**: BDEW-Datenimport (alle Marktteilnehmer)
- **FR-031**: BNetzA-Rollout-Daten-Integration
- **FR-032**: VNB Digital API-Integration (Netzgebiete)
- **FR-033**: Netzbetreiber-Website-Scraping
- **FR-034**: Automatische Datenvalidierung

#### 5. Benutzeroberfläche

- **FR-040**: Responsive Streamlit-Weboberfläche (Read-Only)
- **FR-041**: Interaktive Karten (Netzgebiete)
- **FR-042**: Suchfunktionen (Full-Text, Ähnlichkeit)
- **FR-043**: Datenexport (CSV, JSON, PDF)
- **FR-044**: Mehrsprachige Unterstützung
- **FR-045**: Separate Web-App für Installateur-Interaktionen
- **FR-046**: Data-Admin-WebUI für Datenvalidierung und -kontrolle

#### 6. Data-Administration

- **FR-050**: Tabellen-Explorer mit Filter- und Sortierungsfunktionen
- **FR-051**: BDEW ↔ BNetzA Verknüpfungs-Validation
- **FR-052**: Geo-Informationen-Viewer und -Editor
- **FR-053**: Data-Quality-Monitoring-Dashboard
- **FR-054**: Manuelle Datenkorrektur-Tools mit Audit-Trail
- **FR-055**: Bulk-Edit-Interface für Massenkorrekturen

### Non-Functional Requirements

#### Performance

- **NFR-001**: Antwortzeiten < 2 Sekunden für Standardabfragen (Streamlit)
- **NFR-002**: Unterstützung für 5000+ gleichzeitige Benutzer (Read-Only Portal)
- **NFR-003**: 99.5% Verfügbarkeit
- **NFR-004**: Datenaktualisierung alle 24 Stunden
- **NFR-005**: Caching-Strategien für häufige Abfragen
- **NFR-006**: Separate Performance-Profile für Streamlit vs. Web-App

#### Sicherheit

- **NFR-010**: DSGVO-Konformität
- **NFR-011**: Sichere API-Authentifizierung
- **NFR-012**: Verschlüsselte Datenübertragung (HTTPS/TLS)
- **NFR-013**: Audit-Logging aller Datenänderungen

#### Qualität

- **NFR-020**: 95% Testabdeckung
- **NFR-021**: Automatisierte Code-Qualitätsprüfung
- **NFR-022**: Kontinuierliche Integration/Deployment
- **NFR-023**: Umfassende Dokumentation

---

## 🏗️ Technische Architektur

### System-Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
├─────────────────────────────────────────────────────────────┤
│  Streamlit WebUI  │  REST API  │  GraphQL API  │  Mobile App │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
├─────────────────────────────────────────────────────────────┤
│  Business Logic  │  Authentication  │  Authorization       │
│  Validation      │  Workflows       │  Notifications       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Data Processing Layer                    │
├─────────────────────────────────────────────────────────────┤
│  ETL Pipelines   │  Data Validation │  Transformations     │
│  Schedulers      │  Quality Control │  Monitoring          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                               │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL                 │         File Storage          │
│  Full-Text Search           │      Backup & Archive         │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

#### Backend

- **Runtime**: Python 3.11+
- **Framework**: FastAPI (REST API + Data-Admin-UI + Installateur-Backend), Streamlit (Public WebUI)
- **Database**: Neon (PostgreSQL 16 as a Service)
- **Task Queue**: GitHub Actions (für ETL-Pipelines)
- **Package Management**: uv
- **Deployment**: Streamlit Cloud + Docker Host (FastAPI Services)

#### Frontend

- **Streamlit**: Read-Only Informationsportal (Endverbraucher, Journalisten, Forscher)
  - Preisvergleiche, Marktdaten, Statistiken
  - Hohe Performance für viele gleichzeitige Benutzer-Anfragen
- **FastAPI + HTML/JS**: Data-Admin-WebUI (Datenvalidierung und -kontrolle)
  - Tabellen-Explorer, Verknüpfungs-Validation
  - Geo-Informationen-Viewer, Data-Quality-Monitoring
- **FastAPI + React/Next.js**: Installateur-Portal (interaktive Features)
  - Login/Authentifizierung, Datenerfassung, Workflows
  - Gasteintragung, Formular-Management, Dashboard
- **Maps**: Folium/Leaflet (Streamlit), Leaflet/MapLibre (FastAPI UIs)
- **Charts**: Plotly/Chart.js

#### Infrastructure

- **Containerization**: Docker + DevContainer
- **Database**: Neon (PostgreSQL as a Service)
- **Hosting**:
  - Streamlit Cloud (Read-Only Portal)
  - Docker Host (Data-Admin-UI + Installateur-Backend, FastAPI services)
- **Orchestration**: GitHub Actions (Datenverarbeitung + Deployment)
- **CI/CD**: GitHub Actions
- **Monitoring**: GitHub Actions Status + einfache Health Checks
- **Logging**: Structured Logging (JSON)

### Data Architecture

#### Datenquellen

```
External Data Sources
├── 🏢 BDEW (Marktteilnehmer-Stammdaten)
├── 📊 BNetzA (Smart-Meter-Rollout)
├── 🗺️ VNB Digital API (Netzgebiete)
├── 💰 Netzbetreiber-Websites (Preisblätter)
└── 📄 Regulierungstexte (TAB, Anträge)
```

#### Datenfluss

```
Ingestion  → Validation → Transform   → Storage    → API        → UI
    ↓            ↓            ↓            ↓          ↓            ↓
  Crawlers → Validators → Normalizers → PostgreSQL → REST       → Streamlit
  APIs     → Parsers    → Enrichers   → Redis      → GraphQL    → Mobile
  Files    → Cleaners   → Aggregators → Cache      → WebSockets → Reports
```

---

## 🗄️ Datenmodell

### Core Entities

#### 1. Company (Unternehmen)

```python
class Company:
    id: UUID                   # Primary Key
    code: str                  # BDEW-Code (eindeutig)
    name: str                  # Unternehmensname
    legal_name: str            # Juristische Bezeichnung
    address: Address           # Geschäftsadresse
    contact_info: ContactInfo  # Kontaktdaten
    website_url: str           # Website
    created_at: datetime
    updated_at: datetime

    # Beziehungen
    roles: List[CompanyRole]                     # Many-to-Many zu Rollen
    service_territories: List[ServiceTerritory]  # Netzgebiete
    price_sheets: List[PriceSheet]               # Preisblätter
```

#### 2. CompanyRole (Unternehmensrollen)

```python
class CompanyRole:
    id: UUID
    company_id: UUID          # Foreign Key zu Company
    role_type: RoleType       # Enum: VNB, ÜNB, MSB, etc.
    is_active: bool
    start_date: date
    end_date: date
    role_specific_data: dict  # JSONB für rollenspezifische Daten
```

#### 3. ServiceTerritory (Netzgebiet)

```python
class ServiceTerritory:
    id: UUID
    company_id: UUID
    role_id: UUID
    territory_type: str       # Strom, Gas, etc.
    postal_codes: List[str]   # Bediente PLZ
    geographic_bounds: dict   # GeoJSON Polygon
    population_served: int
```

#### 4. PriceSheet (Preisblatt)

```python
class PriceSheet:
    id: UUID
    company_id: UUID
    document_type: str        # §14a, Standard, etc.
    effective_date: date
    document_url: str
    extracted_prices: dict    # JSONB mit strukturierten Preisen
    validation_status: str
    created_at: datetime
```

### Database Schema Features

#### PostgreSQL Extensions

- **pg_trgm**: Trigram-Ähnlichkeitssuche
- **unaccent**: Akzent-unabhängige Suche
- **uuid-ossp**: UUID-Generierung
- **PostGIS**: Geografische Daten (zukünftig)

#### Performance Indices

```sql
-- Full-Text Search
CREATE INDEX idx_company_name_gin ON companies USING gin(to_tsvector('german', name));

-- Trigram Similarity
CREATE INDEX idx_company_name_trgm ON companies USING gin(name gin_trgm_ops);

-- Geographic Queries
CREATE INDEX idx_service_territory_geom ON service_territories USING gist(geographic_bounds);

-- Role-based Queries
CREATE INDEX idx_company_roles_composite ON company_roles(company_id, role_type, is_active);
```

---

## 🔌 API-Spezifikation

### REST API Endpoints

#### Companies

```http
GET    /api/v1/companies                 # Liste aller Unternehmen
GET    /api/v1/companies/{id}            # Einzelnes Unternehmen
GET    /api/v1/companies/search          # Suchfunktion
POST   /api/v1/companies                 # Neues Unternehmen (Admin)
PUT    /api/v1/companies/{id}            # Unternehmen aktualisieren
DELETE /api/v1/companies/{id}            # Unternehmen löschen
```

#### Price Comparison

```http
GET    /api/v1/prices/compare            # Preisvergleich
GET    /api/v1/prices/14a                # §14a-spezifische Preise
GET    /api/v1/prices/history/{company}  # Preisentwicklung
POST   /api/v1/prices/calculate          # Kostenrechner
```

#### Geographic Services

```http
GET    /api/v1/territories               # Netzgebiete
GET    /api/v1/territories/postal/{plz}  # Netzbetreiber nach PLZ
GET    /api/v1/territories/geojson       # GeoJSON für Karten
```

#### Installer Services

```http
POST   /api/v1/installer/register        # Installateur-Registrierung
POST   /api/v1/installer/guest-entry     # Gasteintragung
GET    /api/v1/installer/forms           # Verfügbare Formulare
GET    /api/v1/installer/documents       # TAB-Dokumente
```

### GraphQL Schema (Zukünftig)

```graphql
type Company {
  id: ID!
  code: String!
  name: String!
  roles: [CompanyRole!]!
  serviceAreas: [ServiceTerritory!]!
  priceSheets(type: PriceSheetType): [PriceSheet!]!
}

type Query {
  companies(filter: CompanyFilter): [Company!]!
  priceComparison(input: PriceComparisonInput!): PriceComparison!
  netOperatorByPostal(postalCode: String!): [Company!]!
}

type Mutation {
  registerInstaller(input: InstallerInput!): InstallerResult!
  requestGuestEntry(input: GuestEntryInput!): GuestEntryResult!
}
```

---

## 🖥️ Benutzeroberfläche

### Streamlit-Anwendung

#### Streamlit-Hauptmenü (Read-Only Portal)

```
📱 VNB Digitaler - Informationsportal
├── 🏠 Startseite
│   ├── Suchfeld (Unternehmen, PLZ)
│   ├── Aktuelle Statistiken
│   └── News/Updates
├── 🔍 Preisvergleich
│   ├── §14a-Netzentgelt-Rechner
│   ├── Postleitzahl-Eingabe
│   ├── Anlagentyp-Auswahl
│   └── Vergleichstabelle (nur Anzeige)
├── 🗺️ Netzgebiete
│   ├── Interaktive Karte
│   ├── PLZ-Suche
│   └── Netzbetreiber-Details
├── � Marktanalyse
│   ├── Preisentwicklung
│   ├── Marktstatistiken
│   └── Datenexport (CSV/JSON)
├── � Installateur-Info
│   ├── Link zur Web-App
│   ├── TAB-Dokumente (Download)
│   └── Kontaktdaten Netzbetreiber
└── ℹ️ Über uns
    ├── Datenschutz
    ├── API-Dokumentation
    └── Link zur Installateur-Web-App
```

#### UI-Komponenten

> **🔌 Detaillierte API-Spezifikationen**: Siehe [API.md](./API.md) - REST & GraphQL Endpoints

Die Streamlit-Oberfläche bietet intuitive Suchkomponenten, Preisvergleich-Interfaces und interaktive Karten für die Visualisierung von Netzgebieten. Detaillierte Implementierungsbeispiele und Code-Snippets finden Sie in der API-Dokumentation.

### Data-Admin-WebUI (FastAPI)

> **🔌 Admin-API-Endpoints**: Siehe [API.md](./API.md) - Admin API Dokumentation
> **🗄️ Datenbank-Schema**: Siehe [DATABASE.md](./DATABASE.md) - Tabellen und Strukturen

Das Admin-Interface für Datenvalidierung bietet umfassende Tools für die Verwaltung und Qualitätssicherung der integrierten Daten:

#### Admin-Interface für Datenvalidierung

```
🔧 VNB Digitaler - Data Admin Portal (FastAPI + HTML/JS)
├── 📊 Dashboard
│   ├── Datenqualitäts-Übersicht
│   ├── Pipeline-Status
│   └── System-Metriken
├── 🗄️ Tabellen-Explorer
│   ├── Company-Verwaltung
│   ├── BDEW-Daten-Review
│   ├── BNetzA-Rollout-Daten
│   └── Service-Territories
├── 🔗 Verknüpfungs-Validation
│   ├── BDEW ↔ BNetzA Mapping
│   ├── Unverknüpfte Datensätze
│   ├── Duplikate-Erkennung
│   └── Manuelle Zuordnung
├── 🗺️ Geo-Informationen
│   ├── Netzgebiete-Viewer
│   ├── PLZ-Zuordnungs-Editor
│   ├── Koordinaten-Validation
│   └── GeoJSON-Import/Export
├── 📈 Data Quality Monitor
│   ├── Vollständigkeits-Metrics
│   ├── Konsistenz-Checks
│   ├── Anomalie-Detection
│   └── Fehler-Logs
└── 🛠️ Datenkorrektur-Tools
    ├── Bulk-Edit-Interface
    ├── Regex-basierte Korrekturen
    ├── Audit-Trail
    └── Rollback-Funktionen
```

Detaillierte API-Endpoints und Implementierungsbeispiele finden Sie in der API-Dokumentation.

#### Separate Anwendung für interaktive Features

> **🔌 Installer-API**: Siehe [API.md](./API.md) - OAuth & Installation Management

```
🔧 VNB Digitaler - Installateur-Portal (Web-App)
├── 🔐 Authentifizierung
│   ├── Login/Registrierung
│   ├── OAuth2-Integration
│   └── Session-Management
├── 👤 Installateur-Dashboard
│   ├── Persönliche Übersicht
│   ├── Aktuelle Anträge
│   └── Fristenerinnerungen
├── 📝 Gasteintragung
│   ├── Netzbetreiber-Auswahl
│   ├── Automatischer Antrag
│   └── Status-Tracking
├── 📋 Antragsmanagement
│   ├── Formular-Erstellung
│   ├── Dokumenten-Upload
│   └── Verlängerungen
├── 📚 Dokumentenverwaltung
│   ├── TAB-Dokumente
│   ├── Anmeldeformulare
│   └── Persönliche Bibliothek
└── 📊 Berichte & Statistiken
    ├── Eigene Aktivitäten
    ├── Erfolgsraten
    └── Zeitersparnis-Analysen
```

Detaillierte API-Spezifikationen für OAuth-Authentication und Installation-Management finden Sie in der API-Dokumentation.

#### Breakpoints

- **Mobile**: < 768px (Single-Column Layout)
- **Tablet**: 768px - 1024px (Adaptive Columns)
- **Desktop**: > 1024px (Full Feature Set)

#### Accessibility

- **WCAG 2.1 AA Konformität**
- **Keyboard Navigation**
- **Screen Reader Support**
- **High Contrast Mode**

---

## 🔄 Datenintegration

### ETL-Pipeline-Architektur

> **🧪 Pipeline-Tests**: Siehe [TESTING.md](./TESTING.md) - Integration & Performance Tests
> **🚀 Pipeline-Deployment**: Siehe [DEPLOYMENT.md](./DEPLOYMENT.md) - GitHub Actions Workflows

Die Datenintegration erfolgt über eine mehrstufige ETL-Pipeline, die verschiedene Datenquellen automatisiert verarbeitet und validiert. Detaillierte Implementierungsbeispiele für BDEW-Integration, BNetzA-Rollout-Daten und Website-Scraping für Preisdaten finden Sie in den verlinkten Dokumenten.

#### Pipeline-Stufen

1. **Extract**: Datenextraktion aus verschiedenen Quellen
2. **Validate**: Datenvalidierung und Qualitätsprüfung
3. **Transform**: Datentransformation und Normalisierung
4. **Load**: Datenladung in die PostgreSQL-Datenbank
5. **Index**: Indizierung für optimierte Suchperformance
6. **Notify**: Benachrichtigung über Pipeline-Status

#### Integrierte Datenquellen

- **BDEW-Integration**: Umfassende Marktteilnehmer-Daten
- **BNetzA-Integration**: Smart-Meter-Rollout-Daten
- **Website-Scraping**: Automatische Preisblatt-Extraktion

### Datenvalidierung

> **🧪 Validierungstests**: Siehe [TESTING.md](./TESTING.md) - Datenqualitäts-Tests

Die Datenvalidierung erfolgt über ein mehrstufiges System mit Schema-Validation, Geschäftsregeln-Prüfung, referenzieller Integrität und geografischer Plausibilitätskontrolle.

---

## 🧪 Qualitätssicherung

> **🧪 Umfassende Test-Dokumentation**: Siehe [TESTING.md](./TESTING.md) - Test-Strategien & Code Quality

### Testing-Strategie

Die Qualitätssicherung basiert auf der bewährten Test-Pyramide mit 80% Unit Tests, 15% Integration Tests und 5% End-to-End Tests. Detaillierte Test-Implementierungen, Performance-Testing und Code-Quality-Standards sind in der Test-Dokumentation zu finden.

---

## 🚀 Betrieb und Wartung

> **🚀 Deployment-Dokumentation**: Siehe [DEPLOYMENT.md](./DEPLOYMENT.md) - Production Setup & Operations

Die Deployment-Architektur nutzt GitHub Actions als Orchestrierungs-Platform für tägliche Datenpipelines und automatisierte Deployments. Das Production Environment läuft auf einem Docker Host mit Nginx für SSL-Termination und einer Neon PostgreSQL-Datenbank für hohe Verfügbarkeit.

---

## 📋 Implementierungsplan

> **📋 Vollständige Roadmap**: Siehe [ROADMAP.md](./ROADMAP.md) für detaillierte Phasen, Meilensteine und aktuelle Checklisten

### Überblick

Das VNB Digitaler Projekt wird in sechs Hauptphasen implementiert:

1. **Foundation** (✅ Abgeschlossen) - Basis-Architektur und Setup
2. **Core Data Integration** (🔄 Aktuell) - BDEW & BNetzA Datenintegration
3. **Data-Admin-WebUI** (📋 Geplant Q4 2025) - Admin-Interface für Datenvalidierung
4. **Price Transparency** (📋 Q1 2026) - §14a-Preisdaten und Vergleiche
5. **Public Portal** (📋 Q1-Q2 2026) - Öffentliche Streamlit-Oberfläche
6. **Installer Services** (📋 Q2-Q3 2026) - Automatisierte Installateur-Workflows

### Technische Implementierungsstrategie

#### Architektur-Prinzipien

- **Modularer Aufbau**: Jede Phase baut auf der vorherigen auf
- **Datenintegrität**: Validierung und Qualitätssicherung in allen Phasen
- **Performance**: PostgreSQL-Optimierung für große Datenmengen
- **Skalierbarkeit**: Cloud-native Deployment mit Neon Database
- **Wartbarkeit**: Umfassende Tests und Dokumentation

#### Deployment-Strategie

- **GitHub Actions**: CI/CD für alle Services
- **Neon Database**: Managed PostgreSQL für Datenbank-Layer
- **Streamlit Cloud**: Hosting der öffentlichen Portal-Oberfläche
- **Docker Host**: Deployment der FastAPI-Services (Admin & Installer)

### Risikomanagement

#### Technische Risiken

| Risiko                     | Wahrscheinlichkeit | Impact | Mitigation                        |
| -------------------------- | ------------------ | ------ | --------------------------------- |
| BDEW-API-Änderungen        | Hoch               | Mittel | Monitoring + Fallback-Strategien  |
| PDF-Extraktion-Genauigkeit | Mittel             | Hoch   | ML-Training + manuelle Validation |
| Performance bei Scale      | Mittel             | Hoch   | Load Testing + Optimierung        |
| Datenschutz-Compliance     | Niedrig            | Hoch   | Legal Review + Privacy by Design  |

#### Geschäftsrisiken

| Risiko                     | Wahrscheinlichkeit | Impact | Mitigation                         |
| -------------------------- | ------------------ | ------ | ---------------------------------- |
| Rechtliche Einschränkungen | Niedrig            | Hoch   | Nur öffentliche Daten verwenden    |
| Marktakzeptanz             | Mittel             | Mittel | MVP-Ansatz + User Feedback         |
| Konkurrenz                 | Mittel             | Mittel | Open Source + Community Building   |
| Finanzierung               | Niedrig            | Hoch   | Modularer Aufbau + Revenue Streams |

### Success Metrics

#### Technical KPIs

- **Datenqualität**: >95% Validierungsrate
- **Performance**: <2s Antwortzeit für 95% der Requests
- **Verfügbarkeit**: >99.5% Uptime
- **Test Coverage**: >95%

#### Business KPIs

- **Nutzer**: 10,000 aktive Nutzer/Monat (Jahr 1)
- **Datenabdeckung**: >90% aller deutschen VNB
- **API-Nutzung**: 1M API-Calls/Monat
- **Kundenzufriedenheit**: >4.5/5 Rating

#### Impact KPIs

- **Transparenz**: Anzahl verfügbarer Preisvergleiche
- **Effizienz**: Zeitersparnis für Installateure
- **Adoption**: Anzahl integrierter Drittanbieter-Tools
- **Community**: GitHub Stars, Contributions, Forks

---

## 📝 Anhang

### Glossar

**BDEW**: Bundesverband der Energie- und Wasserwirtschaft
**BNetzA**: Bundesnetzagentur
**EnWG §14a**: Energiewirtschaftsgesetz §14a (steuerbare Verbrauchseinrichtungen)
**VNB**: Verteilnetzbetreiber
**ÜNB**: Übertragungsnetzbetreiber
**MSB**: Messstellenbetreiber
**TAB**: Technische Anschlussbedingungen

### Referenzen

- [BDEW-Codes](https://bdew-codes.de/)
- [BNetzA Smart-Meter-Rollout](https://www.bundesnetzagentur.de/DE/Sachgebiete/ElektrizitaetundGas/Unternehmen_Institutionen/DatenaustauschundMonitoring/SmartMeterRollout/start.html)
- [EnWG §14a](https://www.gesetze-im-internet.de/enwg_2005/__14a.html)
- [VNB Digital API](https://vnbdigital.de/)

---

_Diese Spezifikation ist ein lebendes Dokument und wird kontinuierlich aktualisiert, um den sich entwickelnden Anforderungen des Projekts gerecht zu werden._
