# Structured Company Matching - Dokumentation

## Überblick

Das neue strukturierte Company-Matching-System (`13_structured_company_matching.py`) implementiert einen klaren, schrittweisen Ansatz zum Abgleich von BNetzA Roll-Out Daten mit der BDEW-Datenbank.

## Architektur

### 🏗️ Strukturierter Ansatz

Das System ist in 7 klar definierte Schritte unterteilt:

1. **📝 BNetzA CSV einlesen** - Lade Roll-Out Daten
2. **🔍 Existing Matches** - Prüfe bereits vorhandene `rollout_report_name`
3. **📊 Variations Matching** - Abgleich mit `rollout_name_variations`
4. **🎯 Exact Matching** - Exakte String-Matches
5. **🔧 Normalized Matching** - Normalisierte Matches (ohne Rechtsformen)
6. **🤖 LLM + User Interaction** - KI-unterstützt mit Benutzerinteraktion
7. **❌ Mark Unmatched** - Verbleibende als UNMATCHED markieren

### 🎯 Verbessertes Logging

Jeder Schritt hat:

- ✅ Klare Erfolgsmeldungen mit Statistiken
- ❌ Detaillierte Fehlermeldungen bei Problemen
- 📊 Zwischen-Statistiken nach jedem Schritt
- 🎉 Abschließende Gesamt-Statistik

## Verwendung

### Basis-Kommando

```bash
uv run python tools/13_structured_company_matching.py \
  --bnetza-csv data/Roll-out-Quoten_Q1_2025.csv
```

### Mit LLM-Unterstützung

```bash
export OPENROUTER_API_KEY="or-your_key_here"  # pragma: allowlist secret
uv run python tools/13_structured_company_matching.py \
  --bnetza-csv data/Roll-out-Quoten_Q1_2025.csv \
  --openrouter-api-key your_key_here  # pragma: allowlist secret
```

## Detaillierte Schritte

### Step 1: BNetzA CSV Loading

- Lädt Roll-Out Quoten CSV
- Erstellt interne BNetzA-Liste
- **Output**: `Loaded X BNetzA companies`

### Step 2: Existing Rollout Name Matches

- Lädt BDEW-Daten aus Datenbank
- Prüft existierende `rollout_report_name` Einträge
- Entfernt bereits gematchte aus der Verarbeitungsliste
- **Output**: `Found X existing matches, Y remaining`

### Step 3: Variations Matching

- Sucht in `rollout_name_variations` Arrays
- Aktualisiert `rollout_report_name` bei Matches
- Fügt alte Namen zu Variations hinzu
- **Database Update**: `rollout_report_name` + `rollout_name_variations`
- **Output**: `Found X variation matches, Y remaining`

### Step 4: Exact String Matching

- Exakter Vergleich BNetzA ↔ BDEW Namen
- **Database Update**: `rollout_report_name` + `rollout_name_variations`
- **Output**: `Found X exact matches, Y remaining`

### Step 5: Normalized Matching

- Normalisiert Firmennamen (entfernt Rechtsformen, etc.)
- Vergleicht normalisierte Namen
- **Database Update**: `rollout_report_name` + `rollout_name_variations`
- **Output**: `Found X normalized matches, Y remaining`

### Step 6: LLM + User Interaction

- Fuzzy-Kandidaten finden (>70% Ähnlichkeit)
- LLM bewertet Top 5 Kandidaten
- Bei <95% Confidence: User-Entscheidung erforderlich
- Interactive CLI für Benutzerauswahl
- **Database Update**: `rollout_report_name` + `rollout_name_variations`
- **Output**: `Found X LLM matches, Y user matches, Z remaining`

### Step 7: Mark Unmatched

- Speichert verbleibende Unternehmen in CSV
- Logged alle ungematchten Namen
- **Output**: `unmatched_bnetza_companies.csv`

## Database Updates

### Intelligente Updates

Das System aktualisiert die BDEW-Datenbank intelligent:

```sql
-- Für jeden Match wird gesetzt:
rollout_report_name = "Exakter BNetzA Name"

-- Bestehende rollout_report_name werden zu Variations:
rollout_name_variations = [
  "Alter rollout_report_name",  -- falls vorhanden
  "Neuer Match Name",           -- immer hinzufügen
  ...existing variations        -- behalten
]
```

## Output Files

### Unmatched Companies

- `data/unmatched_bnetza_companies.csv`
- Enthält alle nicht gematchten BNetzA-Unternehmen
- Für manuelle Nachbearbeitung oder Review

## Vorteile des neuen Systems

### 🎯 Strukturiert & Nachvollziehbar

- Klare Schritt-für-Schritt Verarbeitung
- Detailliertes Logging jedes Schritts
- Statistiken nach jedem Schritt

### 🔄 Inkrementell & Effizient

- Entfernt bereits gematchte aus Verarbeitungsliste
- Keine Duplikate oder redundante Verarbeitung
- Optimierte Datenbankzugriffe

### 🤖 KI + Human Intelligence

- LLM für komplexe Fälle
- User-Interaktion bei Unsicherheit
- 95% Confidence Threshold für automatische Matches

### 📊 Database-Centric

- Aktualisiert Datenbank in Echtzeit
- Nutzt Database als Single Source of Truth
- Intelligente Variations-Verwaltung

### 🛡️ Robust & Fehlertolerant

- Detaillierte Fehlerbehandlung
- Graceful Degradation (LLM optional)
- Klare Exit-Codes für jeden Schritt

## Beispiel-Output

```
📝 STEP 1: Loading BNetzA companies from CSV
✅ Successfully loaded 1,234 BNetzA companies

📊 STEP 2: Matching existing rollout_report_name entries
✅ Found 456 existing rollout_report_name matches
📊 Remaining BNetzA companies to process: 778

🔍 STEP 3: Matching rollout_name_variations
✅ Found 123 variation matches
📊 Remaining BNetzA companies to process: 655
   Updated 123 database records

🎯 STEP 4: Finding exact matches
✅ Found 89 exact matches
📊 Remaining BNetzA companies to process: 566
   Updated 89 database records

🔧 STEP 5: Finding normalized exact matches
✅ Found 67 normalized matches
📊 Remaining BNetzA companies to process: 499
   Updated 67 database records

🤖 STEP 6: LLM-assisted matching with user interaction
✅ Found 45 LLM matches and 23 user-confirmed matches
📊 Remaining BNetzA companies to process: 431
   Updated 68 database records

❌ STEP 7: Marking remaining companies as UNMATCHED
✅ Saved 431 unmatched companies to: data/unmatched_bnetza_companies.csv

📊 FINAL MATCHING STATISTICS
📈 Initial BNetzA companies: 1,234
🎯 Existing rollout_report_name matches: 456
🔍 Variation matches: 123
✅ Exact matches: 89
🔧 Normalized matches: 67
🤖 LLM matches: 45
👤 User-confirmed matches: 23
❌ Unmatched: 431
📊 Total matched: 803/1,234 (65.1%)
🎉 Success rate: 65.1%
```

## Integration

Das strukturierte System kann parallel zum bestehenden System laufen und wird nach dem Testen das alte System (`12_oo_company_matching.py`) ersetzen.
