# Enhanced Company Matching - Step 6

```bash
# Enhanced Matching (verwendet automatisch die Datenbank)
uv run python tools/12_oo_company_matching.py \
  --step 6 \
  --bnetza-csv data/Roll-out-Quoten_Q1_2025.csv

# Mit OpenRouter für LLM-Fallback
export OPENROUTER_API_KEY="or-your_api_key_here"  # pragma: allowlist secret
uv run python tools/12_oo_company_matching.py \
  --step 6 \
  --bnetza-csv data/Roll-out-Quoten_Q1_2025.csv \
  --openrouter-api-key your_key_here
```

### Voraussetzungen

1. **Schritt 03 abgeschlossen**: BDEW-Daten müssen bereits in die Datenbank integriert sein
2. **BDEW Datenbank**: Mit `rollout_report_name` und `rollout_name_variations` Spalten
3. **Optional**: OpenRouter API Key für LLM-Fallback6 implementiert ein verbessertes Company-Matching-System, das eine mehrstufige Matching-Strategie mit datenbankbasierter Suche verwendet.

## Matching-Prioritäten

### 1. **Database Rollout Report Name Lookup** (Priorität 1)

- Direkte Suche nach `rollout_report_name` in der BDEW-Datenbank
- 100% Match-Score bei Erfolg
- Match-Type: `database_rollout_name`

### 2. **Database Name Variations Lookup** (Priorität 2)

- Suche in `rollout_name_variations` Array
- 95% Match-Score bei Erfolg
- Match-Type: `database_variation`

### 3. **Exact Matching** (Priorität 3)

- Verwendung des bestehenden exakten Matchers
- Normalized Name Vergleich
- Match-Type: `exact`

### 4. **Fuzzy Matching** (Priorität 4)

- Fuzzy String Matching mit fuzzywuzzy
- Minimum Threshold: 70%
- Match-Type: `fuzzy`

### 5. **LLM-Assisted Matching** (Priorität 5)

- OpenRouter/OpenAI basierte Bewertung
- Nur bei verfügbaren Fuzzy-Kandidaten
- Match-Type: `llm_assisted`

## Verwendung

### Kommandozeile

```bash
```bash
# Enhanced Matching mit Datenbank (erforderlich)
uv run python tools/12_oo_company_matching.py
  --step 6
  --bnetza-csv data/Roll-out-Quoten_Q1_2025.csv
  --use-db

# Mit OpenRouter für LLM-Fallback
export OPENROUTER_API_KEY="or-your_api_key_here"  # pragma: allowlist secret
uv run python tools/12_oo_company_matching.py
  --step 6
  --bnetza-csv data/Roll-out-Quoten_Q1_2025.csv
  --use-db
  --openrouter-api-key your_key_here  # pragma: allowlist secret
```

### System-Voraussetzungen

1. **Datenbank**: `--use-db` Flag erforderlich (BDEW-Daten kommen aus Datenbank)
2. **BDEW Datenbank**: Mit `rollout_report_name` und `rollout_name_variations` Spalten
3. **Optional**: OpenRouter API Key für LLM-Fallback

## Output Files

### Generated Files

- `data/enhanced_company_matches.csv`: Alle gefundenen Matches mit Details
- `data/enhanced_unmatched_bnetza_companies.csv`: Nicht gematchte BNetzA-Unternehmen

### Match File Format

```csv
bnetza_index,bnetza_name,bdew_code,bdew_name,match_score,match_type
1,Stadtwerke München,10YDE-EON------S,Stadtwerke München GmbH,100.00,database_rollout_name
2,Vattenfall,10YDE-VE-------2,Vattenfall Europe Distribution Berlin GmbH,95.00,database_variation
```

## Konfiguration

### Database Schema Erweiterungen

```sql
-- BDEW Companies Table
ALTER TABLE companies ADD COLUMN rollout_report_name VARCHAR(255);
ALTER TABLE companies ADD COLUMN rollout_name_variations TEXT[];

-- Index für Performance
CREATE INDEX idx_companies_rollout_name ON companies(rollout_report_name);
```

### Environment Variables

```bash
# Database
NEON_DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database  # pragma: allowlist secret

# OpenRouter (optional für LLM-Fallback)
OPENROUTER_API_KEY=or-xxx  # pragma: allowlist secret
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1  # pragma: allowlist secret
```

## Performance

### Matching-Reihenfolge Optimierung

1. **Database Lookup**: Sehr schnell (Index-basiert)
2. **Exact Matching**: Schnell (In-Memory Dictionary)
3. **Fuzzy Matching**: Mittel (String-Algorithmen)
4. **LLM Matching**: Langsam (API-Calls)

### Erwartete Verbesserungen

- **Höhere Accuracy**: Durch database-gespeicherte exakte Namen
- **Bessere Coverage**: Mehrstufiger Fallback-Ansatz
- **Konsistenz**: Deterministische Database-Ergebnisse

## Monitoring

### Log-Level

- Database matches: `DEBUG` level
- Summary statistics: `INFO` level
- Errors: `ERROR` level

### Metriken

- Database match rate
- Exact match rate
- Fuzzy match rate
- LLM match rate
- Total coverage percentage

## Troubleshooting

### Häufige Probleme

1. **No database matches**: Überprüfe `rollout_report_name` Daten in DB
2. **Performance issues**: Überprüfe Database-Indizes
3. **LLM timeouts**: Reduziere `LLM_MAX_CANDIDATES`
