"""Data classes for VNBdigitaler company matching system."""

import re
from dataclasses import dataclass

# Confidence level thresholds
EXCELLENT_MATCH_THRESHOLD = 95
HIGH_MATCH_THRESHOLD = 85
MEDIUM_MATCH_THRESHOLD = 70


@dataclass
class BDEWCompany:
    """Represents a company from the BDEW database."""

    bdew_code: str
    name: str
    city: str | None = None
    normalized_name: str | None = None

    def __post_init__(self) -> None:
        """Normalize the company name after initialization."""
        if self.normalized_name is None:
            self.normalized_name = self.normalize_name(self.name)

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize company name for matching."""
        if not name:
            return ""

        # Convert to lowercase
        normalized = name.lower().strip()

        # Remove punctuation and special characters
        normalized = re.sub(r"[^\w\s]", " ", normalized)

        # Replace multiple spaces with single space
        normalized = re.sub(r"\s+", " ", normalized)

        # Common legal form replacements
        legal_replacements = {
            "gesellschaft mit beschraenkter haftung": "gmbh",
            "gesellschaft mit beschränkter haftung": "gmbh",
            "aktiengesellschaft": "ag",
            "kommanditgesellschaft": "kg",
            "eingetragene genossenschaft": "eg",
            "gmbh co kg": "gmbh co kg",
            "gmbh und co kg": "gmbh co kg",
            "gmbh & co kg": "gmbh co kg",
            "co kg": "co kg",
            "kommunalunternehmen": "",
            "kommunale": "",
        }

        for old, new in legal_replacements.items():
            normalized = normalized.replace(old, new)

        # Remove common business words that don't help matching
        common_words = {
            "gesellschaft",
            "unternehmen",
            "betrieb",
            "betriebe",
            "werke",
            "werk",
            "energie",
            "strom",
            "gas",
            "wasser",
            "versorgung",
            "versorgungs",
            "netze",
            "netz",
            "verteilnetz",
            "verteilung",
            "distribution",
            "regional",
            "local",
            "kommunal",
            "stadtwerke",
            "gemeindewerke",
        }

        words = normalized.split()
        filtered_words = [
            word for word in words if word not in common_words and len(word) > 1
        ]

        return " ".join(filtered_words).strip()

    def get_location_keywords(self) -> set[str]:
        """Extract location-related keywords from company name and city."""
        keywords = set()

        if self.city:
            keywords.add(self.city.lower())

        # Extract potential location names from company name
        # Look for patterns like "Stadtwerke Berlin", "Energie München", etc.
        name_words = self.name.lower().split()
        for word in name_words:
            # Skip common business terms
            if word not in {"gmbh", "ag", "kg", "eg", "co", "und", "&"}:
                keywords.add(word)

        return keywords

    def __str__(self) -> str:
        """String representation."""
        return f"BDEWCompany(code={self.bdew_code}, name='{self.name}', city='{self.city}')"


@dataclass
class BNetzACompany:
    """Represents a company from the BNetzA roll-out report."""

    index: int
    original_name: str
    rollout_quote: float | None = None
    normalized_name: str | None = None

    def __post_init__(self) -> None:
        """Normalize the company name after initialization."""
        if self.normalized_name is None:
            self.normalized_name = BDEWCompany.normalize_name(self.original_name)

    def get_location_keywords(self) -> set[str]:
        """Extract location-related keywords from company name."""
        keywords = set()

        # Extract potential location names from company name
        name_words = self.original_name.lower().split()
        for word in name_words:
            # Skip common business terms
            if word not in {"gmbh", "ag", "kg", "eg", "co", "und", "&"}:
                keywords.add(word)

        return keywords

    def __str__(self) -> str:
        """String representation."""
        return f"BNetzACompany(index={self.index}, name='{self.original_name}')"


@dataclass
class CompanyMatch:
    """Represents a match between BNetzA and BDEW companies."""

    bnetza_company: BNetzACompany
    bdew_company: BDEWCompany
    match_score: float
    match_type: str
    confidence_level: str = "unknown"

    def __post_init__(self) -> None:
        """Determine confidence level based on match score."""
        if self.match_score >= EXCELLENT_MATCH_THRESHOLD:
            self.confidence_level = "excellent"
        elif self.match_score >= HIGH_MATCH_THRESHOLD:
            self.confidence_level = "high"
        elif self.match_score >= MEDIUM_MATCH_THRESHOLD:
            self.confidence_level = "medium"
        else:
            self.confidence_level = "low"

    def to_dict(self) -> dict:
        """Convert match to dictionary for CSV export."""
        return {
            "bnetza_index": self.bnetza_company.index,
            "bdew_code": self.bdew_company.bdew_code,
            "bnetza_name": self.bnetza_company.original_name,
            "bdew_name": self.bdew_company.name,
            "bdew_city": self.bdew_company.city or "",
            "match_score": self.match_score,
            "match_type": self.match_type,
            "confidence_level": self.confidence_level,
            "rollout_quote": self.bnetza_company.rollout_quote or "",
        }

    def __str__(self) -> str:
        """String representation."""
        return (
            f"CompanyMatch({self.bnetza_company.original_name} -> "
            f"{self.bdew_company.name} [{self.match_score}% {self.match_type}])"
        )
