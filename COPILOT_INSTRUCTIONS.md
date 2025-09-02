# VNB Digitaler - Copilot Instructions

## 🎯 Projekt-Überblick

**VNB Digitaler** ist eine Streamlit-Anwendung zur Verwaltung und Analyse von deutschen Verteilnetzbetreiber-Daten (VNB) mit Fokus auf Smart-Meter-Rollout-Management.

## 🏗️ Architektur-Prinzipien

- **Einfachheit**: Bevorzuge klare, verständliche Lösungen
- **Modularität**: Separate Verantwortlichkeiten in eigene Module
- **Datenintegrität**: Sichere und konsistente Datenverarbeitung
- **Performance**: Effiziente Verarbeitung großer Datensätze

## 📊 Datenaktualisierung - Neuorganisation

### Aktuelle Herausforderung

Die bestehenden Datenaktualisierungsschritte müssen von Grund auf neu organisiert werden.
Die WebUI ist schon zu großen Teilen korrekt und funktionsfähig.
Viele der archivierten Scripten enthalten schon Teile einer sehr guten Implementierung,
passen aber nicht ganz zu einen reibungslosen Workflow, der letztlich auch in GitHub
Actions Workflows integriert werden kann.

### Ziel-Architektur für Datenaktualisierung

```
📥 Datenquellen
├── 🏢 BDEW (Stammdaten)
├── 📊 BNetzA (Rollout-Berichte)
└── 🗺️ VNB Digital (Territorien)
     ↓
🔄 Datenverarbeitung
├── 📋 Extraktion
├── 🔍 Validierung
├── 🔀 Transformation
└── 💾 Import
     ↓
🎯 Anwendung
├── 📱 Streamlit UI (für Datenzugriff durch externe User)
└── 🔌 FastAPI: WebUI + REST API (für Verwaltungsaufgaben)
```

### Prioritäten für Neuimplementierung

1. **Datenquellen-Management**
   - Einheitliche Schnittstellen für alle Datenquellen
   - Automatische Erkennung von Datenänderungen
   - Robuste Fehlerbehandlung

2. **Verarbeitungs-Pipeline**
   - Modulare Verarbeitungsschritte
   - Transaktionale Sicherheit
   - Logging und Monitoring

3. **Rollout-Daten-Workflow**
   - Quartalsweise Aktualisierung
     - Quartalsreports werden teils nachaktualisiert (gleicher Filename, anderer ETag)
   - Historische Datenarchivierung
   - Validierung gegen Stammdaten

## 🛠️ Technische Guidelines

### Code-Organisation

```
src/
├── data_sources/          # Datenquellen-Adapter
│   ├── bdew.py           # BDEW-Integration
│   ├── bnetza.py         # BNetzA-Integration
│   └── vnb_digital.py    # VNB Digital API
├── processors/           # Datenverarbeitung
│   ├── extractors/       # Daten-Extraktion
│   ├── validators/       # Datenvalidierung
│   └── transformers/     # Daten-Transformation
├── pipelines/            # Verarbeitungs-Pipelines
└── models/               # Datenmodelle
```

### Entwicklungs-Workflow

1. **Datenquelle analysieren** → Adapter entwickeln
2. **Verarbeitung definieren** → Pipeline implementieren
3. **Validierung sicherstellen** → Tests schreiben
4. **Integration testen** → End-to-End Tests

### Code-Standards

- **Type Hints**: Verwende Python Type Hints für alle Funktionen
- **Error Handling**: Explizite Exception-Behandlung
- **Logging**: Strukturiertes Logging für alle Verarbeitungsschritte
- **Documentation**: Docstrings für alle öffentlichen Funktionen

## 🔄 Datenaktualisierung - Implementierungsplan

### Phase 1: Grundlagen

- [ ] Datenquellen-Interfaces definieren
- [ ] Basis-Pipeline-Architektur erstellen
- [ ] Logging-Framework einrichten

### Phase 2: BDEW-Integration

- [ ] BDEW-Adapter implementieren
- [ ] Stammdaten-Import-Pipeline
- [ ] Validierung gegen bestehende Daten

### Phase 3: Anreicherung der BDEW-Daten aus vnbdigital

- [ ] Datenanreicherungs-Logik implementieren
- [ ] Integration der vnbdigital GraphQL-API (beschränkt)
- [ ] Konvertierung der Layer-Daten von vnbdigital in GeoJSON
- [ ] Anreicherung der GeoDaten mittels Adresslokalisierung

### Phase 4: BNetzA-Integration

- [ ] BNetzA-Rollout-Daten-Adapter
- [ ] Quartalsweise Update-Pipeline
- [ ] Historische Datenarchivierung

### Phase 5: Optimierung

- [ ] Performance-Optimierung
- [ ] Monitoring und Alerting
- [ ] Automatisierung

## 🧪 Testing-Strategie

### Unit Tests

- Jeder Adapter hat eigene Tests
- Mock externe Datenquellen
- Validierung der Datenverarbeitung

### Integration Tests

- End-to-End Pipeline-Tests
- Datenbank-Integration
- API-Endpoint-Tests

### Data Quality Tests

- Datenvalidierung und -konsistenz
- Historische Datenvergleiche
- Performance-Benchmarks

## 📝 Entwicklungs-Guidelines für Copilot

### Bei Datenaktualisierung

1. **Immer zuerst fragen**: "Welche Datenquelle wird aktualisiert?"
2. **Validierung priorisieren**: Stelle sicher, dass Daten validiert werden
3. **Transaktional denken**: Atomare Operationen für Datenänderungen
4. **Logging hinzufügen**: Jeder Verarbeitungsschritt soll geloggt werden

### Code-Stil

- Verwende aussagekräftige Funktions- und Variablennamen
- Kleine, fokussierte Funktionen (max. 20-30 Zeilen)
- Explicit ist besser als implicit
- Dokumentiere komplexe Geschäftslogik

### Fehlerbehandlung

- Verwende spezifische Exception-Typen
- Logge Fehler mit Kontext-Informationen
- Graceful Degradation wo möglich
- Nie silent failures

## 🎯 Ziele für die Neuorganisation

1. **Klarheit**: Verständliche Datenflüsse
2. **Zuverlässigkeit**: Robuste Fehlerbehandlung
3. **Wartbarkeit**: Modularer, testbarer Code
4. **Performance**: Effiziente Datenverarbeitung
5. **Monitoring**: Vollständige Observability

---

*Diese Anweisungen sind ein lebendiges Dokument und sollen bei Bedarf aktualisiert werden.*
