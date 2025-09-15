# 🛣️ VNB Digitaler - Roadmap

> **Transparenz für den deutschen Energiemarkt durch Open-Source-Datenintegration**

## 📅 Aktuelle Phase

**Stand: September 2025** - Phase 2: Core Data Integration 🔄

---

## 🎯 Phasen-Übersicht

### ✅ Phase 1: Foundation (Abgeschlossen)

**Zeitrahmen**: Q1-Q2 2025
**Status**: Produktiv

**Deliverables:**

- [x] Basis-Pipeline-Architektur
- [x] GitHub Actions CI/CD
- [x] Docker-Containerisierung
- [x] Neon PostgreSQL Setup
- [x] Grundlegende Datenmodelle
- [x] uv Package Management

**Technische Basis:**

- Python 3.11+ Stack
- FastAPI + Streamlit
- PostgreSQL 16 (Neon)
- GitHub Actions
- Docker Compose

---

### 🔄 Phase 2: Core Data Integration (Aktuell)

**Zeitrahmen**: Q3-Q4 2025
**Status**: In Entwicklung

**Deliverables:**

- [x] BDEW-Stromnetzbetreiber-Import
- [x] BNetzA-Smart-Meter-Rollout-Daten
- [ ] Fuzzy-Matching-Algorithmus (BDEW ↔ BNetzA)
- [ ] Geografische Datenvalidierung
- [ ] Basis-API-Endpunkte
- [ ] Datenqualitäts-Pipeline

**Aktuelle Arbeitspakete:**

- Verbesserung der Datenverknüpfung
- Performance-Optimierung für große Datensätze
- Implementierung der Geo-Validierung
- API-Endpunkt-Entwicklung

---

### 📊 Phase 2.5: Data-Admin-WebUI (Geplant)

**Zeitrahmen**: Q4 2025
**Status**: Design Phase

**Deliverables:**

- [ ] FastAPI-Backend für Admin-Interface (Port 8081)
- [ ] Data-Explorer-Dashboard
- [ ] BDEW vs. BNetzA Verknüpfungs-Validierung
- [ ] Geo-Informationen Viewer und Editor
- [ ] Data-Quality-Monitoring-Interface
- [ ] Manuelle Datenkorrektur-Tools
- [ ] Data-Release-Kontrolle

**Technische Features:**

- Separater Admin-Service
- Responsive Dashboard mit AG-Grid
- Interaktive Geo-Maps (Leaflet)
- Bulk-Edit-Operationen
- Admin-Authentifizierung

---

### 💰 Phase 3: Price Transparency

**Zeitrahmen**: Q1 2026
**Status**: Planung

**Deliverables:**

- [ ] Netzbetreiber-Website-Crawling
- [ ] PDF-Preisblatt-Extraktion (§14a-Preise)
- [ ] Preis-Normalisierung und -Validierung
- [ ] Preisvergleichs-Engine
- [ ] Historische Preisentwicklung
- [ ] Price-Alert-System

**Technische Herausforderungen:**

- KI-gestützte PDF-Extraktion
- Anti-Bot-Maßnahmen umgehen
- Preisdaten-Standardisierung
- Performance bei großen Datenmengen

---

### 🌐 Phase 4: Public Portal

**Zeitrahmen**: Q1-Q2 2026
**Status**: Konzeption

**Deliverables:**

- [ ] Streamlit-Weboberfläche (Read-Only Portal)
- [ ] Interaktive Karten (Netzgebiete & Rollout-Status)
- [ ] Erweiterte Suchfunktionen
- [ ] Datenexport-Features (CSV, JSON, API)
- [ ] Responsive Design für hohe Nutzerzahlen
- [ ] SEO-Optimierung

**Zielgruppen:**

- Endverbraucher
- Journalisten & Analysten
- Forscher & Studenten
- Entwickler (API-Nutzer)

---

### ⚡ Phase 5: Installer Services

**Zeitrahmen**: Q2-Q3 2026
**Status**: Research

**Deliverables:**

- [ ] Separate Installateur-Web-App (React/Next.js)
- [ ] OAuth2-Benutzerauthentifizierung
- [ ] Automatische Gasteintragungs-Workflows
- [ ] TAB-Dokumentenverwaltung
- [ ] Installateur-Dashboard mit Projektmanagement
- [ ] Fristenerinnerungen und Notifications
- [ ] Integration mit VNB-Systemen

**Business Value:**

- Digitalisierung der Installateur-Workflows
- Reduktion manueller Prozesse
- Verbesserung der Kommunikation VNB ↔ Installateur

---

### 🚀 Phase 6: Advanced Features

**Zeitrahmen**: Q3-Q4 2026
**Status**: Vision

**Deliverables:**

- [ ] KI-gestützte Datenextraktion (LLM-basiert)
- [ ] Predictive Analytics für Rollout-Prognosen
- [ ] API-Marketplace für Drittanbieter
- [ ] Mobile App (React Native)
- [ ] Machine Learning für Preisprediction
- [ ] Real-time Data Streaming

