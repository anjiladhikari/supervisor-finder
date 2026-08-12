from __future__ import annotations

from pydantic import Field

from research_finder.models import StrictModel
from research_finder.relevance import (
    ScoredResearcherProfile,
)


class RankedResearcherProfile(StrictModel):
    """One ranked researcher result."""

    rank: int = Field(
        ge=1,
    )

    result: ScoredResearcherProfile


def _ranking_key(
    result: ScoredResearcherProfile,
) -> tuple[
    int,
    int,
    int,
    int,
    str,
    str,
]:
    """Build deterministic ranking priority."""

    profile = result.profile

    verified = (
        profile.verified_researcher
    )

    candidate = verified.candidate

    researcher = candidate.researcher

    return (
        -result.relevance_score,
        -len(
            profile.current_projects
        ),
        -len(
            candidate.publications
        ),
        -verified.verified_source_count,
        researcher.full_name.casefold(),
        researcher.university_name.casefold(),
    )


def rank_researcher_results(
    results: list[
        ScoredResearcherProfile
    ],
    *,
    max_results: int,
) -> list[RankedResearcherProfile]:
    """Rank researchers and keep strongest matches."""

    if max_results <= 0:
        return []

    relevant_results = [
        result
        for result in results
        if result.relevance_score > 0
    ]

    ordered = sorted(
        relevant_results,
        key=_ranking_key,
    )

    strongest = ordered[
        :max_results
    ]

    return [
        RankedResearcherProfile(
            rank=index,
            result=result,
        )
        for index, result in enumerate(
            strongest,
            start=1,
        )
    ]