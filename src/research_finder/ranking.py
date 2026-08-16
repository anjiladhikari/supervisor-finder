from __future__ import annotations

from pydantic import Field

from research_finder.models import (
    StrictModel,
)
from research_finder.relevance import (
    ScoredResearcherProfile,
)


class RankedResearcherProfile(
    StrictModel
):
    """One ranked researcher."""

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
    researcher = (
        result
        .verified_researcher
        .candidate
    )

    verified = (
        result
        .verified_researcher
    )

    return (
        -result.relevance_score,
        -result.keyword_score,
        -result.semantic_score,
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
) -> list[
    RankedResearcherProfile
]:
    """Rank strongest topic matches."""

    if max_results <= 0:
        return []

    relevant = [
        result
        for result in results
        if result.relevance_score > 0
    ]

    ordered = sorted(
        relevant,
        key=_ranking_key,
    )

    return [
        RankedResearcherProfile(
            rank=index,
            result=result,
        )
        for index, result in enumerate(
            ordered[:max_results],
            start=1,
        )
    ]