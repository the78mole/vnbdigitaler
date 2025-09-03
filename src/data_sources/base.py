"""
Abstrakte Basis-Interfaces für Datenquellen in VNB Digitaler.

Dieses Modul definiert die grundlegenden Schnittstellen für alle
Datenquellen-Adapter.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any


class DataSourceMetadata:
    """Metadaten für eine Datenquelle."""

    def __init__(
        self,
        source_name: str,
        last_updated: datetime | None = None,
        version: str | None = None,
        etag: str | None = None,
        record_count: int | None = None,
        checksum: str | None = None,
    ):
        self.source_name = source_name
        self.last_updated = last_updated
        self.version = version
        self.etag = etag
        self.record_count = record_count
        self.checksum = checksum


class DataSourceError(Exception):
    """Basis-Exception für Datenquellen-Fehler."""

    pass


class DataSourceConnectionError(DataSourceError):
    """Fehler bei der Verbindung zur Datenquelle."""

    pass


class DataSourceValidationError(DataSourceError):
    """Fehler bei der Validierung der Datenquelle."""

    pass


class DataSource(ABC):
    """
    Abstrakte Basisklasse für alle Datenquellen.

    Definiert die grundlegenden Methoden, die jede Datenquelle
    implementieren muss.
    """

    def __init__(self, name: str):
        self.name = name
        self._metadata: DataSourceMetadata | None = None

    @property
    def metadata(self) -> DataSourceMetadata | None:
        """Metadaten der Datenquelle."""
        return self._metadata

    @abstractmethod
    async def connect(self) -> bool:
        """
        Verbindung zur Datenquelle herstellen.

        Returns:
            bool: True bei erfolgreicher Verbindung

        Raises:
            DataSourceConnectionError: Bei Verbindungsfehlern
        """
        pass

    @abstractmethod
    async def check_for_updates(self) -> bool:
        """
        Prüfe, ob neue Daten verfügbar sind.

        Returns:
            bool: True wenn Updates verfügbar sind
        """
        pass

    @abstractmethod
    async def fetch_data(self) -> list[dict[str, Any]]:
        """
        Lade Daten von der Quelle.

        Returns:
            List[Dict[str, Any]]: Liste der Datensätze

        Raises:
            DataSourceError: Bei Fehlern beim Laden
        """
        pass

    @abstractmethod
    async def validate_data(self, data: list[dict[str, Any]]) -> bool:
        """
        Validiere die geladenen Daten.

        Args:
            data: Die zu validierenden Daten

        Returns:
            bool: True wenn Daten valide sind

        Raises:
            DataSourceValidationError: Bei Validierungsfehlern
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Verbindung zur Datenquelle trennen."""


class FileDataSource(DataSource):
    """
    Abstrakte Basisklasse für dateibasierte Datenquellen.
    """

    def __init__(self, name: str, file_path: str | Path):
        super().__init__(name)
        self.file_path = Path(file_path)

    async def connect(self) -> bool:
        """Prüfe ob Datei existiert und lesbar ist."""
        if not self.file_path.exists():
            raise DataSourceConnectionError(f"Datei nicht gefunden: {self.file_path}")

        if not self.file_path.is_file():
            raise DataSourceConnectionError(f"Pfad ist keine Datei: {self.file_path}")

        try:
            # Prüfe Leseberechtigung
            self.file_path.read_text(encoding="utf-8", errors="ignore")
            return True
        except Exception as e:
            raise DataSourceConnectionError(f"Datei nicht lesbar: {e}")

    async def check_for_updates(self) -> bool:
        """Prüfe Datei-Änderungszeit."""
        if not self.file_path.exists():
            return False

        current_mtime = datetime.fromtimestamp(self.file_path.stat().st_mtime)

        if self._metadata is None or self._metadata.last_updated is None:
            return True

        return current_mtime > self._metadata.last_updated


class WebDataSource(DataSource):
    """
    Abstrakte Basisklasse für webbasierte Datenquellen.
    """

    def __init__(self, name: str, base_url: str):
        super().__init__(name)
        self.base_url = base_url.rstrip("/")
        self._session = None

    @abstractmethod
    async def get_auth_headers(self) -> dict[str, str]:
        """
        Authentifizierungs-Header für API-Anfragen.

        Returns:
            Dict[str, str]: Header-Dictionary
        """
        pass


class DatabaseDataSource(DataSource):
    """
    Abstrakte Basisklasse für datenbankbasierte Datenquellen.
    """

    def __init__(self, name: str, connection_string: str):
        super().__init__(name)
        self.connection_string = connection_string
        self._connection = None

    @abstractmethod
    async def execute_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Führe eine Datenbankabfrage aus.

        Args:
            query: SQL-Query
            params: Query-Parameter

        Returns:
            List[Dict[str, Any]]: Abfrageergebnisse
        """
        pass
