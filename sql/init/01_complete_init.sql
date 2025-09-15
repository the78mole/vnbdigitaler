-- VNB Digitaler Database Complete Initialization - NORMALIZED VERSION
-- PostgreSQL 16 compatible
-- This script drops everything and rebuilds with proper normalization

-- ============================================================================
-- CLEANUP - DROP EVERYTHING FIRST
-- ============================================================================

-- Drop all existing tables in correct order (reverse dependency)
DROP TABLE IF EXISTS vnb_digitaler.bdew_sync_log CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.bdew_code_registry CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.bdew_market_participants CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.price_sheets CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.bnetza_rollout_data CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.company_roles CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.companies CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.market_participant_roles CASCADE;

-- Drop lookup tables
DROP TABLE IF EXISTS vnb_digitaler.role_categories CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.markets CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.legal_forms CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.countries CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.registration_authorities CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.status_types CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.data_sources CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.document_types CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.price_categories CASCADE;
DROP TABLE IF EXISTS vnb_digitaler.customer_segments CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS vnb_digitaler.update_updated_at_column() CASCADE;

-- Drop schema (will be recreated)
DROP SCHEMA IF EXISTS vnb_digitaler CASCADE;

-- ============================================================================
-- BASIC SETUP
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schema
CREATE SCHEMA vnb_digitaler;

-- Set search path
SET search_path TO vnb_digitaler, public;

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================================================
-- LOOKUP TABLES (NORMALIZED)
-- ============================================================================

-- Role Categories
CREATE TABLE role_categories (
    id SMALLSERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name_de VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    description TEXT,
    sort_order SMALLINT DEFAULT 999,
    is_active BOOLEAN DEFAULT true
);

-- Markets
CREATE TABLE markets (
    id SMALLSERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name_de VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT true
);

-- Legal Forms
CREATE TABLE legal_forms (
    id SMALLSERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name_de VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    description TEXT,
    country_code VARCHAR(3) DEFAULT 'DEU',
    is_active BOOLEAN DEFAULT true
);

-- Countries
CREATE TABLE countries (
    id SMALLSERIAL PRIMARY KEY,
    iso_code_2 VARCHAR(2) NOT NULL UNIQUE,
    iso_code_3 VARCHAR(3) NOT NULL UNIQUE,
    name_de VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    is_eu_member BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true
);

-- Registration Authorities
CREATE TABLE registration_authorities (
    id SMALLSERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name_de VARCHAR(200) NOT NULL,
    name_en VARCHAR(200),
    website_url VARCHAR(500),
    contact_email VARCHAR(255),
    country_id SMALLINT REFERENCES countries(id),
    is_active BOOLEAN DEFAULT true
);

-- Status Types (generic for different entities)
CREATE TABLE status_types (
    id SMALLSERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL, -- 'company', 'role', 'sync', etc.
    code VARCHAR(20) NOT NULL,
    name_de VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    description TEXT,
    is_active_status BOOLEAN DEFAULT true, -- whether this status means "active"
    sort_order SMALLINT DEFAULT 999,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(entity_type, code)
);

-- Data Sources
CREATE TABLE data_sources (
    id SMALLSERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name_de VARCHAR(200) NOT NULL,
    name_en VARCHAR(200),
    base_url VARCHAR(500),
    api_endpoint VARCHAR(500),
    contact_email VARCHAR(255),
    update_frequency VARCHAR(50), -- daily, weekly, monthly, real-time
    is_official BOOLEAN DEFAULT false, -- official BDEW source vs. third-party
    is_active BOOLEAN DEFAULT true
);

-- Document Types
CREATE TABLE document_types (
    id SMALLSERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name_de VARCHAR(200) NOT NULL,
    name_en VARCHAR(200),
    description TEXT,
    file_extensions VARCHAR(200), -- .pdf,.xlsx,.csv
    is_active BOOLEAN DEFAULT true
);

-- Price Categories
CREATE TABLE price_categories (
    id SMALLSERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name_de VARCHAR(200) NOT NULL,
    name_en VARCHAR(200),
    description TEXT,
    unit VARCHAR(20), -- €/kWh, €/Jahr, etc.
    is_active BOOLEAN DEFAULT true
);

