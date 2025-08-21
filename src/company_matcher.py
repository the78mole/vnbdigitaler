"""Company matching engine for VNBdigitaler."""

import logging
from typing import Any

from fuzzywuzzy import fuzz, process

from .matching_models import BDEWCompany, BNetzACompany, CompanyMatch

logger = logging.getLogger(__name__)

# Matching thresholds
EXACT_MATCH_THRESHOLD = 100
FUZZY_MATCH_THRESHOLD = 70
LOCATION_BOOST = 10  # Points added when location keywords match

# Tuple length constants
TUPLE_WITH_INDEX_LENGTH = 3
TUPLE_WITHOUT_INDEX_LENGTH = 2


class CompanyMatcher:
    """Advanced company matching engine with multiple algorithms."""

    def __init__(self, bdew_companies: list[BDEWCompany]):
        """Initialize matcher with BDEW companies."""
        self.bdew_companies = bdew_companies
        self.normalize_cache: dict[str, str] = {}

        # Create lookup dictionaries for faster searching
        self._build_lookup_indexes()

    def _build_lookup_indexes(self) -> None:
        """Build lookup indexes for faster matching."""
        # Exact match index by normalized name
        self.exact_match_index: dict[str, list[BDEWCompany]] = {}

        # Original name index (case-insensitive)
        self.original_name_index: dict[str, list[BDEWCompany]] = {}

        # City index
        self.city_index: dict[str, list[BDEWCompany]] = {}

        for company in self.bdew_companies:
            # Index by normalized name
            norm_name = company.normalized_name or ""
            if norm_name:
                if norm_name not in self.exact_match_index:
                    self.exact_match_index[norm_name] = []
                self.exact_match_index[norm_name].append(company)

            # Index by original name (lowercase)
            orig_name = company.name.lower().strip()
            if orig_name not in self.original_name_index:
                self.original_name_index[orig_name] = []
            self.original_name_index[orig_name].append(company)

            # Index by city
            if company.city:
                city_key = company.city.lower().strip()
                if city_key not in self.city_index:
                    self.city_index[city_key] = []
                self.city_index[city_key].append(company)

    def find_exact_matches(self, bnetza_company: BNetzACompany) -> list[CompanyMatch]:
        """Find exact matches for a BNetzA company."""
        matches = []

        # Try exact match on normalized names first
        norm_name = bnetza_company.normalized_name or ""
        if norm_name and norm_name in self.exact_match_index:
            for bdew_company in self.exact_match_index[norm_name]:
                match = CompanyMatch(
                    bnetza_company=bnetza_company,
                    bdew_company=bdew_company,
                    match_score=EXACT_MATCH_THRESHOLD,
                    match_type="exact_normalized",
                )
                matches.append(match)

        # Try exact match on original names (case-insensitive)
        orig_name = bnetza_company.original_name.lower().strip()
        if orig_name in self.original_name_index:
            for bdew_company in self.original_name_index[orig_name]:
                # Avoid duplicates
                if not any(
                    m.bdew_company.bdew_code == bdew_company.bdew_code for m in matches
                ):
                    match = CompanyMatch(
                        bnetza_company=bnetza_company,
                        bdew_company=bdew_company,
                        match_score=EXACT_MATCH_THRESHOLD,
                        match_type="exact_original",
                    )
                    matches.append(match)

        return matches

    def find_fuzzy_matches(self, bnetza_company: BNetzACompany) -> list[CompanyMatch]:
        """Find fuzzy matches for a BNetzA company."""
        matches: list[CompanyMatch] = []
        bnetza_norm = bnetza_company.normalized_name or ""
        bnetza_orig = bnetza_company.original_name

        if not bnetza_norm and not bnetza_orig:
            return matches

        # Get location keywords for location-based scoring boost
        bnetza_location_keywords = bnetza_company.get_location_keywords()

        # Prepare candidates for fuzzy matching
        candidates = []
        for bdew_company in self.bdew_companies:
            # Try normalized names
            if bnetza_norm and bdew_company.normalized_name:
                candidates.append(
                    (bdew_company.normalized_name, bdew_company, "fuzzy_normalized")
                )

            # Try original names
            candidates.append((bdew_company.name, bdew_company, "fuzzy_original"))

        # Find best matches using fuzzywuzzy
        search_terms = []
        if bnetza_norm:
            search_terms.append((bnetza_norm, "normalized"))
        search_terms.append((bnetza_orig, "original"))

        for search_term, _term_type in search_terms:
            # Extract best matches
            fuzzy_results = process.extract(
                search_term,
                [candidate[0] for candidate in candidates],
                scorer=fuzz.ratio,
                limit=10,  # Get top 10 candidates
            )

            for result in fuzzy_results:
                # Handle both tuple formats: (text, score) or (text, score, index)
                if len(result) == TUPLE_WITH_INDEX_LENGTH:
                    match_text, score, _index = result
                else:
                    match_text, score = result

                if score >= FUZZY_MATCH_THRESHOLD:
                    # Find corresponding BDEW company
                    for (
                        candidate_text,
                        bdew_company,
                        candidate_match_type,
                    ) in candidates:
                        if candidate_text == match_text:
                            # Apply location boost if applicable
                            final_score = score
                            updated_match_type = candidate_match_type
                            bdew_location_keywords = (
                                bdew_company.get_location_keywords()
                            )

                            # Check for location overlap
                            if bnetza_location_keywords & bdew_location_keywords:
                                final_score = min(100, score + LOCATION_BOOST)
                                updated_match_type += "_with_location_boost"

                            # Avoid duplicates (same BDEW code with lower score)
                            existing_match = next(
                                (
                                    m
                                    for m in matches
                                    if m.bdew_company.bdew_code
                                    == bdew_company.bdew_code
                                ),
                                None,
                            )

                            if existing_match:
                                if final_score > existing_match.match_score:
                                    matches.remove(existing_match)
                                else:
                                    continue  # Skip this lower-scored match

                            match = CompanyMatch(
                                bnetza_company=bnetza_company,
                                bdew_company=bdew_company,
                                match_score=final_score,
                                match_type=updated_match_type,
                            )
                            matches.append(match)
                            break

        # Sort by match score (highest first)
        matches.sort(key=lambda m: m.match_score, reverse=True)

        # Return only top matches to avoid too many weak matches
        return matches[:5]

    def find_best_match(self, bnetza_company: BNetzACompany) -> CompanyMatch | None:
        """Find the single best match for a BNetzA company."""
        # Try exact matches first
        exact_matches = self.find_exact_matches(bnetza_company)

        if exact_matches:
            # For exact matches, use location-based disambiguation
            if len(exact_matches) == 1:
                return exact_matches[0]
            else:
                # Multiple exact matches - use location keywords for disambiguation
                bnetza_keywords = bnetza_company.get_location_keywords()

                scored_matches = []
                for match in exact_matches:
                    bdew_keywords = match.bdew_company.get_location_keywords()
                    location_overlap = len(bnetza_keywords & bdew_keywords)
                    scored_matches.append((match, location_overlap))

                # Sort by location overlap (higher is better)
                scored_matches.sort(key=lambda x: x[1], reverse=True)

                best_match = scored_matches[0][0]
                if scored_matches[0][1] > 0:
                    # Update match type to indicate location-based selection
                    best_match.match_type += "_location_disambiguated"

                return best_match

        # Try fuzzy matches
        fuzzy_matches = self.find_fuzzy_matches(bnetza_company)
        if fuzzy_matches:
            return fuzzy_matches[0]  # Already sorted by score

        return None

    def find_all_matches(self, bnetza_company: BNetzACompany) -> list[CompanyMatch]:
        """Find all possible matches for a BNetzA company."""
        all_matches = []

        # Get exact matches
        exact_matches = self.find_exact_matches(bnetza_company)
        all_matches.extend(exact_matches)

        # Get fuzzy matches (only if no exact matches)
        if not exact_matches:
            fuzzy_matches = self.find_fuzzy_matches(bnetza_company)
            all_matches.extend(fuzzy_matches)

        return all_matches

    def extract_single_exact_matches(
        self, bnetza_companies: list[BNetzACompany]
    ) -> tuple[list[CompanyMatch], list[BNetzACompany], list[BDEWCompany]]:
        """Extract exact matches with only one match and remove them from original lists.

        Returns:
            - List of single exact matches
            - Remaining BNetzA companies (after removals)
            - Remaining BDEW companies (after removals)
        """
        single_exact_matches = []
        used_bnetza_indices = set()
        used_bdew_codes = set()

        logger.info("🔍 Extracting single exact matches...")

        # Find all single exact matches
        for bnetza_company in bnetza_companies:
            if bnetza_company.index in used_bnetza_indices:
                continue

            exact_matches = self.find_exact_matches(bnetza_company)

            # Only process if exactly one exact match found
            if len(exact_matches) == 1:
                match = exact_matches[0]

                # Check if this BDEW company hasn't been used yet
                if match.bdew_company.bdew_code not in used_bdew_codes:
                    single_exact_matches.append(match)
                    used_bnetza_indices.add(bnetza_company.index)
                    used_bdew_codes.add(match.bdew_company.bdew_code)

        # Create new lists without the matched companies
        remaining_bnetza = [
            company
            for company in bnetza_companies
            if company.index not in used_bnetza_indices
        ]

        remaining_bdew = [
            company
            for company in self.bdew_companies
            if company.bdew_code not in used_bdew_codes
        ]

        logger.info(f"✅ Extracted {len(single_exact_matches)} single exact matches")
        logger.info(
            f"📊 Remaining: {len(remaining_bnetza)} BNetzA, {len(remaining_bdew)} BDEW companies"
        )

        return single_exact_matches, remaining_bnetza, remaining_bdew

    def batch_match(self, bnetza_companies: list[BNetzACompany]) -> dict[str, Any]:
        """Process multiple BNetzA companies and return matching results."""
        results: dict[str, Any] = {
            "matches": [],
            "no_matches": [],
            "multiple_matches": [],
            "stats": {
                "total_processed": len(bnetza_companies),
                "exact_matches": 0,
                "fuzzy_matches": 0,
                "no_matches": 0,
                "multiple_exact_matches": 0,
            },
        }

        # Track used BDEW codes to avoid double assignments
        used_bdew_codes = set()

        for bnetza_company in bnetza_companies:
            exact_matches = self.find_exact_matches(bnetza_company)

            if exact_matches:
                # Filter out already used BDEW codes
                available_matches = [
                    match
                    for match in exact_matches
                    if match.bdew_company.bdew_code not in used_bdew_codes
                ]

                if len(available_matches) == 1:
                    match = available_matches[0]
                    results["matches"].append(match)
                    used_bdew_codes.add(match.bdew_company.bdew_code)
                    results["stats"]["exact_matches"] += 1
                elif len(available_matches) > 1:
                    # Multiple available matches - try to disambiguate
                    bnetza_keywords = bnetza_company.get_location_keywords()

                    scored_matches = []
                    for match in available_matches:
                        bdew_keywords = match.bdew_company.get_location_keywords()
                        location_overlap = len(bnetza_keywords & bdew_keywords)
                        scored_matches.append((match, location_overlap))

                    # Sort by location overlap (higher is better)
                    scored_matches.sort(key=lambda x: x[1], reverse=True)

                    # If we have a clear winner (more location overlap), use it
                    if scored_matches[0][1] > scored_matches[1][1]:
                        best_match = scored_matches[0][0]
                        best_match.match_type += "_location_disambiguated"
                        results["matches"].append(best_match)
                        used_bdew_codes.add(best_match.bdew_company.bdew_code)
                        results["stats"]["multiple_exact_matches"] += 1
                    else:
                        # No clear winner - take first available match for now
                        # In practice, this might need manual review
                        best_match = available_matches[0]
                        best_match.match_type += "_first_available"
                        results["matches"].append(best_match)
                        used_bdew_codes.add(best_match.bdew_company.bdew_code)
                        results["stats"]["multiple_exact_matches"] += 1
                elif len(exact_matches) > 0:
                    # All exact matches are already used - try fuzzy matching
                    best_fuzzy = self.find_best_match(bnetza_company)
                    if (
                        best_fuzzy
                        and best_fuzzy.match_score < EXACT_MATCH_THRESHOLD
                        and best_fuzzy.bdew_company.bdew_code not in used_bdew_codes
                    ):
                        results["matches"].append(best_fuzzy)
                        used_bdew_codes.add(best_fuzzy.bdew_company.bdew_code)
                        results["stats"]["fuzzy_matches"] += 1
                    else:
                        results["multiple_matches"].append(
                            {
                                "bnetza_company": bnetza_company,
                                "candidates": exact_matches,
                                "reason": "all_exact_matches_already_used",
                            }
                        )
                else:
                    # No available exact matches - try fuzzy
                    best_fuzzy = self.find_best_match(bnetza_company)
                    if (
                        best_fuzzy
                        and best_fuzzy.match_score < EXACT_MATCH_THRESHOLD
                        and best_fuzzy.bdew_company.bdew_code not in used_bdew_codes
                    ):
                        results["matches"].append(best_fuzzy)
                        used_bdew_codes.add(best_fuzzy.bdew_company.bdew_code)
                        results["stats"]["fuzzy_matches"] += 1
                    else:
                        results["no_matches"].append(bnetza_company)
                        results["stats"]["no_matches"] += 1
            else:
                # Try fuzzy matching
                best_fuzzy = self.find_best_match(bnetza_company)
                if (
                    best_fuzzy
                    and best_fuzzy.bdew_company.bdew_code not in used_bdew_codes
                ):
                    results["matches"].append(best_fuzzy)
                    used_bdew_codes.add(best_fuzzy.bdew_company.bdew_code)
                    results["stats"]["fuzzy_matches"] += 1
                else:
                    results["no_matches"].append(bnetza_company)
                    results["stats"]["no_matches"] += 1

        # Calculate success rate
        total_matched = (
            results["stats"]["exact_matches"] + results["stats"]["fuzzy_matches"]
        )
        results["stats"]["success_rate"] = (
            (total_matched / len(bnetza_companies)) * 100 if bnetza_companies else 0
        )

        return results
