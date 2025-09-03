"""
VNB Digital API-Adapter.

Adapter für die VNB Digital GraphQL-API zur Abfrage von
Verteilnetzbetreiber-Territorien und Geodaten.
"""

from datetime import datetime
from typing import Any

import aiohttp

from .base import (
    DataSourceConnectionError,
    DataSourceError,
    DataSourceMetadata,
    DataSourceValidationError,
    WebDataSource,
)

# HTTP-Status-Konstanten
HTTP_OK = 200


class VNBDigitalDataSource(WebDataSource):
    """
    VNB Digital API-Adapter.

    Stellt Verbindung zur VNB Digital GraphQL-API her und lädt
    Territorien-Daten der deutschen Verteilnetzbetreiber.
    """

    def __init__(self, api_key: str | None = None):
        """Initialisiere VNB Digital Datenquelle."""
        super().__init__(base_url="https://api.vnbdigital.de")
        self.api_key = api_key
        self.graphql_endpoint = "https://api.vnbdigital.de/graphql"

    def get_auth_headers(self) -> dict[str, str]:
        """
        Authentifizierungs-Header für VNB Digital API.

        Returns:
            Dict mit Authorization-Header falls API-Key verfügbar
        """
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    async def connect(self) -> bool:
        """
        Verbindung zur VNB Digital API prüfen.

        Returns:
            True wenn API erreichbar ist
        """
        test_query = """
        query {
            __schema {
                types {
                    name
                }
            }
        }
        """

        headers = self.get_auth_headers()

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    self.graphql_endpoint, json={"query": test_query}, headers=headers
                ) as response,
            ):
                return response.status == HTTP_OK
        except Exception:
            return False

    async def check_for_updates(self) -> bool:
        """
        Prüfe auf verfügbare Updates.

        Returns:
            True wenn neue Daten verfügbar sind
        """
        # Implementierung für Update-Check
        return True

    async def fetch_data(self) -> list[dict[str, Any]]:
        """
        Territorien-Daten von VNB Digital API abrufen.

        Returns:
            Liste von Territorien-Dictionaries

        Raises:
            DataSourceError: Bei API-Fehlern
        """
        territories_query = """
        query {
            territories {
                id
                name
                operator {
                    id
                    name
                    code
                }
                geometry {
                    type
                    coordinates
                }
                properties {
                    population
                    area
                    type
                }
            }
        }
        """

        headers = self.get_auth_headers()

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    self.graphql_endpoint,
                    json={"query": territories_query},
                    headers=headers,
                ) as response,
            ):

                if response.status != HTTP_OK:
                    raise DataSourceError(f"VNB Digital API Fehler: {response.status}")

                result = await response.json()

                if "errors" in result:
                    raise DataSourceError(f"GraphQL Fehler: {result['errors']}")

                territories = result.get("data", {}).get("territories", [])

                # Metadaten aktualisieren
                self._metadata = DataSourceMetadata(
                    source_name="VNB Digital",
                    last_updated=datetime.now(),
                    record_count=len(territories),
                )

                return territories

        except aiohttp.ClientError as e:
            raise DataSourceConnectionError(f"Verbindungsfehler: {e}")
        except Exception as e:
            raise DataSourceError(f"Unerwarteter Fehler: {e}")

    async def validate_data(self, data: list[dict[str, Any]]) -> bool:
        """
        VNB Digital Territorien-Daten validieren.

        Args:
            data: Liste der Territorien-Dictionaries

        Returns:
            True wenn Daten valide sind

        Raises:
            DataSourceValidationError: Bei Validierungsfehlern
        """
        if not data:
            raise DataSourceValidationError("VNB Digital: Keine Daten erhalten")

        # Prüfe erforderliche Felder im ersten Datensatz
        first_record = data[0]
        required_keys = ["id", "name", "operator", "geometry"]
        missing_keys = [key for key in required_keys if key not in first_record]

        if missing_keys:
            raise DataSourceValidationError(
                f"VNB Digital: Fehlende Felder: {missing_keys}"
            )

        # Validiere Operator-Struktur
        operator = first_record.get("operator", {})
        if not isinstance(operator, dict) or "name" not in operator:
            raise DataSourceValidationError("VNB Digital: Ungültige Operator-Struktur")

        return True

    async def fetch_territory_by_operator(
        self, operator_id: str
    ) -> dict[str, Any] | None:
        """
        Spezifisches Territorium eines Betreibers abrufen.

        Args:
            operator_id: ID des Verteilnetzbetreibers

        Returns:
            Territorium-Dictionary oder None wenn nicht gefunden

        Raises:
            DataSourceError: Bei API-Fehlern
        """
        territory_query = f"""
        query {{
            territory(operatorId: "{operator_id}") {{
                id
                name
                operator {{
                    id
                    name
                    code
                }}
                geometry {{
                    type
                    coordinates
                }}
                properties {{
                    population
                    area
                    type
                }}
            }}
        }}
        """

        headers = self.get_auth_headers()

        try:
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    self.graphql_endpoint,
                    json={"query": territory_query},
                    headers=headers,
                ) as response,
            ):

                if response.status != HTTP_OK:
                    return None

                result = await response.json()

                if "errors" in result:
                    return None

                return result.get("data", {}).get("territory")

        except Exception:
            return None

    async def disconnect(self) -> None:
        """Verbindung trennen (nicht erforderlich für HTTP-API)."""
        pass