-- Customer Segments
CREATE TABLE customer_segments (
    id SMALLSERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name_de VARCHAR(200) NOT NULL,
    name_en VARCHAR(200),
    description TEXT,
    consumption_range_min INTEGER, -- kWh/year
    consumption_range_max INTEGER, -- kWh/year
    is_active BOOLEAN DEFAULT true
);

-- ============================================================================
-- CORE TABLES (NORMALIZED)
-- ============================================================================

-- Official BDEW Role Codes (from BDEW documentation)
CREATE TABLE market_participant_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bdew_role_code VARCHAR(10) NOT NULL UNIQUE,
    role_name_de VARCHAR(200) NOT NULL,
    role_name_en VARCHAR(200),
    role_category_id SMALLINT NOT NULL REFERENCES role_categories(id),
    role_description TEXT,
    applicable_market_id SMALLINT REFERENCES markets(id),
    requires_license BOOLEAN DEFAULT false,
    requires_grid_operator_number BOOLEAN DEFAULT false,
    parent_role_code VARCHAR(10), -- For hierarchical roles
    valid_from DATE,
    valid_to DATE,
    is_active BOOLEAN DEFAULT true,
    source_document VARCHAR(200), -- Reference to BDEW document
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Companies (Central Company Registry)
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name VARCHAR(255) NOT NULL UNIQUE,
    company_code VARCHAR(50), -- Internal/standardized code
    legal_form_id SMALLINT REFERENCES legal_forms(id),
    registration_number VARCHAR(100), -- Handelsregisternummer
    vat_number VARCHAR(50), -- Umsatzsteuer-ID
    website_url VARCHAR(500),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    address_street VARCHAR(255),
    address_city VARCHAR(100),
    address_postal_code VARCHAR(20),
    country_id SMALLINT NOT NULL REFERENCES countries(id),
    parent_company_id UUID REFERENCES companies(id),
    -- BDEW-specific fields
    gln VARCHAR(13), -- Global Location Number (GS1)
    eic_code VARCHAR(16), -- Energy Identification Code (ENTSO-E)
    grid_operator_number VARCHAR(50), -- Stromnetzbetreibernummer (für VNB)
    registration_authority_id SMALLINT REFERENCES registration_authorities(id),
    bdew_registration_date DATE, -- Erstes Registrierungsdatum bei BDEW
    status_id SMALLINT NOT NULL REFERENCES status_types(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Company Roles (Many-to-Many relationship)
CREATE TABLE company_roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES market_participant_roles(id) ON DELETE CASCADE,
    -- Role-specific information
    role_specific_code VARCHAR(50), -- Legacy field
    service_territory TEXT, -- Versorgungsgebiet
    license_number VARCHAR(100), -- Lizenz-/Genehmigungsnummer
    valid_from DATE,
    valid_to DATE,
    -- BDEW-specific fields
    bdew_code VARCHAR(13), -- Offizielle BDEW-Codenummer für diese Rolle
    eic_code VARCHAR(16), -- EIC für diese spezifische Rolle
    registration_date DATE, -- Registrierungsdatum bei BDEW für diese Rolle
    certificate_number VARCHAR(50), -- BDEW-Zertifikatsnummer
    status_id SMALLINT NOT NULL REFERENCES status_types(id),
    last_verification_date DATE, -- Letzte Verifikation gegen BDEW-DB
    verification_source_id SMALLINT REFERENCES data_sources(id),
    is_active BOOLEAN DEFAULT true,
    data_source_id SMALLINT REFERENCES data_sources(id),
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, role_id)
);

-- ============================================================================
-- DATA SOURCE SPECIFIC TABLES (NORMALIZED)
-- ============================================================================

-- BDEW Market Participants (enhanced for all market participants)
CREATE TABLE bdew_market_participants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES market_participant_roles(id) ON DELETE CASCADE,
    bdew_code VARCHAR(13),
    bdew_category VARCHAR(100),
    registration_date DATE,
    additional_data JSONB, -- Flexible field for role-specific data
    data_source_id SMALLINT NOT NULL REFERENCES data_sources(id),
    is_active BOOLEAN DEFAULT true,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, role_id, bdew_code)
);

-- BNetzA Rollout Data (specific to metering/network operators)
CREATE TABLE bnetza_rollout_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    rollout_quarter VARCHAR(20) NOT NULL,
    rollout_percentage DECIMAL(5,2),
    total_metering_points INTEGER,
    modernized_metering_points INTEGER,
    rollout_target INTEGER,
    regulatory_notes TEXT,
    data_source_id SMALLINT NOT NULL REFERENCES data_sources(id),
    is_active BOOLEAN DEFAULT true,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, rollout_quarter)
);

