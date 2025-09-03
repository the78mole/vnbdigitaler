#!/usr/bin/env python3
"""
Test-Script für BDEW Web Download Pipeline.

Dieses Script demonstriert die neue Web-Download-Funktionalität
der BDEW-Pipeline, die automatisch Daten von der BDEW-Website lädt.
"""

import asyncio
import sys
from pathlib import Path

# Pfad zur src hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.logging_config import setup_logging

from data_sources.bdew_web import BDEWWebDataSource
from pipelines.bdew_import import BDEWWebDownloadStep


async def test_bdew_web_data_source():
    """Teste die BDEW Web Data Source direkt."""
    print("🧪 Teste BDEW Web Data Source...")

    cache_dir = Path("tmp/test_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    data_source = BDEWWebDataSource(cache_dir=cache_dir)

    try:
        # Lade die ersten 50 Datensätze
        data = await data_source.fetch_data(max_records=50)

        print(f"✅ {len(data)} Datensätze erfolgreich geladen")

        if data:
            sample = data[0]
            print("📋 Beispiel-Datensatz:")
            for key, value in sample.items():
                print(f"  {key}: {value}")

        return data

    except Exception as e:
        print(f"❌ Fehler beim Laden der Daten: {e}")
        return []


async def test_web_download_step():
    """Teste den Web-Download-Step isoliert."""
    print("\n🧪 Teste BDEW Web Download Step...")

    cache_dir = Path("tmp/test_cache")
    step = BDEWWebDownloadStep(cache_dir=cache_dir)

    context = {
        "source": "BDEW Web API Test",
        "max_records": 25,
    }

    try:
        result = await step.execute(context)

        print(f"✅ Step Status: {result.status.value}")
        print(f"📊 Metriken: {result.metrics}")

        if result.status.name == "SUCCESS" and result.data:
            print(f"📋 {len(result.data)} Datensätze erhalten")

        return result

    except Exception as e:
        print(f"❌ Fehler beim Download-Step: {e}")
        return None


async def main():
    """Hauptfunktion für alle Tests."""
    print("🚀 BDEW Web Download Test Suite")
    print("=" * 50)

    # Logging konfigurieren
    setup_logging()

    # Test 1: Data Source direkt
    await test_bdew_web_data_source()

    # Test 2: Download Step isoliert
    await test_web_download_step()

    print("\n✅ Alle Tests abgeschlossen!")
    print("\n💡 Hinweis: Die vollständige Pipeline kann mit:")
    print("   python -m src.pipelines.bdew_import")
    print("   getestet werden.")


if __name__ == "__main__":
    asyncio.run(main())
