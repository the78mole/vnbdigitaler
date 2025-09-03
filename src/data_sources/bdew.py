"""
BDEW Datenquellen-Adapter.

Adapter für Bundesverband der Energie- und Wasserwirtschaft (BDEW) Daten.
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


class BDEWDataSource(FileDataSource):
    """
    BDEW Datenquellen-Adapter für Stammdaten der Verteilnetzbetreiber.

    BDEW stellt Daten zu deutschen Verteilnetzbetreibern bereit,
    die als Basis für die Zuordnung von Rollout-Daten dienen.
    """

    def __init__(self, file_path: Path):
        super().__init__("BDEW", file_path)
        self.expected_columns = {
            "company_name",
            "marktlokations_id",
            "network_operator_id",
            "postal_code",
            "city",
            "federal_state",
        }

    async def fetch_data(self) -> list[dict[str, Any]]:
        """
        Lade BDEW-Daten aus CSV-Datei.

        Returns:
            List[Dict[str, Any]]: BDEW Verteilnetzbetreiber-Daten
        """
        try:
            # Verschiedene Encoding-Varianten versuchen
            encodings = ["utf-8", "iso-8859-1", "cp1252"]
            df = None

            for encoding in encodings:
                try:
                    df = pd.read_csv(
                        self.file_path,
                        encoding=encoding,
                        sep=";",  # BDEW verwendet oft Semikolon
                        low_memory=False,
                    )
                    break
                except UnicodeDecodeError:
                    continue

            if df is None:
                raise ValueError("Konnte Datei mit keinem Encoding lesen")

            # Spaltennamen normalisieren
            df.columns = df.columns.str.lower().str.replace(" ", "_")

            # DataFrame zu Dictionary-Liste konvertieren
            data = df.to_dict("records")

            # Metadaten aktualisieren
            self._metadata = DataSourceMetadata(
                source_name=self.name,
                last_updated=datetime.now(),
                record_count=len(data),
            )

            return [
                {str(k): v for k, v in record.items()} for record in data
            ]  # Ensure str keys

        except Exception as e:
            raise DataSourceError(f"Fehler beim Laden der BDEW-Daten: {e}")

    async def validate_data(self, data: list[dict[str, Any]]) -> bool:
        """
        Validiere BDEW-Daten.

        Args:
            data: BDEW-Datensätze

        Returns:
            bool: True wenn Daten valide sind
        """
        if not data:
            raise DataSourceValidationError("Keine BDEW-Daten vorhanden")

        # Prüfe erste Zeile auf erforderliche Spalten
        first_record = data[0]
        available_columns = set(first_record.keys())

        # Prüfe ob Kernspalten vorhanden sind
        core_columns = {"company_name", "network_operator_id"}
        missing_core = core_columns - available_columns

        if missing_core:
            raise DataSourceValidationError(
                f"Fehlende Kernspalten in BDEW-Daten: {missing_core}"
            )

        # Prüfe auf leere Unternehmensnamen
        empty_names = [
            i
            for i, record in enumerate(data)
            if not record.get("company_name", "").strip()
        ]

        if empty_names:
            raise DataSourceValidationError(
                f"Leere Unternehmensnamen in Zeilen: {empty_names[:5]}..."
            )

        return True

    def get_company_count(self) -> int:
        """Anzahl der geladenen Unternehmen."""
        if self._metadata:
            return self._metadata.record_count or 0
        return 0
