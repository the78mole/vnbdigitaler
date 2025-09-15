# 🗄️ VNB Digitaler - Database Schema

> **📋 Projekt-Roadmap**: [ROADMAP.md](./ROADMAP.md) - Phasen und Meilensteine
> **⚙️ Technische Spezifikation**: [SPECIFICATION.md](./SPECIFICATION.md) - Architektur und Details
> **🔌 API-Dokumentation**: [API.md](./API.md) - REST & GraphQL APIs
> **🧪 Testing**: [TESTING.md](./TESTING.md) - Tests und Code Quality
> **🚀 Deployment**: [DEPLOYMENT.md](./DEPLOYMENT.md) - Production Setup

## 📊 Datenbank-Architektur Übersicht

Die VNB Digitaler Plattform verwendet PostgreSQL (via Neon Database) als primäre Datenbank mit einem normalisierten Schema, das verschiedene Aspekte des deutschen Energiemarkts abdeckt.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           VNB Digitaler Database                     │
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │   Companies     │────│   Linkages      │────│ Rollout Data    │ │
│  │                 │    │                 │    │                 │ │
│  │ • BDEW Codes    │    │ • BDEW ↔ BNetzA │    │ • Smart Meter   │ │
│  │ • Contact Info  │    │ • Confidence    │    │ • Quotas        │ │
│  │ • Roles         │    │ • Method        │    │ • Progress      │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
│           │                       │                       │         │
│           └───────────────────────┼───────────────────────┘         │
│                                   │                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │ Service Areas   │    │  Price Sheets   │    │  Installations  │ │
│  │                 │    │                 │    │                 │ │
│  │ • PostalCodes   │    │ • §14a Tariffs  │    │ • Customer Data │ │
│  │ • Territories   │    │ • Network Fees  │    │ • Status Track  │ │
│  │ • GeoJSON       │    │ • Extractions   │    │ • Documents     │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## 🏗️ Core Schema Definitionen

### Companies (Hauptentität)

```sql
-- Zentrale Unternehmensentität für BDEW-registrierte Marktteilnehmer
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- BDEW Identifikation
    code VARCHAR(20) UNIQUE NOT NULL,  -- 13-stelliger BDEW-Code
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(100),

    -- Geografische Information
    street VARCHAR(255),
    postal_code VARCHAR(10),
    city VARCHAR(100),
    state VARCHAR(50),
    country CHAR(2) DEFAULT 'DE',

    -- Kontaktinformationen
    website VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    fax VARCHAR(50),

    -- Geschäftsinformationen
    status company_status DEFAULT 'active',
    registration_date DATE,
    registration_court VARCHAR(255),
    commercial_register VARCHAR(100),

    -- Geo-Koordinaten
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),

    -- Metadaten
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_latitude CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT valid_longitude CHECK (longitude BETWEEN -180 AND 180),
    CONSTRAINT valid_postal_code CHECK (postal_code ~ '^\d{5}$'),
    CONSTRAINT valid_bdew_code CHECK (length(code) BETWEEN 10 AND 20)
);

-- Company Status Enum
CREATE TYPE company_status AS ENUM (
    'active',
    'inactive',
    'merged',
    'dissolved',
    'pending'
);

-- Indexes für Performance
CREATE INDEX idx_companies_code ON companies(code);
CREATE INDEX idx_companies_name ON companies USING gin(to_tsvector('german', name));
CREATE INDEX idx_companies_location ON companies(postal_code, city);
CREATE INDEX idx_companies_geo ON companies USING gist(point(longitude, latitude));
CREATE INDEX idx_companies_status ON companies(status) WHERE status = 'active';
```

### Company Roles (Marktteilnehmer-Rollen)

