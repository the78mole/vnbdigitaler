"""
Tests für die Pipeline-Architektur.

Einfache Tests zur Validierung der neuen Pipeline-Struktur.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.data_sources.base import DataSource
from src.pipelines.base import (
    DataExtractorStep,
    Pipeline,
    PipelineStep,
    PipelineStepResult,
    PipelineStepStatus,
)


class MockDataSource(DataSource):
    """Mock-Datenquelle für Tests."""

    def __init__(self, name: str, test_data: list):
        super().__init__(name)
        self.test_data = test_data

    async def connect(self) -> bool:
        return True

    async def disconnect(self) -> bool:
        return True

    async def check_for_updates(self) -> bool:
        return True

    async def fetch_data(self):
        return self.test_data

    async def validate_data(self, data):
        return len(data) > 0


class MockPipelineStep(PipelineStep):
    """Mock-Pipeline-Schritt für Tests."""

    def __init__(self, name: str, should_fail: bool = False):
        super().__init__(name, f"Test step {name}")
        self.should_fail = should_fail

    async def execute(self, context):
        if self.should_fail:
            return PipelineStepResult(
                status=PipelineStepStatus.FAILED, message="Test failure"
            )
        else:
            return PipelineStepResult(
                status=PipelineStepStatus.SUCCESS,
                data={"test": "data"},
                message="Test success",
            )


@pytest.mark.asyncio
async def test_pipeline_basic_execution():
    """Test grundlegende Pipeline-Ausführung."""
    pipeline = Pipeline("test_pipeline", "Test pipeline")

    step1 = MockPipelineStep("step1")
    step2 = MockPipelineStep("step2")

    pipeline.add_step(step1)
    pipeline.add_step(step2)

    results = await pipeline.execute()

    assert len(results) == 2
    assert results["step1"].status == PipelineStepStatus.SUCCESS
    assert results["step2"].status == PipelineStepStatus.SUCCESS


@pytest.mark.asyncio
async def test_pipeline_with_dependencies():
    """Test Pipeline mit Abhängigkeiten."""
    pipeline = Pipeline("test_pipeline", "Test pipeline with dependencies")

    step1 = MockPipelineStep("step1")
    step2 = MockPipelineStep("step2")
    step2.add_dependency("step1")

    pipeline.add_step(step2)  # Reihenfolge absichtlich vertauscht
    pipeline.add_step(step1)

    results = await pipeline.execute()

    # step1 sollte vor step2 ausgeführt werden
    assert results["step1"].status == PipelineStepStatus.SUCCESS
    assert results["step2"].status == PipelineStepStatus.SUCCESS


@pytest.mark.asyncio
async def test_pipeline_failure_handling():
    """Test Pipeline-Verhalten bei Fehlern."""
    pipeline = Pipeline("test_pipeline", "Test pipeline with failure")

    step1 = MockPipelineStep("step1", should_fail=True)
    step2 = MockPipelineStep("step2")
    step2.add_dependency("step1")

    pipeline.add_step(step1)
    pipeline.add_step(step2)

    results = await pipeline.execute()

    assert results["step1"].status == PipelineStepStatus.FAILED
    # step2 wird nicht ausgeführt/zurückgegeben da Pipeline bei step1 Fehler abbricht
    assert "step2" not in results


@pytest.mark.asyncio
async def test_data_extractor_step():
    """Test DataExtractorStep."""
    test_data = [{"id": 1, "name": "Test Company"}]
    mock_source = MockDataSource("test_source", test_data)

    extractor = DataExtractorStep("extract", mock_source)

    result = await extractor.execute({})

    assert result.status == PipelineStepStatus.SUCCESS
    assert result.data == test_data
    assert result.metrics["record_count"] == 1


def test_pipeline_step_dependencies():
    """Test Abhängigkeits-Management."""
    step = MockPipelineStep("test_step")

    step.add_dependency("step1")
    step.add_dependency("step2")

    assert "step1" in step.dependencies
    assert "step2" in step.dependencies

    # Kann nicht ausgeführt werden ohne Abhängigkeiten
    assert not step.can_execute([])
    assert not step.can_execute(["step1"])

    # Kann ausgeführt werden mit allen Abhängigkeiten
    assert step.can_execute(["step1", "step2"])


if __name__ == "__main__":
    # Einfacher Test-Runner für lokale Entwicklung
    async def run_tests():
        print("🧪 Teste Pipeline-Architektur...")

        try:
            await test_pipeline_basic_execution()
            print("✅ Grundlegende Pipeline-Ausführung")

            await test_pipeline_with_dependencies()
            print("✅ Pipeline mit Abhängigkeiten")

            await test_pipeline_failure_handling()
            print("✅ Pipeline Fehlerbehandlung")

            await test_data_extractor_step()
            print("✅ DataExtractorStep")

            test_pipeline_step_dependencies()
            print("✅ Pipeline-Schritt Abhängigkeiten")

            print("\n🎉 Alle Tests erfolgreich!")

        except Exception as e:
            print(f"❌ Test fehlgeschlagen: {e}")
            raise

    asyncio.run(run_tests())
