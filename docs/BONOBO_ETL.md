# VNB Digitaler - Bonobo ETL Framework Integration

> **📋 Zurück zur Hauptspezifikation**: [SPECIFICATION.md](./specs/SPECIFICATION.md) > **🗄️ Datenbank-Schema**: [DATABASE.md](./specs/DATABASE.md) > **🧪 Pipeline-Tests**: [TESTING.md](./TESTING.md)

## 🚀 Warum Bonobo?

Bonobo ist ein leichtgewichtiges, Python-natives ETL-Framework, das perfekt zu unserem VNB Digitaler Projekt passt:

### ✅ Vorteile gegenüber komplexeren Lösungen

- **Einfachheit**: Minimale Abhängigkeiten, keine komplexe Konfiguration
- **Python-nativ**: Nahtlose Integration mit unserem FastAPI/Streamlit Stack
- **Testbarkeit**: Jeder ETL-Node ist isoliert und einfach testbar
- **Flexibilität**: Modulare Pipeline-Graphen, einfache Erweiterung
- **Performance**: Built-in Parallelisierung und Stream-Processing
- **Deployment**: Läuft überall wo Python läuft - von Cron-Jobs bis Docker

### 🆚 Vergleich mit anderen ETL-Frameworks

| Feature                | Bonobo           | Prefect      | Airflow             | Luigi       |
| ---------------------- | ---------------- | ------------ | ------------------- | ----------- |
| **Komplexität**        | ⭐ Minimal       | ⭐⭐⭐ Hoch  | ⭐⭐⭐⭐ Sehr hoch  | ⭐⭐ Mittel |
| **Setup-Zeit**         | < 5 Min          | 30+ Min      | 2+ Stunden          | 20+ Min     |
| **Dependencies**       | 3-5              | 50+          | 100+                | 20+         |
| **Learning Curve**     | ⭐ Flach         | ⭐⭐⭐ Steil | ⭐⭐⭐⭐ Sehr steil | ⭐⭐ Mittel |
| **Docker Integration** | ⭐⭐⭐ Nativ     | ⭐⭐ Gut     | ⭐⭐ Gut            | ⭐⭐ Gut    |
| **Testing**            | ⭐⭐⭐ Exzellent | ⭐⭐ Gut     | ⭐ Basic            | ⭐⭐ Gut    |

## 🏗️ Bonobo ETL-Architektur

### Pipeline-Struktur

```python
import bonobo
from bonobo_sqlalchemy import Select, InsertOrUpdate

def get_bdew_sync_graph(**options):
    """Hauptpipeline für BDEW-Daten-Synchronisation."""

    return bonobo.Graph(
        # ======= EXTRACT =======
        extract_bdew_companies,

        # ======= TRANSFORM =======
        validate_bdew_format,
        normalize_company_names,
        enrich_with_geographic_data,
        detect_duplicates,

        # ======= LOAD =======
        upsert_companies_to_db,

        # ======= MONITOR =======
        log_sync_statistics,
        send_completion_notification,
    )
```

### Modulare Node-Bibliothek

```
src/etl/
├── __init__.py
├── nodes/
│   ├── __init__.py
│   ├── extractors/
│   │   ├── bdew_extractor.py
│   │   ├── bnetza_extractor.py
│   │   ├── website_scraper.py
│   │   └── pdf_processor.py
│   ├── transformers/
│   │   ├── validators.py
│   │   ├── normalizers.py
│   │   ├── enrichers.py
│   │   └── aggregators.py
│   ├── loaders/
│   │   ├── database_loader.py
│   │   ├── storage_loader.py
│   │   └── cache_loader.py
│   └── monitors/
│       ├── quality_checker.py
│       ├── statistics.py
│       └── notifications.py
├── graphs/
│   ├── __init__.py
│   ├── bdew_sync.py
│   ├── bnetza_rollout.py
│   ├── price_scraping.py
│   └── quality_control.py
└── utils/
    ├── __init__.py
    ├── database.py
    ├── storage.py
    └── config.py
```

## 📋 ETL-Pipeline-Katalog

### 1. BDEW Marktteilnehmer-Synchronisation

