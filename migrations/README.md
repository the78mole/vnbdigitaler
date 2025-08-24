# VNBdigitaler Database Migrations

Dieses Verzeichnis enthält die Datenbankmigrationen für das VNBdigitaler-Projekt.

## Konsolidierte Schema-Erstellung

**Für neue Installationen verwende:**

```bash
uv run python migrations/create_complete_schema.py
```

Dieses Script erstellt das komplette Datenbankschema von Grund auf neu und umfasst alle bisherigen Migrationen in einem einzigen, umfassenden Setup.

## Datenbankschema Übersicht

### 📋 `companies` Tabelle

- **Zweck**: Haupttabelle für BDEW-Unternehmen mit vnbdigital.de Integration
- **Daten**: BDEW-Codes, Unternehmensnamen, Adressen, Kontaktdaten, Netzgebiete
- **Geocoding**: Latitude/Longitude, Adressinformationen, Geocoding-Metadaten

### 🏢 `rollout_companies` Tabelle

- **Zweck**: BNetzA-Unternehmensnamen für Rollout-Tracking
- **Verknüpfung**: Optionale Verbindung zu BDEW-Unternehmen via `bdew_company_id`
- **Normalisierung**: Normalisierte Namen für besseres Matching

### 📊 `rollout_quotas` Tabelle

- **Zweck**: Zeitreihen-Daten für Rollout-Quoten (Ausstattungsquoten)
- **Zeiterfassung**: Quartal (1-4) und Jahr (2024-2030)
- **Eindeutigkeit**: Pro Unternehmen, Datum, Quartal und Jahr
- **Datenformat**: Rollout-Quote als Dezimalwert (0.0-1.0)

### 📝 `rollout_update_logs` Tabelle

- **Zweck**: Tracking der automatisierten BNetzA-Report-Verarbeitung
- **Funktionen**: Status-Tracking, Statistiken, Fehlerbehandlung
- **Deduplizierung**: Hash-basierte Erkennung bereits verarbeiteter Excel-Dateien

## Beziehungen

```
companies (1) ←--→ (0..1) rollout_companies ←--→ (0..*) rollout_quotas
                                                      ↓
                                           rollout_update_logs (tracking)
```

## Constraints und Validierungen

- **Rollout-Quoten**: 0.0 ≤ rollout_quota ≤ 1.0
- **Quartale**: 1 ≤ report_quarter ≤ 4
- **Jahre**: 2024 ≤ report_year ≤ 2030 (rollout_quotas), 2020 ≤ report_year ≤ 2050 (logs)
- **Status**: 'pending', 'processing', 'completed', 'failed'
- **Eindeutigkeit**: Verhindert Duplikate basierend auf Geschäftslogik

## Indexes für Performance

- **Geografische Suche**: Lat/Lng-Index für Kartenoperationen
- **Textsuche**: Normalisierte Namen für Fuzzy-Matching
- **Zeitreihen**: Quartal/Jahr-Kombinationen für Trend-Analysen
- **Fremdschlüssel**: Alle Referenzen optimiert

## Legacy-Migrationen (Archiv)

Die folgenden Dateien sind historische Migrationen, die in `create_complete_schema.py` konsolidiert wurden:

- `add_company_geolocation.py` - Geocoding-Felder für companies
- `create_rollout_tables.py` - Ursprüngliche Rollout-Tabellen
- `create_rollout_update_logs_table.py` - Update-Logs-Tabelle
- `add_report_year_to_rollout_quotas.py` - report_year-Feld
- `replace_quarter_with_numeric_report_quarter.py` - Numerische Quartale
- `update_rollout_logs_quarter_fields.py` - Quartal-Normalisierung
- `update_rollout_quotas_unique_constraint.py` - Erweiterte Unique-Constraints
- `fix_quarter_fields.py` - Quartal-Feld-Korrekturen

**⚠️ Diese legacy Migrationen sollten nicht mehr verwendet werden!**

## Verwendung

1. **Neue Datenbank**: Verwende `create_complete_schema.py`
2. **Daten importieren**: Nutze die Tools in `/tools/` für BDEW/BNetzA-Daten
3. **Geocoding**: Führe `tools/geocode_companies.py` aus
4. **Rollout-Updates**: Verwende `tools/update_rollout_quotas_simple.py`

## Entwicklung

Bei Schema-Änderungen:

1. Modifiziere `create_complete_schema.py`
2. Aktualisiere entsprechende SQLAlchemy-Models in `src/models.py`
3. Teste mit einer frischen Datenbank
4. Dokumentiere Änderungen hier