-- Price Sheets (applicable to various market participants)
CREATE TABLE price_sheets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    role_id UUID REFERENCES market_participant_roles(id), -- Which role this price sheet is for
    document_type_id SMALLINT NOT NULL REFERENCES document_types(id),
    file_name VARCHAR(255),
    file_path VARCHAR(500),
    extraction_date TIMESTAMP WITH TIME ZONE,
    valid_from DATE,
    valid_to DATE,
    content_hash VARCHAR(64),
    extracted_data JSONB,
    price_category_id SMALLINT REFERENCES price_categories(id),
    customer_segment_id SMALLINT REFERENCES customer_segments(id),
    data_source_id SMALLINT NOT NULL REFERENCES data_sources(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- BDEW Code Registry (downloaded from BDEW API/Website)
CREATE TABLE bdew_code_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bdew_code VARCHAR(13) NOT NULL,
    gln VARCHAR(13), -- Alternative GLN
    eic_code VARCHAR(16),
    company_name VARCHAR(255) NOT NULL,
    role_code VARCHAR(10) NOT NULL,
    registration_date DATE,
    status_id SMALLINT NOT NULL REFERENCES status_types(id),
    certificate_number VARCHAR(50),
    grid_operator_number VARCHAR(50), -- Falls VNB
    service_territory TEXT,
    contact_email VARCHAR(255),
    last_sync_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_source_id SMALLINT NOT NULL REFERENCES data_sources(id),
    data_hash VARCHAR(64), -- For change detection
    raw_data JSONB, -- Complete data from BDEW
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bdew_code, role_code)
);

-- Track synchronization with BDEW sources
CREATE TABLE bdew_sync_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sync_type VARCHAR(50), -- 'full_sync', 'incremental', 'verification'
    data_source_id SMALLINT NOT NULL REFERENCES data_sources(id),
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    status_id SMALLINT NOT NULL REFERENCES status_types(id),
    records_processed INTEGER,
    records_added INTEGER,
    records_updated INTEGER,
    records_failed INTEGER,
    error_message TEXT,
    sync_metadata JSONB -- Additional sync information
);

-- ============================================================================
-- CONSTRAINTS AND INDEXES
-- ============================================================================

-- Additional foreign key constraints
ALTER TABLE market_participant_roles
ADD CONSTRAINT fk_parent_role
FOREIGN KEY (parent_role_code)
REFERENCES market_participant_roles(bdew_role_code);

-- Check constraints
ALTER TABLE companies
ADD CONSTRAINT check_gln_format
CHECK (gln IS NULL OR LENGTH(gln) = 13);

ALTER TABLE companies
ADD CONSTRAINT check_eic_format
CHECK (eic_code IS NULL OR LENGTH(eic_code) = 16);

ALTER TABLE bnetza_rollout_data
ADD CONSTRAINT check_rollout_percentage
CHECK (rollout_percentage >= 0 AND rollout_percentage <= 100);

-- Indexes for performance
CREATE INDEX idx_companies_name_fts ON companies USING gin(to_tsvector('german', company_name));
CREATE INDEX idx_companies_country ON companies(country_id);
CREATE INDEX idx_companies_status ON companies(status_id);
CREATE INDEX idx_companies_legal_form ON companies(legal_form_id);

CREATE INDEX idx_company_roles_company ON company_roles(company_id);
CREATE INDEX idx_company_roles_role ON company_roles(role_id);
CREATE INDEX idx_company_roles_status ON company_roles(status_id);
CREATE INDEX idx_company_roles_bdew_code ON company_roles(bdew_code);

CREATE INDEX idx_market_roles_category ON market_participant_roles(role_category_id);
CREATE INDEX idx_market_roles_market ON market_participant_roles(applicable_market_id);

CREATE INDEX idx_bdew_registry_code ON bdew_code_registry(bdew_code);
CREATE INDEX idx_bdew_registry_role_code ON bdew_code_registry(role_code);
CREATE INDEX idx_bdew_registry_sync_date ON bdew_code_registry(last_sync_date);