```sql
-- Marktteilnehmer-Rollen (VNB, ÜNB, MSB, etc.)
CREATE TABLE company_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    -- Rolle und Gültigkeit
    role_type market_role NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    valid_from DATE,
    valid_until DATE,

    -- Rollenspezifische Informationen (JSON für Flexibilität)
    role_details JSONB DEFAULT '{}',

    -- Metadaten
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    UNIQUE(company_id, role_type),
    CONSTRAINT valid_date_range CHECK (valid_until IS NULL OR valid_until >= valid_from)
);

-- Market Role Enum
CREATE TYPE market_role AS ENUM (
    'VNB',     -- Verteilnetzbetreiber
    'UNB',     -- Übertragungsnetzbetreiber
    'EVU',     -- Energieversorgungsunternehmen
    'MSB',     -- Messstellenbetreiber
    'LNG',     -- Fernleitungsnetzbetreiber
    'RLM',     -- Regelleistungsmarkt
    'BILKO',   -- Bilanzkoordinator
    'BILKRS'   -- Bilanzkreis
);

-- Indexes
CREATE INDEX idx_company_roles_company ON company_roles(company_id);
CREATE INDEX idx_company_roles_type ON company_roles(role_type) WHERE active = TRUE;
CREATE INDEX idx_company_roles_active ON company_roles(active, valid_from, valid_until);
```

### Smart Meter Rollout Data

```sql
-- BNetzA Smart-Meter-Rollout-Daten
CREATE TABLE rollout_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,

    -- Rollout-Informationen
    quarter CHAR(6) NOT NULL,  -- Format: 2025Q1
    rollout_quota DECIMAL(5,4) NOT NULL,  -- 0.0000 - 1.0000
    installations_completed INTEGER DEFAULT 0,
    installations_target INTEGER NOT NULL,
    rollout_deadline DATE,

    -- Fortschritt
    progress_percentage DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE
            WHEN installations_target > 0
            THEN (installations_completed::DECIMAL / installations_target) * 100
            ELSE 0
        END
    ) STORED,

    -- Status
    compliance_status rollout_status DEFAULT 'on_track',
    notes TEXT,

    -- Metadaten
    data_source VARCHAR(100) DEFAULT 'BNetzA',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_quota CHECK (rollout_quota BETWEEN 0 AND 1),
    CONSTRAINT valid_installations CHECK (installations_completed >= 0),
    CONSTRAINT valid_target CHECK (installations_target > 0),
    CONSTRAINT valid_quarter CHECK (quarter ~ '^\d{4}Q[1-4]$'),
    UNIQUE(company_id, quarter)
);

-- Rollout Status Enum
CREATE TYPE rollout_status AS ENUM (
    'ahead_of_schedule',
    'on_track',
    'delayed',
    'critical_delay',
    'non_compliant'
);

-- Indexes
CREATE INDEX idx_rollout_company ON rollout_data(company_id);
CREATE INDEX idx_rollout_quarter ON rollout_data(quarter);
CREATE INDEX idx_rollout_status ON rollout_data(compliance_status);
CREATE INDEX idx_rollout_progress ON rollout_data(progress_percentage DESC);
```

### Data Integration & Linkages

```sql
-- BDEW ↔ BNetzA Datenverknüpfungen
CREATE TABLE data_linkages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Verknüpfte Entitäten
    bdew_company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    bnetza_rollout_id UUID REFERENCES rollout_data(id) ON DELETE SET NULL,

    -- Verknüpfungsqualität
    confidence_score DECIMAL(3,2) NOT NULL,  -- 0.00 - 1.00
    linkage_method linkage_method NOT NULL,

    -- Validation
    manually_verified BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(100),
    verified_at TIMESTAMP WITH TIME ZONE,

    -- Similarity Factors (JSON für Flexibilität)
    similarity_factors JSONB DEFAULT '{}',

    -- Metadaten
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_confidence CHECK (confidence_score BETWEEN 0 AND 1),
    UNIQUE(bdew_company_id, bnetza_rollout_id)
);

-- Linkage Method Enum
CREATE TYPE linkage_method AS ENUM (
    'exact_name_match',
    'fuzzy_name_match',
    'location_match',
    'combined_algorithm',
    'manual_review',
    'ml_prediction'
);

-- Indexes
CREATE INDEX idx_linkages_bdew ON data_linkages(bdew_company_id);
CREATE INDEX idx_linkages_bnetza ON data_linkages(bnetza_rollout_id);
CREATE INDEX idx_linkages_confidence ON data_linkages(confidence_score DESC);
CREATE INDEX idx_linkages_method ON data_linkages(linkage_method);
CREATE INDEX idx_linkages_verified ON data_linkages(manually_verified);
```

### Service Territories (Netzgebiete)

