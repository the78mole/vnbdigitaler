# VNB Digitaler - Projektspezifikation

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

##### Suchkomponenten

```python
# Intelligente Unternehmenssuche
st.text_input(
    "Unternehmen oder PLZ suchen",
    placeholder="z.B. Stadtwerke München oder 80331"
)

# Erweiterte Filter
col1, col2, col3 = st.columns(3)
with col1:
    role_filter = st.multiselect("Rolle", ["VNB", "ÜNB", "MSB"])
with col2:
    state_filter = st.selectbox("Bundesland", states)
with col3:
    size_filter = st.select_slider("Unternehmensgröße", options)
```

##### Preisvergleich-Interface

```python
# §14a-Rechner
with st.form("price_calculator"):
    postal_code = st.text_input("Postleitzahl")
    device_type = st.selectbox("Anlage", ["Wärmepumpe", "Wallbox", "Speicher"])
    power_rating = st.number_input("Anschlusswert (kW)")
    annual_consumption = st.number_input("Jahresverbrauch (kWh)")

    if st.form_submit_button("Preise vergleichen"):
        results = calculate_14a_prices(postal_code, device_type, power_rating)
        display_price_comparison(results)
```

##### Interaktive Karten

```python
# Netzgebiete-Karte mit Folium
map = folium.Map(location=[51.1657, 10.4515], zoom_start=6)

for territory in service_territories:
    folium.GeoJson(
        territory.geographic_bounds,
        popup=f"{territory.company.name}",
        style_function=lambda x: {
            'fillColor': get_color_by_type(x['properties']['type']),
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.6
        }
    ).add_to(map)

st_folium(map, width=700, height=500)
```

### Data-Admin-WebUI (FastAPI)

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

#### FastAPI Admin-Endpoints

```python
# Admin API Endpoints
@router.get("/admin/dashboard")
async def get_admin_dashboard():
    """Dashboard mit Datenqualitäts-Übersicht"""

@router.get("/admin/tables/{table_name}")
async def get_table_data(table_name: str, page: int = 1, size: int = 100):
    """Paginierte Tabellendaten mit Filter/Sort"""

@router.get("/admin/linkage/bdew-bnetza")
async def get_linkage_overview():
    """BDEW ↔ BNetzA Verknüpfungs-Status"""

@router.post("/admin/linkage/manual")
async def create_manual_link(link_data: ManualLinkage):
    """Manuelle Verknüpfung zwischen Datensätzen"""

@router.get("/admin/geo/territories")
async def get_geo_territories():
    """Geo-Informationen der Netzgebiete"""

@router.put("/admin/geo/territories/{id}")
async def update_territory_geo(id: UUID, geo_data: GeoData):
    """Geo-Daten eines Netzgebiets aktualisieren"""

@router.get("/admin/quality/metrics")
async def get_quality_metrics():
    """Datenqualitäts-Kennzahlen"""

@router.post("/admin/corrections/bulk")
async def apply_bulk_corrections(corrections: List[DataCorrection]):
    """Bulk-Datenkorrektur mit Audit-Trail"""
```

#### Separate Anwendung für interaktive Features

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

#### Pipeline-Stufen

```python
class DataPipeline:
    def __init__(self):
        self.steps = [
            ExtractStep(),      # Datenextraktion
            ValidateStep(),     # Datenvalidierung
            TransformStep(),    # Datentransformation
            LoadStep(),         # Datenladung
            IndexStep(),        # Indizierung
            NotifyStep()        # Benachrichtigung
        ]
```

#### BDEW-Integration

```python
class BDEWIntegration:
    """Umfassende BDEW-Datenintegration für alle Marktteilnehmer"""

    endpoints = {
        'stromnetzbetreiber': 'https://bdew-codes.de/Content/Files/StromNB/...',
        'gasnetzbetreiber': 'https://bdew-codes.de/Content/Files/GasNB/...',
        'energielieferanten': 'https://bdew-codes.de/Content/Files/EnergieLief/...',
        'messstellenbetreiber': 'https://bdew-codes.de/Content/Files/MSB/...'
    }

    async def extract_all_roles(self) -> Dict[str, List[Dict]]:
        """Extrahiert alle Marktteilnehmer-Rollen parallel"""
        tasks = []
        for role, endpoint in self.endpoints.items():
            tasks.append(self.extract_role_data(role, endpoint))

        results = await asyncio.gather(*tasks)
        return dict(zip(self.endpoints.keys(), results))
```

#### BNetzA-Integration

```python
class BNetzAIntegration:
    """Smart-Meter-Rollout-Daten von der Bundesnetzagentur"""

    def extract_rollout_data(self) -> List[RolloutData]:
        """Quartalsweise Rollout-Berichte verarbeiten"""
        reports = self.download_quarterly_reports()
        rollout_data = []

        for report in reports:
            parsed_data = self.parse_rollout_report(report)
            validated_data = self.validate_rollout_data(parsed_data)
            rollout_data.extend(validated_data)

        return rollout_data
```

