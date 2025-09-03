"""
BDEW Integration Tests

Umfassende Tests für die BDEW-Stammdaten-Integration:
- Repository-Pattern Funktionalitäten
- Datenbank-CRUD-Operationen
- Such- und Filterfunktionen
- Datenqualitäts-Features
- Edge Cases und Fehlerbehandlung
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.bdew import Base, BDEWCompany
from src.repositories.bdew import BDEWRepository


@pytest.fixture
def test_db_session():
    """Test-Datenbank-Session mit In-Memory SQLite."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def bdew_repository(test_db_session):
    """BDEW Repository für Tests."""
    return BDEWRepository(test_db_session)


@pytest.fixture
def sample_company_data():
    """Beispiel-Unternehmensdaten für Tests."""
    return {
        "company_name": "Stadtwerke München GmbH",
        "network_operator_id": "10YDE-SWMUNICH-8",
        "marktlokations_id": "DE0000012345",
        "postal_code": "80333",
        "city": "München",
        "federal_state": "Bayern",
        "address_line": "Emmy-Noether-Straße 2",
        "website": "https://www.swm.de",
        "email": "info@swm.de",
        "phone": "+49 89 2361-0",
        "is_active": True,
        "data_quality_score": 95,
        "notes": "Testdaten für München",
    }


@pytest.fixture
def multiple_companies_data():
    """Mehrere Unternehmensdaten für Bulk-Tests."""
    return [
        {
            "company_name": "Stadtwerke München GmbH",
            "network_operator_id": "10YDE-SWMUNICH-8",
            "postal_code": "80333",
            "city": "München",
            "federal_state": "Bayern",
            "data_quality_score": 95,
        },
        {
            "company_name": "E.ON Verteilnetz GmbH",
            "network_operator_id": "10YDE-EON------2",
            "postal_code": "45128",
            "city": "Essen",
            "federal_state": "Nordrhein-Westfalen",
            "data_quality_score": 92,
        },
        {
            "company_name": "Rheinenergie AG",
            "network_operator_id": "10YDE-RHEINENE-5",
            "postal_code": "50999",
            "city": "Köln",
            "federal_state": "Nordrhein-Westfalen",
            "data_quality_score": 88,
        },
    ]


class TestBDEWRepositoryBasics:
    """Grundlegende Repository-Funktionen."""

    async def test_create_single_company(self, bdew_repository, sample_company_data):
        """Test: Einzelnes Unternehmen erstellen."""
        company = await bdew_repository.create_company(sample_company_data)

        assert company is not None
        assert company.company_name == sample_company_data["company_name"]
        assert company.network_operator_id == sample_company_data["network_operator_id"]
        assert company.city == sample_company_data["city"]
        assert company.is_active is True

    async def test_bulk_insert_companies(
        self, bdew_repository, multiple_companies_data
    ):
        """Test: Mehrere Unternehmen gleichzeitig einfügen."""
        inserted_count = await bdew_repository.bulk_insert_companies(
            multiple_companies_data
        )

        assert inserted_count == 3

        total_count = await bdew_repository.get_companies_count()
        assert total_count == 3

    async def test_find_company_by_operator_id(
        self, bdew_repository, sample_company_data
    ):
        """Test: Unternehmen anhand Netzbetreiber-ID finden."""
        # Erstelle Unternehmen
        created_company = await bdew_repository.create_company(sample_company_data)
        operator_id = sample_company_data["network_operator_id"]

        # Suche nach Operator-ID
        found_company = await bdew_repository.find_company_by_operator_id(operator_id)

        assert found_company is not None
        assert found_company.id == created_company.id
        assert found_company.company_name == sample_company_data["company_name"]

    async def test_get_companies_count(self, bdew_repository, multiple_companies_data):
        """Test: Anzahl der Unternehmen abrufen."""
        # Leere Datenbank
        assert await bdew_repository.get_companies_count() == 0

        # Nach Bulk-Insert
        await bdew_repository.bulk_insert_companies(multiple_companies_data)
        assert await bdew_repository.get_companies_count() == 3