```python
# src/etl/graphs/bdew_sync.py

import bonobo
from ..nodes.extractors.bdew_extractor import extract_bdew_companies
from ..nodes.transformers.validators import validate_company_data
from ..nodes.transformers.normalizers import normalize_addresses
from ..nodes.loaders.database_loader import upsert_companies

def get_bdew_sync_graph(**options):
    """
    Tägliche Synchronisation der BDEW-Marktteilnehmer-Daten.

    Verarbeitet:
    - Unternehmensstammdaten
    - BDEW-Codes und Rollen
    - Adress-Normalisierung
    - Geo-Koordinaten-Anreicherung
    """

    return bonobo.Graph(
        # Extract from BDEW API
        extract_bdew_companies,

        # Data Quality & Validation
        validate_company_data,
        bonobo.Filter(lambda x: x.get('valid', False)),

        # Normalization
        normalize_addresses,
        enrich_with_coordinates,

        # Duplicate Detection
        detect_company_duplicates,

        # Database Operations
        upsert_companies,
        update_company_roles,

        # Quality Monitoring
        calculate_sync_statistics,
        log_data_quality_metrics,

        # Notifications
        send_sync_completion_email.use(
            smtp_config=options.get('smtp_config')
        ),
    )

# Ausführung
if __name__ == '__main__':
    with bonobo.parse_args() as options:
        bonobo.run(get_bdew_sync_graph(**options))
```

### 2. BNetzA Smart-Meter-Rollout-Integration

```python
# src/etl/graphs/bnetza_rollout.py

def get_bnetza_rollout_graph(**options):
    """
    Quarterly Update der BNetzA Smart-Meter-Rollout-Daten.

    Verarbeitet:
    - Rollout-Quoten pro Netzbetreiber
    - Zeitpläne und Fortschrittsdaten
    - Verknüpfung mit BDEW-Unternehmensdaten
    """

    return bonobo.Graph(
        # Extract from BNetzA
        extract_rollout_data,
        parse_excel_rollout_files,

        # Data Cleaning
        clean_rollout_percentages,
        validate_rollout_dates,

        # Linking with BDEW data
        match_with_bdew_companies,
        resolve_company_name_variations,

        # Database Operations
        upsert_rollout_data,
        update_rollout_statistics,

        # Analytics
        calculate_rollout_trends,
        generate_rollout_insights,

        # Storage
        export_rollout_summary_csv,
        backup_to_r2_storage,
    )
```

### 3. Website-Scraping für Preisblätter

```python
# src/etl/graphs/price_scraping.py

def get_price_scraping_graph(**options):
    """
    Wöchentliches Scraping von VNB-Websites für Preisblätter.

    Verarbeitet:
    - PDF-Download von VNB-Websites
    - Text-Extraktion aus PDFs
    - Preis-Pattern-Erkennung
    - Cloudflare R2-Speicherung
    """

    return bonobo.Graph(
        # Get VNB list for scraping
        get_vnb_websites_for_scraping,

        # Web Scraping
        scrape_vnb_price_pages,
        download_price_pdfs,

        # PDF Processing
        extract_text_from_pdfs,
        parse_price_information,
        validate_price_data,

        # Storage & Backup
        upload_pdfs_to_r2,
        store_price_metadata,

        # Quality Control
        detect_price_anomalies,
        flag_outdated_prices,

        # Notifications
        notify_admin_of_failures,
        report_scraping_statistics,
    )
```

## 🔧 Deployment & Scheduling

### Docker Integration

```dockerfile
# Dockerfile.etl
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy ETL code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Set up cron for scheduling
RUN apt-get update && apt-get install -y cron
COPY crontab /etc/cron.d/etl-jobs
RUN chmod 0644 /etc/cron.d/etl-jobs
RUN crontab /etc/cron.d/etl-jobs

# Entry point
CMD ["cron", "-f"]
```

### Cron-basiertes Scheduling

```bash
# crontab - ETL Job Scheduling

# BDEW Daily Sync (jeden Tag um 2:00 Uhr)
0 2 * * * /app/scripts/run_etl.sh bdew_sync >> /var/log/etl/bdew_sync.log 2>&1

# Website Scraping (jeden Sonntag um 3:00 Uhr)
0 3 * * 0 /app/scripts/run_etl.sh price_scraping >> /var/log/etl/price_scraping.log 2>&1

# BNetzA Rollout Update (am 1. jeden Monats um 4:00 Uhr)
0 4 1 * * /app/scripts/run_etl.sh bnetza_rollout >> /var/log/etl/bnetza_rollout.log 2>&1

# Data Quality Check (täglich um 6:00 Uhr)
0 6 * * * /app/scripts/run_etl.sh quality_control >> /var/log/etl/quality_control.log 2>&1
```

