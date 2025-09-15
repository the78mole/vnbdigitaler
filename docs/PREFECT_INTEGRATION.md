# 🔧 VNB Digitaler - Prefect Integration

> **📋 Hauptspezifikation**: [SPECIFICATION.md](../SPECIFICATION.md) - Gesamtarchitektur
> **🔄 Flow-Implementierungen**: [PREFECT_FLOWS.md](./PREFECT_FLOWS.md) - Code-Beispiele
> **🚀 Deployment**: [PREFECT_DEPLOYMENT.md](./PREFECT_DEPLOYMENT.md) - Konfigurationen

## 📋 Inhaltsverzeichnis

1. [Pipeline-Adapter Integration](#pipeline-adapter-integration)
2. [Bestehende Pipeline-Klassen erweitern](#bestehende-pipeline-klassen-erweitern)
3. [Fehlerbehandlung & Retry-Logic](#fehlerbehandlung--retry-logic)
4. [Monitoring & Observability](#monitoring--observability)
5. [Testing-Framework](#testing-framework)

---

## Pipeline-Adapter Integration

### Prefect-Pipeline-Adapter

```python
# src/prefect_flows/adapters/pipeline_adapter.py
from typing import Any, Dict, Optional
from prefect import task, get_run_logger
from ..pipelines.base import Pipeline, PipelineStep, PipelineContext, PipelineResult

class PrefectPipelineAdapter:
    """
    Adapter zwischen bestehenden Pipeline-Klassen und Prefect Tasks.
    Ermöglicht nahtlose Integration ohne Breaking Changes.
    """

    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline
        self.logger = get_run_logger()

    async def execute_as_task(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Führe Pipeline als Prefect Task aus.

        Returns:
            Serialisiertes PipelineResult für weitere Prefect Tasks
        """
        try:
            # Context vorbereiten
            pipeline_context = PipelineContext(context or {})

            # Pipeline ausführen
            self.logger.info(f"Executing pipeline: {self.pipeline.name}")
            result = await self.pipeline.execute(pipeline_context)

            # Ergebnis für Prefect serialisieren
            return {
                "status": result.status.value,
                "data": result.data,
                "metrics": result.metrics,
                "error": str(result.error) if result.error else None,
                "execution_time": result.execution_time
            }

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            return {
                "status": "failed",
                "data": None,
                "metrics": {},
                "error": str(e),
                "execution_time": 0
            }

def create_pipeline_task(
    pipeline: Pipeline,
    task_name: Optional[str] = None,
    retries: int = 1,
    retry_delay_seconds: int = 60
):
    """
    Factory-Funktion zum Erstellen von Prefect Tasks aus Pipelines.

    Args:
        pipeline: Bestehende Pipeline-Instanz
        task_name: Optional task name (default: pipeline.name)
        retries: Anzahl Wiederholungen bei Fehlern
        retry_delay_seconds: Wartezeit zwischen Wiederholungen

    Returns:
        Prefect Task-Decorator
    """
    @task(
        name=task_name or f"Pipeline: {pipeline.name}",
        retries=retries,
        retry_delay_seconds=retry_delay_seconds
    )
    async def pipeline_task(context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        adapter = PrefectPipelineAdapter(pipeline)
        return await adapter.execute_as_task(context)

    return pipeline_task
```

### Pipeline-Step zu Prefect Task Mapping

```python
# src/prefect_flows/adapters/step_adapter.py
from prefect import task
from ..pipelines.base import PipelineStep

def create_step_task(
    step: PipelineStep,
    task_name: Optional[str] = None
):
    """
    Wandle einzelnen PipelineStep in Prefect Task um.
    Ermöglicht feinere Kontrolle und besseres Monitoring.
    """
    @task(name=task_name or f"Step: {step.name}")
    async def step_task(context: Dict[str, Any]) -> Dict[str, Any]:
        pipeline_context = PipelineContext(context)
        result = await step.execute(pipeline_context)

        return {
            "status": result.status.value,
            "data": result.data,
            "metrics": result.metrics,
            "error": str(result.error) if result.error else None
        }

    return step_task

# Beispiel-Verwendung
from ..pipelines.bdew_import import BDEWExtractor, BDEWValidator

bdew_extract_task = create_step_task(
    BDEWExtractor("company-data"),
    "BDEW Company Extraction"
)

bdew_validate_task = create_step_task(
    BDEWValidator("data-validation"),
    "BDEW Data Validation"
)
```

---

## Bestehende Pipeline-Klassen erweitern

### Pipeline-Klasse mit Prefect Support

```python
# src/pipelines/base.py (Erweiterung)
from typing import Optional
from prefect import get_run_context
from prefect.logging import get_run_logger

class Pipeline:
    """Erweiterte Pipeline-Klasse mit Prefect-Integration."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: List[PipelineStep] = []
        self._prefect_context = None
        self._prefect_logger = None

    @property
    def is_prefect_context(self) -> bool:
        """Prüfe ob Pipeline in Prefect-Kontext ausgeführt wird."""
        try:
            get_run_context()
            return True
        except RuntimeError:
            return False

    @property
    def logger(self):
        """Verwende Prefect Logger wenn verfügbar, sonst Standard Logger."""
        if self.is_prefect_context:
            return get_run_logger()
        return self._standard_logger

    async def execute(self, context: PipelineContext) -> PipelineResult:
        """
        Erweiterte execute-Methode mit Prefect-Integration.
        Behält Rückwärtskompatibilität bei.
        """
        start_time = datetime.now()

        # Prefect Artifacts für besseres Monitoring
        if self.is_prefect_context:
            await self._create_execution_artifact()

        try:
            # Bestehende Pipeline-Logik
            result = await self._execute_steps(context)

            # Prefect Success Artifact
            if self.is_prefect_context:
                await self._create_success_artifact(result)

            return result

        except Exception as e:
            # Prefect Error Artifact
            if self.is_prefect_context:
                await self._create_error_artifact(e)
            raise

    async def _create_execution_artifact(self):
        """Erstelle Prefect Artifact für Pipeline-Start."""
        from prefect.artifacts import create_markdown_artifact

        await create_markdown_artifact(
            key=f"pipeline-{self.name}-start",
            markdown=f"""
# Pipeline Execution: {self.name}

**Started:** {datetime.now().isoformat()}
**Description:** {self.description}
**Steps:** {len(self.steps)}

## Pipeline Steps
{chr(10).join([f"- {step.name}" for step in self.steps])}
            """
        )

    async def _create_success_artifact(self, result: PipelineResult):
        """Erstelle Success-Artifact mit Metriken."""
        from prefect.artifacts import create_table_artifact

        metrics_table = [
            ["Metric", "Value"],
            *[[k, str(v)] for k, v in result.metrics.items()]
        ]

        await create_table_artifact(
            key=f"pipeline-{self.name}-metrics",
            table=metrics_table,
            description=f"Execution metrics for {self.name}"
        )
```

### BDEW Pipeline mit Prefect-Features

```python
# src/pipelines/bdew_import.py (Erweiterung)
from prefect.blocks.system import Secret

class BDEWImportPipeline(Pipeline):
    """BDEW Import Pipeline mit Prefect-Integration."""

    def __init__(self):
        super().__init__(
            name="BDEW Company Import",
            description="Import von BDEW Energiemarktakteur-Daten"
        )

        # Pipeline Steps hinzufügen
        self.add_step(BDEWApiConnector("bdew-api-connect"))
        self.add_step(BDEWExtractor("bdew-extract"))
        self.add_step(BDEWValidator("bdew-validate"))
        self.add_step(BDEWTransformer("bdew-transform"))
        self.add_step(DatabaseImporter("bdew-import"))

    async def _get_api_credentials(self) -> Dict[str, str]:
        """Hole BDEW API Credentials aus Prefect Secrets."""
        if self.is_prefect_context:
            api_key_block = await Secret.load("bdew-api-key")
            return {"api_key": api_key_block.get()}
        else:
            # Fallback für Non-Prefect Execution
            return {"api_key": os.getenv("BDEW_API_KEY")}

class BDEWExtractor(PipelineStep):
    """BDEW Data Extractor mit Prefect Features."""

    async def execute(self, context: PipelineContext) -> PipelineResult:
        """Erweiterte Extraktion mit Prefect Progress Tracking."""

        # Prefect Progress Artifacts
        if self._is_prefect_context():
            from prefect.artifacts import create_progress_artifact
            await create_progress_artifact(
                progress=0.0,
                description="Starting BDEW extraction"
            )

        try:
            # API Call
            data = await self._extract_bdew_data(context)

            # Progress Update
            if self._is_prefect_context():
                await create_progress_artifact(
                    progress=0.5,
                    description=f"Extracted {len(data)} records"
                )

            # Validation
            validated_data = await self._validate_data(data)

            # Final Progress
            if self._is_prefect_context():
                await create_progress_artifact(
                    progress=1.0,
                    description="BDEW extraction completed"
                )

            return PipelineResult.success(
                data=validated_data,
                metrics={"extracted_records": len(validated_data)}
            )

        except Exception as e:
            return PipelineResult.failure(error=e)
```

---

## Fehlerbehandlung & Retry-Logic

### Intelligente Retry-Strategien

```python
# src/prefect_flows/utils/retry_strategies.py
from prefect.retries import RetryPolicy
from prefect import task
import asyncio

class AdaptiveRetryPolicy:
    """
    Adaptive Retry-Strategie basierend auf Fehlertyp.
    """

    @staticmethod
    def get_retry_policy(error_type: type) -> RetryPolicy:
        """Bestimme Retry-Strategie basierend auf Fehlertyp."""

        if issubclass(error_type, (ConnectionError, TimeoutError)):
            # Netzwerkfehler: Aggressive Retries mit exponential backoff
            return RetryPolicy(
                max_retries=5,
                delay_seconds=[30, 60, 120, 300, 600]
            )

        elif issubclass(error_type, ValueError):
            # Datenvalidierungsfehler: Wenige Retries
            return RetryPolicy(
                max_retries=2,
                delay_seconds=[10, 30]
            )

        else:
            # Unbekannte Fehler: Moderate Retries
            return RetryPolicy(
                max_retries=3,
                delay_seconds=[60, 120, 180]
            )

@task(
    retries=3,
    retry_delay_seconds=60,
    retry_condition=lambda task, task_run, state: state.name == "Failed"
)
async def resilient_api_call_task(
    url: str,
    max_timeout: int = 30
) -> Dict[str, Any]:
    """
    Robuster API-Call mit Circuit Breaker Pattern.
    """
    from ..utils.circuit_breaker import CircuitBreaker

    circuit_breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=300  # 5 Minuten
    )

    async def api_call():
        async with httpx.AsyncClient(timeout=max_timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    return await circuit_breaker.call(api_call)
```

### Error Aggregation & Reporting

```python
# src/prefect_flows/utils/error_handling.py
from prefect import task, get_run_logger
from prefect.artifacts import create_markdown_artifact

@task(name="Aggregate Flow Errors")
async def aggregate_flow_errors_task(
    flow_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Sammle und kategorisiere alle Fehler eines Flows.
    Erstelle detaillierte Error-Reports.
    """
    logger = get_run_logger()

    errors = []
    warnings = []
    successful_tasks = 0

    for result in flow_results:
        if result.get("status") == "failed":
            errors.append({
                "task": result.get("task_name", "Unknown"),
                "error": result.get("error"),
                "timestamp": result.get("timestamp")
            })
        elif result.get("status") == "warning":
            warnings.append(result)
        else:
            successful_tasks += 1

    # Error Report als Prefect Artifact
    if errors:
        error_markdown = f"""
# Flow Error Report

## Summary
- **Total Tasks**: {len(flow_results)}
- **Successful**: {successful_tasks}
- **Failed**: {len(errors)}
- **Warnings**: {len(warnings)}

## Failed Tasks
{chr(10).join([f"### {error['task']}" + chr(10) + f"**Error**: {error['error']}" + chr(10) + f"**Time**: {error['timestamp']}" for error in errors])}

## Warnings
{chr(10).join([f"- {warning.get('message', 'Unknown warning')}" for warning in warnings])}
        """

        await create_markdown_artifact(
            key="flow-error-report",
            markdown=error_markdown
        )

    return {
        "total_errors": len(errors),
        "total_warnings": len(warnings),
        "success_rate": successful_tasks / len(flow_results),
        "requires_attention": len(errors) > 0
    }
```

---

## Monitoring & Observability

### Custom Metrics für Business Logic

```python
# src/prefect_flows/monitoring/metrics.py
from prefect import task
from prefect.artifacts import create_table_artifact, create_markdown_artifact
from typing import Dict, List, Any

@task(name="Business Metrics Collection")
async def collect_business_metrics_task(
    data_sources: List[str] = ["bdew", "bnetza", "vnb_pricing"]
) -> Dict[str, Any]:
    """
    Sammle business-relevante Metriken für Dashboard.
    """
    from ..database import get_async_session

    metrics = {}

    async with get_async_session() as session:
        for source in data_sources:
            source_metrics = await _collect_source_metrics(session, source)
            metrics[source] = source_metrics

    # Business Dashboard Artifact
    await _create_business_dashboard_artifact(metrics)

    return metrics

async def _collect_source_metrics(session, source: str) -> Dict[str, Any]:
    """Sammle Metriken für spezifische Datenquelle."""

    if source == "bdew":
        return {
            "total_companies": await _count_bdew_companies(session),
            "last_update": await _get_last_bdew_update(session),
            "data_freshness_hours": await _calculate_bdew_freshness(session),
            "quality_score": await _calculate_bdew_quality(session)
        }

    elif source == "bnetza":
        return {
            "total_rollout_entries": await _count_rollout_entries(session),
            "latest_quarter": await _get_latest_quarter(session),
            "rollout_completion_rate": await _calculate_rollout_rate(session),
            "quality_score": await _calculate_rollout_quality(session)
        }

    elif source == "vnb_pricing":
        return {
            "total_price_sheets": await _count_price_sheets(session),
            "covered_vnbs": await _count_covered_vnbs(session),
            "price_sheet_freshness": await _calculate_pricing_freshness(session),
            "extraction_success_rate": await _calculate_extraction_success(session)
        }

async def _create_business_dashboard_artifact(metrics: Dict[str, Any]):
    """Erstelle Business Dashboard als Prefect Artifact."""

    # Summary Table
    summary_data = [
        ["Data Source", "Records", "Freshness", "Quality"],
        ["BDEW Companies",
         str(metrics["bdew"]["total_companies"]),
         f"{metrics['bdew']['data_freshness_hours']:.1f}h",
         f"{metrics['bdew']['quality_score']:.1%}"],
        ["BNetzA Rollout",
         str(metrics["bnetza"]["total_rollout_entries"]),
         metrics["bnetza"]["latest_quarter"],
         f"{metrics['bnetza']['quality_score']:.1%}"],
        ["VNB Pricing",
         str(metrics["vnb_pricing"]["total_price_sheets"]),
         f"{metrics['vnb_pricing']['price_sheet_freshness']:.1f}h",
         f"{metrics['vnb_pricing']['extraction_success_rate']:.1%}"]
    ]

    await create_table_artifact(
        key="business-metrics-summary",
        table=summary_data,
        description="VNB Digitaler Business Metrics Dashboard"
    )

    # Detailed Report
    detail_markdown = f"""
# VNB Digitaler - Business Metrics Report

## Data Quality Overview

### BDEW Companies
- **Total Companies**: {metrics['bdew']['total_companies']:,}
- **Last Update**: {metrics['bdew']['last_update']}
- **Data Freshness**: {metrics['bdew']['data_freshness_hours']:.1f} hours
- **Quality Score**: {metrics['bdew']['quality_score']:.1%}

### BNetzA Smart Meter Rollout
- **Total Rollout Entries**: {metrics['bnetza']['total_rollout_entries']:,}
- **Latest Quarter**: {metrics['bnetza']['latest_quarter']}
- **Rollout Completion**: {metrics['bnetza']['rollout_completion_rate']:.1%}
- **Quality Score**: {metrics['bnetza']['quality_score']:.1%}

### VNB Price Sheets
- **Total Price Sheets**: {metrics['vnb_pricing']['total_price_sheets']:,}
- **Covered VNBs**: {metrics['vnb_pricing']['covered_vnbs']:,}
- **Extraction Success**: {metrics['vnb_pricing']['extraction_success_rate']:.1%}
- **Data Freshness**: {metrics['vnb_pricing']['price_sheet_freshness']:.1f} hours

## Action Items

{_generate_action_items(metrics)}
    """

    await create_markdown_artifact(
        key="business-metrics-detail",
        markdown=detail_markdown
    )

def _generate_action_items(metrics: Dict[str, Any]) -> str:
    """Generiere automatische Action Items basierend auf Metriken."""
    items = []

    # Datenqualität prüfen
    for source, data in metrics.items():
        if data["quality_score"] < 0.9:
            items.append(f"⚠️ {source.upper()}: Quality score below 90% - Review data validation")

    # Datenfrische prüfen
    if metrics["bdew"]["data_freshness_hours"] > 24:
        items.append("🔄 BDEW: Data older than 24h - Schedule update")

    if metrics["vnb_pricing"]["extraction_success_rate"] < 0.8:
        items.append("📄 VNB Pricing: Extraction success below 80% - Review PDF processors")

    return "\n".join([f"- {item}" for item in items]) if items else "✅ All metrics within acceptable ranges"
```

---

## Testing-Framework

### Prefect Flow Testing

```python
# tests/prefect_flows/test_bdew_flow.py
import pytest
from prefect.testing.utilities import prefect_test_harness
from src.prefect_flows.flows.bdew.company_import import bdew_company_import_flow

@pytest.fixture
def mock_bdew_api(monkeypatch):
    """Mock BDEW API für Testing."""
    async def mock_check_sources():
        return {"available": True}

    async def mock_extract_data(category, params):
        return {
            "category": category,
            "status": "success",
            "data": [{"company": f"Test {category} Company"}],
            "metrics": {"extracted": 1}
        }

    monkeypatch.setattr(
        "src.prefect_flows.flows.bdew.company_import.check_bdew_data_sources_task",
        mock_check_sources
    )
    monkeypatch.setattr(
        "src.prefect_flows.flows.bdew.company_import.extract_bdew_data_by_category_task",
        mock_extract_data
    )

@pytest.mark.asyncio
async def test_bdew_flow_success(mock_bdew_api):
    """Teste erfolgreichen BDEW Import Flow."""

    with prefect_test_harness():
        result = await bdew_company_import_flow(
            incremental=True,
            dry_run=True
        )

        assert result["status"] == "dry_run"
        assert "data_summary" in result

@pytest.mark.asyncio
async def test_bdew_flow_api_unavailable():
    """Teste Flow bei nicht verfügbarer BDEW API."""

    with prefect_test_harness():
        # Mock API als nicht verfügbar
        async def mock_unavailable():
            return {"available": False}

        # ... monkeypatch setup

        result = await bdew_company_import_flow()

        assert result["status"] == "skipped"
        assert result["reason"] == "BDEW API nicht verfügbar"

class TestPipelineAdapter:
    """Test Pipeline-Adapter Integration."""

    def test_pipeline_to_task_conversion(self):
        """Teste Konvertierung von Pipeline zu Prefect Task."""
        from src.pipelines.bdew_import import BDEWImportPipeline
        from src.prefect_flows.adapters.pipeline_adapter import create_pipeline_task

        pipeline = BDEWImportPipeline()
        task = create_pipeline_task(pipeline, retries=2)

        assert task.name == "Pipeline: BDEW Company Import"
        assert task.retries == 2

    @pytest.mark.asyncio
    async def test_pipeline_execution_in_prefect(self, mock_database):
        """Teste Pipeline-Ausführung in Prefect-Kontext."""

        with prefect_test_harness():
            # ... Test-Setup

            result = await pipeline_task.fn({"test_mode": True})

            assert result["status"] == "success"
            assert "metrics" in result
```

### Integration Tests mit echten Services

```python
# tests/integration/test_full_pipeline.py
import pytest
from prefect.testing.utilities import prefect_test_harness

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_data_pipeline():
    """
    Vollständiger Integration-Test der gesamten Pipeline.
    Nur in CI/CD mit echten Test-Services.
    """

    with prefect_test_harness():
        # 1. BDEW Import
        bdew_result = await bdew_company_import_flow(
            incremental=False,
            dry_run=False
        )
        assert bdew_result["status"] == "success"

        # 2. BNetzA Rollout Import
        rollout_result = await bnetza_rollout_import_flow(
            quarter="2025-Q1",
            force_download=True
        )
        assert rollout_result["status"] == "success"

        # 3. Datenqualitäts-Check
        quality_metrics = await collect_business_metrics_task()

        # Assertions auf Datenqualität
        assert quality_metrics["bdew"]["quality_score"] > 0.8
        assert quality_metrics["bnetza"]["quality_score"] > 0.8

        # 4. End-to-End Consistency Check
        consistency_result = await verify_data_consistency_task(
            bdew_result, rollout_result
        )
        assert consistency_result["consistent"] is True
```

---

_Diese Integration-Patterns ermöglichen nahtlose Prefect-Adoption ohne Breaking Changes an bestehenden Pipeline-Klassen._