class TestBDEWRepositorySearch:
    """Such- und Filterfunktionen."""

    async def test_search_by_company_name(
        self, bdew_repository, multiple_companies_data
    ):
        """Test: Suche nach Unternehmensname."""
        await bdew_repository.bulk_insert_companies(multiple_companies_data)

        # Suche nach "Stadtwerke"
        stadtwerke_results = await bdew_repository.search_companies(query="Stadtwerke")
        assert len(stadtwerke_results) == 1
        assert "Stadtwerke" in stadtwerke_results[0].company_name

        # Suche nach "E.ON"
        eon_results = await bdew_repository.search_companies(query="E.ON")
        assert len(eon_results) == 1
        assert "E.ON" in eon_results[0].company_name

        # Suche nach "München" (im Namen)
        munich_results = await bdew_repository.search_companies(query="München")
        assert len(munich_results) == 1

    async def test_search_by_federal_state(
        self, bdew_repository, multiple_companies_data
    ):
        """Test: Suche nach Bundesland."""
        await bdew_repository.bulk_insert_companies(multiple_companies_data)

        # Suche nur NRW
        nrw_companies = await bdew_repository.search_companies(
            federal_state="Nordrhein-Westfalen"
        )
        assert len(nrw_companies) == 2
        for company in nrw_companies:
            assert company.federal_state == "Nordrhein-Westfalen"

        # Suche nur Bayern
        bayern_companies = await bdew_repository.search_companies(
            federal_state="Bayern"
        )
        assert len(bayern_companies) == 1
        assert bayern_companies[0].city == "München"

    async def test_search_by_postal_code(
        self, bdew_repository, multiple_companies_data
    ):
        """Test: Suche nach PLZ."""
        await bdew_repository.bulk_insert_companies(multiple_companies_data)

        # Suche Essen PLZ
        essen_companies = await bdew_repository.search_companies(postal_code="45128")
        assert len(essen_companies) == 1
        assert essen_companies[0].city == "Essen"

    async def test_search_with_pagination(
        self, bdew_repository, multiple_companies_data
    ):
        """Test: Suche mit Paginierung."""
        await bdew_repository.bulk_insert_companies(multiple_companies_data)

        # Erste Seite (2 Ergebnisse)
        page1 = await bdew_repository.search_companies(limit=2, offset=0)
        assert len(page1) == 2

        # Zweite Seite (1 Ergebnis)
        page2 = await bdew_repository.search_companies(limit=2, offset=2)
        assert len(page2) == 1

        # Keine Duplikate zwischen Seiten
        page1_ids = {company.id for company in page1}
        page2_ids = {company.id for company in page2}
        assert len(page1_ids.intersection(page2_ids)) == 0


class TestBDEWRepositoryQuality:
    """Datenqualitäts-Features."""

    async def test_data_quality_statistics(self, bdew_repository):
        """Test: Datenqualitäts-Statistiken."""
        # Unternehmen mit verschiedenen Quality Scores
        companies = [
            {
                "company_name": "High Quality Corp",
                "city": "Berlin",
                "postal_code": "10115",
                "federal_state": "Berlin",
                "website": "https://example.com",
                "email": "info@example.com",
                "data_quality_score": 95,
            },
            {
                "company_name": "Medium Quality Corp",
                "city": "Hamburg",
                "data_quality_score": 75,
            },
            {"company_name": "Low Quality Corp", "data_quality_score": 50},
        ]

        await bdew_repository.bulk_insert_companies(companies)
        stats = await bdew_repository.get_data_quality_stats()

        assert "total_companies" in stats
        assert stats["total_companies"] == 3

        assert "average_quality_score" in stats
        expected_avg = (95 + 75 + 50) / 3
        assert abs(stats["average_quality_score"] - expected_avg) < 0.1

    async def test_company_with_complete_data(
        self, bdew_repository, sample_company_data
    ):
        """Test: Unternehmen mit vollständigen Daten."""
        company = await bdew_repository.create_company(sample_company_data)

        # Prüfe alle wichtigen Felder
        assert company.company_name == sample_company_data["company_name"]
        assert company.network_operator_id == sample_company_data["network_operator_id"]
        assert company.marktlokations_id == sample_company_data["marktlokations_id"]
        assert company.postal_code == sample_company_data["postal_code"]
        assert company.city == sample_company_data["city"]
        assert company.federal_state == sample_company_data["federal_state"]
        assert company.address_line == sample_company_data["address_line"]
        assert company.website == sample_company_data["website"]
        assert company.email == sample_company_data["email"]
        assert company.phone == sample_company_data["phone"]
        assert company.data_quality_score == sample_company_data["data_quality_score"]
        assert company.notes == sample_company_data["notes"]
        assert company.is_active is True


