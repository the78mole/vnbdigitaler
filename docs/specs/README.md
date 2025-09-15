# 📋 VNB Digitaler - Projekt-Spezifikationen

Willkommen zu den technischen Spezifikationen des VNB Digitaler Projekts. Diese Dokumente enthalten die vollständige technische Dokumentation für Entwickler, Architekten und Betreiber.

## 📚 Dokumentations-Übersicht

### 🛣️ Strategische Planung

- **[ROADMAP.md](./ROADMAP.md)** - Die autoritative Quelle für alle Phasen, Meilensteine und Checklisten
  - Projekt-Timeline und kritische Pfade
  - Aktuelle Checklisten und TODOs
  - Qualitätskennzahlen und Success Metrics

### ⚙️ Technische Architektur

- **[SPECIFICATION.md](./SPECIFICATION.md)** - Umfassende technische Spezifikation
  - Funktionale Anforderungen und Geschäftsziele
  - System-Architektur und UI-Design
  - Datenintegrations-Pipeline
  - Implementierungsplan und Risikomanagement

### 🔌 API-Referenz

- **[API.md](./API.md)** - Vollständige API-Dokumentation
  - Admin API (Port 8081) - Datenvalidierung und -verwaltung
  - Installer API (Port 8080) - OAuth2 und Installation Management
  - Public API (Streamlit) - Öffentliche Suchschnittstellen
  - GraphQL Schema für komplexe Abfragen

### 🗄️ Datenbank-Design

- **[DATABASE.md](./DATABASE.md)** - Komplettes Datenbankschema
  - PostgreSQL-Tabellen mit Constraints und Indexes
  - Performance-Optimierungen und Partitioning
  - Security (Row Level Security, Encryption)
  - Backup-Strategien und Monitoring

### 🧪 Qualitätssicherung

- **[TESTING.md](./TESTING.md)** - Test-Strategien und Code Quality
  - Test-Pyramide: Unit, Integration, E2E Tests
  - Code-Quality-Standards (Black, isort, mypy, pytest)
  - Pre-Commit Hooks und CI/CD-Testing
  - Load Testing und Performance-Validierung

### 🚀 Operations

- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Production Setup und Operations
  - Docker-Compose Production-Konfiguration
  - Nginx-Setup mit SSL-Termination
  - GitHub Actions CI/CD-Workflows
  - Neon Database-Integration und Monitoring

## 🔗 Cross-References

Alle Dokumente sind miteinander verknüpft und verweisen aufeinander für eine nahtlose Navigation:

```
ROADMAP.md ←→ SPECIFICATION.md ←→ API.md
     ↕               ↕              ↕
TESTING.md  ←→  DATABASE.md ←→ DEPLOYMENT.md
```

## 🎯 Zielgruppen

- **Entwickler**: API.md, DATABASE.md, TESTING.md
- **DevOps/Operations**: DEPLOYMENT.md, TESTING.md
- **Projektmanagement**: ROADMAP.md, SPECIFICATION.md
- **Architekten**: SPECIFICATION.md, DATABASE.md, API.md

## 📝 Versionierung

Diese Spezifikationen werden kontinuierlich aktualisiert und sind synchron mit dem Hauptprojekt. Letzte Aktualisierung: September 2025.

## 🤝 Mitwirkung

Verbesserungen und Ergänzungen zu den Spezifikationen sind willkommen! Bitte erstelle einen Pull Request oder öffne ein Issue.

---

**📁 Übergeordnete Dokumentation**: [../README.md](../README.md)
**🏠 Projekt-Root**: [../../README.md](../../README.md)
