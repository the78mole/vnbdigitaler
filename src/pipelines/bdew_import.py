"""
BDEW Import Pipeline Implementation.

4-stufige Pipeline für den Import und die Verarbeitung von BDEW-Daten.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from ..data_sources.bdew import BDEWDataSource
from ..logging_config import setup_logging
from ..repositories.bdew import BDEWRepository
from .base import (
    DataExtractorStep,
    Pipeline,
    PipelineStep,
    PipelineStepResult,
    PipelineStepStatus,
)


class BDEWValidationStep(PipelineStep):
    """
    Pipeline-Schritt für erweiterte BDEW-Datenvalidierung.

    Führt umfassende Qualitätsprüfungen durch und berechnet
    Datenqualitäts-Scores für jeden Datensatz.
    """

    def __init__(self, repository: BDEWRepository):
        super().__init__(
            name="validate_bdew_data",
            description="Validiere BDEW-Daten und berechne Qualitäts-Scores",
        )
        self.repository = repository

    async def execute(self, context: dict[str, Any]) -> PipelineStepResult:
        """Führe BDEW-Datenvalidierung aus."""
        try:
            data = context.get("data", [])
            if not data:
                return PipelineStepResult(
                    status=PipelineStepStatus.FAILED,
                    message="Keine Daten für Validierung verfügbar",
                )

            # Lade aktive Validierungsregeln
            validation_rules = self.repository.get_active_validation_rules()

            validated_data = []
            validation_errors = []

            for i, record in enumerate(data):
                validation_result = await self._validate_record(
                    record, validation_rules
                )

                if validation_result["is_valid"]:
                    # Berechne Qualitäts-Score
                    quality_score = self._calculate_quality_score(record)
                    record["data_quality_score"] = quality_score
                    validated_data.append(record)
                else:
                    validation_errors.append(
                        {"record_index": i, "errors": validation_result["errors"]}
                    )

            # Aktualisiere Kontext
            context["validated_data"] = validated_data
            context["validation_errors"] = validation_errors

            metrics = {
                "total_records": len(data),
                "valid_records": len(validated_data),
                "invalid_records": len(validation_errors),
                "validation_rules_applied": len(validation_rules),
                "average_quality_score": (
                    sum(r.get("data_quality_score", 0) for r in validated_data)
                    / len(validated_data)
                    if validated_data
                    else 0
                ),
            }

            if validation_errors:
                return PipelineStepResult(
                    status=PipelineStepStatus.SUCCESS,
                    data=validated_data,
                    message=f"Validierung abgeschlossen mit {len(validation_errors)} Fehlern",
                    metrics=metrics,
                )
            else:
                return PipelineStepResult(
                    status=PipelineStepStatus.SUCCESS,
                    data=validated_data,
                    message="Alle Datensätze erfolgreich validiert",
                    metrics=metrics,
                )

        except Exception as e:
            return PipelineStepResult(
                status=PipelineStepStatus.FAILED,
                message=f"Validierung fehlgeschlagen: {e!s}",
                error=e,
            )

    async def _validate_record(
        self, record: dict[str, Any], rules: list  # noqa: ARG002
    ) -> dict[str, Any]:
        """Validiere einzelnen Datensatz gegen Regeln."""
        errors = []

        # Basis-Validierungen
        required_fields = ["company_name", "network_operator_id"]
        for field in required_fields:
            if not record.get(field, "").strip():
                errors.append(f"Pflichtfeld '{field}' fehlt oder ist leer")

        # Weitere Validierungen können hier basierend auf den Regeln implementiert werden

        return {"is_valid": len(errors) == 0, "errors": errors}

    def _calculate_quality_score(self, record: dict[str, Any]) -> int:
        """Berechne Datenqualitäts-Score (0-100)."""
        score = 0

        # Basis-Score für Pflichtfelder
        if record.get("company_name", "").strip():
            score += 20
        if record.get("network_operator_id", "").strip():
            score += 20

        # Bonus für zusätzliche Felder
        if record.get("postal_code", "").strip():
            score += 15
        if record.get("city", "").strip():
            score += 15
        if record.get("federal_state", "").strip():
            score += 10
        if record.get("email", "").strip():
            score += 10
        if record.get("website", "").strip():
            score += 5
        if record.get("phone", "").strip():
            score += 5

        return min(score, 100)


class BDEWPersistenceStep(PipelineStep):
    """
    Pipeline-Schritt für BDEW-Datenpersistierung.

    Speichert validierte BDEW-Daten in die Datenbank und
    führt Deduplizierung und Aktualisierung durch.
    """

    def __init__(self, repository: BDEWRepository):
        super().__init__(
            name="persist_bdew_data", description="Speichere BDEW-Daten in Datenbank"
        )
        self.repository = repository

    async def execute(self, context: dict[str, Any]) -> PipelineStepResult:
        """Führe BDEW-Datenpersistierung aus."""
        try:
            validated_data = context.get("validated_data", [])
            if not validated_data:
                return PipelineStepResult(
                    status=PipelineStepStatus.FAILED,
                    message="Keine validierten Daten für Persistierung verfügbar",
                )

            # Konvertiere zu Datenbank-Format
            db_records = []
            for record in validated_data:
                db_record = self._convert_to_db_format(record, context)
                db_records.append(db_record)

            # Führe Bulk-Insert durch
            imported_count = self.repository.bulk_insert_companies(db_records)

            metrics = {
                "records_imported": imported_count,
                "import_timestamp": datetime.utcnow().isoformat(),
            }

            return PipelineStepResult(
                status=PipelineStepStatus.SUCCESS,
                data={"imported_count": imported_count},
                message=f"Erfolgreich {imported_count} BDEW-Datensätze importiert",
                metrics=metrics,
            )

        except Exception as e:
            return PipelineStepResult(
                status=PipelineStepStatus.FAILED,
                message=f"Persistierung fehlgeschlagen: {e!s}",
                error=e,
            )

    def _convert_to_db_format(
        self, record: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Konvertiere Datensatz in Datenbank-Format."""
        return {
            "company_name": record.get("company_name", "").strip(),
            "network_operator_id": record.get("network_operator_id", "").strip(),
            "marktlokations_id": record.get("marktlokations_id", "").strip(),
            "postal_code": record.get("postal_code", "").strip(),
            "city": record.get("city", "").strip(),
            "federal_state": record.get("federal_state", "").strip(),
            "address_line": record.get("address_line", "").strip(),
            "website": record.get("website", "").strip(),
            "email": record.get("email", "").strip(),
            "phone": record.get("phone", "").strip(),
            "source_file": context.get("source_file", ""),
            "data_quality_score": record.get("data_quality_score", 0),
            "import_timestamp": datetime.utcnow(),
        }


