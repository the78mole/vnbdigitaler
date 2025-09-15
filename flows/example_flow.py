"""
VNB Digitaler - Example Prefect Flow
Demonstriert grundlegende Prefect-Funktionalität für das Projekt.
"""

import asyncio
from datetime import datetime
from pathlib import Path

from prefect import flow, get_run_logger, task

# Constants for magic numbers
MIN_QUALITY_SCORE = 0.9
MAX_DATA_FRESHNESS_HOURS = 24


@task
async def fetch_data_info() -> dict:
    """Simuliert das Abrufen von Dateninformationen."""
    logger = get_run_logger()

    # Simuliere API-Aufruf oder Datenbankabfrage
    data_info = {
        "filename": "Roll-out-Quoten_Q1_2025.csv",
        "size_mb": 2.5,
        "last_modified": datetime.now().isoformat(),
        "source": "external_api",
    }

    logger.info(f"Dateninfo abgerufen: {data_info['filename']}")
    return data_info


@task
async def validate_data_source(data_info: dict) -> bool:
    """Validiert die Datenquelle."""
    logger = get_run_logger()

    # Simuliere Validierung
    valid_sources = ["external_api", "manual_upload", "scheduled_import"]
    is_valid = data_info.get("source") in valid_sources

    if is_valid:
        logger.info(f"Datenquelle '{data_info['source']}' ist gültig")
    else:
        logger.warning(f"Ungültige Datenquelle: {data_info['source']}")

    return is_valid


@task
async def simulate_csv_analysis_task() -> dict:
    """
    Simuliert die CSV-Analyse - ähnlich wie das existierende analyze_rollout_csv.py.
    """
    logger = get_run_logger()

    # Simuliere CSV-Verarbeitung
    await asyncio.sleep(0.5)  # Simuliere Verarbeitungszeit

    analysis_result = {
        "rows_processed": 1245,
        "columns_found": ["Verteilnetzbetreiber", "Rollout_Quote_Q1_2025", "Region"],
        "quality_score": 0.95,
        "warnings": [],
        "data_freshness_hours": 12,
        "summary": "Erfolgreiche Analyse der Rollout-Daten",
    }

    logger.info(
        f"CSV-Analyse abgeschlossen: {analysis_result['rows_processed']} Zeilen verarbeitet"
    )
    return analysis_result


@task
async def generate_report(analysis: dict, data_info: dict) -> dict:
    """Generiert einen Bericht basierend auf der Analyse."""
    logger = get_run_logger()

    # Simuliere Berichtsgenerierung
    await asyncio.sleep(0.3)

    report = {
        "report_id": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "data_source": data_info["filename"],
        "analysis_summary": analysis["summary"],
        "quality_check": (
            "PASSED" if analysis["quality_score"] >= MIN_QUALITY_SCORE else "FAILED"
        ),
        "freshness_check": (
            "PASSED"
            if analysis["data_freshness_hours"] <= MAX_DATA_FRESHNESS_HOURS
            else "FAILED"
        ),
        "recommendations": [],
    }

    # Qualitätsprüfungen
    if analysis["quality_score"] < MIN_QUALITY_SCORE:
        report["recommendations"].append(
            f"Datenqualität verbessern (aktuell: {analysis['quality_score']})"
        )

    if analysis["data_freshness_hours"] > MAX_DATA_FRESHNESS_HOURS:
        report["recommendations"].append(
            f"Daten aktualisieren (alter: {analysis['data_freshness_hours']}h)"
        )

    logger.info(f"Bericht generiert: {report['report_id']}")
    return report


@task
async def save_results(report: dict) -> str:
    """Speichert die Ergebnisse in eine Datei."""
    logger = get_run_logger()

    # Simuliere Speicherung
    output_dir = Path("tmp/prefect_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{report['report_id']}.txt"

    # Einfache Textspeicherung für Demo
    report_content = f"""
VNB Digitaler - Analysebericht
==============================
Bericht-ID: {report["report_id"]}
Datenquelle: {report["data_source"]}
Zusammenfassung: {report["analysis_summary"]}
Qualitätsprüfung: {report["quality_check"]}
Aktualitätsprüfung: {report["freshness_check"]}

Empfehlungen:
{chr(10).join(f"- {rec}" for rec in report["recommendations"]) if report["recommendations"] else "Keine Empfehlungen"}
"""

    output_file.write_text(report_content.strip())

    logger.info(f"Ergebnisse gespeichert in: {output_file}")
    return str(output_file)


@flow(name="vnb-digitaler-example-flow")
async def vnb_digitaler_example_flow():
    """
    Hauptflow für VNB Digitaler - Demonstriert die Analyse von Rollout-Daten.
    """
    logger = get_run_logger()
    logger.info("Starte VNB Digitaler Example Flow")

    # Schritt 1: Dateninfo abrufen
    data_info = await fetch_data_info()

    # Schritt 2: Datenquelle validieren
    is_valid = await validate_data_source(data_info)

    if not is_valid:
        logger.error("Datenquelle ist ungültig - Flow wird beendet")
        return {"status": "failed", "reason": "invalid_data_source"}

    # Schritt 3: CSV-Analyse durchführen
    analysis = await simulate_csv_analysis_task()

    # Schritt 4: Bericht generieren
    report = await generate_report(analysis, data_info)

    # Schritt 5: Ergebnisse speichern
    output_file = await save_results(report)

    logger.info("VNB Digitaler Example Flow erfolgreich abgeschlossen")

    return {
        "status": "success",
        "report_id": report["report_id"],
        "output_file": output_file,
        "quality_score": analysis["quality_score"],
        "rows_processed": analysis["rows_processed"],
    }


if __name__ == "__main__":
    # Für lokale Ausführung
    import asyncio

    async def main():
        result = await vnb_digitaler_example_flow()
        print(f"Flow-Ergebnis: {result}")

    asyncio.run(main())
