# VNB-Digitaler Datenbankstruktur

## Übersicht

Dieses Dokument spezifiziert die Datenbankstruktur für das VNB-Digitaler Projekt, das Smart Meter Roll-Out Daten von der BNetzA sammelt, analysiert und strukturiert speichert.

## Technologie-Stack

- **Datenbank**: PostgreSQL (Neon Cloud)
- **ORM**: SQLAlchemy 2.0 mit asyncpg
- **Python-Version**: 3.11+
- **Async Support**: Vollständig asynchrone Operationen

## Haupttabellen

### 1. `rollout_reports` - Roll-Out Berichte *(bereits implementiert)*

Speichert Metadaten über identifizierte BNetzA Roll-Out Berichte aus der AI-Analyse.

| Spalte                | Datentyp                 | Optional | Anmerkungen                                                                                  |
| --------------------- | ------------------------ | -------- | -------------------------------------------------------------------------------------------- |
| `id`                  | SERIAL                   | Nein     | Primary Key                                                                                  |
| `filename`            | VARCHAR(255)             | Nein     | Name der Excel-Datei                                                                         |
| `url`                 | TEXT                     | Nein     | Download-URL der Datei                                                                       |
| `quarter`             | INTEGER                  | Nein     | Quartal (1-4), CHECK constraint                                                              |
| `year`                | INTEGER                  | Nein     | Jahr der Erhebung                                                                            |
| `confidence`          | VARCHAR(20)              | Nein     | AI-Vertrauen: high, medium, low                                                              |
| `method`              | INTEGER                  | Nein     | Erkennungsmethode: 0=unknown, 1=ai_analysis, 2=fallback_pattern, DEFAULT 0, CHECK constraint |
| `reasoning`           | TEXT                     | Ja       | AI-Begründung für Auswahl                                                                    |
| `ai_model_used`       | VARCHAR(100)             | Ja       | Verwendetes AI-Model                                                                         |
| `ai_tokens_used`      | INTEGER                  | Ja       | Verbrauchte AI-Tokens                                                                        |
| `ai_response`         | TEXT                     | Ja       | Vollständige AI-Antwort                                                                      |
| `download_session_id` | VARCHAR(100)             | Ja       | Referenz zur Download-Session                                                                |
| `source_metadata`     | JSONB                    | Ja       | Zusätzliche Metadaten                                                                        |
| `is_latest`           | BOOLEAN                  | Ja       | Ist dies der neueste Bericht? DEFAULT FALSE                                                  |
| `is_processed`        | BOOLEAN                  | Ja       | Wurde bereits verarbeitet? DEFAULT FALSE                                                     |
| `created_at`          | TIMESTAMP WITH TIME ZONE | Nein     | DEFAULT NOW()                                                                                |
| `updated_at`          | TIMESTAMP WITH TIME ZONE | Nein     | DEFAULT NOW()                                                                                |

**Indizes für `rollout_reports`:**

| Index-Name                             | Spalten               | Typ             | Zweck                                  |
| -------------------------------------- | --------------------- | --------------- | -------------------------------------- |
| `rollout_reports_pkey`                 | `id`                  | PRIMARY KEY     | Eindeutige Identifikation              |
| `idx_rollout_reports_filename`         | `filename`            | INDEX           | Suche nach Dateinamen                  |
| `idx_rollout_reports_quarter`          | `quarter`             | INDEX           | Filterung nach Quartal                 |
| `idx_rollout_reports_year`             | `year`                | INDEX           | Filterung nach Jahr                    |
| `idx_rollout_reports_method`           | `method`              | INDEX           | Filterung nach Erkennungsmethode       |
| `idx_rollout_reports_quarter_year`     | `quarter, year`       | COMPOSITE INDEX | Kombinierte Quartal/Jahr-Suche         |
| `idx_rollout_reports_download_session` | `download_session_id` | INDEX           | Verknüpfung zur Download-Session       |
| `idx_rollout_reports_is_latest`        | `is_latest`           | INDEX           | Schnelle Suche nach neuesten Berichten |
| `idx_rollout_reports_is_processed`     | `is_processed`        | INDEX           | Status-basierte Filterung              |

### 2. `download_sessions` - Download-Sitzungen *(bereits implementiert)*

Verfolgt BNetzA Download- und Scraping-Sitzungen.