```sql
-- VNB Service-Gebiete und Netzterritorien
CREATE TABLE service_territories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    -- Territory Identification
    name VARCHAR(255) NOT NULL,
    territory_code VARCHAR(50),

    -- Geographic Data
    postal_codes TEXT[], -- Array von Postleitzahlen
    geometry GEOMETRY(MULTIPOLYGON, 4326), -- GeoJSON-kompatible Geometrie

    -- Demographics
    population_served INTEGER,
    area_km2 DECIMAL(10,2),
    customer_count INTEGER,
    household_count INTEGER,

    -- Grid Information
    voltage_levels INTEGER[] DEFAULT ARRAY[400, 230], -- Spannungsebenen in V
    grid_length_km DECIMAL(10,2),
    substations_count INTEGER,

    -- Service Quality
    reliability_index DECIMAL(5,4), -- SAIDI (System Average Interruption Duration Index)
    customer_satisfaction DECIMAL(3,2), -- 1.00 - 5.00

    -- Metadaten
    data_source VARCHAR(100) DEFAULT 'manual',
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_population CHECK (population_served >= 0),
    CONSTRAINT valid_area CHECK (area_km2 > 0),
    CONSTRAINT valid_reliability CHECK (reliability_index BETWEEN 0 AND 24),
    CONSTRAINT valid_satisfaction CHECK (customer_satisfaction BETWEEN 1 AND 5)
);

-- Spatial Indexes für geografische Abfragen
CREATE INDEX idx_territories_company ON service_territories(company_id);
CREATE INDEX idx_territories_geometry ON service_territories USING gist(geometry);
CREATE INDEX idx_territories_postal_codes ON service_territories USING gin(postal_codes);
CREATE INDEX idx_territories_population ON service_territories(population_served DESC);

-- PostGIS Spatial Reference System
INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, proj4text, srtext) VALUES (
    4326,
    'EPSG',
    4326,
    '+proj=longlat +datum=WGS84 +no_defs',
    'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]'
) ON CONFLICT (srid) DO NOTHING;
```

### Price Sheets & §14a Tariffs

```sql
-- Preisblätter und Tarifinformationen
CREATE TABLE price_sheets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    -- Preisblatt-Informationen
    title VARCHAR(255) NOT NULL,
    document_type price_sheet_type NOT NULL,
    version VARCHAR(50),

    -- Gültigkeit
    valid_from DATE NOT NULL,
    valid_until DATE,

    -- Dokument-Details
    source_url VARCHAR(500),
    file_path VARCHAR(255),
    file_size_bytes INTEGER,
    file_hash VARCHAR(64), -- SHA-256

    -- Extraktion Status
    extracted BOOLEAN DEFAULT FALSE,
    extraction_method extraction_method,
    extraction_confidence DECIMAL(3,2),
    extraction_date TIMESTAMP WITH TIME ZONE,

    -- Strukturierte Preisdaten (JSON für Flexibilität)
    price_data JSONB DEFAULT '{}',

    -- Metadaten
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_date_range CHECK (valid_until IS NULL OR valid_until >= valid_from),
    CONSTRAINT valid_confidence CHECK (extraction_confidence BETWEEN 0 AND 1),
    UNIQUE(company_id, document_type, valid_from)
);

-- Price Sheet Type Enum
CREATE TYPE price_sheet_type AS ENUM (
    'network_charges',
    'section_14a',
    'metering_charges',
    'connection_charges',
    'general_terms'
);

-- Extraction Method Enum
CREATE TYPE extraction_method AS ENUM (
    'manual',
    'pdf_text_extraction',
    'ocr_processing',
    'ml_structured_extraction',
    'web_scraping'
);

-- Indexes
CREATE INDEX idx_price_sheets_company ON price_sheets(company_id);
CREATE INDEX idx_price_sheets_type ON price_sheets(document_type);
CREATE INDEX idx_price_sheets_validity ON price_sheets(valid_from, valid_until);
CREATE INDEX idx_price_sheets_extracted ON price_sheets(extracted, extraction_date);
```

### §14a Pricing Details

