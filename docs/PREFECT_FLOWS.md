# 🔄 VNB Digitaler - Prefect Flow Implementierungen

> **⚙️ Hauptspezifikation**: [SPECIFICATION.md](./specs/SPECIFICATION.md) - ETL-Pipeline-Architektur
> **🔧 Integration-Code**: [PREFECT_INTEGRATION.md](./PREFECT_INTEGRATION.md) - Pipeline-Adapter
> **🚀 Deployment**: [PREFECT_DEPLOYMENT.md](./PREFECT_DEPLOYMENT.md) - Konfigurationen

## 📋 Inhaltsverzeichnis

1. [BDEW Company Data Import Flow](#bdew-company-data-import-flow)
2. [BNetzA Smart Meter Rollout Flow](#bnetza-smart-meter-rollout-flow)
3. [VNB Price Sheet Processing Flow](#vnb-price-sheet-processing-flow)
4. [Flow-Utilities und Helper-Tasks](#flow-utilities-und-helper-tasks)

---

## BDEW Company Data Import Flow

### Flow-Definition

```python
# src/prefect_flows/flows/bdew/company_import.py
from prefect import flow, task
from datetime import timedelta

@flow(
    name="BDEW Company Data Import",
    description="Import und Update von BDEW Energiemarktakteur-Daten",
    version="1.0.0",
    flow_run_name="bdew-import-{date}",
    timeout_seconds=3600,
    retries=1,
    retry_delay_seconds=300
)
async def bdew_company_import_flow(
    incremental: bool = True,
    dry_run: bool = False
) -> dict[str, Any]:
    """
    Hauptflow für BDEW-Datenimport.

    Args:
        incremental: Nur geänderte Daten importieren
        dry_run: Simulation ohne Datenbankänderungen
    """
    # 1. Datenquellen-Status prüfen
    source_status = await check_bdew_data_sources_task()

    if not source_status["available"]:
        return {"status": "skipped", "reason": "BDEW API nicht verfügbar"}

    # 2. Incrementeller vs. Full Import
    if incremental:
        last_update = await get_last_bdew_update_task()
        extract_params = {"since": last_update}
    else:
        extract_params = {"full_refresh": True}

    # 3. Datenextraktion (parallelisiert nach Kategorien)
    extraction_tasks = await extract_bdew_data_by_category_task.map([
        "stromnetzbetreiber",
        "gasnetzbetreiber",
        "energielieferanten",
        "messstellenbetreiber"
    ], extract_params=[extract_params] * 4)

    # 4. Datenvalidierung
    validated_data = await validate_bdew_data_task(extraction_tasks)

    # 5. Transformation & Normalisierung
    transformed_data = await transform_bdew_data_task(validated_data)

    # 6. Database Import (bei Success)
    if not dry_run and transformed_data["validation_passed"]:
        import_result = await import_bdew_to_database_task(transformed_data)

        # 7. Post-Import Verification
        verification = await verify_bdew_import_task(import_result)

        return {
            "status": "success",
            "imported_records": import_result["record_count"],
            "categories": import_result["categories"],
            "verification": verification
        }

    return {
        "status": "dry_run" if dry_run else "validation_failed",
        "data_summary": transformed_data["summary"]
    }
```

### Task-Implementierungen

```python
@task(name="Extract BDEW Data by Category", retries=2)
async def extract_bdew_data_by_category_task(
    category: str,
    params: dict[str, Any]
) -> dict[str, Any]:
    """Extrahiere BDEW-Daten für spezifische Kategorie."""
    # Integration mit bestehender Pipeline
    from ...pipelines.bdew_import import BDEWExtractor

    extractor = BDEWExtractor(category=category)
    context = {"params": params}
    result = await extractor.execute(context)

    return {
        "category": category,
        "status": result.status.value,
        "data": result.data,
        "metrics": result.metrics
    }

@task(name="Validate BDEW Data", retries=1)
async def validate_bdew_data_task(
    extraction_results: list[dict[str, Any]]
) -> dict[str, Any]:
    """Validiere extrahierte BDEW-Daten."""
    from ...pipelines.base import DataValidatorStep
    from ...validators.bdew_validator import BDEWDataValidator

    validator = DataValidatorStep("bdew-validation", BDEWDataValidator())

    # Kombiniere alle Extraktion-Ergebnisse
    combined_data = []
    for result in extraction_results:
        if result["status"] == "success":
            combined_data.extend(result["data"])

    context = {"data": combined_data}
    validation_result = await validator.execute(context)

    return {
        "validation_passed": validation_result.status.name == "SUCCESS",
        "data": validation_result.data,
        "metrics": validation_result.metrics,
        "errors": validation_result.message if validation_result.error else None
    }
```

---

## BNetzA Smart Meter Rollout Flow

### BNetzA Flow-Definition

```python
# src/prefect_flows/flows/bnetza/rollout_import.py
from prefect import flow, task
from prefect.artifacts import create_markdown_artifact

@flow(
    name="BNetzA Smart Meter Rollout Import",
    description="Quartalsweiser Import von Smart Meter Rollout-Daten",
    version="1.0.0",
    timeout_seconds=1800
)
async def bnetza_rollout_import_flow(
    quarter: str = None,  # Format: "2025-Q1"
    force_download: bool = False
) -> dict[str, Any]:
    """
    Import von BNetzA Smart Meter Rollout-Berichten.

    Args:
        quarter: Spezifisches Quartal (None = aktuellstes)
        force_download: Erzwinge Download auch bei unveränderter ETag
    """
    # 1. BNetzA Website Discovery
    available_reports = await discover_bnetza_reports_task()

    if not quarter:
        quarter = available_reports["latest_quarter"]

    target_report = available_reports["reports"][quarter]

    # 2. Download-Entscheidung basierend auf ETag
    download_needed = await check_rollout_download_required_task(
        target_report["url"],
        target_report["etag"],
        force_download
    )

    if not download_needed:
        return {
            "status": "skipped",
            "reason": "Rollout-Daten unverändert",
            "quarter": quarter
        }

    # 3. Excel Download & Validation
    excel_file = await download_bnetza_excel_task(target_report["url"])
    validation_result = await validate_excel_structure_task(excel_file)

    if not validation_result["valid"]:
        await create_markdown_artifact(
            key="rollout-validation-error",
            markdown=f"# Rollout Validation Error\\n\\n{validation_result['errors']}"
        )
        raise ValueError(f"Excel-Validation fehlgeschlagen: {validation_result['errors']}")

    # 4. Excel zu CSV Konvertierung
    csv_data = await convert_excel_to_csv_task(excel_file)

    # 5. Company Matching (Fuzzy-Matching zu BDEW-Daten)
    matching_result = await match_rollout_companies_task(csv_data["companies"])

    # 6. Rollout-Quoten-Verarbeitung
    quota_result = await process_rollout_quotas_task(
        csv_data["quotas"],
        matching_result["matched_companies"]
    )

    # 7. Database Import
    import_result = await import_rollout_data_task({
        "quarter": quarter,
        "companies": matching_result,
        "quotas": quota_result,
        "metadata": {
            "source_url": target_report["url"],
            "etag": target_report["etag"],
            "processed_at": datetime.now().isoformat()
        }
    })

    # 8. Erfolgs-Artefakt erstellen
    await create_markdown_artifact(
        key=f"rollout-import-{quarter}",
        markdown=f"""
# Smart Meter Rollout Import - {quarter}

## Erfolgreiche Verarbeitung

- **Companies Matched**: {matching_result['match_rate']:.1%}
- **Quotas Imported**: {quota_result['quota_count']}
- **Database Records**: {import_result['total_records']}

## Details

### Company Matching
- Exact Matches: {matching_result['exact_matches']}
- Fuzzy Matches: {matching_result['fuzzy_matches']}
- No Matches: {matching_result['no_matches']}

### Data Quality
- Validation Errors: {validation_result['warnings']}
- Data Completeness: {quota_result['completeness']:.1%}
        """
    )

    return {
        "status": "success",
        "quarter": quarter,
        "import_summary": import_result,
        "match_rate": matching_result["match_rate"]
    }
```

---

## VNB Price Sheet Processing Flow

### Price Sheet Flow-Definition

```python
# src/prefect_flows/flows/pricing/vnb_price_sheets.py
from prefect import flow, task, get_run_logger
from prefect.concurrency import concurrency

@flow(
    name="VNB Price Sheet Processing",
    description="§14a-Netzentgelt-Preisblätter von VNB-Websites extrahieren",
    version="1.0.0"
)
async def vnb_price_sheet_flow(
    vnb_codes: list[str] = None,  # Spezifische BDEW-Codes
    year: int = None,             # Standard: aktuelles Jahr
    parallel_limit: int = 10      # Parallelitäts-Limit
) -> dict[str, Any]:
    """
    Verarbeitung von VNB-Preisblättern für §14a-Netzentgelte.

    Args:
        vnb_codes: Liste von BDEW-Codes (None = alle VNB)
        year: Zieljahr für Preisblätter
        parallel_limit: Maximale parallele Downloads
    """
    if not year:
        year = datetime.now().year

    # 1. VNB-Liste aus Datenbank holen
    if vnb_codes:
        target_vnbs = await get_vnbs_by_codes_task(vnb_codes)
    else:
        target_vnbs = await get_all_active_vnbs_task()

    logger = get_run_logger()
    logger.info(f"Processing {len(target_vnbs)} VNBs for year {year}")

    # 2. Website Discovery für jeden VNB (parallelisiert mit Limit)
    async with concurrency("vnb-website-discovery", parallel_limit):
        discovery_results = await discover_vnb_websites_task.map(
            [vnb["bdew_code"] for vnb in target_vnbs],
            year=[year] * len(target_vnbs)
        )

    # 3. PDF Download (nur für gefundene Price Sheets)
    available_pdfs = [
        result for result in discovery_results
        if result["pdf_found"]
    ]

    async with concurrency("pdf-download", parallel_limit):
        pdf_downloads = await download_price_sheet_pdf_task.map(
            [pdf["url"] for pdf in available_pdfs],
            [pdf["vnb_code"] for pdf in available_pdfs]
        )

    # 4. PDF-zu-Structured-Data Extraktion
    extraction_results = await extract_price_data_from_pdfs_task.map(
        pdf_downloads
    )

    # 5. Datenvalidierung & Standardisierung
    validated_data = await validate_price_data_task(extraction_results)

    # 6. Cloudflare R2 Upload (Original PDFs)
    storage_results = await upload_pdfs_to_r2_task.map(
        pdf_downloads,
        storage_paths=[f"price-sheets/{year}/{pdf['vnb_code']}.pdf"
                      for pdf in pdf_downloads]
    )

    # 7. Database Import
    import_result = await import_price_data_task({
        "year": year,
        "price_data": validated_data,
        "storage_metadata": storage_results,
        "processing_stats": {
            "total_vnbs": len(target_vnbs),
            "websites_found": len(discovery_results),
            "pdfs_downloaded": len(pdf_downloads),
            "successful_extractions": len([r for r in extraction_results if r["success"]])
        }
    })

    return {
        "status": "success",
        "year": year,
        "processing_summary": import_result["processing_stats"],
        "data_quality": validated_data["quality_metrics"]
    }
```

### PDF-Extraktion Task

```python
@task(name="Extract Price Data from PDF", retries=2)
async def extract_price_data_from_pdfs_task(
    pdf_download: dict[str, Any]
) -> dict[str, Any]:
    """Extrahiere strukturierte Preisdaten aus PDF."""
    # Integration mit AI-basierter PDF-Extraktion
    from ...processors.pdf_extractor import PriceSheetExtractor

    extractor = PriceSheetExtractor()

    try:
        price_data = await extractor.extract_price_data(
            pdf_path=pdf_download["local_path"],
            vnb_code=pdf_download["vnb_code"]
        )

        return {
            "vnb_code": pdf_download["vnb_code"],
            "success": True,
            "price_data": price_data,
            "confidence": price_data.get("extraction_confidence", 0.0)
        }
    except Exception as e:
        return {
            "vnb_code": pdf_download["vnb_code"],
            "success": False,
            "error": str(e)
        }
```

---

## Flow-Utilities und Helper-Tasks

### Common Database Tasks

```python
# src/prefect_flows/tasks/database.py
from prefect import task
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_async_session

@task(name="Database Transaction")
async def database_transaction_task(
    operations: list[Any],
    session_factory=get_async_session
) -> dict[str, Any]:
    """Führe Datenbank-Operationen in Transaktion aus."""
    async with session_factory() as session:
        try:
            results = {}
            for operation in operations:
                result = await operation.execute(session)
                results[operation.name] = result
            await session.commit()
            return results
        except Exception:
            await session.rollback()
            raise
```

### External API Tasks

```python
# src/prefect_flows/tasks/external_apis.py
from prefect import task
from httpx import AsyncClient

@task(name="Fetch External Data", retries=3, retry_delay_seconds=[60, 120, 300])
async def fetch_external_data_task(
    url: str,
    headers: dict[str, str] = None,
    timeout: int = 30
) -> dict[str, Any]:
    """Hole Daten von externen APIs mit Retry-Logic."""
    async with AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers or {})
        response.raise_for_status()
        return response.json()
```

### Monitoring Tasks

```python
# src/prefect_flows/tasks/monitoring.py
from prefect import task, get_run_logger
from prefect.artifacts import create_table_artifact

@task(name="Create Data Quality Report")
async def create_data_quality_report_task(
    flow_results: dict[str, Any]
) -> None:
    """Erstelle Datenqualitäts-Report als Prefect Artifact."""

    quality_data = [
        ["Data Source", "Last Update", "Record Count", "Quality Score"],
        ["BDEW", flow_results["bdew"]["last_update"],
         flow_results["bdew"]["record_count"], flow_results["bdew"]["quality"]],
        ["BNetzA", flow_results["bnetza"]["last_update"],
         flow_results["bnetza"]["record_count"], flow_results["bnetza"]["quality"]],
        ["Price Sheets", flow_results["pricing"]["last_update"],
         flow_results["pricing"]["record_count"], flow_results["pricing"]["quality"]]
    ]

    await create_table_artifact(
        key="data-quality-summary",
        table=quality_data,
        description="Aktuelle Datenqualität aller Quellen"
    )
```

---

_Diese Flows implementieren die in der Hauptspezifikation definierten Prefect-Orchestrierungs-Patterns für VNB Digitaler._
