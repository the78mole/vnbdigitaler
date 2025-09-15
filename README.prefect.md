# VNB Digitaler - Prefect Development Setup

Dieses Verzeichnis enthält die Prefect-Integration für VNB Digitaler mit SQLite für Development und einfacher Migration zu Neon PostgreSQL für Production.

## 🚀 Quick Start

```bash
# 1. Setup-Script ausführen
./scripts/setup_prefect_dev.sh

# 2. Prefect UI öffnen
open http://localhost:4200

# 3. Beispiel-Flow testen
uv run python flows/example_flow.py
```

## 📦 Enthaltene Komponenten

### Docker Compose Services

- **prefect-server**: Prefect Server mit SQLite Backend
- **prefect-worker**: Worker-Container für Flow-Ausführung
- **prefect-ui**: Optional separate UI (Port 4201)

### Verzeichnisstruktur

```
flows/                          # Prefect Flows
├── example_flow.py            # Beispiel-Flow für Testing
├── bdew/                      # BDEW Import Flows
├── bnetza/                    # BNetzA Rollout Flows
├── pricing/                   # VNB Pricing Flows
└── monitoring/                # System Monitoring Flows

deployments/                   # Deployment Konfigurationen
prefect_config/               # Prefect-spezifische Config
├── blocks/                   # Prefect Blocks
├── work_pools/              # Work Pool Configs
└── neon_migration.py        # Neon Migration Helper

data/                        # Daten (SQLite, Storage, Logs)
├── sqlite/                  # SQLite Datenbanken
├── storage/                 # File Storage
└── logs/                    # Log Files
```

## 🗄️ Database Configuration

### Development (SQLite)

```bash
# Standardkonfiguration in .env.prefect
VNB_DATABASE_URL=sqlite+aiosqlite:///app/data/vnb_digitaler.db
```

### Production (Neon PostgreSQL)

```bash
# Migration zu Neon
python prefect_config/neon_migration.py

# .env.neon konfigurieren
cp .env.neon.template .env.neon
# Neon Credentials eintragen

# Mit Neon starten
docker-compose -f docker-compose.prefect.yml -f docker-compose.neon.yml up
```

## 🔧 Development Commands

```bash
# Services verwalten
docker-compose -f docker-compose.prefect.yml up -d     # Start
docker-compose -f docker-compose.prefect.yml down      # Stop
docker-compose -f docker-compose.prefect.yml restart   # Restart

# Logs anzeigen
docker-compose -f docker-compose.prefect.yml logs -f prefect-server
docker-compose -f docker-compose.prefect.yml logs -f prefect-worker

# Worker Shell
docker exec -it vnbdigitaler-prefect-worker-1 bash

# Flow direkt ausführen
uv run python flows/example_flow.py
```

## 📊 Monitoring & Debugging

### Prefect UI Features

- **Flow Runs**: <http://localhost:4200/flow-runs>
- **Work Pools**: <http://localhost:4200/work-pools>
- **Blocks**: <http://localhost:4200/blocks>
- **Logs**: Integriert in Flow Run Details

### Debugging

```bash
# Debug-Modus aktivieren
export VNB_ENABLE_DEBUG_LOGGING=true
export VNB_VERBOSE_LOGGING=true

# Intermediate Results speichern
export VNB_SAVE_INTERMEDIATE_RESULTS=true

# Dry-Run für Testing
export VNB_DRY_RUN_MODE=true
```

## 🚀 Migration von SQLite zu Neon

### 1. Neon Project Setup

1. Neon Dashboard öffnen: <https://console.neon.tech>
2. Neues Project erstellen: "vnb-digitaler"
3. Database erstellen: "vnb_digitaler"
4. Connection String kopieren

### 2. Migration ausführen

```bash
# Migration Helper ausführen
python prefect_config/neon_migration.py

# Neon Credentials konfigurieren
cp .env.neon.template .env.neon
# NEON_DATABASE_URL mit echten Credentials setzen

# Services mit Neon starten
docker-compose -f docker-compose.prefect.yml -f docker-compose.neon.yml up -d
```

### 3. Daten Migration (falls nötig)

```bash
# Bestehende SQLite Daten exportieren
docker exec vnbdigitaler-prefect-server-1 prefect database export backup.sql

# In Neon importieren (nach Service-Start mit Neon)
docker exec vnbdigitaler-prefect-server-1 prefect database import backup.sql
```

## 🔐 Security & Environment

### Development

- SQLite ohne Authentifizierung
- Lokale Docker-Netzwerke
- Debug-Logging aktiviert

### Production

- Neon PostgreSQL mit SSL
- Environment-basierte Secrets
- Monitoring & Alerting

## 📝 Nächste Schritte

1. **Dependencies hinzufügen**: `uv add prefect[all]`
2. **Echte Flows entwickeln**: BDEW, BNetzA, VNB Pricing
3. **Pipeline Integration**: Bestehende Pipeline-Klassen einbinden
4. **Monitoring Setup**: Slack/Teams Notifications
5. **Production Deployment**: Neon Migration + Secrets Management

## 📖 Weitere Dokumentation

- [Prefect Flows](../docs/PREFECT_FLOWS.md) - Detaillierte Flow-Implementierungen
- [Prefect Integration](../docs/PREFECT_INTEGRATION.md) - Pipeline-Adapter
- [Prefect Deployment](../docs/PREFECT_DEPLOYMENT.md) - Production Setup
- [Hauptspezifikation](../docs/specs/SPECIFICATION.md) - Gesamtarchitektur