```sql
-- Detaillierte §14a-Preisstrukturen
CREATE TABLE section_14a_pricing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    price_sheet_id UUID NOT NULL REFERENCES price_sheets(id) ON DELETE CASCADE,

    -- Anwendungsbereich
    application_type application_type NOT NULL,
    power_range_min_kw DECIMAL(8,2),
    power_range_max_kw DECIMAL(8,2),

    -- Preisstruktur
    base_price_ct_kwh DECIMAL(8,4),
    reduced_price_ct_kwh DECIMAL(8,4),
    reduction_percentage DECIMAL(5,2), -- Calculated field

    -- Zusatzkosten
    monthly_fee_eur DECIMAL(8,2) DEFAULT 0,
    connection_fee_eur DECIMAL(8,2) DEFAULT 0,

    -- Bedingungen
    controllability_required BOOLEAN DEFAULT TRUE,
    minimum_contract_duration_months INTEGER DEFAULT 12,
    special_conditions TEXT[],

    -- Time-of-Use Pricing
    peak_hours TIME[],
    off_peak_discount_percent DECIMAL(5,2),

    -- Metadaten
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_power_range CHECK (power_range_max_kw IS NULL OR power_range_max_kw >= power_range_min_kw),
    CONSTRAINT valid_prices CHECK (base_price_ct_kwh > 0 AND reduced_price_ct_kwh >= 0),
    CONSTRAINT valid_reduction CHECK (reduction_percentage BETWEEN 0 AND 100),
    CONSTRAINT valid_contract_duration CHECK (minimum_contract_duration_months > 0)
);

-- Application Type Enum (§14a-steuerbare Verbrauchseinrichtungen)
CREATE TYPE application_type AS ENUM (
    'wallbox',
    'heat_pump',
    'energy_storage',
    'pv_system',
    'night_storage_heater',
    'air_conditioning',
    'pool_heating'
);

-- Calculated field trigger for reduction percentage
CREATE OR REPLACE FUNCTION calculate_reduction_percentage()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.base_price_ct_kwh > 0 AND NEW.reduced_price_ct_kwh IS NOT NULL THEN
        NEW.reduction_percentage := ((NEW.base_price_ct_kwh - NEW.reduced_price_ct_kwh) / NEW.base_price_ct_kwh) * 100;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_calculate_reduction_percentage
    BEFORE INSERT OR UPDATE ON section_14a_pricing
    FOR EACH ROW EXECUTE FUNCTION calculate_reduction_percentage();

-- Indexes
CREATE INDEX idx_14a_pricing_sheet ON section_14a_pricing(price_sheet_id);
CREATE INDEX idx_14a_pricing_application ON section_14a_pricing(application_type);
CREATE INDEX idx_14a_pricing_power_range ON section_14a_pricing(power_range_min_kw, power_range_max_kw);
CREATE INDEX idx_14a_pricing_reduction ON section_14a_pricing(reduction_percentage DESC);
```

## 🔧 Installer Services Schema

### Installation Requests

