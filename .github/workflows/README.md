# VNBdigitaler Central Data Update Workflows

Dieses Repository enthält ein modulares GitHub Actions Workflow-System für automatische Datenaktualisierungen.

## 🏗️ Workflow-Architektur

### Zentrale Workflows

1. **`central-data-update.yml`** - Haupt-Orchestrator für alle Datenaktualisierungen
2. **`reusable-rollout-update.yml`** - Wiederverwendbarer Workflow für BNetzA Rollout-Quoten

### Reusable Workflow Pattern

Das System nutzt GitHub's [reusable workflows](https://docs.github.com/en/actions/using-workflows/reusing-workflows) für:
- **Modularität**: Einzelne Workflows können isoliert getestet werden
- **Wiederverwendbarkeit**: Workflows können von anderen Repositories genutzt werden
- **Wartbarkeit**: Zentrale Logik an einem Ort
- **Flexibilität**: Verschiedene Trigger und Parameter-Kombinationen

## 🚀 Features

### Automatische Ausführung
- **Täglich um 6:00 UTC** (8:00 CEST) - optimaler Zeitpunkt nach nächtlichen BNetzA-Updates
- **Intelligente Erkennung** neuer Reports mit bestehenden Tools

### Manuelle Kontrolle
- **Update Type Selection**: all, rollout-quotas, bdew-companies, check-only
- **Force Update**: Erzwingt Update auch ohne Änderungen
- **Dry Run**: Zeigt Änderungen ohne sie durchzuführen

### Robuste Fehlerbehandlung
- **Automatische Issue-Erstellung** bei Fehlern
- **Detailliertes Logging** für Debugging
- **Comprehensive Summary Reports** für jeden Run

## 📋 Update Types

| Type | Beschreibung | Status |
|------|-------------|---------|
| `all` | Alle verfügbaren Updates ausführen | ✅ Implementiert |
| `rollout-quotas` | Nur BNetzA Rollout-Quoten aktualisieren | ✅ Implementiert |
| `bdew-companies` | Nur BDEW Unternehmensdaten aktualisieren | 🏗️ Geplant |
| `check-only` | Nur prüfen, keine Aktualisierungen durchführen | ✅ Implementiert |

## 🔧 Setup

### 1. GitHub Secrets konfigurieren

```
DATABASE_URL - PostgreSQL Verbindungs-URL für Neon oder andere DB
NEON_DATABASE_URL - Alternative Neon Database URL (optional)
```

### 2. Workflow aktivieren

Der Workflow ist automatisch aktiv nach dem Push in den main branch.

### 3. Manuell testen

```bash
# Lokal testen mit verschiedenen Optionen
./test-update-workflow.sh --help
./test-update-workflow.sh --dry-run --update-type rollout-quotas
./test-update-workflow.sh --force-update --update-type all
```

## 🎯 Workflow Outputs

Jeder reusable workflow stellt Outputs zur Verfügung:

```yaml
outputs:
  has_updates: 'true/false'
  action_taken: 'Beschreibung der durchgeführten Aktion'
  companies_processed: 'Anzahl verarbeiteter Unternehmen'
```

## 📊 Monitoring & Debugging

### Workflow Logs
- Detaillierte Logs in GitHub Actions
- Strukturierte Ausgabe mit Progress-Indikatoren
- Fehler-spezifische Logs mit Kontext

### Summary Reports
Jeder Workflow-Run erstellt ein Summary-Report mit:
- Konfiguration und Trigger-Info
- Ergebnisse aller Jobs
- Links zu relevanten Ressourcen
- Nächste Schritte

### Automatische Issue-Erstellung
Bei Fehlern wird automatisch ein Issue erstellt mit:
- Detaillierte Fehlerinformationen
- Mögliche Ursachen
- Empfohlene Lösungsschritte
- Links zu Logs und Debugging-Ressourcen

## 🔄 Erweiterung

### Neuen Update-Typ hinzufügen

1. **Reusable Workflow erstellen**:
   ```yaml
   # .github/workflows/reusable-new-update.yml
   name: Reusable New Data Update
   on:
     workflow_call:
       inputs:
         # Parameter definieren
       secrets:
         # Secrets definieren
       outputs:
         # Outputs definieren
   ```

2. **Im Central Workflow einbinden**:
   ```yaml
   # In central-data-update.yml
   new-data-update:
     uses: ./.github/workflows/reusable-new-update.yml
     with:
       # Parameter übergeben
     secrets:
       # Secrets übergeben
   ```

3. **Test-Script erweitern**:
   ```bash
   # In test-update-workflow.sh
   case "$UPDATE_TYPE" in
       "new-data"|"all")
           # Test-Logik hinzufügen
   esac
   ```

## 🛠️ Troubleshooting

### Häufige Probleme

1. **Database Connection**:
   - Prüfe DATABASE_URL Secret
   - Teste Verbindung lokal
   - Prüfe Neon Database Status

2. **BNetzA Website Changes**:
   - Teste rollout_report_updater.py manuell
   - Prüfe Logs auf HTTP-Fehler
   - Verifiziere URL-Strukturen

3. **Dependencies**:
   - Prüfe uv.lock und pyproject.toml
   - Teste lokale Installation
   - Verifiziere Python-Version

### Debugging Steps

```bash
# 1. Lokale Umgebung prüfen
uv sync
uv run python --version

# 2. Database-Verbindung testen
uv run python -c "from src.database import DatabaseManager; print('DB OK')"

# 3. Update-Tools einzeln testen
uv run python src/bnetza/rollout_report_updater.py --check-update --verbose

# 4. Workflow simulieren
./test-update-workflow.sh --dry-run --update-type check-only
```

### Recovery bei Fehlern

1. **Issue checken**: Automatisch erstellte Issues enthalten Diagnose-Info
2. **Manual re-run**: Workflow manuell mit force-update ausführen
3. **Rollback**: Bei Datenproblemen Database-Backup verwenden
4. **Monitoring**: WebUI Dashboard für Datenvalidierung nutzen