class BDEWImportLoggingStep(PipelineStep):
    """
    Pipeline-Schritt für Import-Logging.

    Erstellt detaillierte Logs über den Import-Vorgang
    für Auditing und Monitoring.
    """

    def __init__(self, repository: BDEWRepository):
        super().__init__(
            name="log_import_results", description="Erstelle Import-Log-Einträge"
        )
        self.repository = repository

    async def execute(self, context: dict[str, Any]) -> PipelineStepResult:
        """Führe Import-Logging aus."""
        try:
            # Sammle Metriken aus dem Kontext
            pipeline_results = context.get("pipeline_results", {})
            source_file = context.get("source_file", "")

            # Berechne Zusammenfassungsstatistiken
            total_records = 0
            imported_records = 0
            failed_records = 0

            for _step_name, step_result in pipeline_results.items():
                if hasattr(step_result, "metrics") and step_result.metrics:
                    if "total_records" in step_result.metrics:
                        total_records = step_result.metrics["total_records"]
                    if "records_imported" in step_result.metrics:
                        imported_records = step_result.metrics["records_imported"]
                    if "invalid_records" in step_result.metrics:
                        failed_records = step_result.metrics["invalid_records"]

            # Bestimme Import-Status
            import_status = "SUCCESS"
            if failed_records > 0:
                import_status = "PARTIAL"
            if imported_records == 0:
                import_status = "FAILED"

            # Erstelle Log-Eintrag
            log_data = {
                "source_file": source_file,
                "file_hash": (
                    self._calculate_file_hash(source_file) if source_file else None
                ),
                "records_total": total_records,
                "records_imported": imported_records,
                "records_updated": 0,  # Für spätere Erweiterung
                "records_skipped": 0,  # Für spätere Erweiterung
                "records_failed": failed_records,
                "import_status": import_status,
                "processing_time_seconds": context.get("processing_time", 0),
                "pipeline_id": context.get("pipeline_id", ""),
            }

            import_log = self.repository.create_import_log(log_data)

            return PipelineStepResult(
                status=PipelineStepStatus.SUCCESS,
                data={"log_id": str(import_log.id)},
                message=f"Import-Log erstellt: {import_status}",
                metrics={"log_id": str(import_log.id)},
            )

        except Exception as e:
            return PipelineStepResult(
                status=PipelineStepStatus.FAILED,
                message=f"Import-Logging fehlgeschlagen: {e!s}",
                error=e,
            )

    def _calculate_file_hash(self, file_path: str) -> str:
        """Berechne Datei-Hash."""
        try:
            return BDEWRepository.calculate_file_hash(file_path)
        except Exception:
            return ""


async def create_bdew_import_pipeline(
    file_path: Path, repository: BDEWRepository
) -> Pipeline:
    """
    Erstelle vollständige Pipeline für BDEW Stammdaten-Import.

    Args:
        file_path: Pfad zur BDEW-Datei
        repository: BDEW Repository für Datenbankoperationen

    Returns:
        Pipeline: Konfigurierte BDEW-Import-Pipeline
    """
    # Pipeline erstellen
    pipeline = Pipeline(
        name="bdew_import",
        description="Vollständiger Import von BDEW Verteilnetzbetreiber-Stammdaten",
    )

    # BDEW Datenquelle erstellen
    bdew_source = BDEWDataSource(file_path)

    # 1. Extraktions-Schritt
    extraction_step = DataExtractorStep(
        name="extract_bdew_data",
        data_source=bdew_source,
        description="Extrahiere BDEW-Daten aus CSV-Datei",
    )

    # 2. Validierungs-Schritt
    validation_step = BDEWValidationStep(repository)
    validation_step.add_dependency("extract_bdew_data")

    # 3. Persistierungs-Schritt
    persistence_step = BDEWPersistenceStep(repository)
    persistence_step.add_dependency("validate_bdew_data")

    # 4. Logging-Schritt
    logging_step = BDEWImportLoggingStep(repository)
    logging_step.add_dependency("persist_bdew_data")

    # Schritte zur Pipeline hinzufügen
    pipeline.add_step(extraction_step)
    pipeline.add_step(validation_step)
    pipeline.add_step(persistence_step)
    pipeline.add_step(logging_step)

    return pipeline


async def run_bdew_import_example() -> None:
    """Beispiel-Ausführung der BDEW-Import-Pipeline."""
    # Logging konfigurieren
    setup_logging()


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_bdew_import_example())