#### Website-Scraping für Preisdaten

```python
class PriceExtractor:
    """Automatische Extraktion von Preisblättern"""

    def extract_prices_from_website(self, company: Company) -> PriceSheet:
        """KI-gestützte Preisextraktion von Netzbetreiber-Websites"""

        # 1. Website crawlen
        pages = self.crawl_company_website(company.website_url)

        # 2. Preisblätter identifizieren
        price_documents = self.identify_price_documents(pages)

        # 3. PDF-Inhalte extrahieren
        extracted_data = []
        for doc in price_documents:
            if doc.type == 'pdf':
                content = self.extract_pdf_content(doc.url)
            else:
                content = self.extract_web_content(doc.url)

            extracted_data.append(content)

        # 4. Strukturierte Preise extrahieren
        structured_prices = self.parse_price_data(extracted_data)

        return PriceSheet(
            company_id=company.id,
            extracted_prices=structured_prices,
            validation_status='pending'
        )
```

### Datenvalidierung

#### Multi-Level-Validation

```python
class DataValidator:
    """Mehrstufige Datenvalidierung"""

    def validate(self, data: Any, context: ValidationContext) -> ValidationResult:
        validators = [
            SchemaValidator(),      # JSON Schema Validation
            BusinessRuleValidator(), # Geschäftsregeln
            CrossReferenceValidator(), # Referenzielle Integrität
            HistoricalValidator(),  # Historische Konsistenz
            GeographicValidator()   # Geografische Plausibilität
        ]

        results = []
        for validator in validators:
            result = validator.validate(data, context)
            results.append(result)

            if result.severity == 'critical':
                break  # Stop bei kritischen Fehlern

        return ValidationResult.combine(results)
```

#### Qualitätskennzahlen

```python
class DataQualityMetrics:
    """Datenqualitäts-Monitoring"""

    metrics = {
        'completeness': lambda df: df.notna().sum() / len(df),
        'uniqueness': lambda df: df.nunique() / len(df),
        'validity': lambda df: self.validate_format(df).sum() / len(df),
        'consistency': lambda df: self.check_consistency(df),
        'accuracy': lambda df: self.verify_accuracy(df)
    }
```

---

## 🧪 Qualitätssicherung

### Testing-Strategie

#### Test-Pyramide

```
    /\     E2E Tests (5%)
   /  \    API Integration Tests (15%)
  /____\   Unit Tests (80%)
```

#### Unit Tests

```python
# Beispiel: BDEW-Datenvalidierung
class TestBDEWDataValidation:
    def test_company_code_validation(self):
        """BDEW-Code muss dem Standard entsprechen"""
        validator = BDEWCodeValidator()

        # Valide Codes
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
```

#### Integration Tests

```python
class TestDataPipelineIntegration:
    async def test_bdew_full_pipeline(self):
        """Vollständiger BDEW-Import-Test"""
        pipeline = BDEWImportPipeline()

        # Mock-Daten verwenden
        with mock_bdew_api():
            result = await pipeline.run()

        assert result.status == 'success'
        assert result.records_processed > 0
        assert result.validation_errors == 0

    def test_price_extraction_accuracy(self):
        """Preisextraktion-Genauigkeit testen"""
        extractor = PriceExtractor()

        # Test mit bekannten Preisblättern
        test_pdfs = load_test_price_sheets()

        for pdf in test_pdfs:
            extracted = extractor.extract_prices(pdf.content)
            expected = pdf.expected_prices

            accuracy = calculate_extraction_accuracy(extracted, expected)
            assert accuracy > 0.95  # 95% Genauigkeit erforderlich
```

### Code Quality

#### Code-Standards

```python
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
multi_line_output = 3

[tool.mypy]
python_version = "3.11"
strict = true
disallow_untyped_defs = true

[tool.pytest]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "--cov=src --cov-report=html --cov-fail-under=95"
```

#### Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy

  - repo: https://github.com/pycqa/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
```

### Performance Testing

#### Load Testing

```python
# locustfile.py
from locust import HttpUser, task, between

class VNBDigitalUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def search_companies(self):
        """Unternehmensuche simulieren"""
        self.client.get("/api/v1/companies/search?q=stadtwerke")

    @task(2)
    def price_comparison(self):
        """Preisvergleich simulieren"""
        self.client.get("/api/v1/prices/14a?postal_code=80331")

    @task(1)
    def view_territories(self):
        """Netzgebiete abrufen"""
        self.client.get("/api/v1/territories/geojson")