CREATE INDEX idx_sync_log_source ON bdew_sync_log(data_source_id);
CREATE INDEX idx_sync_log_status ON bdew_sync_log(status_id);
CREATE INDEX idx_sync_log_start_time ON bdew_sync_log(start_time);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Update timestamp triggers
CREATE TRIGGER update_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_company_roles_updated_at
    BEFORE UPDATE ON company_roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_market_participant_roles_updated_at
    BEFORE UPDATE ON market_participant_roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bdew_market_participants_updated_at
    BEFORE UPDATE ON bdew_market_participants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bnetza_rollout_data_updated_at
    BEFORE UPDATE ON bnetza_rollout_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_price_sheets_updated_at
    BEFORE UPDATE ON price_sheets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bdew_code_registry_updated_at
    BEFORE UPDATE ON bdew_code_registry
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- INITIAL LOOKUP DATA
-- ============================================================================

-- Role Categories (based on BDEW Rollenmodell)
INSERT INTO role_categories (code, name_de, name_en, sort_order) VALUES
('GRID', 'Netzbetrieb', 'Grid Operations', 1),
('METERING', 'Messwesen', 'Metering Services', 2),
('TRADING', 'Energiehandel', 'Energy Trading', 3),
('SUPPLY', 'Energieversorgung', 'Energy Supply', 4),
('BALANCING', 'Bilanzierung', 'Balancing', 5),
('CLEARING', 'Abrechnung', 'Settlement/Clearing', 6),
('PLATFORM', 'Marktplattform', 'Market Platform', 7),
('AUTHORITY', 'Behörde', 'Regulatory Authority', 8),
('SERVICE', 'Dienstleistung', 'Service Provider', 9),
('OTHER', 'Sonstige', 'Other', 999);

-- Markets
INSERT INTO markets (code, name_de, name_en) VALUES
('POWER', 'Strommarkt', 'Electricity Market'),
('GAS', 'Gasmarkt', 'Gas Market'),
('HEAT', 'Wärmemarkt', 'District Heating Market'),
('HYDROGEN', 'Wasserstoffmarkt', 'Hydrogen Market'),
('ALL', 'Alle Märkte', 'All Markets');

-- Legal Forms (German legal forms)
INSERT INTO legal_forms (code, name_de, name_en, country_code) VALUES
('AG', 'Aktiengesellschaft', 'Stock Corporation', 'DEU'),
('GmbH', 'Gesellschaft mit beschränkter Haftung', 'Limited Liability Company', 'DEU'),
('SE', 'Societas Europaea', 'European Company', 'DEU'),
('eG', 'eingetragene Genossenschaft', 'Registered Cooperative', 'DEU'),
('KG', 'Kommanditgesellschaft', 'Limited Partnership', 'DEU'),
('GmbH_Co_KG', 'GmbH & Co. KG', 'GmbH & Co. KG', 'DEU'),
('AöR', 'Anstalt des öffentlichen Rechts', 'Public Law Institution', 'DEU'),
('KöR', 'Körperschaft des öffentlichen Rechts', 'Public Corporation', 'DEU'),
('KOMMUNAL', 'Kommunalunternehmen', 'Municipal Company', 'DEU'),
('SONSTIGE', 'Sonstige Rechtsform', 'Other Legal Form', 'DEU');

-- Countries
INSERT INTO countries (iso_code_2, iso_code_3, name_de, name_en, is_eu_member) VALUES
('DE', 'DEU', 'Deutschland', 'Germany', true),
('AT', 'AUT', 'Österreich', 'Austria', true),
('CH', 'CHE', 'Schweiz', 'Switzerland', false),
('FR', 'FRA', 'Frankreich', 'France', true),
('NL', 'NLD', 'Niederlande', 'Netherlands', true),
('BE', 'BEL', 'Belgien', 'Belgium', true),
('DK', 'DNK', 'Dänemark', 'Denmark', true),
('PL', 'POL', 'Polen', 'Poland', true),
('CZ', 'CZE', 'Tschechien', 'Czech Republic', true),
('LU', 'LUX', 'Luxemburg', 'Luxembourg', true);

-- Registration Authorities
INSERT INTO registration_authorities (code, name_de, name_en, website_url, country_id) VALUES
('BDEW', 'Bundesverband der Energie- und Wasserwirtschaft', 'German Association of Energy and Water Industries', 'https://www.bdew.de', 1),
('BNETZA', 'Bundesnetzagentur', 'Federal Network Agency', 'https://www.bundesnetzagentur.de', 1),
('ENTSOE', 'ENTSO-E', 'European Network of Transmission System Operators', 'https://www.entsoe.eu', NULL),
('E_CONTROL', 'E-Control', 'Austrian Energy Regulator', 'https://www.e-control.at', 2),
('ELIA', 'Elia Group', 'Belgian TSO', 'https://www.elia.be', 6);

