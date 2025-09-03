# PostgreSQL Integration Guide

## Überblick

Diese Anwendung nutzt PostgreSQL 16 als primäre Datenbank mit erweiterten Features für optimale Performance und Flexibilität bei BDEW-Datenoperationen.

## DevContainer-Setup

### Automatische PostgreSQL-Bereitstellung

Der DevContainer nutzt externe Features von `the78mole/devcontainer-features`:

```json
{
  "features": {
    "ghcr.io/the78mole/devcontainer-features/uv:1": {
      "version": "latest"
    },
    "ghcr.io/the78mole/devcontainer-features/postgresql:1": {
      "version": "16"
    }
  },
  "forwardPorts": [5432]
}
```

### Automatische Konfiguration

- **PostgreSQL 16**: Läuft automatisch beim Container-Start
- **Port**: 5432 (automatisch weitergeleitet)
- **Datenbank**: `vnbdigitaler` (automatisch erstellt)
- **User**: `postgres` (Trust-Authentifizierung für Entwicklung)
- **Extensions**: Automatische Installation von `pg_trgm`, `uuid-ossp`

## Datenbank-Architektur

### Schema-Design

```sql
-- BDEW-Unternehmen mit PostgreSQL-Features
CREATE TABLE bdew_companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    network_operator_id VARCHAR(20) UNIQUE NOT NULL,
    bdew_code VARCHAR(20) UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    company_name_normalized VARCHAR(255),

    -- Adressdaten
    street VARCHAR(255),
    postal_code VARCHAR(10),
    city VARCHAR(100),
    federal_state VARCHAR(50),

    -- Geo-Koordinaten für Spatial-Queries
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),

    -- JSONB für flexible Territorien-Speicherung
    service_territory JSONB,

    -- Qualitäts-Tracking
    data_quality_score INTEGER,
    is_active BOOLEAN DEFAULT true,

    -- Zeitstempel
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints für Datenqualität
    CONSTRAINT chk_quality_score CHECK (data_quality_score BETWEEN 0 AND 100),
    CONSTRAINT chk_coordinates CHECK (
        (latitude IS NULL AND longitude IS NULL) OR
        (latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)
    )
);
```

### Performance-Indices

```sql
-- Full-Text-Search für deutsche Sprache
CREATE INDEX idx_bdew_companies_fulltext_german
ON bdew_companies
USING gin(to_tsvector('german',
    COALESCE(company_name, '') || ' ' ||
    COALESCE(city, '') || ' ' ||
    COALESCE(federal_state, '')
));

-- Trigram-Index für Ähnlichkeitssuche
CREATE INDEX idx_bdew_companies_trgm_name
ON bdew_companies
USING gin(company_name_normalized gin_trgm_ops);

-- JSONB-Index für Territory-Queries
CREATE INDEX idx_bdew_companies_service_territory
ON bdew_companies
USING gin(service_territory);

-- Geo-Index für Location-Queries
CREATE INDEX idx_bdew_companies_location
ON bdew_companies (latitude, longitude)
WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
```

## Repository-Pattern

### Async Database Manager

```python
from database import DatabaseManager

# Singleton-Pattern für optimale Verbindungsnutzung
db_manager = DatabaseManager()

# Async Session Management
async with db_manager.get_session() as session:
    # Session wird automatisch geschlossen
    pass
```

### Repository-Operationen

```python
from repositories.bdew import BDEWRepository

async def example_operations():
    async with DatabaseManager().get_session() as session:
        repo = BDEWRepository(session)

        # Upsert mit PostgreSQL ON CONFLICT
        company, was_created = await repo.upsert_company({
            "network_operator_id": "9900000000001",
            "company_name": "Stadtwerke München",
            "service_territory": {
                "type": "Feature",
                "geometry": {...}
            }
        })

        # Full-Text-Suche
        results = await repo.search_companies_fulltext(
            search_term="Stadtwerke München",
            min_quality_score=80
        )

        # Geo-Proximity-Suche
        nearby = await repo.find_companies_by_location(
            latitude=48.1351,
            longitude=11.5820,
            radius_km=50
        )
```

## Erweiterte PostgreSQL-Features

### JSONB-Operationen

#### Service-Territory-Speicherung

```python
# GeoJSON-Territory speichern
territory = {
    "type": "Feature",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[11.4, 48.0], [11.7, 48.0], [11.7, 48.3], [11.4, 48.3], [11.4, 48.0]]]
    },
    "properties": {
        "name": "München Stadtgebiet",
        "population": 1487708,
        "area_km2": 310.7
    }
}

await repo.update_service_territory(company_id, territory)
```

#### JSONB-Queries

```sql
-- Unternehmen mit bestimmten Territory-Properties
SELECT * FROM bdew_companies
WHERE service_territory->'properties'->>'name' LIKE '%München%';

-- Territory-Area größer als Schwellenwert
SELECT * FROM bdew_companies
WHERE (service_territory->'properties'->'area_km2')::numeric > 100;
```

### Full-Text-Search

#### Deutsche Volltextsuche

```python
# Suche mit deutschem Stemming und Ranking
companies = await repo.search_companies_fulltext(
    search_term="Stadtwerke München Energie",
    limit=20,
    min_quality_score=70
)
```

#### SQL-Implementierung

```sql
SELECT *,
       ts_rank(
           to_tsvector('german', company_name || ' ' || city),
           plainto_tsquery('german', 'Stadtwerke München')
       ) as relevance
FROM bdew_companies
WHERE to_tsvector('german', company_name || ' ' || city)
      @@ plainto_tsquery('german', 'Stadtwerke München')
ORDER BY relevance DESC;
```

### Trigram-Ähnlichkeitssuche

