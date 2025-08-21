# LLM-Assisted Company Matching - Dokumentation

## Überblick

Step 5 des Company-Matching-Prozesses verwendet ein Large Language Model (LLM) um schwierige Fälle zu bewerten, bei denen das Fuzzy-Matching alleine nicht ausreichend ist.

## Funktionsweise

### 1. **LLM-Workflow**

```
BNetzA Unternehmen → Fuzzy Kandidaten → LLM Bewertung → Finales Match
```

### 2. **Template-System**

- Jinja2-Template: `tools/templates/llm_company_matching.j2`
- Strukturierter Prompt mit:
  - BNetzA-Unternehmen Details
  - Top 5 Fuzzy-Kandidaten mit Scores
  - Bewertungskriterien
  - JSON-Antwortformat

### 3. **LLM-Konfiguration**

- Model: `gpt-4o-mini` (kosteneffizient für Klassifikation)
- Temperature: 0.1 (konsistente Ergebnisse)
- Max Tokens: 500
- Confidence Threshold: 0.7

## Verwendung

### Kommandozeile

```bash
# Mit API Key als Argument
uv run python tools/12_oo_company_matching.py \
  --step 5 \
  --bnetza-csv data/Roll-out-Quoten_Q1_2025.csv \
  --bdew-csv data/bdew_grid_operators.csv \
  --openai-api-key your_api_key_here

# Mit Umgebungsvariable
export OPENAI_API_KEY="your_api_key_here" # pragma: allowlist secret
uv run python tools/12_oo_company_matching.py \
  --step 5 \
  --bnetza-csv data/Roll-out-Quoten_Q1_2025.csv \
  --bdew-csv data/bdew_grid_operators.csv
```

### Voraussetzungen

1. **Vorangegangene Steps**: Step 5 lädt automatisch Ergebnisse aus Step 4
2. **OpenAI API Key**: Entweder via Parameter oder Umgebungsvariable
3. **Datenfiles**:
   - `data/final_remaining_bnetza_companies.csv`
   - `data/final_remaining_bdew_companies.csv`
   - `data/all_confirmed_matches.csv`

## Output-Dateien

### 1. **final_all_matches.csv**

Alle bestätigten Matches (Exact + Fuzzy + LLM)

### 2. **llm_assisted_matches.csv**

Nur die neuen LLM-Matches

### 3. **final_unmatched_bnetza_companies.csv**

BNetzA-Unternehmen ohne Match

### 4. **final_unmatched_bdew_companies.csv**

BDEW-Unternehmen ohne Match

## LLM-Response Format

```json
{
  "match_found": true,
  "bdew_code": "1234",
  "confidence": 0.95,
  "reasoning": "Eindeutige Übereinstimmung bei Name und Stadt"
}
```

oder

```json
{
  "match_found": false,
  "confidence": 0.90,
  "reasoning": "Keine der Kandidaten passt geografisch oder strukturell"
}
```

## Bewertungskriterien

Das LLM bewertet folgende Faktoren:

- **Unternehmensname** (mit Variationen wie GmbH/AG/KG/eG)
- **Geografische Lage/Stadt**
- **Branche** (Stadtwerke, Energienetze, etc.)
- **Rechtliche Struktur**

## Confidence-Levels

- **0.95-1.0**: Sehr sicher (eindeutige Übereinstimmung)
- **0.80-0.94**: Sicher (klare Indizien)
- **0.60-0.79**: Unsicher (gemischte Signale)
- **0.0-0.59**: Sehr unsicher (schwache Indizien)

## Rate Limiting

- Automatische Pause alle 10 verarbeitete Unternehmen
- 1 Sekunde Wartezeit zur Einhaltung der API-Limits

## Fehlerbehandlung

- JSON-Parsing Fehler werden abgefangen
- API-Fehler werden geloggt und übersprungen
- Markdown-Code-Blocks werden automatisch extrahiert

## Kosten-Optimierung

- Verwendung von `gpt-4o-mini` statt größerer Modelle
- Limitierung auf Top 5 Fuzzy-Kandidaten
- Niedrige Temperature für weniger Token-Verbrauch
- Strukturiertes JSON-Format für präzise Antworten

## Sicherheit

- Jinja2 Auto-Escaping aktiviert
- API-Key über Umgebungsvariablen
- Input-Validierung für LLM-Responses