-- Status Types
INSERT INTO status_types (entity_type, code, name_de, name_en, is_active_status) VALUES
('company', 'ACTIVE', 'Aktiv', 'Active', true),
('company', 'INACTIVE', 'Inaktiv', 'Inactive', false),
('company', 'PENDING', 'Genehmigung ausstehend', 'Pending Approval', false),
('company', 'SUSPENDED', 'Suspendiert', 'Suspended', false),
('role', 'ACTIVE', 'Aktiv', 'Active', true),
('role', 'INACTIVE', 'Inaktiv', 'Inactive', false),
('role', 'PROVISIONAL', 'Vorläufig', 'Provisional', true),
('role', 'EXPIRED', 'Abgelaufen', 'Expired', false),
('sync', 'SUCCESS', 'Erfolgreich', 'Successful', true),
('sync', 'FAILED', 'Fehlgeschlagen', 'Failed', false),
('sync', 'RUNNING', 'Läuft', 'Running', true),
('sync', 'PARTIAL', 'Teilweise erfolgreich', 'Partially Successful', true);

-- Data Sources
INSERT INTO data_sources (code, name_de, name_en, base_url, is_official, update_frequency) VALUES
('BDEW_API', 'BDEW Codenummern-API', 'BDEW Code Numbers API', 'https://bdew-codes.de', true, 'daily'),
('BDEW_WEB', 'BDEW Website', 'BDEW Website', 'https://bdew-codes.de', true, 'daily'),
('BNETZA_API', 'BNetzA Smart Meter API', 'BNetzA Smart Meter API', 'https://www.bundesnetzagentur.de', true, 'quarterly'),
('MANUAL', 'Manuelle Eingabe', 'Manual Entry', NULL, false, 'on-demand'),
('PDF_EXTRACT', 'PDF-Extraktion', 'PDF Extraction', NULL, false, 'on-demand');

-- Document Types
INSERT INTO document_types (code, name_de, name_en, file_extensions) VALUES
('PRICE_SHEET', 'Preisblatt', 'Price Sheet', '.pdf,.xlsx,.docx'),
('NETWORK_CHARGES', 'Netzentgelte', 'Network Charges', '.pdf,.xlsx'),
('GENERAL_TERMS', 'AGB', 'General Terms and Conditions', '.pdf,.docx'),
('ROLLOUT_REPORT', 'Rollout-Bericht', 'Rollout Report', '.pdf,.xlsx,.csv'),
('CERTIFICATE', 'Zertifikat', 'Certificate', '.pdf'),
('LICENSE', 'Lizenz', 'License', '.pdf');

-- Price Categories
INSERT INTO price_categories (code, name_de, name_en, unit) VALUES
('ELECTRICITY_BASE', 'Strom Grundversorgung', 'Electricity Basic Supply', 'ct/kWh'),
('ELECTRICITY_MARKET', 'Strom Marktpreis', 'Electricity Market Price', 'ct/kWh'),
('NETWORK_CHARGE', 'Netznutzungsentgelt', 'Network Usage Charge', 'ct/kWh'),
('GAS_BASE', 'Gas Grundversorgung', 'Gas Basic Supply', 'ct/kWh'),
('METERING_CHARGE', 'Messstellenbetrieb', 'Metering Service', '€/Jahr');

-- Customer Segments
INSERT INTO customer_segments (code, name_de, name_en, consumption_range_min, consumption_range_max) VALUES
('HOUSEHOLD', 'Haushaltskunden', 'Household Customers', 1500, 4000),
('SME', 'Kleingewerbe', 'Small and Medium Enterprises', 4000, 100000),
('INDUSTRIAL', 'Industriekunden', 'Industrial Customers', 100000, NULL),
('MUNICIPAL', 'Kommunale Kunden', 'Municipal Customers', 10000, NULL),
('ALL', 'Alle Kundensegmente', 'All Customer Segments', NULL, NULL);

-- ============================================================================
-- BDEW ROLE CODES (Official from BDEW Rollenmodell v2.1)
-- ============================================================================