```sql
-- Installationsanträge und -tracking
CREATE TABLE installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Installation Identification
    installation_number VARCHAR(50) UNIQUE NOT NULL, -- Human-readable ID

    -- Customer Information
    customer_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255),
    customer_phone VARCHAR(50),

    -- Installation Address
    installation_street VARCHAR(255) NOT NULL,
    installation_postal_code VARCHAR(10) NOT NULL,
    installation_city VARCHAR(100) NOT NULL,
    installation_state VARCHAR(50),

    -- Installation Details
    installation_type installation_type NOT NULL,
    device_manufacturer VARCHAR(100),
    device_model VARCHAR(100),
    power_rating_kw DECIMAL(8,2) NOT NULL,
    planned_installation_date DATE,
    actual_installation_date DATE,

    -- Grid Connection
    grid_operator_id UUID REFERENCES companies(id),
    meter_number VARCHAR(50),
    connection_type connection_type DEFAULT 'single_phase',
    existing_grid_capacity_kw DECIMAL(8,2),

    -- Installer Information
    installer_company VARCHAR(255) NOT NULL,
    installer_contact_person VARCHAR(255),
    installer_email VARCHAR(255),
    installer_phone VARCHAR(50),
    installer_license_number VARCHAR(100),

    -- Status Tracking
    status installation_status DEFAULT 'created',
    status_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Requirements & Approvals
    grid_operator_approval_required BOOLEAN DEFAULT TRUE,
    grid_operator_approval_received BOOLEAN DEFAULT FALSE,
    grid_operator_response_date DATE,

    -- Special Requirements
    electrical_panel_upgrade_required BOOLEAN DEFAULT FALSE,
    additional_safety_measures TEXT[],
    special_installation_notes TEXT,

    -- Financial Information
    estimated_cost_eur DECIMAL(10,2),
    section_14a_discount_applicable BOOLEAN DEFAULT FALSE,
    estimated_annual_savings_eur DECIMAL(8,2),

    -- Metadaten
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_power_rating CHECK (power_rating_kw > 0),
    CONSTRAINT valid_postal_code CHECK (installation_postal_code ~ '^\d{5}$'),
    CONSTRAINT valid_email CHECK (customer_email IS NULL OR customer_email LIKE '%@%'),
    CONSTRAINT valid_planned_date CHECK (planned_installation_date IS NULL OR planned_installation_date >= CURRENT_DATE)
);

-- Installation Type Enum
CREATE TYPE installation_type AS ENUM (
    'wallbox',
    'heat_pump',
    'energy_storage_system',
    'pv_system',
    'combined_heat_power',
    'night_storage_heater'
);

-- Connection Type Enum
CREATE TYPE connection_type AS ENUM (
    'single_phase',
    'three_phase',
    'high_voltage'
);

-- Installation Status Enum
CREATE TYPE installation_status AS ENUM (
    'created',
    'customer_confirmed',
    'documents_submitted',
    'grid_operator_review',
    'approved',
    'installation_scheduled',
    'installation_completed',
    'commissioned',
    'cancelled',
    'rejected'
);

-- Indexes
CREATE INDEX idx_installations_number ON installations(installation_number);
CREATE INDEX idx_installations_customer ON installations(customer_email);
CREATE INDEX idx_installations_installer ON installations(installer_company);
CREATE INDEX idx_installations_grid_operator ON installations(grid_operator_id);
CREATE INDEX idx_installations_status ON installations(status);
CREATE INDEX idx_installations_postal_code ON installations(installation_postal_code);
CREATE INDEX idx_installations_planned_date ON installations(planned_installation_date);
```

### Installation Documents

```sql
-- Dokumente für Installationsanträge
CREATE TABLE installation_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    installation_id UUID NOT NULL REFERENCES installations(id) ON DELETE CASCADE,

    -- Document Information
    document_type document_type NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500),
    file_size_bytes INTEGER,
    mime_type VARCHAR(100),
    file_hash VARCHAR(64), -- SHA-256

    -- Document Status
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    verified BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(100),
    verified_at TIMESTAMP WITH TIME ZONE,

    -- Document Source
    uploaded_by_user VARCHAR(255),
    auto_generated BOOLEAN DEFAULT FALSE,
    template_used VARCHAR(255),

    -- Additional Metadata
    document_version VARCHAR(50),
    requires_signature BOOLEAN DEFAULT FALSE,
    signature_received BOOLEAN DEFAULT FALSE,
    expiry_date DATE,

    -- Metadaten
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_file_size CHECK (file_size_bytes > 0),
    CONSTRAINT valid_mime_type CHECK (mime_type SIMILAR TO '(application|image|text)/%')
);

-- Document Type Enum
CREATE TYPE document_type AS ENUM (
    'grid_connection_application',
    'electrical_safety_certificate',
    'installation_protocol',
    'device_specification_sheet',
    'installer_qualification_certificate',
    'customer_consent_form',
    'technical_drawing',
    'photo_documentation',
    'commissioning_report',
    'warranty_documentation'
);

-- Indexes
CREATE INDEX idx_documents_installation ON installation_documents(installation_id);
CREATE INDEX idx_documents_type ON installation_documents(document_type);
CREATE INDEX idx_documents_verified ON installation_documents(verified);
CREATE INDEX idx_documents_uploaded ON installation_documents(uploaded_at);
```

## 🔍 Advanced Features Schema

### User Management