| Spalte             | Datentyp                 | Optional | Anmerkungen                                           |
| ------------------ | ------------------------ | -------- | ----------------------------------------------------- |
| `id`               | SERIAL                   | Nein     | Primary Key                                           |
| `session_id`       | VARCHAR(100)             | Nein     | Eindeutige Session-ID, UNIQUE constraint              |
| `temp_directory`   | VARCHAR(255)             | Nein     | Pfad zum temporären Verzeichnis                       |
| `total_urls_found` | INTEGER                  | Ja       | Anzahl gefundener URLs, DEFAULT 0                     |
| `excel_urls_found` | INTEGER                  | Ja       | Anzahl Excel-URLs, DEFAULT 0                          |
| `user_agent`       | VARCHAR(255)             | Nein     | HTTP User-Agent String                                |
| `script_version`   | VARCHAR(50)              | Nein     | Version des Download-Scripts                          |
| `status`           | VARCHAR(20)              | Ja       | Status: running, completed, failed, DEFAULT 'running' |
| `error_message`    | TEXT                     | Ja       | Fehlermeldung bei Problemen                           |
| `metadata`         | JSONB                    | Ja       | Zusätzliche Session-Metadaten                         |
| `started_at`       | TIMESTAMP WITH TIME ZONE | Nein     | DEFAULT NOW()                                         |
| `completed_at`     | TIMESTAMP WITH TIME ZONE | Ja       | Zeitpunkt der Fertigstellung                          |

**Indizes für `download_sessions`:**

| Index-Name                         | Spalten      | Typ          | Zweck                        |
| ---------------------------------- | ------------ | ------------ | ---------------------------- |
| `download_sessions_pkey`           | `id`         | PRIMARY KEY  | Eindeutige Identifikation    |
| `download_sessions_session_id_key` | `session_id` | UNIQUE INDEX | Eindeutigkeit der Session-ID |
| `idx_download_sessions_status`     | `status`     | INDEX        | Filterung nach Status        |

### 3. `analysis_sessions` - AI-Analyse-Sitzungen *(bereits implementiert)*

Verfolgt KI-basierte URL-Klassifikations-Sitzungen.

| Spalte                | Datentyp                 | Optional | Anmerkungen                                           |
| --------------------- | ------------------------ | -------- | ----------------------------------------------------- |
| `id`                  | SERIAL                   | Nein     | Primary Key                                           |
| `download_session_id` | VARCHAR(100)             | Nein     | Referenz zur Download-Session                         |
| `model_used`          | VARCHAR(100)             | Nein     | Name des verwendeten AI-Models                        |
| `dry_run`             | BOOLEAN                  | Ja       | War es ein Test-Lauf? DEFAULT FALSE                   |
| `selected_report_id`  | INTEGER                  | Ja       | ID des ausgewählten Reports                           |
| `total_tokens_used`   | INTEGER                  | Ja       | Gesamte verbrauchte AI-Tokens                         |
| `status`              | VARCHAR(20)              | Ja       | Status: running, completed, failed, DEFAULT 'running' |
| `error_message`       | TEXT                     | Ja       | Fehlermeldung bei Problemen                           |
| `analysis_metadata`   | JSONB                    | Ja       | Zusätzliche Analyse-Metadaten                         |
| `started_at`          | TIMESTAMP WITH TIME ZONE | Nein     | DEFAULT NOW()                                         |
| `completed_at`        | TIMESTAMP WITH TIME ZONE | Ja       | Zeitpunkt der Fertigstellung                          |

**Indizes für `analysis_sessions`:**

| Index-Name                               | Spalten               | Typ         | Zweck                            |
| ---------------------------------------- | --------------------- | ----------- | -------------------------------- |
| `analysis_sessions_pkey`                 | `id`                  | PRIMARY KEY | Eindeutige Identifikation        |
| `idx_analysis_sessions_download_session` | `download_session_id` | INDEX       | Verknüpfung zur Download-Session |
| `idx_analysis_sessions_status`           | `status`              | INDEX       | Filterung nach Status            |

### 4. `companies` - Unternehmen/Netzbetreiber *(erweitert)*

Speichert Informationen über die Netzbetreiber und Energieunternehmen. **BDEW-Daten sind die Single Source of Truth** für offizielle Firmendaten.