### ETL-Ausführungs-Script

```bash
#!/bin/bash
# scripts/run_etl.sh

set -e

ETL_JOB=$1
LOG_DIR="/var/log/etl"
CONFIG_FILE="/app/config/etl_config.yaml"

# Logging setup
mkdir -p $LOG_DIR
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
LOG_FILE="$LOG_DIR/${ETL_JOB}_${TIMESTAMP}.log"

echo "Starting ETL job: $ETL_JOB" | tee -a $LOG_FILE

case $ETL_JOB in
    "bdew_sync")
        cd /app && python -m src.etl.graphs.bdew_sync --config $CONFIG_FILE
        ;;
    "price_scraping")
        cd /app && python -m src.etl.graphs.price_scraping --config $CONFIG_FILE
        ;;
    "bnetza_rollout")
        cd /app && python -m src.etl.graphs.bnetza_rollout --config $CONFIG_FILE
        ;;
    "quality_control")
        cd /app && python -m src.etl.graphs.quality_control --config $CONFIG_FILE
        ;;
    *)
        echo "Unknown ETL job: $ETL_JOB" | tee -a $LOG_FILE
        exit 1
        ;;
esac

echo "ETL job completed: $ETL_JOB" | tee -a $LOG_FILE
```

## 🧪 Testing & Quality Assurance

### Unit Testing für ETL-Nodes

```python
# tests/etl/test_bdew_extractor.py

import pytest
import bonobo
from src.etl.nodes.extractors.bdew_extractor import extract_bdew_companies

def test_extract_bdew_companies_valid_response(mock_bdew_api):
    """Test BDEW extraction with valid API response."""

    # Mock API response
    mock_bdew_api.return_value = [
        {
            'company_name': 'Test VNB GmbH',
            'bdew_code': '1234567890123',
            'address': 'Teststraße 1, 12345 Teststadt'
        }
    ]

    # Execute extraction
    result = list(extract_bdew_companies())

    # Assertions
    assert len(result) == 1
    assert result[0]['company_name'] == 'Test VNB GmbH'
    assert len(result[0]['bdew_code']) == 13

def test_extract_bdew_companies_empty_response(mock_bdew_api):
    """Test BDEW extraction with empty API response."""

    mock_bdew_api.return_value = []
    result = list(extract_bdew_companies())

    assert len(result) == 0
```

### Integration Testing für Pipelines

```python
# tests/etl/test_integration.py

import pytest
import bonobo
from src.etl.graphs.bdew_sync import get_bdew_sync_graph

@pytest.mark.integration
def test_bdew_sync_pipeline_end_to_end(test_database, mock_apis):
    """Test complete BDEW sync pipeline."""

    # Setup test data
    mock_apis.bdew.return_value = [
        {'company_name': 'Test VNB', 'bdew_code': '1234567890123'}
    ]

    # Execute pipeline
    with bonobo.parse_args([]) as options:
        options['database_url'] = test_database.url
        bonobo.run(get_bdew_sync_graph(**options))

    # Verify results
    companies = test_database.query("SELECT * FROM companies")
    assert len(companies) == 1
    assert companies[0]['company_name'] == 'Test VNB'
```

### Performance & Load Testing

```python
# tests/etl/test_performance.py

import pytest
import time
from src.etl.graphs.bdew_sync import get_bdew_sync_graph

@pytest.mark.performance
def test_bdew_sync_performance_large_dataset():
    """Test pipeline performance with large dataset."""

    start_time = time.time()

    # Generate large test dataset (10k companies)
    large_dataset = generate_test_companies(10000)

    # Execute pipeline
    with bonobo.parse_args([]) as options:
        bonobo.run(get_bdew_sync_graph(**options))

    execution_time = time.time() - start_time

    # Performance assertions
    assert execution_time < 300  # Should complete within 5 minutes
    assert memory_usage < 500_000_000  # Should use less than 500MB RAM
```

## 📊 Monitoring & Observability

### Pipeline-Metriken