```sql
-- Benutzer und Authentifizierung
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Authentication
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255), -- NULL für OAuth-only users
    oauth_provider VARCHAR(50),
    oauth_subject VARCHAR(255),

    -- Profile Information
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    company_name VARCHAR(255),
    phone VARCHAR(50),

    -- User Type & Permissions
    user_type user_type NOT NULL DEFAULT 'installer',
    roles VARCHAR(50)[] DEFAULT ARRAY['user'],
    permissions JSONB DEFAULT '{}',

    -- Account Status
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_token VARCHAR(255),

    -- Security
    last_login TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE,
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP WITH TIME ZONE,

    -- Preferences
    language CHAR(2) DEFAULT 'de',
    timezone VARCHAR(50) DEFAULT 'Europe/Berlin',
    notification_preferences JSONB DEFAULT '{}',

    -- Metadaten
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_email CHECK (email LIKE '%@%'),
    CONSTRAINT valid_language CHECK (language IN ('de', 'en')),
    CONSTRAINT unique_oauth_user UNIQUE(oauth_provider, oauth_subject)
);

-- User Type Enum
CREATE TYPE user_type AS ENUM (
    'admin',
    'installer',
    'grid_operator',
    'public',
    'api_client'
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_subject);
CREATE INDEX idx_users_type ON users(user_type);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = TRUE;
```

### API Usage & Analytics

```sql
-- API-Nutzungsstatistiken
CREATE TABLE api_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Request Information
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    api_key_id UUID, -- Referenz zu API-Keys falls implementiert

    -- Request Details
    request_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    response_status INTEGER NOT NULL,
    response_time_ms INTEGER,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,

    -- Geographic Information
    client_ip INET,
    user_agent TEXT,
    country_code CHAR(2),

    -- Query Information
    query_parameters JSONB,
    request_body_hash VARCHAR(64), -- Hash des Request Body für Privacy

    -- Rate Limiting
    rate_limit_remaining INTEGER,
    rate_limit_reset TIMESTAMP WITH TIME ZONE,

    -- Error Information
    error_code VARCHAR(50),
    error_message TEXT,

    -- Partitioning (für Performance bei großen Datenmengen)
    created_date DATE GENERATED ALWAYS AS (request_timestamp::DATE) STORED
) PARTITION BY RANGE (created_date);

-- Create monthly partitions (example for 2025)
CREATE TABLE api_usage_logs_2025_01 PARTITION OF api_usage_logs
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE api_usage_logs_2025_02 PARTITION OF api_usage_logs
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
-- ... weitere Partitionen nach Bedarf

-- Indexes
CREATE INDEX idx_api_logs_timestamp ON api_usage_logs(request_timestamp);
CREATE INDEX idx_api_logs_user ON api_usage_logs(user_id);
CREATE INDEX idx_api_logs_endpoint ON api_usage_logs(endpoint);
CREATE INDEX idx_api_logs_status ON api_usage_logs(response_status);
CREATE INDEX idx_api_logs_ip ON api_usage_logs USING hash(client_ip);
```

### Data Quality & Audit Trail

```sql
-- Datenqualitäts-Tracking
CREATE TABLE data_quality_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Metric Identification
    table_name VARCHAR(100) NOT NULL,
    metric_type quality_metric_type NOT NULL,

    -- Metric Values
    metric_value DECIMAL(10,6) NOT NULL,
    threshold_value DECIMAL(10,6),
    status quality_status NOT NULL,

    -- Assessment Details
    assessment_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    total_records INTEGER,
    affected_records INTEGER,

    -- Issue Details
    issues_found JSONB DEFAULT '[]',
    recommendations TEXT[],

    -- Resolution
    resolved BOOLEAN DEFAULT FALSE,
    resolved_by VARCHAR(100),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,

    -- Metadaten
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Quality Metric Type Enum
CREATE TYPE quality_metric_type AS ENUM (
    'completeness',
    'accuracy',
    'consistency',
    'timeliness',
    'validity',
    'uniqueness'
);

-- Quality Status Enum
CREATE TYPE quality_status AS ENUM (
    'excellent',
    'good',
    'warning',
    'critical',
    'failed'
);

-- Audit Trail für Datenänderungen
CREATE TABLE audit_trail (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Change Information
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    operation audit_operation NOT NULL,

    -- User Information
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    session_id VARCHAR(255),

    -- Change Details
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],

    -- Context
    change_reason VARCHAR(500),
    approval_required BOOLEAN DEFAULT FALSE,
    approved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    approved_at TIMESTAMP WITH TIME ZONE,

    -- Metadaten
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Partitioning für Performance
    created_date DATE GENERATED ALWAYS AS (created_at::DATE) STORED
) PARTITION BY RANGE (created_date);

-- Audit Operation Enum
CREATE TYPE audit_operation AS ENUM (
    'INSERT',
    'UPDATE',
    'DELETE',
    'BULK_UPDATE',
    'BULK_DELETE'
);

-- Indexes
CREATE INDEX idx_audit_table_record ON audit_trail(table_name, record_id);
CREATE INDEX idx_audit_user ON audit_trail(user_id);
CREATE INDEX idx_audit_timestamp ON audit_trail(created_at);
CREATE INDEX idx_audit_operation ON audit_trail(operation);
```