| Spalte                             | Datentyp                 | Optional | Anmerkungen                                                          |
| ---------------------------------- | ------------------------ | -------- | -------------------------------------------------------------------- |
| `id`                               | SERIAL                   | Nein     | Primary Key                                                          |
| `bdew_code`                        | VARCHAR(20)              | Nein     | **BDEW-Stromnetzbetreibernummer (offizielle ID)**, UNIQUE constraint |
| `bdew_name`                        | VARCHAR(500)             | Nein     | **Offizieller Firmenname laut BDEW (Single Source of Truth)**        |
| `bdew_city`                        | VARCHAR(200)             | Ja       | Stadt laut BDEW-Registrierung                                        |
| `bdew_name_normalized`             | VARCHAR(500)             | Nein     | Normalisierte BDEW-Namen für Matching, UNIQUE constraint             |
| `bdew_last_updated`                | DATE                     | Ja       | Letzte Aktualisierung der BDEW-Daten                                 |
| `rollout_report_name`              | VARCHAR(500)             | Ja       | Name wie er in Roll-Out-Reports erscheint (kann abweichen!)          |
| `rollout_name_variations`          | TEXT[]                   | Ja       | Array aller gefundenen Namensabweichungen in Excel-Files             |
| `name_matching_confidence`         | DECIMAL(3,2)             | Ja       | AI-Confidence für automatisches Name-Matching (0.00-1.00)            |
| `rollout_company_manually_checked` | BOOLEAN                  | Ja       | Wurde die Rollout-Zuordnung manuell überprüft? DEFAULT FALSE         |
| `manual_verification`              | BOOLEAN                  | Ja       | Wurde die Zuordnung manuell überprüft? DEFAULT FALSE                 |
| `company_type`                     | VARCHAR(100)             | Ja       | z.B. "Stadtwerke", "Netzbetreiber", "GmbH"                           |
| `first_seen_report_id`             | INTEGER                  | Ja       | Foreign Key zu rollout_reports(id)                                   |
| `last_seen_report_id`              | INTEGER                  | Ja       | Foreign Key zu rollout_reports(id)                                   |
| `total_reports_count`              | INTEGER                  | Ja       | Anzahl Berichte mit diesem Unternehmen, DEFAULT 1                    |
| `created_at`                       | TIMESTAMP WITH TIME ZONE | Nein     | DEFAULT NOW()                                                        |
| `updated_at`                       | TIMESTAMP WITH TIME ZONE | Nein     | DEFAULT NOW()                                                        |

**Wichtige Design-Prinzipien:**

- **BDEW-Daten sind autoritativ**: `bdew_name` ist die offizielle Firmenbezeichnung
- **Roll-Out-Namen können abweichen**: `rollout_report_name` speichert Excel-Varianten
- **Varianten-Tracking**: `rollout_name_variations` sammelt alle gefundenen Schreibweisen
- **Qualitätssicherung**: `manual_verification` für kritische Zuordnungen

**Indizes für `companies`:**

| Index-Name                       | Spalten                            | Typ          | Zweck                                      |
| -------------------------------- | ---------------------------------- | ------------ | ------------------------------------------ |
| `companies_pkey`                 | `id`                               | PRIMARY KEY  | Eindeutige Identifikation                  |
| `companies_bdew_code_key`        | `bdew_code`                        | UNIQUE INDEX | Eindeutige BDEW-Codes (Single Source)      |
| `companies_bdew_name_norm_key`   | `bdew_name_normalized`             | UNIQUE INDEX | Verhindert BDEW-Duplikate                  |
| `idx_companies_bdew_name`        | `bdew_name`                        | INDEX        | Suche nach offiziellen BDEW-Namen          |
| `idx_companies_rollout_name`     | `rollout_report_name`              | INDEX        | Suche nach Roll-Out-Report-Namen           |
| `idx_companies_city`             | `bdew_city`                        | INDEX        | Geografische Suche                         |
| `idx_companies_company_type`     | `company_type`                     | INDEX        | Filterung nach Unternehmenstyp             |
| `idx_companies_matching_conf`    | `name_matching_confidence`         | INDEX        | Qualitätsfilterung                         |
| `idx_companies_manually_checked` | `rollout_company_manually_checked` | INDEX        | Filterung nach Rollout-Verifikationsstatus |
| `idx_companies_manual_verified`  | `manual_verification`              | INDEX        | Filterung nach Verifikationsstatus         |

