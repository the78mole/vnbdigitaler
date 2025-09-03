"""
BDEW Import Pipeline Implementation.

4-stufige Pipeline für den Import und die Verarbeitung von BDEW-Daten.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..data_sources.bdew_web import BDEWWebDataSource
from ..logging_config import setup_logging
from ..repositories.bdew import BDEWRepository
from .base import (
    Pipeline,
    PipelineStep,
    PipelineStepResult,
    PipelineStepStatus,
)

# Validation constants
MIN_BDEW_CODE_LENGTH = 3
MIN_COMPANY_NAME_LENGTH = 5
MIN_CITY_NAME_LENGTH = 3
MAX_VALIDATION_ERRORS_DISPLAYED = 10

# Quality scoring constants
MIN_COMPANY_NAME_WORDS = 2


class BDEWWebDownloadStep(PipelineStep):
    """
    Pipeline-Schritt für automatischen Download von BDEW-Daten.

    Lädt aktuelle BDEW-Daten direkt von der offiziellen Website
    und speichert sie für die weitere Verarbeitung.
    """

    def __init__(self, cache_dir: Path | None = None):
        """Initialize BDEW Web Download Step."""
        super().__init__(
            name="BDEW Web Download",
            description="Download aktueller BDEW-Daten von der offiziellen Website",
        )
        self.cache_dir = cache_dir or Path("data/cache/bdew")

    async def execute(self, context: dict[str, Any]) -> PipelineStepResult:
        """Download BDEW-Daten von der offiziellen Website."""
        try:
            # BDEW Web Data Source initialisieren
            bdew_web = BDEWWebDataSource(cache_dir=self.cache_dir)

            # Verbindung herstellen
            connected = await bdew_web.connect()
            if not connected:
                return PipelineStepResult(
                    status=PipelineStepStatus.FAILED,
                    message="Failed to connect to BDEW web API",
                )

            try:
                # Daten herunterladen
                operators = await bdew_web.fetch_data()

                # Daten validieren
                is_valid = await bdew_web.validate_data(operators)
                if not is_valid:
                    return PipelineStepResult(
                        status=PipelineStepStatus.FAILED,
                        message="Downloaded BDEW data failed validation",
                    )

                # Download-Statistiken
                stats = bdew_web.get_download_stats()

                # Cache-Datei erstellen für weitere Verarbeitung
                cache_file = (
                    self.cache_dir
                    / f"bdew_operators_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )

                # Cache-Datei speichern
                with cache_file.open("w", encoding="utf-8") as f:
                    json.dump(operators, f, ensure_ascii=False, indent=2)

                # Daten im Context für nachfolgende Steps bereitstellen
                context["bdew_data"] = operators
                context["cache_file"] = str(cache_file)
                context["download_stats"] = stats

                return PipelineStepResult(
                    status=PipelineStepStatus.SUCCESS,
                    data=operators,
                    message=f"Successfully downloaded {len(operators)} BDEW operators",
                    metrics={
                        "total_records": len(operators),
                        "active_operators": stats.get("active_operators", 0),
                        "inactive_operators": stats.get("inactive_operators", 0),
                        "pages_fetched": stats.get("pages_fetched", 0),
                        "cache_file": str(cache_file),
                        "data_source": "BDEW Web API",
                        "download_time": context.get("processing_time", 0),
                        "quality_score": (
                            sum(op.get("data_quality_score", 0) for op in operators)
                            / len(operators)
                            if operators
                            else 0
                        ),
                    },
                )

            finally:
                # Verbindung schließen
                await bdew_web.disconnect()

        except Exception as e:
            return PipelineStepResult(
                status=PipelineStepStatus.FAILED,
                message=f"BDEW download failed: {e!s}",
                error=e,
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
        """
        Validate BDEW data and compute quality scores.

        Args:
            context: Pipeline context containing 'bdew_data' key

        Returns:
            PipelineStepResult with validation results and quality metrics
        """
        try:
            # Daten aus Context laden
            bdew_data = context.get("bdew_data", [])

            if not bdew_data:
                return PipelineStepResult(
                    status=PipelineStepStatus.FAILED,
                    message="No BDEW data found in context for validation",
                )

            # Validierungsregeln definieren
            validation_rules = [
                {
                    "field": "bdew_code",
                    "required": True,
                    "min_length": MIN_BDEW_CODE_LENGTH,
                },
                {
                    "field": "company_name",
                    "required": True,
                    "min_length": MIN_COMPANY_NAME_LENGTH,
                },
                {
                    "field": "city",
                    "required": False,
                    "min_length": MIN_CITY_NAME_LENGTH,
                },
            ]

            validated_records = []
            validation_errors = []

            for i, record in enumerate(bdew_data):
                try:
                    validated_record = await self._validate_record(
                        record, validation_rules
                    )
                    validated_records.append(validated_record)
                except Exception as e:
                    validation_errors.append(f"Record {i}: {e}")

            # Statistiken erstellen
            total_records = len(bdew_data)
            valid_records = len(validated_records)
            error_count = len(validation_errors)

            if error_count > total_records * 0.1:  # Mehr als 10% Fehler
                return PipelineStepResult(
                    status=PipelineStepStatus.FAILED,
                    message=f"Too many validation errors: {error_count}/{total_records}",
                    errors=validation_errors[
                        :MAX_VALIDATION_ERRORS_DISPLAYED
                    ],  # Erste 10 Fehler
                )

            # Validierte Daten im Context speichern
            context["validated_data"] = validated_records
            context["validation_stats"] = {
                "total_records": total_records,
                "valid_records": valid_records,
                "error_count": error_count,
                "validation_errors": validation_errors,
            }

            return PipelineStepResult(
                status=PipelineStepStatus.SUCCESS,
                data=validated_records,
                message=f"Successfully validated {valid_records}/{total_records} records",
                metrics={
                    "total_records": total_records,
                    "valid_records": valid_records,
                    "error_count": error_count,
                    "error_rate": (
                        error_count / total_records if total_records > 0 else 0
                    ),
                },
            )

        except Exception as e:
            return PipelineStepResult(
                status=PipelineStepStatus.FAILED,
                message=f"Validation step failed: {e!s}",
                error=e,
            )

    async def _validate_record(
        self, record: dict[str, Any], rules: list
    ) -> dict[str, Any]:
        """Validiere einzelnen Datensatz."""
        validated_record = record.copy()

        for rule in rules:
            field = rule["field"]
            value = record.get(field)

            if rule.get("required", False) and not value:
                raise ValueError(f"Required field '{field}' is missing or empty")

                if (
                    value
                    and rule.get("min_length")
                    and len(str(value)) < rule["min_length"]
                ):
                    raise ValueError(
                        f"Field '{field}' too short: {len(str(value))} < {rule['min_length']}"
                    )  # Qualitäts-Score berechnen
        quality_score = self._calculate_quality_score(record)
        validated_record["data_quality_score"] = quality_score

        return validated_record

    def _calculate_quality_score(self, record: dict[str, Any]) -> int:
        """Berechne Datenqualitäts-Score für Datensatz."""
        score = 0

        # BDEW Code Qualität (30 Punkte)
        code = record.get("bdew_code", "")
        if code and len(code) >= MIN_BDEW_CODE_LENGTH:
            score += 30

        # Firmenname Qualität (40 Punkte)
        name = record.get("company_name", "")
        if name:
            if len(name) >= MIN_COMPANY_NAME_LENGTH:
                score += 20
            if len(name.split()) >= MIN_COMPANY_NAME_WORDS:
                score += 10
            if not any(word in name.lower() for word in ["test", "dummy", "example"]):
                score += 10

        # Stadt-Information (20 Punkte)
        city = record.get("city", "")
        if city and len(city) >= MIN_CITY_NAME_LENGTH:
            score += 20

        # Gültigkeit (10 Punkte)
        valid_from = record.get("valid_from")
        if valid_from:
            score += 10

        return score


class BDEWPersistenceStep(PipelineStep):
    """
    Pipeline-Schritt für BDEW-Datenpersistierung.

    Speichert validierte BDEW-Daten in die Datenbank und
    führt Deduplizierung und Aktualisierung durch.
    """

    def __init__(self, repository: BDEWRepository):
        super().__init__(
            name="persist_bdew_data",
            description="Speichere validierte BDEW-Daten in Datenbank",
        )
        self.repository = repository

    async def execute(self, context: dict[str, Any]) -> PipelineStepResult:
        """
        Save validated BDEW data to database.

        Args:
            context: Pipeline context containing 'validated_data' key

        Returns:
            PipelineStepResult with persistence results and statistics
        """
        try:
            # Validierte Daten aus Context laden
            validated_data = context.get("validated_data", [])

            if not validated_data:
                return PipelineStepResult(
                    status=PipelineStepStatus.FAILED,
                    message="No validated data found in context for persistence",
                )

            # Daten in DB-Format konvertieren
            db_records = []
            for record in validated_data:
                db_record = self._convert_to_db_format(record, context)
                db_records.append(db_record)

            # Batch-Insert/Update
            created_count = 0
            updated_count = 0
            error_count = 0

            for db_record in db_records:
                try:
                    # Prüfe ob Datensatz bereits existiert
                    existing = self.repository.find_by_code(
                        db_record["network_operator_id"]
                    )

                    if existing:
                        # Update
                        self.repository.update(existing.id, db_record)
                        updated_count += 1
                    else:
                        # Create
                        self.repository.create(db_record)
                        created_count += 1

                except Exception as e:
                    error_count += 1
                    logging.warning(f"Failed to persist record: {e}")

            # Ergebnisse im Context speichern
            context["persistence_stats"] = {
                "created_count": created_count,
                "updated_count": updated_count,
                "error_count": error_count,
                "total_processed": len(db_records),
            }

            return PipelineStepResult(
                status=PipelineStepStatus.SUCCESS,
                message=f"Persisted {created_count + updated_count} records "
                f"({created_count} new, {updated_count} updated)",
                metrics={
                    "created_count": created_count,
                    "updated_count": updated_count,
                    "error_count": error_count,
                    "total_processed": len(db_records),
                },
            )

        except Exception as e:
            return PipelineStepResult(
                status=PipelineStepStatus.FAILED,
                message=f"Persistence step failed: {e!s}",
                error=e,
            )

    def _convert_to_db_format(
        self, record: dict[str, Any], _context: dict[str, Any]
    ) -> dict[str, Any]:
        """Konvertiere Datensatz in Datenbank-Format."""
        return {
            "network_operator_id": record.get("bdew_code"),
            "company_name": record.get("company_name"),
            "city": record.get("city"),
            "valid_from": record.get("valid_from"),
            "valid_until": record.get("valid_until"),
            "is_active": record.get("is_active", True),
            "data_quality_score": record.get("data_quality_score", 0),
            "data_source": record.get("data_source", "BDEW"),
            "import_timestamp": datetime.now(),
            "raw_data": record.get("raw_data", {}),
        }


class BDEWImportLoggingStep(PipelineStep):
    """
    Pipeline-Schritt für Import-Logging.

    Erstellt detaillierte Logs über den Import-Vorgang
    für Auditing und Monitoring.
    """

    def __init__(self, repository: BDEWRepository):
        super().__init__(
            name="log_bdew_import",
            description="Erstelle Import-Log für Auditing",
        )
        self.repository = repository

    async def execute(self, context: dict[str, Any]) -> PipelineStepResult:
        """
        Create comprehensive import log for auditing and monitoring.

        Args:
            context: Pipeline context containing statistics from all previous steps

        Returns:
            PipelineStepResult with logging results and final statistics
        """
        try:
            # Sammle alle Statistiken aus dem Context
            download_stats = context.get("download_stats", {})
            validation_stats = context.get("validation_stats", {})
            persistence_stats = context.get("persistence_stats", {})

            # Import-Log-Eintrag erstellen
            import_log = {
                "source": context.get("source", "Unknown"),
                "import_timestamp": datetime.now(),
                "cache_file": context.get("cache_file"),
                "file_hash": (
                    self._calculate_file_hash(context["cache_file"])
                    if context.get("cache_file")
                    else None
                ),
                "download_stats": download_stats,
                "validation_stats": validation_stats,
                "persistence_stats": persistence_stats,
                "status": "SUCCESS",
                "errors": [],
            }

            # Log in Repository speichern (falls verfügbar)
            try:
                # Hier könnte ein ImportLog-Repository verwendet werden
                pass
            except Exception as e:
                logging.warning(f"Failed to persist import log: {e}")

            # Strukturiertes Logging
            logging.info("📊 BDEW Import Summary:")
            logging.info(f"  Source: {import_log['source']}")
            logging.info(
                f"  Downloaded: {download_stats.get('total_downloaded', 0)} records"
            )
            logging.info(
                f"  Validated: {validation_stats.get('valid_records', 0)} records"
            )
            logging.info(
                f"  Created: {persistence_stats.get('created_count', 0)} records"
            )
            logging.info(
                f"  Updated: {persistence_stats.get('updated_count', 0)} records"
            )

            if validation_stats.get("error_count", 0) > 0:
                logging.warning(
                    f"  Validation errors: {validation_stats['error_count']}"
                )

            if persistence_stats.get("error_count", 0) > 0:
                logging.warning(
                    f"  Persistence errors: {persistence_stats['error_count']}"
                )

            return PipelineStepResult(
                status=PipelineStepStatus.SUCCESS,
                message="Import logging completed successfully",
                data=import_log,
                metrics={
                    "log_created": True,
                    "total_records_processed": (
                        persistence_stats.get("total_processed", 0)
                    ),
                },
            )

        except Exception as e:
            return PipelineStepResult(
                status=PipelineStepStatus.FAILED,
                message=f"Logging step failed: {e!s}",
                error=e,
            )

    def _calculate_file_hash(self, file_path: str) -> str:
        """Berechne SHA-256 Hash einer Datei."""
        try:
            with Path(file_path).open("rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            return file_hash
        except Exception:
            return ""


def create_bdew_import_pipeline(
    repository: BDEWRepository | None = None,
) -> Pipeline:
    """
    Erstelle eine Standard-BDEW-Import-Pipeline.

    Diese Pipeline lädt BDEW-Daten aus lokalen Dateien und verarbeitet sie.

    Args:
        repository: BDEW Repository Instanz

    Returns:
        Konfigurierte Pipeline-Instanz
    """
    if not repository:
        raise ValueError("Repository is required for BDEW import pipeline")

    pipeline = Pipeline("BDEW Import Pipeline")

    # Steps hinzufügen
    pipeline.add_step(BDEWValidationStep(repository))
    pipeline.add_step(BDEWPersistenceStep(repository))
    pipeline.add_step(BDEWImportLoggingStep(repository))

    return pipeline


def create_bdew_web_import_pipeline(
    repository: BDEWRepository | None = None,
    cache_dir: Path | None = None,
) -> Pipeline:
    """
    Erstelle eine BDEW-Web-Import-Pipeline mit automatischem Download.

    Diese Pipeline lädt BDEW-Daten automatisch von der offiziellen Website
    herunter und verarbeitet sie vollständig.

    Args:
        repository: BDEW Repository Instanz
        cache_dir: Verzeichnis für Cache-Dateien

    Returns:
        Konfigurierte Pipeline-Instanz mit Web-Download
    """
    if not repository:
        raise ValueError("Repository is required for BDEW web import pipeline")

    pipeline = Pipeline("BDEW Web Import Pipeline")

    # Steps hinzufügen (in der richtigen Reihenfolge)
    pipeline.add_step(BDEWWebDownloadStep(cache_dir))  # 1. Download von Web
    pipeline.add_step(BDEWValidationStep(repository))  # 2. Validierung
    pipeline.add_step(BDEWPersistenceStep(repository))  # 3. Speicherung
    pipeline.add_step(BDEWImportLoggingStep(repository))  # 4. Logging

    return pipeline


async def run_bdew_import_example() -> None:
    """Beispiel-Ausführung der BDEW-Web-Import-Pipeline."""
    # Logging konfigurieren
    setup_logging()
    logger = logging.getLogger("bdew_import_example")
    logger.info("🚀 Starte BDEW Web Import Beispiel...")

    try:
        # Datenbank-Setup für Test
        engine = create_engine("sqlite:///test_bdew.db")
        SessionLocal = sessionmaker(bind=engine)

        with SessionLocal() as session:
            repository = BDEWRepository(session)

            # Pipeline mit Web-Download erstellen
            pipeline = create_bdew_web_import_pipeline(
                repository=repository, cache_dir=Path("data/cache/bdew")
            )

            # Pipeline ausführen
            context = {
                "source": "BDEW Web API",
                "batch_size": 100,
            }

            results = await pipeline.execute(context)

            # Ergebnisse analysieren
            success_count = 0
            error_count = 0
            total_records = 0

            for step_name, step_result in results.items():
                logger.info(f"Step {step_name}: {step_result.status.value}")

                if step_result.status == PipelineStepStatus.SUCCESS:
                    success_count += 1
                    if step_result.metrics:
                        total_records += step_result.metrics.get("total_records", 0)
                else:
                    error_count += 1
                    if step_result.error:
                        logger.error(f"  Error: {step_result.error}")

            if error_count == 0:
                logger.info("✅ BDEW Web Import erfolgreich abgeschlossen")
                logger.info(f"📊 Verarbeitete Datensätze: {total_records}")
            else:
                logger.error(
                    f"❌ BDEW Web Import mit {error_count} Fehlern abgeschlossen"
                )

    except Exception as e:
        logger.error(f"💥 Unerwarteter Fehler: {e}")
        raise


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_bdew_import_example())
