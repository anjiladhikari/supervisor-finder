from __future__ import annotations

import re

from pydantic import Field

from research_finder.models import StrictModel
from research_finder.verification import (
    VerifiedResearcherCandidate,
)

_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "using",
    "with",
}

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

KEYWORD_WEIGHT = 0.70
SEMANTIC_WEIGHT = 0.30


class ScoredResearcherProfile(StrictModel):
    """Verified researcher with topic-match score."""

    verified_researcher: VerifiedResearcherCandidate

    relevance_score: int = Field(
        ge=0,
        le=100,
    )

    keyword_score: int = Field(
        ge=0,
        le=100,
    )

    semantic_score: int = Field(
        ge=0,
        le=100,
    )

    matched_terms: list[str] = Field(
        default_factory=list,
        max_length=30,
    )

    match_explanation: list[str] = Field(
        default_factory=list,
        max_length=5,
    )


def _normalise(value: str) -> str:
    return " ".join(
        value.casefold().split()
    )


def _tokenise(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_PATTERN.findall(
            value.casefold()
        )
        if (
            len(token) >= 2
            and token not in _STOP_WORDS
        )
    }


def _topic_match_score(
    topic: str,
    interest: str,
) -> tuple[int, set[str]]:
    """Compare one topic with one official research interest."""

    normalised_topic = _normalise(topic)
    normalised_interest = _normalise(interest)

    if not normalised_topic:
        return 0, set()

    # Exact phrase match is strongest.
    if (
        normalised_topic
        == normalised_interest
        or normalised_topic
        in normalised_interest
    ):
        return 100, _tokenise(topic)

    topic_tokens = _tokenise(topic)
    interest_tokens = _tokenise(interest)

    if not topic_tokens:
        return 0, set()

    matched = (
        topic_tokens
        & interest_tokens
    )

    score = round(
        100
        * len(matched)
        / len(topic_tokens)
    )

    return score, matched


def _best_match(
    topics: list[str],
    interests: list[str],
) -> tuple[int, set[str], str | None]:
    best_score = 0
    best_terms: set[str] = set()
    best_topic: str | None = None

    for topic in topics:
        for interest in interests:
            score, matched = (
                _topic_match_score(
                    topic,
                    interest,
                )
            )

            if score > best_score:
                best_score = score
                best_terms = matched
                best_topic = topic

    return (
        best_score,
        best_terms,
        best_topic,
    )


def score_researcher_profile(
    verified: VerifiedResearcherCandidate,
    *,
    research_topic: str,
    expanded_topics: list[str],
) -> ScoredResearcherProfile:
    """Combine direct and semantic topic matching."""

    candidate = verified.candidate

    interests = (
        candidate.research_interests
    )

    keyword_score, keyword_terms, _ = (
        _best_match(
            [research_topic],
            interests,
        )
    )

    original_topic = _normalise(
        research_topic
    )

    semantic_topics = [
        topic
        for topic in expanded_topics
        if (
            _normalise(topic)
            != original_topic
        )
    ]

    (
        semantic_score,
        semantic_terms,
        semantic_topic,
    ) = _best_match(
        semantic_topics,
        interests,
    )

    relevance_score = round(
        (
            keyword_score
            * KEYWORD_WEIGHT
        )
        +
        (
            semantic_score
            * SEMANTIC_WEIGHT
        )
    )

    matched_terms = sorted(
        keyword_terms
        | semantic_terms
    )

    explanation = [
        (
            f"Direct topic match: "
            f"{keyword_score}/100."
        ),
        (
            f"Semantic related-topic match: "
            f"{semantic_score}/100."
        ),
    ]

    if semantic_topic:
        explanation.append(
            
                "Best related topic: "
                f"{semantic_topic}."
            
        )

    return ScoredResearcherProfile(
        verified_researcher=verified,
        relevance_score=(
            relevance_score
        ),
        keyword_score=(
            keyword_score
        ),
        semantic_score=(
            semantic_score
        ),
        matched_terms=(
            matched_terms
        ),
        match_explanation=(
            explanation
        ),
    )


def score_researcher_profiles(
    researchers: list[
        VerifiedResearcherCandidate
    ],
    *,
    research_topic: str,
    expanded_topics: list[str],
) -> list[ScoredResearcherProfile]:
    return [
        score_researcher_profile(
            researcher,
            research_topic=(
                research_topic
            ),
            expanded_topics=(
                expanded_topics
            ),
        )
        for researcher in researchers
    ]