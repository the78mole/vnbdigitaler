# Tool 17: LLM BDEW-zu-BNetzA Company Matching - Implementierungsvereinbarung

## Übersicht

Das Tool `17_llm_bdew_bnetza_company_match.py` führt eine intelligente Zuordnung von BDEW-Unternehmen zu BNetzA-Rollout-Unternehmen durch. Es kombiniert exakte String-Matches mit LLM-basierter Analyse für optimale Automatisierung.

## Architektur & Datenfluss

### 1. Mehrstufiger Matching-Prozess

```mermaid
TBD
```

### 2. Datenquellen

#### BDEW-Daten (Datenbank)

- **Tabelle**: `companies`
- **Felder**: `id, bdew_code, bdew_name, bdew_city, rollout_report_name, manual_verification`

#### BNetzA-Daten (CSV-Datei)

- **Quelle**: `data/Roll-out-Quoten_Q1_2025.csv` (als Kommandozeilen-Argument)
- **Feld**: `Unternehmen` (Unternehmensname)
- **Format**: CSV mit Header

### 3. LLM-Integration

- **LLM-Api** ist OpenRouter
- **API-Key** aus dem `.env` konfiguriert: `OPENROUTER_API_KEY`
- **Python-Lib** ist OpenAI
- **Model** aus dem `.env` konfiguriert: `ROLL_OUT_REPORT_FIND_MODEL`
- **Prompt-Template** ist Jinja2 `tools/templates/match_bdew_to_bnetza.md.j2`
- **Maximale LLM-Anfragen** per Script-Argument festlegen

### 4. Durchführungsschritte

- Einlesen der BDEW-Einträge aus der Datenbank (im Folgenden: BDEW-Liste)
- Einlesen der BNetzA-Unternehmen aus der CSV-Datei (im Folgenden: BNetzA-Liste)
- Filtern der BNetzA-Unternehmen, die bereits manuell überprüft wurden
  (BDEW:`manual_verification` == TRUE) über matching BNetzA:`Unternehmen` vs.
  BDEW:`rollout_report_name` und entfernen der Einträge aus beiden Listen
- In den übrigen Einträgen der BDEW-Liste nach exaktem String BDEW:`rollout_report_name`
  in der BNetzA-Liste BNetzA:`Unternehmen` suchen, matches als manually verified in der
  DB kennzeichnen und aus beiden Listen entfernen
- Die übrigen Einträge sortieren, längste Strings zuerst
- In den übrigen Einträgen der BDEW-Liste nach exaktem Match BDEW:`bdew_name` und
  BNetzA:`Unternehmen` suchen, matches nicht als manually verified in der DB
  kennzeichnen und aus beiden Listen entfernen, aber in eine neue Approval-CSV-Liste
  `data/match_approval.csv` mit folgenden Spalten schreiben:
  `id`, `bdew_code`, `bnetza_id`, `bdew_name`, `bnetza_name`, `confidence_score`.
- Für jeden verbleibenden BDEW-Eintrag eine einzelne LLM-Anfrage an die OpenRouter API
  mit dem Jinja2-prozessierten Prompt-Template stellen. Ergebnisse entsprechend
  verarbeiten:
  `recommendation/auto_approve` führt zu einem `manual_verification` = True in der DB,
  `recommendation/manual_review` führt zu einem `manual_verification` = False in der DB
  und einem Eintrag in der Approval-CSV-Liste,
  `recommendation/no_match` führt zu einem `manual_verification` = False
  in der DB und einem Eintrag in eine unmatched-CSV.

### 5. Finale Review-Phase (Optional)

- **Template**: `tools/templates/final_match_review.md.j2`
- **Input**: Alle Einträge aus der Approval-CSV im JSON-Format
- **Zweck**: Gesamtkontextuelle Bewertung aller manuellen Review-Fälle
- **Output**: JSON-Array mit überarbeiteten Confidence-Scores und finalen Empfehlungen
- **Trigger**: Separater Script-Parameter `--final-review` oder eigenes Tool

#### Bewertungskriterien der finalen Review

- Unternehmensidentität und Konzernstrukturen
- Geografische und rechtliche Konsistenz
- Branchenkontext und zeitliche Faktoren
- Erkennung von Dopplungen/Widersprüchen

#### JSON-Output-Format

```json
[
  {
    "match_id": 1,
    "bdew_name": "Unternehmen",
    "proposed_bnetz_name": "BNetzA Name",
    "original_confidence": 85,
    "revised_confidence": 92,
    "confidence_change_reason": "Begründung",
    "recommendation": "auto_approve|manual_review|reject|requires_research",
    "final_reasoning": "Finale Bewertung",
    "risk_factors": ["geographic_mismatch", "legal_form_uncertainty"],
    "requires_attention": false
  }
]
```