**Geschäftsregeln für `companies`:**

```sql
-- BDEW-Code muss immer gesetzt sein (Single Source of Truth)
ALTER TABLE companies ADD CONSTRAINT chk_bdew_code_required
    CHECK (bdew_code IS NOT NULL AND length(trim(bdew_code)) > 0);

-- BDEW-Name muss immer gesetzt sein
ALTER TABLE companies ADD CONSTRAINT chk_bdew_name_required
    CHECK (bdew_name IS NOT NULL AND length(trim(bdew_name)) > 0);

-- Matching-Confidence zwischen 0 und 1
ALTER TABLE companies ADD CONSTRAINT chk_matching_confidence_range
    CHECK (name_matching_confidence IS NULL OR
           (name_matching_confidence >= 0.0 AND name_matching_confidence <= 1.0));

-- Normalisierte Namen dürfen nicht leer sein
ALTER TABLE companies ADD CONSTRAINT chk_normalized_name_not_empty
    CHECK (length(trim(bdew_name_normalized)) > 0);
```

### 5. `quota_data` - Ausstattungsquoten *(neu)*

Speichert die eigentlichen Smart Meter Ausstattungsquoten-Daten.

| Spalte               | Datentyp                 | Optional | Anmerkungen                                          |
| -------------------- | ------------------------ | -------- | ---------------------------------------------------- |
| `id`                 | SERIAL                   | Nein     | Primary Key                                          |
| `report_id`          | INTEGER                  | Nein     | Foreign Key zu rollout_reports(id) ON DELETE CASCADE |
| `company_id`         | INTEGER                  | Nein     | Foreign Key zu companies(id)                         |
| `quota_value`        | DECIMAL(8,6)             | Nein     | Quotenwert 0.000000 bis 1.000000, CHECK constraint   |
| `stichtag`           | DATE                     | Nein     | Stichtag für die Quota                               |
| `data_source_row`    | INTEGER                  | Ja       | Originale Zeilennummer in der CSV                    |
| `is_converted_value` | BOOLEAN                  | Ja       | War Konvertierung nötig? DEFAULT FALSE               |
| `original_value`     | TEXT                     | Ja       | Originalwert vor Konvertierung (falls konvertiert)   |
| `conversion_notes`   | TEXT                     | Ja       | Details zur Konvertierung                            |
| `created_at`         | TIMESTAMP WITH TIME ZONE | Nein     | DEFAULT NOW()                                        |

**Indizes für `quota_data`:**

| Index-Name                               | Spalten                           | Typ          | Zweck                                    |
| ---------------------------------------- | --------------------------------- | ------------ | ---------------------------------------- |
| `quota_data_pkey`                        | `id`                              | PRIMARY KEY  | Eindeutige Identifikation                |
| `quota_data_report_company_stichtag_key` | `report_id, company_id, stichtag` | UNIQUE INDEX | Ein Wert pro Unternehmen/Report/Stichtag |
| `idx_quota_data_report_id`               | `report_id`                       | INDEX        | Filterung nach Report                    |
| `idx_quota_data_company_id`              | `company_id`                      | INDEX        | Filterung nach Unternehmen               |
| `idx_quota_data_stichtag`                | `stichtag`                        | INDEX        | Filterung nach Stichtag                  |
| `idx_quota_data_quota_value`             | `quota_value`                     | INDEX        | Bereichsabfragen für Quotenwerte         |
| `idx_quota_data_is_converted`            | `is_converted_value`              | INDEX        | Suche nach konvertierten Werten          |

### 6. `excel_download_sessions` - Excel-Download-Sitzungen *(neu)*

Verfolgt Excel-Download und CSV-Konvertierungssitzungen (Script 03).