```python
# src/etl/nodes/monitors/statistics.py

import bonobo
from datetime import datetime
import logging

@bonobo.config.use_context
def log_pipeline_statistics(context):
    """Node für Pipeline-Statistiken und Monitoring."""

    def log_stats(fs, **kwargs):
        # Sammle Pipeline-Statistiken
        total_processed = context.get_input_count()
        total_output = context.get_output_count()
        processing_time = context.get_execution_time()

        stats = {
            'pipeline_name': context.get_graph().name,
            'timestamp': datetime.now().isoformat(),
            'records_processed': total_processed,
            'records_output': total_output,
            'processing_time_seconds': processing_time,
            'throughput_per_second': total_processed / processing_time if processing_time > 0 else 0,
            'success_rate': (total_output / total_processed * 100) if total_processed > 0 else 0
        }

        # Log as structured JSON
        logging.info("Pipeline Statistics", extra=stats)

        # Optional: Send to monitoring system
        send_metrics_to_grafana(stats)

        yield stats

    return log_stats
```

### Fehler-Handling & Retry-Logik

```python
# src/etl/utils/error_handling.py

import bonobo
import logging
from functools import wraps
from time import sleep

def with_retry(max_retries=3, delay=1):
    """Decorator für automatische Retry-Logik."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logging.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}"
                    )

                    if attempt < max_retries - 1:
                        sleep(delay * (2 ** attempt))  # Exponential backoff

            # All retries failed
            logging.error(f"All {max_retries} attempts failed for {func.__name__}")
            raise last_exception

        return wrapper
    return decorator

@with_retry(max_retries=3, delay=2)
def extract_from_api(api_url):
    """Extractor mit automatischer Retry-Logik."""
    response = requests.get(api_url, timeout=30)
    response.raise_for_status()
    return response.json()
```

## 🚀 Migration von Prefect zu Bonobo

### Prefect vs. Bonobo Konzept-Mapping

| Prefect Konzept | Bonobo Äquivalent         | Migration Notes              |
| --------------- | ------------------------- | ---------------------------- |
| `@flow`         | `bonobo.Graph()`          | Pipeline-Definition          |
| `@task`         | Python-Funktion + `yield` | Node-Implementation          |
| Flow Run        | `bonobo.run(graph)`       | Pipeline-Ausführung          |
| Deployment      | Cron + Docker             | Vereinfachtes Scheduling     |
| Work Pools      | Nicht benötigt            | Direkte Ausführung           |
| Server/UI       | Logs + Monitoring         | Leichtgewichtige Alternative |

### Migration-Schritte

1. **✅ Bonobo-Dependencies hinzufügen**

   ```bash
   uv add bonobo bonobo-sqlalchemy
   ```

2. **📁 ETL-Struktur erstellen**

   ```bash
   mkdir -p src/etl/{nodes,graphs,utils}
   ```

3. **🔄 Prefect-Flows zu Bonobo-Graphs konvertieren**

   ```python
   # Alt: Prefect Flow
   @flow
   def vnb_flow():
       data = extract_task()
       result = transform_task(data)
       load_task(result)

   # Neu: Bonobo Graph
   def get_vnb_graph():
       return bonobo.Graph(
           extract_node,
           transform_node,
           load_node,
       )
   ```

4. **⏰ Scheduling auf Cron umstellen**

   ```bash
   # Prefect Deployment ersetzen durch Cron
   0 2 * * * /app/scripts/run_etl.sh vnb_pipeline
   ```

5. **📊 Monitoring anpassen**
   - Prefect UI → Structured Logging
   - Flow Status → Pipeline Statistics
   - Work Pool Metrics → Custom Metrics

### Vorteile der Migration

- **🎯 Fokus**: Keine Ablenkung durch komplexe Orchestrierung
- **🔧 Einfachheit**: Weniger bewegliche Teile, einfacher zu debuggen
- **💰 Kosten**: Keine zusätzliche Infrastructure für Prefect Server
- **🚀 Performance**: Direkte Ausführung ohne Overhead
- **🧪 Testing**: Einfachere Unit- und Integration-Tests

---

## 📝 Nächste Schritte

1. **Bonobo-Setup**: Abhängigkeiten installieren und Basis-Struktur erstellen
2. **BDEW-Pipeline**: Erste ETL-Pipeline für BDEW-Daten implementieren
3. **Testing**: Umfassende Tests für ETL-Nodes schreiben
4. **Scheduling**: Cron-Jobs für automatische Pipeline-Ausführung einrichten
5. **Monitoring**: Logging und Metriken für Pipeline-Observability

Bonobo bietet uns die perfekte Balance zwischen Funktionalität und Einfachheit für unsere ETL-Anforderungen im VNB Digitaler Projekt.
