#!/usr/bin/env python3
"""
BNetzA Roll-Out Data Matching Script

Matches BNetzA Roll-Out companies with existing BDEW companies in the database
based on normalized company names.
"""

import asyncio
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import func, select, update

from src.database import get_db_manager
from src.models import Company, RolloutCompany

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


def normalize_company_name(name: str) -> str:
    """
    Normalize company name for matching.
    Same logic as in import_rollout_csv.py
    """
    if not name:
        return ""

    # Convert to lowercase and strip whitespace
    normalized = name.lower().strip()

    # Remove common legal suffixes
    legal_suffixes = [
        " gmbh",
        " ag",
        " se",
        " kg",
        " ohg",
        " gbr",
        " ev",
        " eg",
        " mbh",
        " gmbh & co. kg",
        " gmbh & co kg",
        " co. kg",
        " co kg",
        " & co. kg",
        " & co kg",
        " gesellschaft mit beschränkter haftung",
        " aktiengesellschaft",
        " kommanditgesellschaft",
        " offene handelsgesellschaft",
        " gesellschaft bürgerlichen rechts",
        " eingetragener verein",
        " eingetragene genossenschaft",
    ]

    for suffix in legal_suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()

    # Remove special characters but keep spaces and basic punctuation
    normalized = re.sub(r"[^\w\s\-\.]", "", normalized)

    # Normalize multiple spaces to single space
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


async def find_matching_companies() -> list[tuple[int, int, str, str]]:
    """
    Find matches between rollout companies and BDEW companies.
    Returns list of (rollout_company_id, bdew_company_id, rollout_name, bdew_name) tuples.
    """
    db_manager = get_db_manager()

    matches = []

    async for session in db_manager.get_async_session():
        # Get all unmatched rollout companies
        rollout_query = select(RolloutCompany).where(
            RolloutCompany.bdew_company_id.is_(None)
        )
        rollout_result = await session.execute(rollout_query)
        rollout_companies = rollout_result.scalars().all()

        # Get all companies with bdew_name
        company_query = select(Company).where(Company.bdew_name.is_not(None))
        company_result = await session.execute(company_query)
        companies = company_result.scalars().all()

        print(f"📊 Found {len(rollout_companies)} unmatched rollout companies")
        print(f"📊 Found {len(companies)} companies with BDEW names")

        # Create lookup dictionary for companies by normalized name
        company_lookup = {}
        for company in companies:
            if company.bdew_name:
                normalized_name = normalize_company_name(company.bdew_name)
                if normalized_name:
                    company_lookup[normalized_name] = company

        print(f"📊 Created lookup for {len(company_lookup)} normalized company names")

        # Try to match rollout companies
        for rollout_company in rollout_companies:
            normalized_rollout_name = normalize_company_name(
                rollout_company.bnetza_name
            )

            if normalized_rollout_name in company_lookup:
                company = company_lookup[normalized_rollout_name]
                matches.append(
                    (
                        rollout_company.id,
                        company.id,
                        rollout_company.bnetza_name,
                        company.bdew_name,
                    )
                )

        break  # Only use first session

    return matches


async def apply_matches(matches: list[tuple[int, int, str, str]]) -> None:
    """Apply the found matches to the database."""
    db_manager = get_db_manager()

    async for session in db_manager.get_async_session():
        for rollout_company_id, bdew_company_id, rollout_name, company_name in matches:
            # Update the rollout company with the matched BDEW company ID
            update_query = (
                update(RolloutCompany)
                .where(RolloutCompany.id == rollout_company_id)
                .values(bdew_company_id=bdew_company_id)
            )
            await session.execute(update_query)
            print(
                f"✅ Matched: '{rollout_name}' → '{company_name}' (ID: {bdew_company_id})"
            )

        # Commit all changes
        await session.commit()
        print(f"💾 Committed {len(matches)} matches to database")
        break  # Only use first session


async def get_matching_statistics() -> dict[str, int | float]:
    """Get statistics about the matching process."""
    db_manager = get_db_manager()

    async for session in db_manager.get_async_session():
        # Total rollout companies
        total_query = select(func.count()).select_from(RolloutCompany)
        total_result = await session.execute(total_query)
        total_companies = total_result.scalar()

        # Matched companies (those with bdew_company_id)
        matched_query = (
            select(func.count())
            .select_from(RolloutCompany)
            .where(RolloutCompany.bdew_company_id.is_not(None))
        )
        matched_result = await session.execute(matched_query)
        matched_companies = matched_result.scalar()

        # Ensure we have valid integers (handle None case)
        total_companies = total_companies or 0
        matched_companies = matched_companies or 0

        # Unmatched companies
        unmatched_companies = total_companies - matched_companies

        return {
            "total_entries": total_companies,
            "matched_entries": matched_companies,
            "unmatched_entries": unmatched_companies,
            "match_rate": (
                (matched_companies / total_companies * 100)
                if total_companies > 0
                else 0.0
            ),
        }

    # Fallback if no session is available
    return {
        "total_entries": 0,
        "matched_entries": 0,
        "unmatched_entries": 0,
        "match_rate": 0.0,
    }


async def main():
    """Main matching process."""
    print("🔄 Starting BNetzA Roll-Out data matching process...")

    try:
        # Show initial statistics
        initial_stats = await get_matching_statistics()
        print("\n📈 Initial Statistics:")
        print(f"   Total companies: {initial_stats['total_entries']}")
        print(f"   Already matched: {initial_stats['matched_entries']}")
        print(f"   Unmatched: {initial_stats['unmatched_entries']}")
        print(f"   Match rate: {initial_stats['match_rate']:.1f}%")

        # Find matches
        print("\n🔍 Searching for matches...")
        matches = await find_matching_companies()

        if matches:
            print(f"\n✨ Found {len(matches)} potential matches:")
            # Show first few matches for preview
            PREVIEW_LIMIT = 10
            for _, _, rollout_name, company_name in matches[:PREVIEW_LIMIT]:
                print(f"   '{rollout_name}' → '{company_name}'")

            if len(matches) > PREVIEW_LIMIT:
                print(f"   ... and {len(matches) - PREVIEW_LIMIT} more matches")

            # Ask for confirmation (in a real scenario, you might want this)
            print(f"\n💾 Applying {len(matches)} matches to database...")
            await apply_matches(matches)

            # Show final statistics
            final_stats = await get_matching_statistics()
            print("\n📈 Final Statistics:")
            print(f"   Total companies: {final_stats['total_entries']}")
            print(
                f"   Matched: {final_stats['matched_entries']} (+{final_stats['matched_entries'] - initial_stats['matched_entries']})"
            )
            print(f"   Unmatched: {final_stats['unmatched_entries']}")
            print(
                f"   Match rate: {final_stats['match_rate']:.1f}% (+{final_stats['match_rate'] - initial_stats['match_rate']:.1f}%)"
            )

        else:
            print("❌ No new matches found")

        print("\n✅ Matching process completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during matching process: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