| Spalte                  | Datentyp                 | Optional | Anmerkungen                                                           |
| ----------------------- | ------------------------ | -------- | --------------------------------------------------------------------- |
| `id`                    | SERIAL                   | Nein     | Primary Key                                                           |
| `session_uuid`          | UUID                     | Nein     | Eindeutige Session-UUID, DEFAULT gen_random_uuid(), UNIQUE constraint |
| `rollout_report_id`     | INTEGER                  | Nein     | Foreign Key zu rollout_reports(id)                                    |
| `excel_url`             | TEXT                     | Nein     | Download-URL der Excel-Datei                                          |
| `excel_filename`        | VARCHAR(255)             | Ja       | Name der Excel-Datei                                                  |
| `csv_filename`          | VARCHAR(255)             | Ja       | Name der konvertierten CSV-Datei                                      |
| `file_size_bytes`       | INTEGER                  | Ja       | Dateigröße in Bytes                                                   |
| `excel_file_hash`       | VARCHAR(64)              | Ja       | SHA-256 Hash zur Duplikatserkennung, UNIQUE constraint                |
| `sheets_processed`      | INTEGER                  | Ja       | Anzahl verarbeiteter Excel-Sheets, DEFAULT 0                          |
| `total_companies_found` | INTEGER                  | Ja       | Gefundene Unternehmen, DEFAULT 0                                      |
| `companies_with_quota`  | INTEGER                  | Ja       | Unternehmen mit gültigen Quoten, DEFAULT 0                            |
| `header_row_detected`   | INTEGER                  | Ja       | Erkannte Header-Zeile                                                 |
| `columns_cleaned`       | INTEGER                  | Ja       | Bereinigte Spalten, DEFAULT 0                                         |
| `conversion_warnings`   | INTEGER                  | Ja       | Anzahl Warnungen bei Konvertierung, DEFAULT 0                         |
| `data_quality_score`    | DECIMAL(5,2)             | Ja       | Prozent gültiger Daten                                                |
| `processing_metadata`   | JSONB                    | Ja       | Detaillierte Verarbeitungsinfos                                       |
| `status`                | VARCHAR(20)              | Nein     | Status: running, completed, failed, DEFAULT 'running'                 |
| `error_message`         | TEXT                     | Ja       | Fehlermeldung bei Problemen                                           |
| `started_at`            | TIMESTAMP WITH TIME ZONE | Nein     | DEFAULT NOW()                                                         |
| `completed_at`          | TIMESTAMP WITH TIME ZONE | Ja       | Zeitpunkt der Fertigstellung                                          |

**Indizes für `excel_download_sessions`:**

| Index-Name                                    | Spalten             | Typ          | Zweck                          |
| --------------------------------------------- | ------------------- | ------------ | ------------------------------ |
| `excel_download_sessions_pkey`                | `id`                | PRIMARY KEY  | Eindeutige Identifikation      |
| `excel_download_sessions_session_uuid_key`    | `session_uuid`      | UNIQUE INDEX | Eindeutigkeit der Session-UUID |
| `excel_download_sessions_excel_file_hash_key` | `excel_file_hash`   | UNIQUE INDEX | Verhindert Duplikate           |
| `idx_excel_download_sessions_rollout_report`  | `rollout_report_id` | INDEX        | Verknüpfung zum Report         |
| `idx_excel_download_sessions_status`          | `status`            | INDEX        | Filterung nach Status          |
| `idx_excel_download_sessions_started_at`      | `started_at`        | INDEX        | Zeitbasierte Abfragen          |

### 7. `ai_analysis_results` - KI-Analyse-Ergebnisse *(erweitert)*

Speichert Ergebnisse der KI-basierten Datenvalidierung und -verarbeitung.

| Spalte               | Datentyp                 | Optional | Anmerkungen                                                           |
| -------------------- | ------------------------ | -------- | --------------------------------------------------------------------- |
| `id`                 | SERIAL                   | Nein     | Primary Key                                                           |
| `analysis_type`      | VARCHAR(50)              | Nein     | Art der Analyse: url_classification, data_validation, column_cleaning |
| `session_reference`  | VARCHAR(100)             | Ja       | Referenz zu entsprechender Session                                    |
| `input_data`         | JSONB                    | Nein     | Eingabedaten für die KI                                               |
| `ai_response`        | JSONB                    | Nein     | Vollständige KI-Antwort                                               |
| `confidence_score`   | DECIMAL(3,2)             | Ja       | Vertrauen: 0.00 bis 1.00                                              |
| `model_used`         | VARCHAR(100)             | Nein     | z.B. "hermes-2-pro-mistral-7b"                                        |
| `processing_time_ms` | INTEGER                  | Ja       | Verarbeitungszeit in Millisekunden                                    |
| `created_at`         | TIMESTAMP WITH TIME ZONE | Nein     | DEFAULT NOW()                                                         |