**Innovation Bereiche:**

- Large Language Models für Dokumentenanalyse
- Zeitreihenanalyse für Marktprognosen
- Edge Computing für Performance
- Blockchain für Datenintegrität

---

## 🎯 Meilensteine 2025-2026

### Q4 2025

- **Oktober**: Data-Admin-WebUI MVP
- **November**: BDEW-BNetzA-Verknüpfung optimiert
- **Dezember**: Erste §14a-Preisdaten integriert

### Q1 2026

- **Januar**: Public Portal Beta
- **Februar**: Price Transparency MVP
- **März**: First Public Release

### Q2 2026

- **April**: Installer Services Alpha
- **Mai**: Mobile-optimierte Oberfläche
- **Juni**: API v1.0 Launch

### Q3 2026

- **Juli**: Installer Dashboard Beta
- **August**: KI-Features Integration
- **September**: Performance-Optimierung

### Q4 2026

- **Oktober**: Advanced Analytics
- **November**: API Marketplace
- **Dezember**: Version 2.0 Release

---

## 📊 Success Metrics

### Technische KPIs

| Metrik            | Q4 2025 | Q2 2026 | Q4 2026 |
| ----------------- | ------- | ------- | ------- |
| Datenqualität     | >90%    | >95%    | >98%    |
| API Response Time | <3s     | <2s     | <1s     |
| Uptime            | >99%    | >99.5%  | >99.9%  |
| Test Coverage     | >85%    | >90%    | >95%    |

### Business KPIs

| Metrik                | Q4 2025 | Q2 2026 | Q4 2026 |
| --------------------- | ------- | ------- | ------- |
| Aktive Nutzer/Monat   | 1,000   | 5,000   | 15,000  |
| VNB-Abdeckung         | 70%     | 85%     | 95%     |
| API Calls/Monat       | 100K    | 500K    | 2M      |
| Partner-Integrationen | 0       | 3       | 10      |

### Impact KPIs

- **Transparenz**: Verfügbare Preisvergleiche
- **Effizienz**: Zeitersparnis für Installateure
- **Adoption**: GitHub Stars & Community Growth
- **Innovation**: Neue Use Cases durch API

---

## 🚧 Aktuelle Blocker & Risiken

### Technische Risiken

- **BDEW-API-Stabilität**: Monitoring & Fallback-Strategien
- **PDF-Extraktion-Genauigkeit**: ML-Training erforderlich
- **Performance bei Scale**: Load Testing geplant Q4 2025

### Regulatorische Risiken

- **Datenschutz-Compliance**: Privacy by Design implementiert
- **Urheberrecht bei Preisdaten**: Legal Review Q4 2025
- **VNB-Kooperation**: Stakeholder-Management verstärken

### Business Risiken

- **Finanzierung**: Open Source + Revenue Streams Model
- **Marktakzeptanz**: User Research & MVP-Feedback
- **Konkurrenz**: Community Building & Innovation fokus

---

## 🤝 Community & Contributions

### Wie beitragen?

1. **Issues & Bug Reports**: GitHub Issues verwenden
2. **Feature Requests**: Roadmap-Diskussionen in GitHub
3. **Code Contributions**: Pull Requests willkommen
4. **Dokumentation**: Wiki & Tutorials erweitern
5. **Testing**: Beta-Testing & Feedback

### Contributor Guidelines

- **Code Quality**: 95% Test Coverage erforderlich
- **Documentation**: Änderungen dokumentieren
- **Performance**: Benchmarks bei API-Änderungen
- **Security**: Security Reviews für kritische Features

---

## 📚 Ressourcen

### Dokumentation

- [SPECIFICATION.md](./SPECIFICATION.md) - Vollständige technische Spezifikation
- [COPILOT_INSTRUCTIONS.md](./COPILOT_INSTRUCTIONS.md) - Projekt-Kontext
- [README.md](./README.md) - Projekt-Übersicht

### APIs & Datenquellen

- [BDEW-Codes](https://bdew-codes.de/)
- [BNetzA Smart-Meter-Rollout](https://www.bundesnetzagentur.de/DE/Sachgebiete/ElektrizitaetundGas/Unternehmen_Institutionen/DatenaustauschundMonitoring/SmartMeterRollout/start.html)
- [VNB Digital API](https://vnbdigital.de/)

### Technologie-Stack

- **Backend**: FastAPI, Python 3.11+, PostgreSQL
- **Frontend**: Streamlit (Portal), React (Installer-App)
- **Infrastructure**: Docker, GitHub Actions, Neon Database
- **Monitoring**: Native Logging + Health Checks

---

**🎯 Vision**: Bis Ende 2026 die führende Open-Source-Plattform für Transparenz im deutschen Energiemarkt zu werden und Installateuren, Verbrauchern und Forschern gleichermaßen zu dienen.

---

## 📝 Letzte Aktualisierung

**Letzte Aktualisierung**: September 2025
**Nächste Review**: Oktober 2025