INSERT INTO market_participant_roles (bdew_role_code, role_name_de, role_name_en, role_category_id, role_description, applicable_market_id, requires_license, requires_grid_operator_number) VALUES
('VNB', 'Verteilnetzbetreiber', 'Distribution System Operator', 1, 'Betreiber von Verteilungsnetzen für Strom oder Gas', 1, true, true),
('UNB', 'Übertragungsnetzbetreiber', 'Transmission System Operator', 1, 'Betreiber von Übertragungsnetzen für Strom oder Gas', 1, true, true),
('MSB', 'Messstellenbetreiber', 'Metering Point Operator', 2, 'Betreiber von Messstellen', 1, true, false),
('MDL', 'Messdienstleister', 'Metering Service Provider', 2, 'Erbringer von Messdienstleistungen', 1, true, false),
('LF', 'Lieferant', 'Supplier', 4, 'Energielieferant für Endkunden', 1, true, false),
('ESCO', 'Energiedienstleister', 'Energy Service Company', 9, 'Anbieter von Energiedienstleistungen', 5, false, false),
('BKV', 'Bilanzkreisverantwortlicher', 'Balance Responsible Party', 5, 'Verantwortlicher für Bilanzkreise', 1, true, false),
('ÜNB', 'Übertragungsnetzbetreiber', 'Transmission System Operator', 1, 'Alternative Bezeichnung für UNB', 1, true, true),
('GMSB', 'Grundzuständiger Messstellenbetreiber', 'Basic Metering Point Operator', 2, 'Grundzuständiger MSB im Netzgebiet', 1, true, false),
('WMSB', 'Wettbewerblicher Messstellenbetreiber', 'Competitive Metering Point Operator', 2, 'Wettbewerblicher MSB', 1, true, false);

-- ============================================================================
-- SAMPLE COMPANIES AND ROLES
-- ============================================================================

INSERT INTO companies (id, company_name, legal_form_id, registration_number, website_url, contact_email, address_street, address_city, address_postal_code, country_id, gln, eic_code, grid_operator_number, registration_authority_id, status_id) VALUES
(uuid_generate_v4(), 'SÜC Energie und H2O GmbH', 2, 'HRB 1234', 'https://www.suec.de', 'info@suec.de', 'Rodacher Str. 8-10', 'Coburg', '96450', 1, '4260123456789', '10Y1001A1001A123', '12345', 1, 1),
(uuid_generate_v4(), 'N-ERGIE Aktiengesellschaft', 1, 'HRB 5678', 'https://www.n-ergie.de', 'info@n-ergie.de', 'Am Plärrer 43', 'Nürnberg', '90429', 1, '4260123456790', '10Y1001A1001A124', '12346', 1, 1),
(uuid_generate_v4(), 'E.ON SE', 4, 'HRB 9012', 'https://www.eon.de', 'info@eon.de', 'E.ON-Platz 1', 'Essen', '45141', 1, '4260123456791', '10Y1001A1001A125', '12347', 1, 1),
(uuid_generate_v4(), 'EnBW Energie Baden-Württemberg AG', 1, 'HRB 3456', 'https://www.enbw.com', 'info@enbw.com', 'Durlacher Allee 93', 'Karlsruhe', '76131', 1, '4260123456792', '10Y1001A1001A126', '12348', 1, 1),
(uuid_generate_v4(), 'Discovergy GmbH', 2, 'HRB 7890', 'https://www.discovergy.com', 'info@discovergy.com', 'Im Entenfang 15', 'Heidelberg', '69123', 1, '4260123456793', '10Y1001A1001A127', NULL, 1, 1);