**Indizes für `ai_analysis_results`:**

| Index-Name                                  | Spalten             | Typ         | Zweck                          |
| ------------------------------------------- | ------------------- | ----------- | ------------------------------ |
| `ai_analysis_results_pkey`                  | `id`                | PRIMARY KEY | Eindeutige Identifikation      |
| `idx_ai_analysis_results_analysis_type`     | `analysis_type`     | INDEX       | Filterung nach Analyse-Typ     |
| `idx_ai_analysis_results_session_reference` | `session_reference` | INDEX       | Verknüpfung zu Sessions        |
| `idx_ai_analysis_results_confidence_score`  | `confidence_score`  | INDEX       | Bereichsabfragen für Vertrauen |
| `idx_ai_analysis_results_created_at`        | `created_at`        | INDEX       | Zeitbasierte Abfragen          |

### 8. `processing_logs` - Verarbeitungsprotokoll *(neu)*

Speichert detaillierte Logs von Datenverarbeitungsschritten.

| Spalte         | Datentyp                 | Optional | Anmerkungen                                       |
| -------------- | ------------------------ | -------- | ------------------------------------------------- |
| `id`           | SERIAL                   | Nein     | Primary Key                                       |
| `session_type` | VARCHAR(50)              | Nein     | Session-Typ: download, analysis, excel_processing |
| `session_id`   | VARCHAR(100)             | Nein     | ID der zugehörigen Session                        |
| `log_level`    | VARCHAR(10)              | Nein     | Log-Level: DEBUG, INFO, WARNING, ERROR            |
| `message`      | TEXT                     | Nein     | Log-Nachricht                                     |
| `context_data` | JSONB                    | Ja       | Zusätzliche strukturierte Daten                   |
| `source_file`  | VARCHAR(100)             | Ja       | Script-Datei, die den Log erzeugt hat             |
| `line_number`  | INTEGER                  | Ja       | Zeilennummer im Source-Code                       |
| `created_at`   | TIMESTAMP WITH TIME ZONE | Nein     | DEFAULT NOW()                                     |

**Indizes für `processing_logs`:**

| Index-Name                       | Spalten                    | Typ             | Zweck                                |
| -------------------------------- | -------------------------- | --------------- | ------------------------------------ |
| `processing_logs_pkey`           | `id`                       | PRIMARY KEY     | Eindeutige Identifikation            |
| `idx_processing_logs_session`    | `session_type, session_id` | COMPOSITE INDEX | Effiziente Session-basierte Abfragen |
| `idx_processing_logs_log_level`  | `log_level`                | INDEX           | Filterung nach Log-Level             |
| `idx_processing_logs_created_at` | `created_at`               | INDEX           | Zeitbasierte Abfragen                |

## Views und Analytische Abfragen

### 1. Aktuelle Quota-Übersicht

```sql
CREATE VIEW current_quota_overview AS
SELECT
    c.name AS company_name,
    c.company_type,
    qd.quota_value,
    qd.stichtag,
    CONCAT('Q', rr.quarter) AS quarter_display,  -- Show as Q1, Q2, etc.
    rr.quarter,
    rr.year,
    CASE
        WHEN rr.method = 1 THEN 'ai_analysis'
        WHEN rr.method = 2 THEN 'fallback_pattern'
        ELSE 'unknown'
    END AS method_name,
    rr.method,
    qd.is_converted_value
FROM quota_data qd
JOIN companies c ON qd.company_id = c.id
JOIN rollout_reports rr ON qd.report_id = rr.id
WHERE rr.is_latest = true
ORDER BY rr.year DESC, rr.quarter DESC, c.name;
```

### 2. Quota-Entwicklung über Zeit

```sql
CREATE VIEW quota_timeline AS
SELECT
    c.name AS company_name,
    qd.quota_value,
    qd.stichtag,
    CONCAT('Q', rr.quarter) AS quarter_display,
    rr.quarter,
    rr.year,
    CASE
        WHEN rr.method = 1 THEN 'ai_analysis'
        WHEN rr.method = 2 THEN 'fallback_pattern'
        ELSE 'unknown'
    END AS method_name,
    rr.created_at,
    LAG(qd.quota_value) OVER (PARTITION BY c.id ORDER BY rr.year, rr.quarter) AS previous_quota,
    (qd.quota_value - LAG(qd.quota_value) OVER (PARTITION BY c.id ORDER BY rr.year, rr.quarter)) AS quota_change
FROM quota_data qd
JOIN companies c ON qd.company_id = c.id
JOIN rollout_reports rr ON qd.report_id = rr.id
ORDER BY c.name, rr.year, rr.quarter;
```

