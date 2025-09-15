# BDEW-Codes Integration Plan

## Übersicht über BDEW-Codes System

Basierend auf <https://bdew-codes.de/Codenumbers/BDEWCodes/CodeOverview> analysiert:

### Zentrale Identifikatoren im deutschen Energiemarkt

1. **BDEW-Codenummern** (MP-ID)

   - Marktpartneridentifikationsnummer für deutschen Strommarkt
   - **Pro Rolle eindeutig** - ein Unternehmen kann mehrere Codes haben
   - Alternative: GLN (Global Location Number) von GS1

2. **Stromnetzbetreibernummern**

   - Spezifisch für Netzbetreiber nach §§ 3 Ziff. 3, 14 EnWG
   - Benötigt für Zählpunktbezeichnung (MeteringCode VDE-AR-N 4400)
   - Voraussetzung für BDEW-Codenummer in Netzbetreiber-Rolle

3. **Energy Identification Code (EIC)**

   - Europaweit eindeutige Identifikation
   - ENTSO-E als Central Issuing Office (CIO)
   - BDEW als Local Issuing Office (LIO) für Deutschland

4. **Weitere Codes**
   - Netzlokations-ID
   - NEBE-ID (Netzgebiet-ID)
   - E-Mobility-ID

## Probleme mit aktueller Datenbankstruktur

### ❌ Fehlende BDEW-Codes Integration

- Keine Felder für offizielle BDEW-Codes
- Keine EIC-Codes
- Keine Stromnetzbetreibernummern
- Selbst erfundene `role_specific_code` statt echter BDEW-Codes

### ❌ Rollenmodell unvollständig

- BDEW hat offizielles Rollenmodell-Dokument
- Unsere Rollen könnten nicht standardkonform sein
- Fehlende Verknüpfung zu offiziellen BDEW-Dokumenten

## Empfohlene Datenbankstruktur-Anpassung

### 1. Erweiterte Company-Tabelle

```sql
ALTER TABLE companies ADD COLUMN
    gln VARCHAR(13),                    -- Global Location Number (optional)
    eic_code VARCHAR(16),               -- Energy Identification Code
    grid_operator_number VARCHAR(50),   -- Stromnetzbetreibernummer (falls VNB)
    registration_authority VARCHAR(50), -- BDEW, GS1, etc.
```

### 2. Erweiterte Company-Roles Tabelle

```sql
ALTER TABLE company_roles ADD COLUMN
    bdew_code VARCHAR(13),              -- Offizielle BDEW-Codenummer für diese Rolle
    bdew_role_code VARCHAR(10),         -- Offizieller BDEW-Rollencode
    registration_date DATE,             -- Registrierungsdatum bei BDEW
    certificate_number VARCHAR(50),     -- Zertifikatsnummer
    status VARCHAR(20),                 -- active, suspended, revoked
```

### 3. BDEW-Rollen Synchronisation

- Offizielles BDEW-Rollenmodell als Basis verwenden
- PDF "Rollenmodell für die Marktkommunikation" analysieren
- Rollen-Codes von BDEW übernehmen

### 4. API-Integration

- BDEW bietet Webservice-Zugang an
- Automatische Synchronisation der Codes
- Real-time Validierung gegen BDEW-Datenbank

## Nächste Schritte

1. **BDEW-Rollenmodell PDF analysieren**

   - Download: 2023-03-06-AWH-Rollenmodell_MaKo_V2.1_BcwsudV.pdf
   - Offizielle Rollen extrahieren
   - Unsere `market_participant_roles` anpassen

2. **Webservice-Integration planen**

   - BDEW-Codes API dokumentieren
   - ETL-Pipeline für BDEW-Codes entwickeln
   - Sync-Mechanismus implementieren

3. **Datenbankschema erweitern**

   - BDEW-spezifische Felder hinzufügen
   - Constraints für Code-Validierung
   - Migration bestehender Daten

4. **Test-Implementierung**
   - Echte BDEW-Codes für Stadtwerke München beschaffen
   - Validation gegen offizielle Datenbank testen
   - Multi-Rollen-Codes validieren

## Wichtige Erkenntnisse

- **Ein Unternehmen = Mehrere BDEW-Codes** (pro Rolle)
- **BDEW-Codes sind die zentrale Datenquelle** für deutsche Energiemarkt
- **EIC-Codes** für europäische Integration wichtig
- **Webservice verfügbar** für automatisierten Zugriff
- **Offizielle Dokumentation** als Basis verwenden statt eigene Rollen erfinden

Die BDEW-Codes-Website ist definitiv die **Wurzel für unseren Datenpool** - alle anderen Datenquellen sollten gegen diese validiert werden.