## 🔧 Database Functions & Triggers

### Automatic Timestamp Updates

```sql
-- Generic function für updated_at Trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger für alle relevanten Tabellen
CREATE TRIGGER trg_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_company_roles_updated_at
    BEFORE UPDATE ON company_roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_rollout_data_updated_at
    BEFORE UPDATE ON rollout_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_data_linkages_updated_at
    BEFORE UPDATE ON data_linkages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_installations_updated_at
    BEFORE UPDATE ON installations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### Data Validation Functions

```sql
-- BDEW-Code Validation
CREATE OR REPLACE FUNCTION validate_bdew_code(code TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- BDEW-Codes sind 13-stellig und numerisch
    RETURN code ~ '^\d{13}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- PostalCode Validation für Deutschland
CREATE OR REPLACE FUNCTION validate_german_postal_code(postal_code TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- Deutsche PLZ: 5-stellig, 01000-99999
    RETURN postal_code ~ '^\d{5}$' AND postal_code::INTEGER BETWEEN 1000 AND 99999;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Email Validation
CREATE OR REPLACE FUNCTION validate_email(email TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

### Search Functions

```sql
-- Full-Text Search für Companies
CREATE OR REPLACE FUNCTION search_companies(
    search_query TEXT,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE(
    company_id UUID,
    name VARCHAR(255),
    city VARCHAR(100),
    postal_code VARCHAR(10),
    rank REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.name,
        c.city,
        c.postal_code,
        ts_rank(
            to_tsvector('german', COALESCE(c.name, '') || ' ' || COALESCE(c.city, '')),
            plainto_tsquery('german', search_query)
        ) as rank
    FROM companies c
    WHERE to_tsvector('german', COALESCE(c.name, '') || ' ' || COALESCE(c.city, ''))
          @@ plainto_tsquery('german', search_query)
    ORDER BY rank DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Geographic Search
CREATE OR REPLACE FUNCTION find_vnb_by_postal_code(
    postal_code_input TEXT
)
RETURNS TABLE(
    company_id UUID,
    company_name VARCHAR(255),
    coverage_area TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.name,
        st.postal_codes
    FROM companies c
    JOIN company_roles cr ON c.id = cr.company_id
    JOIN service_territories st ON c.id = st.company_id
    WHERE cr.role_type = 'VNB'
      AND cr.active = TRUE
      AND postal_code_input = ANY(st.postal_codes);
END;
$$ LANGUAGE plpgsql;
```

## 📊 Performance Optimizations

### Connection Pooling

```sql
-- Connection Pooling Configuration für Neon
-- Diese Einstellungen werden in der Applikation konfiguriert

-- Empfohlene Pool-Einstellungen:
-- pool_size = 5           -- Basis-Verbindungen
-- max_overflow = 10       -- Zusätzliche Verbindungen bei Bedarf
-- pool_pre_ping = True    -- Verbindungen vor Nutzung testen
-- pool_recycle = 3600     -- Verbindungen nach 1h erneuern
```

### Query Optimization

```sql
-- Materialized Views für häufige Abfragen
CREATE MATERIALIZED VIEW vnb_with_rollout_summary AS
SELECT
    c.id,
    c.name,
    c.city,
    c.postal_code,
    rd.rollout_quota,
    rd.progress_percentage,
    rd.compliance_status,
    COUNT(st.id) as territory_count,
    SUM(st.population_served) as total_population_served
FROM companies c
JOIN company_roles cr ON c.id = cr.company_id AND cr.role_type = 'VNB' AND cr.active = TRUE
LEFT JOIN rollout_data rd ON c.id = rd.company_id
    AND rd.quarter = (SELECT MAX(quarter) FROM rollout_data)
LEFT JOIN service_territories st ON c.id = st.company_id
GROUP BY c.id, c.name, c.city, c.postal_code, rd.rollout_quota, rd.progress_percentage, rd.compliance_status;

-- Index für Materialized View
CREATE INDEX idx_vnb_rollout_summary_name ON vnb_with_rollout_summary USING gin(to_tsvector('german', name));
CREATE INDEX idx_vnb_rollout_summary_progress ON vnb_with_rollout_summary(progress_percentage DESC);

-- Refresh-Funktion für Materialized View
CREATE OR REPLACE FUNCTION refresh_vnb_rollout_summary()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY vnb_with_rollout_summary;
END;
$$ LANGUAGE plpgsql;
```

### Table Partitioning für große Tabellen

```sql
-- Partitioning für API Logs (bereits implementiert oben)
-- Partitioning für Audit Trail (bereits implementiert oben)

-- Automatische Partition-Erstellung
CREATE OR REPLACE FUNCTION create_monthly_partition(
    table_name TEXT,
    start_date DATE
)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    end_date DATE;
BEGIN
    partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
    end_date := start_date + INTERVAL '1 month';

    EXECUTE format('CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;
```

## 🔐 Security & Permissions

### Row Level Security

```sql
-- Row Level Security für Multi-Tenant Szenarios
ALTER TABLE installations ENABLE ROW LEVEL SECURITY;

-- Policy: Installateure sehen nur ihre eigenen Installationen
CREATE POLICY installer_installations_policy ON installations
    FOR ALL TO installer_role
    USING (installer_email = current_setting('app.user_email'));

-- Policy: Admins sehen alles
CREATE POLICY admin_installations_policy ON installations
    FOR ALL TO admin_role
    USING (true);

-- Rollen erstellen
CREATE ROLE installer_role;
CREATE ROLE admin_role;

-- Grundlegende Berechtigungen
GRANT SELECT, INSERT, UPDATE ON installations TO installer_role;
GRANT ALL ON installations TO admin_role;
```

### Data Encryption

```sql
-- Sensitive Daten verschlüsseln (PostgreSQL pgcrypto)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Beispiel: Verschlüsselung von Kundendaten
ALTER TABLE installations
ADD COLUMN customer_email_encrypted BYTEA,
ADD COLUMN customer_phone_encrypted BYTEA;

-- Verschlüsselungs-/Entschlüsselungsfunktionen
CREATE OR REPLACE FUNCTION encrypt_pii(data TEXT, key TEXT)
RETURNS BYTEA AS $$
BEGIN
    RETURN pgp_sym_encrypt(data, key);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION decrypt_pii(encrypted_data BYTEA, key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(encrypted_data, key);
END;
$$ LANGUAGE plpgsql;
```

## 📝 Database Maintenance

### Backup Strategy

```sql
-- Backup-relevante Views für Export
CREATE VIEW companies_export AS
SELECT
    code,
    name,
    city,
    postal_code,
    status,
    ARRAY_AGG(cr.role_type) as roles
FROM companies c
LEFT JOIN company_roles cr ON c.id = cr.company_id AND cr.active = TRUE
WHERE c.status = 'active'
GROUP BY c.code, c.name, c.city, c.postal_code, c.status;

-- Critical Data View für Notfall-Recovery
CREATE VIEW critical_data_export AS
SELECT
    'companies' as table_name,
    COUNT(*) as record_count,
    MAX(updated_at) as last_update
FROM companies
UNION ALL
SELECT
    'rollout_data',
    COUNT(*),
    MAX(updated_at)
FROM rollout_data
UNION ALL
SELECT
    'installations',
    COUNT(*),
    MAX(updated_at)
FROM installations;
```

### Statistics & Monitoring

```sql
-- Database Statistics View
CREATE VIEW db_statistics AS
SELECT
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_rows,
    n_dead_tup as dead_rows,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;

-- Index Usage Statistics
CREATE VIEW index_usage AS
SELECT
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan,
    CASE
        WHEN idx_scan = 0 THEN 'Unused'
        WHEN idx_scan < 100 THEN 'Low Usage'
        ELSE 'Active'
    END as usage_status
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

---

_Diese Datenbank-Dokumentation wird kontinuierlich erweitert und optimiert, um die wachsenden Anforderungen der VNB Digitaler Plattform zu erfüllen._
