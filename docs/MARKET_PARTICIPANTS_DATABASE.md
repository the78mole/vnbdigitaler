# VNB Digitaler - Market Participants Database Schema

## Überblick

Die neue Datenbankstruktur wurde entwickelt, um **alle Marktteilnehmer-Rollen** im deutschen Energiemarkt abzubilden, nicht nur Netzbetreiber. Diese flexible Struktur ermöglicht es, Unternehmen mit mehreren Rollen (z.B. Netzbetreiber und Energielieferant) korrekt zu modellieren.

## Kern-Konzept

### 📋 Marktteilnehmer-Rollen (market_participant_roles)

Vordefinierte Rollen im Energiemarkt:

- **VNB** - Verteilnetzbetreiber
- **UNB** - Übertragungsnetzbetreiber
- **MSB** - Messstellenbetreiber
- **MDL** - Messdienstleister
- **LF** - Lieferant
- **BKV** - Bilanzkreisverantwortlicher
- **EH** - Energiehändler
- **ESC** - Energiedienstleister

### 🏢 Unternehmen (companies)

Zentrale Unternehmensdatenbank mit:

- Stammdaten (Name, Rechtsform, Kontakt, Adresse)
- Hierarchie (Parent-Child Beziehungen)
- Registrierungsdaten (Handelsregister, USt-ID)

### 🔗 Unternehmens-Rollen (company_roles)

Many-to-Many Beziehung zwischen Unternehmen und Rollen:

- Ein Unternehmen kann mehrere Rollen haben
- Jede Rolle kann rollenspezifische Daten haben (Code, Versorgungsgebiet, Lizenzen)

## Datenbankschema

```sql
-- Kern-Tabellen
┌─────────────────────────┐    ┌─────────────────────────┐    ┌─────────────────────────┐
│ market_participant_roles│    │     company_roles       │    │       companies         │
├─────────────────────────┤    ├─────────────────────────┤    ├─────────────────────────┤
│ id (UUID)              │◄──┤ role_id (FK)           │┌──►│ id (UUID)              │
│ role_code (VNB,LF,etc) │    │ company_id (FK)        ││   │ company_name (UNIQUE)  │
│ role_name_de           │    │ role_specific_code     ││   │ company_code           │
│ role_category          │    │ service_territory      ││   │ legal_form             │
│ description            │    │ license_number         ││   │ website_url            │
└─────────────────────────┘    │ valid_from/valid_to    ││   │ contact_*              │
                               └─────────────────────────┘│   │ address_*              │
                                                         │   │ parent_company_id (FK) │
                                                         └───│ ...                    │
                                                             └─────────────────────────┘

-- Datenquellen-spezifische Tabellen
┌─────────────────────────┐    ┌─────────────────────────┐    ┌─────────────────────────┐
│ bdew_market_participants│    │   bnetza_rollout_data   │    │     price_sheets        │
├─────────────────────────┤    ├─────────────────────────┤    ├─────────────────────────┤
│ company_id (FK)        │    │ company_id (FK)        │    │ company_id (FK)        │
│ role_id (FK)           │    │ rollout_quarter        │    │ role_id (FK)           │
│ bdew_code              │    │ rollout_percentage     │    │ document_type          │
│ bdew_category          │    │ total_metering_points  │    │ price_category         │
│ additional_data (JSONB)│    │ modernized_points      │    │ extracted_data (JSONB) │
└─────────────────────────┘    └─────────────────────────┘    └─────────────────────────┘
```

## Beispiel-Daten

### Unternehmen mit mehreren Rollen

```sql
-- Stadtwerke München: VNB + LF + MSB
SELECT c.company_name, r.role_code, cr.role_specific_code, cr.service_territory
FROM companies c
JOIN company_roles cr ON c.id = cr.company_id
JOIN market_participant_roles r ON cr.role_id = r.id
WHERE c.company_name = 'Stadtwerke München GmbH';

-- Ergebnis:
-- Stadtwerke München GmbH | VNB | SWM_NET | München Stadt
-- Stadtwerke München GmbH | LF  | SWM_LF  | München Stadt
-- Stadtwerke München GmbH | MSB | SWM_MSB | München Stadt
```

## Vorteile der neuen Struktur

### ✅ Flexibilität

- **Multi-Rollen**: Unternehmen können mehrere Marktrollen gleichzeitig haben
- **Erweiterbar**: Neue Rollen können einfach hinzugefügt werden
- **Hierarchien**: Parent-Child Beziehungen zwischen Unternehmen

### ✅ Datenqualität

- **Normalisiert**: Keine Redundanz in Unternehmensdaten
- **Constraints**: Eindeutige Firmennamen, Foreign Key Constraints
- **Versionierung**: Zeiträume für Rollen-Gültigkeit

### ✅ Integration

- **BDEW-Daten**: Flexible Zuordnung zu Unternehmen und Rollen
- **BNetzA-Daten**: Rollout-Daten mit Unternehmensbezug
- **Preisblätter**: Zuordnung zu Unternehmen und spezifischen Rollen

### ✅ Suchfunktionen

- **Full-Text**: Deutsche Volltextsuche in Firmennamen
- **Performance**: Optimierte Indizes für alle Zugriffsmuster
- **Geografisch**: Suche nach Versorgungsgebieten

## Migration von alter Struktur

Die alte `bdew_grid_operators` Tabelle wird ersetzt durch:

1. **companies** - Grunddaten der Unternehmen
2. **company_roles** - Zuordnung zur VNB-Rolle
3. **bdew_market_participants** - BDEW-spezifische Daten

## Nächste Schritte

1. **ETL-Pipelines** anpassen für neue Struktur
2. **APIs** entwickeln für Marktteilnehmer-Suche
3. **Frontend** für Multi-Rollen-Darstellung
4. **Import-Skripte** für bestehende Daten

## Datenbankzugriff

```bash
# PostgreSQL Container
docker exec -it vnbdigitaler-postgres psql -U vnb_admin -d vnb_digitaler

# PgAdmin Web Interface
http://localhost:8080
# Login: admin@vnbdigitaler.de / admin123
```