```

---

## 🚀 Betrieb und Wartung

### Deployment-Architektur

#### GitHub Actions als Orchestrierungs-Platform

```yaml
# .github/workflows/data-pipeline.yml
name: Daily Data Pipeline
on:
  schedule:
    - cron: "0 2 * * *" # Täglich um 2:00 UTC
  workflow_dispatch:

jobs:
  bdew-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python + uv
        uses: astral-sh/setup-uv@v1
      - name: Run BDEW data sync
        run: uv run python -m src.pipelines.bdew_import
        env:
          DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}

  price-extraction:
    needs: bdew-sync
    runs-on: ubuntu-latest
    steps:
      - name: Extract VNB price sheets
        run: uv run python -m src.pipelines.price_extraction
        env:
          DATABASE_URL: ${{ secrets.NEON_DATABASE_URL }}

  deploy-webapp:
    needs: [bdew-sync, price-extraction]
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Docker Host
        run: |
          docker-compose -f docker-compose.prod.yml up -d --build webapp
        env:
          DOCKER_HOST: ${{ secrets.DOCKER_HOST_URL }}
```

#### Production Environment (Vereinfacht)

```yaml
# docker-compose.prod.yml
version: "3.8"
services:
  # Data Admin UI (FastAPI)
  admin-api:
    build:
      context: .
      dockerfile: Dockerfile.admin
    ports:
      - "8081:8081"
    environment:
      - ENV=production
      - DATABASE_URL=${{ secrets.NEON_DATABASE_URL }}
      - ADMIN_SECRET_KEY=${{ secrets.ADMIN_SECRET_KEY }}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  # Installateur Web-App (FastAPI + React)
  installer-api:
    build:
      context: .
      dockerfile: Dockerfile.installer
    ports:
      - "8080:8080"
    environment:
      - ENV=production
      - DATABASE_URL=${{ secrets.NEON_DATABASE_URL }}
      - OAUTH_CLIENT_ID=${{ secrets.OAUTH_CLIENT_ID }}
      - OAUTH_CLIENT_SECRET=${{ secrets.OAUTH_CLIENT_SECRET }}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  # Nginx für HTTPS/SSL-Termination und Routing
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - admin-api
      - installer-api
    restart: unless-stopped
```

#### Nginx Routing Configuration

```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name admin.vnbdigitaler.de;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://admin-api:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