### 3. Datenqualitäts-Statistiken

```sql
CREATE VIEW data_quality_stats AS
SELECT
    CONCAT('Q', rr.quarter, ' ', rr.year) AS period_display,
    rr.quarter,
    rr.year,
    CASE
        WHEN rr.method = 1 THEN 'ai_analysis'
        WHEN rr.method = 2 THEN 'fallback_pattern'
        ELSE 'unknown'
    END AS method_name,
    COUNT(*) AS total_entries,
    COUNT(CASE WHEN qd.is_converted_value THEN 1 END) AS converted_values,
    ROUND(AVG(qd.quota_value), 6) AS avg_quota,
    MIN(qd.quota_value) AS min_quota,
    MAX(qd.quota_value) AS max_quota,
    COUNT(DISTINCT qd.stichtag) AS unique_stichtage
FROM quota_data qd
JOIN rollout_reports rr ON qd.report_id = rr.id
GROUP BY rr.quarter, rr.year, rr.method, rr.id
ORDER BY rr.year DESC, rr.quarter DESC;
```

### 4. Top Performers nach Quarter

```sql
CREATE VIEW top_quota_performers AS
SELECT
    CONCAT('Q', rr.quarter, ' ', rr.year) AS period,
    rr.quarter,
    rr.year,
    c.name AS company_name,
    qd.quota_value,
    RANK() OVER (PARTITION BY rr.quarter, rr.year ORDER BY qd.quota_value DESC) AS rank_in_period
FROM quota_data qd
JOIN companies c ON qd.company_id = c.id
JOIN rollout_reports rr ON qd.report_id = rr.id
WHERE qd.quota_value > 0
ORDER BY rr.year DESC, rr.quarter DESC, qd.quota_value DESC;
```

### 5. Method-Performance-Analyse *(neu)*

```sql
CREATE VIEW method_performance_stats AS
SELECT
    CASE
        WHEN method = 1 THEN 'ai_analysis'
        WHEN method = 2 THEN 'fallback_pattern'
        ELSE 'unknown'
    END AS method_name,
    method,
    COUNT(*) AS reports_count,
    COUNT(CASE WHEN confidence = 'high' THEN 1 END) AS high_confidence_count,
    COUNT(CASE WHEN confidence = 'medium' THEN 1 END) AS medium_confidence_count,
    COUNT(CASE WHEN confidence = 'low' THEN 1 END) AS low_confidence_count,
    ROUND(AVG(ai_tokens_used), 0) AS avg_tokens_used,
    COUNT(CASE WHEN is_processed = true THEN 1 END) AS successfully_processed
FROM rollout_reports
GROUP BY method
ORDER BY method;
```

## Indizierung-Strategie

### Performance-kritische Indizes

```sql
-- Composite Index für häufige Abfragen
CREATE INDEX idx_quota_company_period ON quota_data(company_id, stichtag);
CREATE INDEX idx_company_name_lookup ON companies(name_normalized, name);
CREATE INDEX idx_report_quarter_year ON rollout_reports(quarter, year, created_at);

-- Funktionale Indizes
CREATE INDEX idx_quota_high_values ON quota_data(quota_value) WHERE quota_value > 0.1;
CREATE INDEX idx_converted_values ON quota_data(company_id) WHERE is_converted_value = true;
```

## Datentypen und Constraints

### Enum-Werte und Codes

#### Method Codes (rollout_reports.method)

- **0**: `unknown` - Unbekannte Methode
- **1**: `ai_analysis` - KI-basierte URL-Analyse
- **2**: `fallback_pattern` - Pattern-Matching Fallback

#### Quarter Values (rollout_reports.quarter)

- **1**: Q1 (Januar-März)
- **2**: Q2 (April-Juni)
- **3**: Q3 (Juli-September)
- **4**: Q4 (Oktober-Dezember)

### Geschäftsregeln