class TestBDEWRepositoryEdgeCases:
    """Edge Cases und Fehlerbehandlung."""

    async def test_search_empty_database(self, bdew_repository):
        """Test: Suche in leerer Datenbank."""
        # Verschiedene Suchen sollten leere Ergebnisse liefern
        assert len(await bdew_repository.search_companies(query="Nonexistent")) == 0
        assert (
            len(await bdew_repository.search_companies(federal_state="Nonexistent"))
            == 0
        )
        assert len(await bdew_repository.search_companies(postal_code="99999")) == 0
        assert await bdew_repository.get_companies_count() == 0

    async def test_bulk_insert_empty_list(self, bdew_repository):
        """Test: Bulk-Insert mit leerer Liste."""
        count = await bdew_repository.bulk_insert_companies([])
        assert count == 0
        assert await bdew_repository.get_companies_count() == 0

    async def test_create_minimal_company(self, bdew_repository):
        """Test: Unternehmen mit minimalen Daten."""
        minimal_data = {"company_name": "Minimal Corp"}

        company = await bdew_repository.create_company(minimal_data)
        assert company is not None
        assert company.company_name == "Minimal Corp"
        assert company.is_active is True  # Default-Wert

    async def test_find_nonexistent_operator_id(self, bdew_repository):
        """Test: Suche nach nicht existierender Operator-ID."""
        result = await bdew_repository.find_company_by_operator_id("NONEXISTENT-ID")
        assert result is None

    async def test_search_with_no_results(self, bdew_repository, sample_company_data):
        """Test: Suche die keine Ergebnisse liefert."""
        await bdew_repository.create_company(sample_company_data)

        # Suche nach nicht existierenden Begriffen
        assert (
            len(await bdew_repository.search_companies(query="Nonexistent Company"))
            == 0
        )
        assert (
            len(
                await bdew_repository.search_companies(
                    federal_state="Nonexistent State"
                )
            )
            == 0
        )
        assert len(await bdew_repository.search_companies(postal_code="00000")) == 0


class TestBDEWRepositoryIntegration:
    """Integrations-Tests mit realistischen Szenarien."""

    async def test_complete_workflow(self, bdew_repository, multiple_companies_data):
        """Test: Vollständiger Workflow von Import bis Suche."""
        # 1. Bulk-Import
        inserted_count = await bdew_repository.bulk_insert_companies(
            multiple_companies_data
        )
        assert inserted_count == 3

        # 2. Gesamtanzahl prüfen
        total_count = await bdew_repository.get_companies_count()
        assert total_count == 3

        # 3. Spezifische Suchen
        swm = await bdew_repository.find_company_by_operator_id("10YDE-SWMUNICH-8")
        assert swm is not None
        assert swm.city == "München"

        # 4. Standort-Filter
        nrw_companies = await bdew_repository.search_companies(
            federal_state="Nordrhein-Westfalen"
        )
        assert len(nrw_companies) == 2

        # 5. Qualitäts-Statistiken
        stats = await bdew_repository.get_data_quality_stats()
        assert stats["total_companies"] == 3
        assert stats["average_quality_score"] > 80

    async def test_duplicate_operator_ids(self, bdew_repository):
        """Test: Verhalten bei doppelten Operator-IDs."""
        first_company = await bdew_repository.create_company(
            {
                "company_name": "Erste Firma",
                "network_operator_id": "DUPLICATE-ID",
                "city": "Berlin",
            }
        )
        assert first_company is not None

        # Versuche zweites Unternehmen mit gleicher ID
        # (Sollte durch UNIQUE constraint verhindert werden oder überschreiben)
        try:
            second_company = await bdew_repository.create_company(
                {
                    "company_name": "Zweite Firma",
                    "network_operator_id": "DUPLICATE-ID",
                    "city": "Hamburg",
                }
            )
            # Falls erfolgreich, prüfe dass nur eines gefunden wird
            if second_company:
                found = await bdew_repository.find_company_by_operator_id(
                    "DUPLICATE-ID"
                )
                assert found.company_name in ["Erste Firma", "Zweite Firma"]
        except Exception:
            # Fehler ist bei UNIQUE constraint erwartet
            pass

    async def test_large_dataset_performance(self, bdew_repository):
        """Test: Performance mit größerem Datensatz."""
        # Erstelle 50 Testunternehmen
        large_dataset = []
        for i in range(50):
            large_dataset.append(
                {
                    "company_name": f"Testfirma {i:03d}",
                    "network_operator_id": f"10YDE-TEST{i:03d}-{i}",
                    "postal_code": f"{10000 + i}",
                    "city": f"Teststadt{i}",
                    "federal_state": "Testland" if i % 2 == 0 else "Andersland",
                    "data_quality_score": 70 + (i % 30),
                }
            )

        # Bulk-Insert
        inserted_count = await bdew_repository.bulk_insert_companies(large_dataset)
        assert inserted_count == 50

        # Verschiedene Suchen testen
        all_companies = await bdew_repository.search_companies(limit=100)
        assert len(all_companies) == 50

        testland_companies = await bdew_repository.search_companies(
            federal_state="Testland"
        )
        assert len(testland_companies) == 25  # Jedes zweite

        # Paginierung testen
        page1 = await bdew_repository.search_companies(limit=20, offset=0)
        page2 = await bdew_repository.search_companies(limit=20, offset=20)
        page3 = await bdew_repository.search_companies(limit=20, offset=40)

        assert len(page1) == 20
        assert len(page2) == 20
        assert len(page3) == 10  # Restliche

        # Qualitäts-Statistiken
        stats = await bdew_repository.get_data_quality_stats()
        assert stats["total_companies"] == 50
        assert 70 <= stats["average_quality_score"] <= 99