server {
    listen 443 ssl;
    server_name installer.vnbdigitaler.de;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location / {
        proxy_pass http://installer-api:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Neon Database Setup

```python
# Database Connection für Neon
DATABASE_URL = "postgresql://username:password@ep-xyz.us-east-1.aws.neon.tech/vnbdigitaler?sslmode=require"  # pragma: allowlist secret

# Connection Pooling für Neon
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)
```

### Monitoring & Observability (Vereinfacht)

#### GitHub Actions Monitoring

```yaml
# .github/workflows/health-check.yml
name: System Health Check
on:
  schedule:
    - cron: "*/30 * * * *" # Alle 30 Minuten
  workflow_dispatch:

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - name: Check Streamlit App
        run: |
          curl -f https://vnbdigitaler.streamlit.app/health || exit 1

      - name: Check Database Connection
        run: |
          python -c "
          import psycopg2
          conn = psycopg2.connect('${{ secrets.NEON_DATABASE_URL }}')
          print('Database OK')
          "

      - name: Check Docker Host App
        run: |
          curl -f https://installer.vnbdigitaler.de/health || exit 1
```

#### Einfache Metriken

```python
# src/monitoring/simple_metrics.py
import json
from datetime import datetime
from pathlib import Path

class SimpleMetrics:
    """Einfaches Monitoring ohne Prometheus"""

    def __init__(self, metrics_file: str = "metrics.json"):
        self.metrics_file = Path(metrics_file)

    def record_pipeline_run(self, pipeline: str, status: str, records: int):
        metrics = self.load_metrics()
        metrics["pipeline_runs"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "pipeline": pipeline,
            "status": status,
            "records_processed": records
        })
        self.save_metrics(metrics)

    def record_api_request(self, endpoint: str, duration_ms: int):
        metrics = self.load_metrics()
        metrics["api_requests"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": endpoint,
            "duration_ms": duration_ms
        })
        self.save_metrics(metrics)
```

#### Health Checks (Vereinfacht)

```python
# src/health.py
from fastapi import APIRouter, status
import psycopg2

router = APIRouter()

@router.get("/health")
async def health_check():
    """Einfache Gesundheitsprüfung für Docker Host"""
    try:
        # Database Check
        conn = psycopg2.connect(DATABASE_URL)
        conn.close()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "database": "connected",
            "environment": "production"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }, 503
```

### Backup & Recovery (Neon-basiert)

#### Automatische Neon-Backups

```python
# Neon bietet automatische Backups
# Backup-Strategie: Neon-native Features nutzen

class NeonBackupManager:
    """Backup-Management mit Neon Database Features"""

    def __init__(self, neon_api_key: str):
        self.api_key = neon_api_key
        self.base_url = "https://console.neon.tech/api/v2"

    def create_branch_backup(self, project_id: str, backup_name: str):
        """Erstellt einen Branch als Backup (Neon-Feature)"""
        response = requests.post(
            f"{self.base_url}/projects/{project_id}/branches",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "name": f"backup-{backup_name}-{datetime.now().strftime('%Y%m%d')}",
                "parent_id": "main"
            }
        )
        return response.json()

    def export_schema_ddl(self):
        """Exportiert Schema-DDL als zusätzliches Backup"""
        with psycopg2.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT ddl FROM pg_get_schema_ddl('public')")
                return cur.fetchone()[0]
```

#### GitHub Actions Backup Workflow

```yaml
# .github/workflows/backup.yml
name: Weekly Backup
on:
  schedule:
    - cron: "0 3 * * 0" # Sonntags um 3:00 UTC

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - name: Create Neon Branch Backup
        run: |
          curl -X POST \
            -H "Authorization: Bearer ${{ secrets.NEON_API_KEY }}" \
            -H "Content-Type: application/json" \
            -d '{
              "name": "backup-$(date +%Y%m%d)",
              "parent_id": "main"
            }' \
            https://console.neon.tech/api/v2/projects/${{ secrets.NEON_PROJECT_ID }}/branches

      - name: Export Schema DDL
        run: |
          python scripts/backup_schema.py > backup-schema-$(date +%Y%m%d).sql

      - name: Upload to GitHub Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: schema-backup
          path: backup-schema-*.sql
```

#### Disaster Recovery Plan (Vereinfacht)

1. **RTO (Recovery Time Objective)**: 2 Stunden (Single Host)
2. **RPO (Recovery Point Objective)**: 15 Minuten (Neon automatische Backups)
3. **Backup-Strategie**: Neon-Branches + Schema-Exports
4. **Failover**: Manueller Neustart auf Docker Host

---

## 📋 Implementierungsplan

### Roadmap

#### Phase 1: Foundation (Abgeschlossen ✅)

**Zeitrahmen**: Q4 2025

- [x] Basis-Pipeline-Architektur
- [x] PostgreSQL-Integration
- [x] DevContainer-Setup
- [x] BDEW-Datenmodelle
- [x] Test-Framework

#### Phase 2: Core Data Integration (Aktuell 🔄)

**Zeitrahmen**: Q4 2025

- [x] BDEW-Stromnetzbetreiber-Import
- [ ] Multi-Rollen-BDEW-Integration (alle Marktteilnehmer)
- [ ] BNetzA-Rollout-Daten-Integration
- [ ] VNB Digital API-Integration
- [ ] Basis-Datenvalidierung

#### Phase 2.5: Data-Admin-WebUI (Geplant 📋)

**Zeitrahmen**: Q4 2025/Q1 2026

- [ ] FastAPI-Backend für Admin-Interface
- [ ] Data-Explorer-Dashboard (Tabellen-Übersicht)
- [ ] BDEW vs. BNetzA Verknüpfungs-Validierung
- [ ] Geo-Informationen Viewer und Editor
- [ ] Data-Quality-Monitoring-Interface
- [ ] Manuelle Datenkorrektur-Tools

#### Phase 3: Price Transparency (Geplant 📋)

**Zeitrahmen**: Q1 2026

- [ ] Netzbetreiber-Website-Crawling
- [ ] PDF-Preisblatt-Extraktion
- [ ] §14a-Preis-Normalisierung
- [ ] Preisvergleichs-Engine
- [ ] Historische Preisentwicklung

#### Phase 4: User Interface (Geplant 📋)

**Zeitrahmen**: Q1 2026

- [ ] Streamlit-Weboberfläche (Read-Only Portal)
- [ ] Interaktive Karten (Netzgebiete)
- [ ] Suchfunktionen und Datenexport
- [ ] Responsive Design für hohe Nutzerzahlen
- [ ] Separate Web-App für Installateur-Services (Grundgerüst)

#### Phase 5: Installer Services (Geplant 📋)

**Zeitrahmen**: Q1 2026

- [ ] Web-App-Entwicklung (React/Next.js)
- [ ] Benutzerauthentifizierung (OAuth2)
- [ ] Automatische Gasteintragung
- [ ] TAB-Dokumentenverwaltung
- [ ] Installateur-Dashboard mit Workflows
- [ ] Fristenerinnerungen und Notifications

#### Phase 6: Advanced Features (Geplant 📋)

**Zeitrahmen**: Q2-Q3 2026

- [ ] KI-gestützte Datenextraktion
- [ ] Predictive Analytics
- [ ] API-Marketplace
- [ ] Mobile App
- [ ] Machine Learning für Preisprediction

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
