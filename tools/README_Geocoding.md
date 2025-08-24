# Company Geocoding Tool

Das `geocode_companies.py` Script geocodiert Company-Adressen mithilfe des Nominatim-Services (OpenStreetMap) und speichert die Koordinaten in den Datenbank-Spalten `company_latitude` und `company_longitude`.

## Features

- ✅ **Automatische Adress-Geocodierung**: Nutzt geopy und Nominatim für präzise Koordinaten
- ✅ **Rate Limiting**: Respektiert Nominatim-Richtlinien (max. 1 Request/Sekunde)
- ✅ **Intelligente Adress-Erkennung**: Bevorzugt vnbdigital.de Adressdaten, fallback zu BDEW-Daten
- ✅ **Fehlerbehandlung**: Retry-Logik bei temporären Fehlern
- ✅ **Caching**: Vermeidet doppelte Anfragen für identische Adressen
- ✅ **Dry-Run Modus**: Test-Modus ohne Datenbank-Updates
- ✅ **Fortschritts-Anzeige**: Detaillierte Statistiken und Status-Updates
- ✅ **Batch-Processing**: Automatische Commits alle 10 Companies
- ✅ **Filteroptionen**: Nach Stadt, Limit, bereits geocodierte Companies

## Usage

### Basis-Commands

```bash
# Hilfe anzeigen
uv run python tools/geocode_companies.py --help

# Dry-Run mit ersten 10 Companies
uv run python tools/geocode_companies.py --dry-run --limit 10

# Alle Companies ohne Koordinaten geocodieren
uv run python tools/geocode_companies.py

# Nur Companies aus bestimmter Stadt
uv run python tools/geocode_companies.py --city "Berlin"

# Auch bereits geocodierte Companies aktualisieren
uv run python tools/geocode_companies.py --force-update --limit 5
```

### Parameter

| Parameter | Beschreibung |
|-----------|-------------|
| `--dry-run` | Test-Modus, keine Datenbank-Updates |
| `--limit N` | Beschränke auf N Companies |
| `--force-update` | Update auch bereits geocodierte Companies |
| `--city NAME` | Filtere nach Stadt-Namen (case-insensitive) |

## Adress-Logik

Das Script baut Adressen mit folgender Priorität:

1. **vnbdigital.de Daten** (falls verfügbar):
   - `vnbdigital_address`
   - `vnbdigital_postcode` + `vnbdigital_city`

2. **BDEW Daten** (Fallback):
   - `bdew_city`
   - `bdew_name` (als letzter Ausweg)

3. **Immer hinzugefügt**: "Deutschland" für bessere Geocoding-Genauigkeit

## Beispiel Ausgabe

```
🗺️  VNBdigitaler Company Geocoding Tool
==================================================
📋 Loading companies...
📊 Found 5 companies to process

🔄 Progress: 1/5

📍 Processing 1: ASCANETZ GmbH
    ID: 523, BDEW Code: 963
    🔍 Geocoding: Magdeburger Straße, 26, 06449 Aschersleben , Deutschland
    ✅ Found: 51.759286, 11.449527
    💾 Updated database

============================================================
📊 GEOCODING STATISTICS
============================================================
Processed:       5
Successful:      5
Failed:          0
Skipped:         0
Cached:          0
Success rate: 100.0%
============================================================
```

## Rate Limiting & Nominatim Policy

- **Request Rate**: 1.1 Sekunden zwischen Requests (respektiert Nominatim 1/sec Limit)
- **Timeout**: 10 Sekunden pro Request
- **Retry Logic**: 3 Versuche bei temporären Fehlern
- **User Agent**: "vnbdigitaler/1.0 (<daniel@thinkmoles.de>)"

## Datenbank-Schema

Die Koordinaten werden in folgenden Spalten gespeichert:

```sql
company_latitude   NUMERIC(10,7)  -- Range: -90.0 to 90.0
company_longitude  NUMERIC(10,7)  -- Range: -180.0 to 180.0
```

Mit Constraints:

- `check_latitude_range`: lat ≥ -90 AND lat ≤ 90
- `check_longitude_range`: lon ≥ -180 AND lon ≤ 180

## API Integration

Die Koordinaten sind automatisch über die Companies-API verfügbar:

```bash
curl "http://localhost:8000/companies/api?page=1&page_size=10" | \
  jq '.companies[] | select(.company_latitude != null) | {id, bdew_name, company_latitude, company_longitude}'
```

## Tipps & Best Practices

### Für große Datenmengen

```bash
# Erst testen mit kleiner Anzahl
uv run python tools/geocode_companies.py --dry-run --limit 50

# Dann schrittweise vergrößern
uv run python tools/geocode_companies.py --limit 100
uv run python tools/geocode_companies.py --limit 500
```

### Fehlerbehandlung

- Script kann jederzeit mit Ctrl+C unterbrochen werden
- Automatisches Rollback bei Fehlern
- Bereits geocodierte Companies werden automatisch übersprungen

### Performance

- ~1.1 Sekunden pro Company (due to rate limiting)
- ~54 Companies/Minute
- ~3,240 Companies/Stunde

### Cache-Verhalten

- Identische Adressen werden nur einmal geocodiert
- Cache ist nur während Script-Laufzeit aktiv
- Für persistenten Cache müsste Redis/Database-Lösung implementiert werden

## Troubleshooting

### Häufige Probleme

**Keine Ergebnisse gefunden:**

```
❌ No results found
```

→ Adresse möglicherweise unvollständig oder fehlerhaft

**Timeout-Fehler:**

```
⚠️  Attempt 1/3 failed: Request timed out
```

→ Temporäres Netzwerk-Problem, Script versucht automatisch erneut

**Database-Fehler:**

```
❌ Database update failed: FOREIGN KEY constraint failed
```

→ Company-ID existiert nicht mehr, sollte nicht auftreten

### Debugging

```bash
# Verbose Output für spezifische City
uv run python tools/geocode_companies.py --dry-run --city "Berlin" --limit 5

# Force-Update für bereits geocodierte Company
uv run python tools/geocode_companies.py --force-update --limit 1
```
