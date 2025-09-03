"""
Basis-Pipeline-Architektur für VNB Digitaler.

Dieses Modul definiert die grundlegenden Klassen und Interfaces
für die modulare Datenverarbeitungs-Pipeline.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

from ..logging_config import PipelineLogger, get_pipeline_logger


class PipelineStepStatus(Enum):
    """Status eines Pipeline-Schritts."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStepResult:
    """Ergebnis eines Pipeline-Schritts."""

    def __init__(
        self,
        status: PipelineStepStatus,
        data: Any | None = None,
        message: str | None = None,
        metrics: dict[str, Any] | None = None,
        error: Exception | None = None,
    ):
        self.status = status
        self.data = data
        self.message = message
        self.metrics = metrics or {}
        self.error = error
        self.timestamp = datetime.now()


class PipelineStep(ABC):
    """
    Abstrakte Basisklasse für Pipeline-Schritte.

    Jeder Pipeline-Schritt implementiert eine spezifische
    Verarbeitungslogik und kann mit anderen Schritten
    zu einer vollständigen Pipeline verknüpft werden.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.status = PipelineStepStatus.PENDING
        self.result: PipelineStepResult | None = None
        self.dependencies: list[str] = []

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> PipelineStepResult:
        """
        Führe den Pipeline-Schritt aus.

        Args:
            context: Pipeline-Kontext mit Daten und Konfiguration

        Returns:
            PipelineStepResult: Ergebnis der Ausführung
        """
        pass

    def add_dependency(self, step_name: str) -> None:
        """Füge Abhängigkeit zu anderem Pipeline-Schritt hinzu."""
        if step_name not in self.dependencies:
            self.dependencies.append(step_name)

    def can_execute(self, completed_steps: list[str]) -> bool:
        """Prüfe ob alle Abhängigkeiten erfüllt sind."""
        return all(dep in completed_steps for dep in self.dependencies)


class DataExtractorStep(PipelineStep):
    """
    Pipeline-Schritt für Datenextraktion.

    Extrahiert Daten aus einer Datenquelle und stellt sie
    für nachfolgende Schritte bereit.
    """

    def __init__(self, name: str, data_source: Any, description: str = ""):
        super().__init__(name, description)
        self.data_source = data_source

    async def execute(
        self, context: dict[str, Any]  # noqa: ARG002
    ) -> PipelineStepResult:
        """Extrahiere Daten aus der konfigurierten Datenquelle."""
        try:
            # Verbindung zur Datenquelle herstellen
            await self.data_source.connect()

            # Daten laden
            data = await self.data_source.fetch_data()

            # Daten validieren
            is_valid = await self.data_source.validate_data(data)

            if not is_valid:
                return PipelineStepResult(
                    status=PipelineStepStatus.FAILED,
                    message="Datenvalidierung fehlgeschlagen",
                )

            metrics = {"record_count": len(data), "source_name": self.data_source.name}

            if hasattr(self.data_source, "metadata") and self.data_source.metadata:
                metrics.update(
                    {
                        "last_updated": (
                            self.data_source.metadata.last_updated.isoformat()
                            if self.data_source.metadata.last_updated
                            else None
                        ),
                        "version": self.data_source.metadata.version,
                    }
                )

            return PipelineStepResult(
                status=PipelineStepStatus.SUCCESS,
                data=data,
                message=f"Erfolgreich {len(data)} Datensätze extrahiert",
                metrics=metrics,
            )

        except Exception as e:
            return PipelineStepResult(
                status=PipelineStepStatus.FAILED,
                message=f"Extraktion fehlgeschlagen: {e!s}",
                error=e,
            )
        finally:
            # Verbindung trennen
            await self.data_source.disconnect()


class DataValidatorStep(PipelineStep):
    """
    Pipeline-Schritt für Datenvalidierung.

    Validiert Daten gegen definierte Regeln und
    Qualitätskriterien.
    """

    def __init__(self, name: str, validator: Any, description: str = ""):
        super().__init__(name, description)
        self.validator = validator

    async def execute(self, context: dict[str, Any]) -> PipelineStepResult:
        """Validiere Daten mit dem konfigurierten Validator."""
        try:
            # Daten aus Kontext holen
            data = context.get("data")
            if data is None:
                return PipelineStepResult(
                    status=PipelineStepStatus.FAILED,
                    message="Keine Daten für Validierung verfügbar",
                )

            # Validierung durchführen
            validation_result = await self.validator.validate(data)

            if validation_result.is_valid:
                return PipelineStepResult(
                    status=PipelineStepStatus.SUCCESS,
                    data=data,
                    message="Datenvalidierung erfolgreich",
                    metrics=validation_result.metrics,
                )
            else:
                return PipelineStepResult(
                    status=PipelineStepStatus.FAILED,
                    message=f"Validierung fehlgeschlagen: {validation_result.error_message}",
                    metrics=validation_result.metrics,
                )

        except Exception as e:
            return PipelineStepResult(
                status=PipelineStepStatus.FAILED,
                message=f"Validierung fehlgeschlagen: {e!s}",
                error=e,
            )


class DataTransformerStep(PipelineStep):
    """
    Pipeline-Schritt für Datentransformation.

    Transformiert Daten von einem Format in ein anderes.
    """

    def __init__(self, name: str, transformer: Any, description: str = ""):
        super().__init__(name, description)
        self.transformer = transformer

    async def execute(self, context: dict[str, Any]) -> PipelineStepResult:
        """Transformiere Daten mit dem konfigurierten Transformer."""
        try:
            # Daten aus Kontext holen
            data = context.get("data")
            if data is None:
                return PipelineStepResult(
                    status=PipelineStepStatus.FAILED,
                    message="Keine Daten für Transformation verfügbar",
                )

            # Transformation durchführen
            transformed_data = await self.transformer.transform(data)

            metrics = {
                "input_count": len(data) if isinstance(data, list) else 1,
                "output_count": (
                    len(transformed_data) if isinstance(transformed_data, list) else 1
                ),
            }

            return PipelineStepResult(
                status=PipelineStepStatus.SUCCESS,
                data=transformed_data,
                message="Datentransformation erfolgreich",
                metrics=metrics,
            )

        except Exception as e:
            return PipelineStepResult(
                status=PipelineStepStatus.FAILED,
                message=f"Transformation fehlgeschlagen: {e!s}",
                error=e,
            )


class Pipeline:
    """
    Hauptklasse für Datenverarbeitungs-Pipelines.

    Orchestriert die Ausführung von Pipeline-Schritten
    und verwaltet Abhängigkeiten und Kontext.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: dict[str, PipelineStep] = {}
        self.execution_order: list[str] = []
        self.context: dict[str, Any] = {}
        self.logger: PipelineLogger = get_pipeline_logger(name)
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None

    def add_step(self, step: PipelineStep) -> None:
        """Füge Pipeline-Schritt hinzu."""
        self.steps[step.name] = step
        self._calculate_execution_order()

    def _calculate_execution_order(self) -> None:
        """Berechne Ausführungsreihenfolge basierend auf Abhängigkeiten."""
        # Topologische Sortierung für Abhängigkeitsauflösung
        visited = set()
        temp_visited = set()
        order = []

        def visit(step_name: str):
            if step_name in temp_visited:
                raise ValueError(f"Zirkuläre Abhängigkeit erkannt bei: {step_name}")

            if step_name not in visited:
                temp_visited.add(step_name)

                step = self.steps[step_name]
                for dep in step.dependencies:
                    if dep in self.steps:
                        visit(dep)

                temp_visited.remove(step_name)
                visited.add(step_name)
                order.append(step_name)

        for step_name in self.steps:
            if step_name not in visited:
                visit(step_name)

        self.execution_order = order

    async def execute(
        self, initial_context: dict[str, Any] | None = None
    ) -> dict[str, PipelineStepResult]:
        """
        Führe Pipeline aus.

        Args:
            initial_context: Initialer Kontext für Pipeline

        Returns:
            Dict[str, PipelineStepResult]: Ergebnisse aller Schritte
        """
        self.start_time = datetime.now()
        self.context = initial_context or {}
        results: dict[str, PipelineStepResult] = {}
        completed_steps: list[str] = []

        self.logger.start_pipeline(
            description=self.description, step_count=len(self.steps)
        )

        try:
            for step_name in self.execution_order:
                step = self.steps[step_name]

                # Prüfe Abhängigkeiten
                if not step.can_execute(completed_steps):
                    self.logger.step(
                        step_name,
                        status="skipped",
                        reason="Abhängigkeiten nicht erfüllt",
                    )
                    results[step_name] = PipelineStepResult(
                        status=PipelineStepStatus.SKIPPED,
                        message="Abhängigkeiten nicht erfüllt",
                    )
                    continue

                # Schritt ausführen
                self.logger.step(step_name, description=step.description)
                step.status = PipelineStepStatus.RUNNING

                result = await step.execute(self.context)
                results[step_name] = result
                step.result = result
                step.status = result.status

                # Kontext aktualisieren bei Erfolg
                if (
                    result.status == PipelineStepStatus.SUCCESS
                    and result.data is not None
                ):
                    self.context["data"] = result.data
                    completed_steps.append(step_name)

                    self.logger.step(
                        step_name,
                        status="success",
                        message=result.message,
                        metrics=result.metrics,
                    )
                else:
                    self.logger.step(step_name, status="failed", message=result.message)

                    # Bei kritischen Fehlern Pipeline abbrechen
                    if result.status == PipelineStepStatus.FAILED:
                        break

            self.end_time = datetime.now()

            # Pipeline-Erfolg bestimmen
            failed_steps = [
                name
                for name, result in results.items()
                if result.status == PipelineStepStatus.FAILED
            ]

            if not failed_steps:
                self.logger.success(
                    completed_steps=len(completed_steps), total_steps=len(self.steps)
                )
            else:
                self.logger.error(
                    f"Pipeline fehlgeschlagen bei Schritten: {failed_steps}",
                    failed_steps=failed_steps,
                )

            return results

        except Exception as e:
            self.end_time = datetime.now()
            self.logger.error(f"Unerwarteter Pipeline-Fehler: {e!s}")
            raise

    def get_execution_time(self) -> float | None:
        """Hole Ausführungszeit in Sekunden."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