-- Get company IDs for role assignments
WITH company_ids AS (
    SELECT
        id,
        company_name,
        ROW_NUMBER() OVER (ORDER BY company_name) as rn
    FROM companies
    WHERE company_name IN ('SÜC Energie und H2O GmbH', 'N-ERGIE Aktiengesellschaft', 'E.ON SE', 'EnBW Energie Baden-Württemberg AG', 'Discovergy GmbH')
),
role_ids AS (
    SELECT
        id,
        bdew_role_code,
        ROW_NUMBER() OVER (ORDER BY bdew_role_code) as rn
    FROM market_participant_roles
    WHERE bdew_role_code IN ('VNB', 'LF', 'MSB', 'GMSB', 'WMSB')
)
INSERT INTO company_roles (company_id, role_id, bdew_code, service_territory, valid_from, status_id, data_source_id)
SELECT
    c.id,
    r.id,
    CASE
        WHEN c.company_name = 'SÜC Energie und H2O GmbH' AND r.bdew_role_code = 'VNB' THEN '1234567890123'
        WHEN c.company_name = 'SÜC Energie und H2O GmbH' AND r.bdew_role_code = 'LF' THEN '1234567890124'
        WHEN c.company_name = 'N-ERGIE Aktiengesellschaft' AND r.bdew_role_code = 'VNB' THEN '2345678901234'
        WHEN c.company_name = 'N-ERGIE Aktiengesellschaft' AND r.bdew_role_code = 'LF' THEN '2345678901235'
        WHEN c.company_name = 'E.ON SE' AND r.bdew_role_code = 'VNB' THEN '3456789012345'
        WHEN c.company_name = 'E.ON SE' AND r.bdew_role_code = 'LF' THEN '3456789012346'
        WHEN c.company_name = 'EnBW Energie Baden-Württemberg AG' AND r.bdew_role_code = 'VNB' THEN '4567890123456'
        WHEN c.company_name = 'EnBW Energie Baden-Württemberg AG' AND r.bdew_role_code = 'LF' THEN '4567890123457'
        WHEN c.company_name = 'Discovergy GmbH' AND r.bdew_role_code = 'WMSB' THEN '5678901234567'
    END,
    CASE
        WHEN c.company_name = 'SÜC Energie und H2O GmbH' AND r.bdew_role_code = 'VNB' THEN 'Coburg und Umgebung'
        WHEN c.company_name = 'N-ERGIE Aktiengesellschaft' AND r.bdew_role_code = 'VNB' THEN 'Nürnberg und Umgebung'
        WHEN c.company_name = 'E.ON SE' AND r.bdew_role_code = 'VNB' THEN 'Bayern'
        WHEN c.company_name = 'EnBW Energie Baden-Württemberg AG' AND r.bdew_role_code = 'VNB' THEN 'Baden-Württemberg'
        WHEN c.company_name = 'Discovergy GmbH' AND r.bdew_role_code = 'WMSB' THEN 'Deutschland'
        ELSE 'Deutschland'
    END,
    '2024-01-01',
    1,
    4
FROM company_ids c
CROSS JOIN role_ids r
WHERE
    (c.company_name = 'SÜC Energie und H2O GmbH' AND r.bdew_role_code IN ('VNB', 'LF'))
    OR (c.company_name = 'N-ERGIE Aktiengesellschaft' AND r.bdew_role_code IN ('VNB', 'LF'))
    OR (c.company_name = 'E.ON SE' AND r.bdew_role_code IN ('VNB', 'LF'))
    OR (c.company_name = 'EnBW Energie Baden-Württemberg AG' AND r.bdew_role_code IN ('VNB', 'LF'))
    OR (c.company_name = 'Discovergy GmbH' AND r.bdew_role_code = 'WMSB');

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE 'VNB Digitaler Database successfully initialized with NORMALIZED structure!';
    RAISE NOTICE 'Created % lookup tables with proper normalization',
        (SELECT COUNT(*) FROM information_schema.tables
         WHERE table_schema = 'vnb_digitaler'
         AND table_name IN ('role_categories', 'markets', 'legal_forms', 'countries', 'registration_authorities', 'status_types', 'data_sources', 'document_types', 'price_categories', 'customer_segments'));
    RAISE NOTICE 'Created % core data tables',
        (SELECT COUNT(*) FROM information_schema.tables
         WHERE table_schema = 'vnb_digitaler'
         AND table_name IN ('market_participant_roles', 'companies', 'company_roles', 'bdew_market_participants', 'bnetza_rollout_data', 'price_sheets', 'bdew_code_registry', 'bdew_sync_log'));
    RAISE NOTICE 'Inserted % BDEW role codes',
        (SELECT COUNT(*) FROM vnb_digitaler.market_participant_roles);
    RAISE NOTICE 'Inserted % companies with % role assignments',
        (SELECT COUNT(*) FROM vnb_digitaler.companies),
        (SELECT COUNT(*) FROM vnb_digitaler.company_roles);
    RAISE NOTICE 'Database is ready for production use with optimal JOIN performance!';
END $$;