- **Quota-Werte**: Müssen zwischen 0.0 und 1.0 liegen (0% bis 100%)
- **Stichtage**: Dürfen nicht in der Zukunft liegen
- **Unternehmensnamen**: Automatische Normalisierung zur Duplikatserkennung
- **File-Hashes**: Verhindern versehentliche Duplikate

### Datenintegrität

```sql
-- Zusätzliche Constraints
ALTER TABLE quota_data ADD CONSTRAINT chk_stichtag_not_future
    CHECK (stichtag <= CURRENT_DATE);

ALTER TABLE companies ADD CONSTRAINT chk_name_not_empty
    CHECK (length(trim(name)) > 0);

ALTER TABLE roll_out_reports ADD CONSTRAINT chk_positive_file_size
    CHECK (file_size_bytes > 0);
```

## Migration und Versionierung

### Schema-Versioning

```sql
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    checksum VARCHAR(64) NOT NULL
);

INSERT INTO schema_migrations (version, description, checksum)
VALUES (1, 'Initial schema creation', 'sha256_hash_here');
```

## Backup und Wartung

### Automatische Bereinigung

```sql
-- Alte Download-Sessions bereinigen (älter als 90 Tage)
DELETE FROM download_sessions
WHERE created_at < NOW() - INTERVAL '90 days'
AND status IN ('completed', 'failed');

-- Alte AI-Analyse-Ergebnisse bereinigen (älter als 180 Tage)
DELETE FROM ai_analysis_results
WHERE created_at < NOW() - INTERVAL '180 days';
```

## Beispiel-Abfragen

### Quartalsspezifische Abfragen

```sql
-- Alle Q1 2025 Berichte
SELECT * FROM rollout_reports
WHERE quarter = 1 AND year = 2025;

-- Durchschnittliche Quota pro Quarter
SELECT
    quarter,
    year,
    ROUND(AVG(quota_value), 4) as avg_quota,
    COUNT(*) as company_count
FROM quota_data qd
JOIN rollout_reports rr ON qd.report_id = rr.id
GROUP BY quarter, year
ORDER BY year DESC, quarter DESC;

-- Unternehmen mit steigender Quota-Entwicklung
SELECT
    c.name,
    q1.quota_value as q1_quota,
    q2.quota_value as q2_quota,
    (q2.quota_value - q1.quota_value) as growth
FROM companies c
JOIN quota_data q1 ON c.id = q1.company_id
JOIN rollout_reports r1 ON q1.report_id = r1.id AND r1.quarter = 1 AND r1.year = 2025
JOIN quota_data q2 ON c.id = q2.company_id
JOIN rollout_reports r2 ON q2.report_id = r2.id AND r2.quarter = 2 AND r2.year = 2025
WHERE q2.quota_value > q1.quota_value
ORDER BY growth DESC;
```

### Method-spezifische Abfragen

```sql
-- KI-analysierte vs. Pattern-basierte Berichte
SELECT
    CASE
        WHEN method = 1 THEN 'AI Analysis'
        WHEN method = 2 THEN 'Pattern Matching'
        ELSE 'Unknown'
    END as method_name,
    COUNT(*) as report_count,
    AVG(CASE WHEN confidence = 'high' THEN 1.0 ELSE 0.0 END) * 100 as high_confidence_pct
FROM rollout_reports
GROUP BY method
ORDER BY method;

-- Nur AI-analysierte Berichte mit hoher Konfidenz
SELECT filename, quarter, year, confidence, ai_model_used
FROM rollout_reports
WHERE method = 1 AND confidence = 'high'
ORDER BY year DESC, quarter DESC;

-- Performance-Vergleich zwischen Methoden
SELECT
    method,
    COUNT(*) as total_reports,
    COUNT(CASE WHEN is_processed = true THEN 1 END) as processed_successfully,
    ROUND(COUNT(CASE WHEN is_processed = true THEN 1 END) * 100.0 / COUNT(*), 2) as success_rate
FROM rollout_reports
GROUP BY method
ORDER BY success_rate DESC;
```

## Nächste Schritte

1. **Implementierung der Models** in `src/models.py`
2. **Migration Scripts** für Datenbankinitialisierung
3. **Repository Pattern** für Datenzugriff
4. **Datenimport-Pipeline** von CSV zu Datenbank
5. **Analytische Abfragen** und Reporting-Tools

---

*Letzte Aktualisierung: August 2025*
*Version: 1.0*
