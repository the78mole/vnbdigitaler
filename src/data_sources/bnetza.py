"""
BNetzA Datenquellen-Adapter.

Adapter für Bundesnetzagentur (BNetzA) Rollout-Berichte.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .base import (
    DataSourceError,
    DataSourceMetadata,
    DataSourceValidationError,
    FileDataSource,
)


class BNetzARolloutDataSource(FileDataSource):
    """
    BNetzA Rollout-Datenquellen-Adapter.

    Lädt und validiert Quartalsberichte der Bundesnetzagentur
    zum Smart-Meter-Rollout.
    """

    def __init__(self, file_path: Path, quarter: str, year: int):
        super().__init__(f"BNetzA_Q{quarter}_{year}", file_path)
        self.quarter = quarter
        self.year = year
        self.expected_columns = {
            "company_name",
            "rollout_quota",
            "installed_systems",
            "quarter",
            "year",
        }

    async def fetch_data(self) -> list[dict[str, Any]]:
        """
        Lade BNetzA Rollout-Daten.

        Returns:
            List[Dict[str, Any]]: Rollout-Daten pro Unternehmen
        """
        try:
            # Excel oder CSV-Datei laden
            if self.file_path.suffix.lower() in [".xlsx", ".xls"]:
                df = pd.read_excel(self.file_path, engine="openpyxl")
            else:
                # CSV mit verschiedenen Encodings versuchen
                encodings = ["utf-8", "iso-8859-1", "cp1252"]
                df = None

                for encoding in encodings:
                    try:
                        df = pd.read_csv(
                            self.file_path, encoding=encoding, sep=";", low_memory=False
                        )
                        break
                    except UnicodeDecodeError:
                        continue

                if df is None:
                    raise ValueError("Konnte Datei mit keinem Encoding lesen")

            # Spaltennamen normalisieren
            df.columns = (
                df.columns.str.lower().str.replace(" ", "_").str.replace("-", "_")
            )

            # Quarter und Year hinzufügen falls nicht vorhanden
            if "quarter" not in df.columns:
                df["quarter"] = self.quarter
            if "year" not in df.columns:
                df["year"] = self.year

            # NaN-Werte behandeln
            df = df.fillna(
                {"rollout_quota": 0.0, "installed_systems": 0, "company_name": ""}
            )

            # DataFrame zu Dictionary-Liste konvertieren
            data = df.to_dict("records")

            # Metadaten aktualisieren
            self._metadata = DataSourceMetadata(
                source_name=self.name,
                last_updated=datetime.now(),
                record_count=len(data),
                version=f"Q{self.quarter}_{self.year}",
            )

            return [
                {str(k): v for k, v in record.items()} for record in data
            ]  # Ensure str keys

        except Exception as e:
            raise DataSourceError(f"Fehler beim Laden der BNetzA-Daten: {e}")

    async def validate_data(self, data: list[dict[str, Any]]) -> bool:
        """
        Validiere BNetzA Rollout-Daten.

        Args:
            data: BNetzA-Datensätze

        Returns:
            bool: True wenn Daten valide sind
        """
        if not data:
            raise DataSourceValidationError("Keine BNetzA-Rollout-Daten vorhanden")

        # Prüfe erste Zeile auf erforderliche Spalten
        first_record = data[0]
        available_columns = set(first_record.keys())

        # Prüfe ob Kernspalten vorhanden sind
        core_columns = {"company_name", "quarter", "year"}
        missing_core = core_columns - available_columns

        if missing_core:
            raise DataSourceValidationError(
                f"Fehlende Kernspalten in BNetzA-Daten: {missing_core}"
            )

        # Validiere Quarter/Year Konsistenz
        inconsistent_quarters = [
            i
            for i, record in enumerate(data)
            if str(record.get("quarter", "")).strip() != str(self.quarter)
            and record.get("quarter") is not None
        ]

        if inconsistent_quarters:
            raise DataSourceValidationError(
                f"Inkonsistente Quartalsdaten in Zeilen: {inconsistent_quarters[:5]}..."
            )

        inconsistent_years = [
            i
            for i, record in enumerate(data)
            if record.get("year") != self.year and record.get("year") is not None
        ]

        if inconsistent_years:
            raise DataSourceValidationError(
                f"Inkonsistente Jahresdaten in Zeilen: {inconsistent_years[:5]}..."
            )

        # Prüfe numerische Werte
        invalid_quotas = [
            i
            for i, record in enumerate(data)
            if record.get("rollout_quota") is not None
            and not isinstance(record.get("rollout_quota"), int | float)
        ]

        if invalid_quotas:
            raise DataSourceValidationError(
                f"Ungültige Rollout-Quoten in Zeilen: {invalid_quotas[:5]}..."
            )

        return True

    def get_quarter_info(self) -> dict[str, Any]:
        """Informationen über das Quartal."""
        return {
            "quarter": self.quarter,
            "year": self.year,
            "period": f"Q{self.quarter} {self.year}",
            "record_count": self._metadata.record_count if self._metadata else 0,
        }
