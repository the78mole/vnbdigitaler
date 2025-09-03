# Migration zur umfassenden BDEW-Architektur

## 🎯 Vision: Vollständige BDEW-Marktteilnehmer-Datenbasis

Basierend auf der Erkenntnis, dass BDEW eine umfassende Datenbasis aller Energiemarktakteure bereitstellt, schlagen wir eine erweiterte Architektur vor:

### 📊 Aktuelle Situation

- ✅ Fokus nur auf **Stromnetzbetreiber**
- ✅ Funktionierende Pipeline für Download/Import
- ✅ Basis-Datenmodell und Repository-Pattern
- ❌ **Beschränkt auf eine Rolle im Energiemarkt**

### 🚀 Ziel-Architektur

- 🎯 **Alle BDEW-Marktteilnehmer** als Basis
- 🎯 **Rollen-basierte Spezialisierung** (Netzbetreiber, Lieferanten, etc.)
- 🎯 **Cross-Reference zwischen Rollen** (Ein Unternehmen = Multiple Rollen)
- 🎯 **Verteilnetzbetreiber-spezifische Anreicherung** für Rollout-Daten

## 🔄 Migrations-Strategie

### Phase 1: Basis-Erweiterung (Sofort umsetzbar)

```python
# Erweitere bestehende BDEWCompany um Rollen-Konzept
class BDEWCompany:
    # Bestehende Felder bleiben
    company_name = Column(String(255), nullable=False)
    network_operator_id = Column(String(50), unique=True)  # Wird optional

    # NEU: Rollen-Support
    primary_role = Column(String(50), index=True)          # Hauptrolle
    additional_roles = Column(JSON)                         # Zusätzliche Rollen
    company_type = Column(String(50), index=True)          # Stadtwerk, Regional, etc.

    # NEU: Erweiterte Identifikatoren
    bdew_code = Column(String(50), unique=True, index=True)  # Haupt-BDEW-Code
    role_specific_codes = Column(JSON)                       # Rollen-spezifische Codes
```

### Phase 2: Multi-Endpoint Data Source (2-3 Wochen)

```python
# Erweitere bestehende BDEWWebDataSource
class BDEWMultiRoleDataSource(BDEWWebDataSource):
    ENDPOINTS = {
        'stromnetzbetreiber': 'https://bdew-codes.de/.../GetElectricityList',
        'gasnetzbetreiber': 'https://bdew-codes.de/.../GetGasList',          # TBD
        'marktteilnehmer': 'https://bdew-codes.de/.../GetMarketParticipants'  # TBD
    }

    async def fetch_all_roles(self) -> Dict[str, List[Dict]]:
        """Lädt alle verfügbaren BDEW-Marktteilnehmer-Kategorien"""
```

### Phase 3: Spezialisierte Anreicherung (3-4 Wochen)

```python
# Neue Tabelle für Verteilnetzbetreiber-Details
class BDEWGridOperatorDetail(Base):
    company_id = Column(UUID, ForeignKey('bdew_companies.id'))

    # Rollout-spezifische Daten
    smart_meter_rollout_start = Column(DateTime)
    rollout_plan_url = Column(String(500))
    total_metering_points = Column(Integer)

    # vnbdigital.de Integration
    vnbdigital_data = Column(JSON)
```

## 🛠 Praktische Umsetzung

### Schritt 1: Website-Analyse

```bash
# Untersuche alle verfügbaren BDEW-Endpunkte
vnbdigitaler bdew discover --analyze-endpoints --save-structure
```

### Schritt 2: Bestehende Pipeline erweitern

```python
# Erweitere CLI um Multi-Role-Support
vnbdigitaler bdew import --roles="stromnetzbetreiber,gasnetzbetreiber"
vnbdigitaler bdew import --all-roles
vnbdigitaler bdew search --role="verteilnetzbetreiber" "stadtwerke"
```

### Schritt 3: Datenmodell migrieren

```sql
-- Migration Script
ALTER TABLE bdew_companies ADD COLUMN primary_role VARCHAR(50);
ALTER TABLE bdew_companies ADD COLUMN additional_roles JSON;
ALTER TABLE bdew_companies ADD COLUMN company_type VARCHAR(50);
ALTER TABLE bdew_companies ADD COLUMN bdew_code VARCHAR(50) UNIQUE;

-- Index für Performance
CREATE INDEX idx_bdew_companies_role ON bdew_companies(primary_role);
CREATE INDEX idx_bdew_companies_type ON bdew_companies(company_type);
```

## 📋 Konkrete nächste Schritte

### 1. **Website-Endpunkt-Analyse** (Diese Woche)

- [ ] Alle verfügbaren BDEW-API-Endpunkte identifizieren
- [ ] Parameter und Datenstrukturen dokumentieren
- [ ] Test-Abfragen für verschiedene Marktteilnehmer-Kategorien

### 2. **Datenmodell-Erweiterung** (Nächste Woche)

- [ ] Migration Script für bestehende Datenbank
- [ ] Erweiterte BDEWCompany-Klasse
- [ ] Rollen-Enum definieren
- [ ] Tests für erweiterte Struktur

### 3. **Multi-Endpoint Data Source** (Folgewoche)

- [ ] BDEWMultiRoleDataSource implementieren
- [ ] Pipeline für verschiedene Endpunkte
- [ ] Daten-Normalisierung und -Vereinheitlichung
- [ ] Rolle-zu-Unternehmen-Zuordnung

### 4. **CLI-Erweiterung** (Danach)

- [ ] Multi-Role-Import-Kommandos
- [ ] Rollen-spezifische Suche und Statistiken
- [ ] Marktstruktur-Analyse-Tools

## 💡 Vorteile der erweiterten Architektur

### Für das aktuelle Projekt

- ✅ **Vollständige Datenbasis**: Alle Energiemarktakteure, nicht nur Netzbetreiber
- ✅ **Bessere Datenqualität**: Cross-Validation zwischen verschiedenen Rollen
- ✅ **Umfassende Marktanalyse**: Verstehen der gesamten Energiemarktstruktur

### Für zukünftige Entwicklung

- 🚀 **Skalierbarkeit**: Einfache Erweiterung um neue Marktteilnehmer-Kategorien
- 🚀 **Integration**: Basis für weitere Energiemarkt-Datenquellen
- 🚀 **Analytics**: Marktkonzentration, Unternehmensgruppen, geografische Verteilung

## 🎯 Quick Win: Sofortige Implementierung

**Diese Woche umsetzbar:**

```python
# Erweitere bestehende CLI um Endpunkt-Analyse
vnbdigitaler bdew discover --url="https://bdew-codes.de/Codenumbers/BDEWCodes/CodeOverview"

# Analysiere verfügbare Datenquellen
vnbdigitaler bdew analyze-endpoints --dry-run --verbose
```

**Ergebnis:** Vollständige Übersicht aller BDEW-Datenquellen als Basis für die Architektur-Erweiterung!

---

**Fazit:** Diese erweiterte Architektur macht vnbdigitaler zur umfassenden Plattform für alle deutschen Energiemarktakteure - nicht nur Verteilnetzbetreiber! 🎯