```python
# Fuzzy-Matching für Unternehmensnamen
similar = await repo.find_similar_companies(
    company_name="Stadtwerke Muenchen",
    threshold=0.7
)
```

```sql
-- Nutzt pg_trgm Extension
SELECT *, similarity(company_name_normalized, 'stadtwerke muenchen') as sim
FROM bdew_companies
WHERE similarity(company_name_normalized, 'stadtwerke muenchen') > 0.7
ORDER BY sim DESC;
```

## Change Tracking & Auditing

### Automatisches Change-Tracking

```python
# Datenänderungen werden automatisch verfolgt
await repo.track_data_change(
    company_id=company.id,
    change_type="UPDATE",
    old_values={"company_name": "Alte Stadtwerke"},
    new_values={"company_name": "Neue Stadtwerke GmbH"},
    changed_by="import_system",
    import_log_id=log.id
)
```

### History-Tabelle

```sql
CREATE TABLE bdew_data_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES bdew_companies(id),
    change_type VARCHAR(20) NOT NULL, -- INSERT, UPDATE, DELETE
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],
    changed_by VARCHAR(255),
    change_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    import_log_id UUID REFERENCES bdew_import_logs(id)
);
```

## Import-Logs & Monitoring

### Erweiterte Import-Logs

```python
import_log = await repo.create_import_log({
    "file_name": "bdew_data_2025.csv",
    "file_hash": "sha256:abc123...",
    "import_status": "SUCCESS",
    "records_imported": 1500,
    "processing_time_seconds": 45.2,
    "file_size_bytes": 2048576,
    "import_metadata": {
        "source_system": "BDEW Portal",
        "data_version": "2025-Q1",
        "validation_rules_applied": ["email_format", "phone_format"]
    }
})
```

### Import-Statistiken

```python
stats = await repo.get_import_statistics(days=30)
# {
#   "total_imports": 15,
#   "successful_imports": 14,
#   "success_rate": 93.3,
#   "total_records_imported": 22500,
#   "average_processing_time": 42.1,
#   "total_data_processed_mb": 45.2
# }
```

## Datenqualitäts-Management

### Automatische Qualitäts-Bewertung

```python
def calculate_quality_score(company_data):
    """Berechne Datenqualitäts-Score (0-100)."""
    score = 0

    # Pflichtfelder (40 Punkte)
    if company_data.get('company_name'): score += 10
    if company_data.get('network_operator_id'): score += 10
    if company_data.get('city'): score += 10
    if company_data.get('federal_state'): score += 10

    # Kontaktdaten (30 Punkte)
    if company_data.get('email'): score += 10
    if company_data.get('phone'): score += 10
    if company_data.get('website'): score += 10

    # Geo-Daten (20 Punkte)
    if company_data.get('latitude') and company_data.get('longitude'):
        score += 20

    # Service-Territory (10 Punkte)
    if company_data.get('service_territory'): score += 10

    return min(score, 100)
```

### Qualitäts-Monitoring

```python
# Übersicht der Datenqualität
quality_stats = await repo.get_quality_distribution()
# {
#   "total_companies": 1500,
#   "average_quality_score": 85.2,
#   "median_quality_score": 88.0,
#   "high_quality_count": 1200,  # Score >= 80
#   "low_quality_count": 150,    # Score < 50
#   "with_coordinates_count": 1350,
#   "coordinate_coverage_percent": 90.0
# }
```

## Performance-Optimierung

### Connection Pooling

```python
# Automatisches Connection Pooling via SQLAlchemy
engine = create_async_engine(
    database_url,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600
)
```

### Query-Optimierung

1. **Indices nutzen**: Alle wichtigen Spalten sind indiziert
2. **JSONB-Queries**: Effiziente Abfragen auf JSONB-Daten
3. **Prepared Statements**: Automatisch via SQLAlchemy
4. **Connection Reuse**: Session-Management mit Context Managern

### Monitoring

```python
# Health Check
health = await repo.health_check()
# {
#   "database_connection": "healthy",
#   "total_companies": 1500,
#   "average_quality_score": 85.2,
#   "last_import": {
#     "timestamp": "2025-01-09T10:30:00Z",
#     "status": "SUCCESS"
#   },
#   "status": "healthy"
# }
```

## Migration & Backup

### Schema-Migrationen

```bash
# Neue Migration erstellen
alembic revision --autogenerate -m "Add new JSONB fields"

# Migration ausführen
alembic upgrade head
```

### Backup-Strategien

```bash
# Database Dump
pg_dump postgresql://postgres@localhost:5432/vnbdigitaler > backup.sql

# Backup mit Kompression
pg_dump postgresql://postgres@localhost:5432/vnbdigitaler | gzip > backup.sql.gz

# Restore
psql postgresql://postgres@localhost:5432/vnbdigitaler < backup.sql
```

## Troubleshooting

### Häufige Probleme

1. **Connection Timeout**

   ```python
   # Verbindungs-Pool-Einstellungen anpassen
   DATABASE_URL="postgresql+asyncpg://postgres@localhost:5432/vnbdigitaler?pool_timeout=60"
   ```

2. **JSONB-Queries langsam**

   ```sql
   -- Spezifische JSONB-Indices erstellen
   CREATE INDEX idx_specific_property
   ON bdew_companies USING gin((service_territory->'properties'));
   ```

3. **Full-Text-Search funktioniert nicht**

   ```sql
   -- Deutsche Language-Extension prüfen
   SELECT * FROM pg_ts_config WHERE cfgname = 'german';
   ```

### Debug-Modus

```python
# SQL-Logging aktivieren
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Database Debug-Informationen
async with db_manager.get_session() as session:
    result = await session.execute(text("SELECT version()"))
    print(f"PostgreSQL Version: {result.scalar()}")
```
