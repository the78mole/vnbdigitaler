# OpenRouter API-Key Konfiguration

## 1. API-Key erhalten

1. Gehe zu [OpenRouter.ai](https://openrouter.ai)
2. Registriere dich kostenlos
3. Gehe zu "API Keys" in deinem Dashboard
4. Erstelle einen neuen API-Key
5. Kopiere den Key (format: `or-xxxx...`)

## 2. AI Modell konfigurieren

### Umgebungsvariable (empfohlen)

```bash
# In der .env Datei:
ROLL_OUT_REPORT_FIND_MODEL=meta-llama/llama-3.2-3b-instruct:free
```

### Kommandozeile

```bash
uv run tools/02_find_roll_out_report.py --model "openai/gpt-4o-mini" ...
```

### Verfügbare Modelle

- **Kostenlose Modelle:**
  - `meta-llama/llama-3.2-3b-instruct:free` (Standard)
  - `microsoft/phi-3.5-mini-128k-instruct:free`

- **Premium Modelle:** (sehr günstig)
  - `openai/gpt-4o-mini` (empfohlen für beste Ergebnisse)
  - `anthropic/claude-3.5-haiku`

## 3. API-Key einrichten

### Option A: .env Datei (empfohlen)

```bash
# Bearbeite die .env Datei im Projektverzeichnis:
nano .env

# Trage deinen API-Key ein:
OPENROUTER_API_KEY=or-dein-api-key-hier
ROLL_OUT_REPORT_FIND_MODEL=meta-llama/llama-3.2-3b-instruct:free
```

### Option B: Umgebungsvariable

```bash
export OPENROUTER_API_KEY="or-dein-api-key-hier"  # pragma: allowlist secret
export ROLL_OUT_REPORT_FIND_MODEL="openai/gpt-4o-mini"
```

### Option C: Kommandozeilen-Parameter

```bash
uv run tools/02_find_roll_out_report.py --api-key "or-dein-api-key-hier" --model "openai/gpt-4o-mini" --metadata-file ...  # pragma: allowlist secret
```

## 4. Testen

```bash
# Mit Standard-Modell aus .env:
uv run tools/02_find_roll_out_report.py --metadata-file /tmp/bnetza_download_*/download_metadata.json

# Mit anderem Modell:
uv run tools/02_find_roll_out_report.py --model "openai/gpt-4o-mini" --metadata-file ...

# Ohne API-Key (Pattern-Matching Fallback):
OPENROUTER_API_KEY="" uv run tools/02_find_roll_out_report.py --metadata-file ...
```

## 5. Kosten & Performance

| Modell           | Kosten    | Token | Performance      |
| ---------------- | --------- | ----- | ---------------- |
| **Llama 3.2-3B** | Kostenlos | ~783  | Sehr gut ✅       |
| **GPT-4o-mini**  | ~$0.001   | ~462  | Exzellent ⭐      |
| **Fallback**     | Kostenlos | 0     | Gut für BNetzA 📋 |

## 6. Konfigurationspriorität

1. **--model** Kommandozeilen-Parameter (höchste Priorität)
2. **ROLL_OUT_REPORT_FIND_MODEL** Umgebungsvariable
3. **Standard:** `meta-llama/llama-3.2-3b-instruct:free`

## 7. Sicherheit

- ✅ API-Key wird aus .env geladen (nicht in Git committed)
- ✅ .env ist bereits in .gitignore eingetragen
- ✅ Mehrere Konfigurationsoptionen verfügbar
- ✅ Automatischer Fallback ohne API-Key
