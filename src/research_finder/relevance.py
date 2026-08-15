from __future__ import annotations

import re

from pydantic import Field

from research_finder.models import StrictModel
from research_finder.research_profile import (
    OrganisedResearcherProfile,
)
from research_finder.researcher_details import (
    ResearchEvidenceItem,
)


class RelevanceScoreBreakdown(StrictModel):
    """Explainable components of one relevance score."""

    research_interests: int = Field(
        ge=0,
        le=40,
    )
    current_projects: int = Field(
        ge=0,
        le=25,
    )
    publications: int = Field(
        ge=0,
        le=15,
    )
    labs: int = Field(
        ge=0,
        le=10,
    )
    previous_projects: int = Field(
        ge=0,
        le=5,
    )
    unknown_projects: int = Field(
        ge=0,
        le=5,
    )


class ScoredResearcherProfile(StrictModel):
    """Researcher profile with deterministic relevance score."""

    profile: OrganisedResearcherProfile

    relevance_score: int = Field(
        ge=0,
        le=100,
    )

    breakdown: RelevanceScoreBreakdown

    matched_terms: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    match_explanation: list[str] = Field(
        default_factory=list,
        max_length=10,
    )


_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
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


def _normalise(value: str) -> str:
    """Normalise text for matching."""

    return " ".join(_TOKEN_PATTERN.findall(value.casefold()))


def _tokenise(value: str) -> set[str]:
    """Convert text into meaningful deterministic tokens."""

    return {
        token
        for token in _TOKEN_PATTERN.findall(value.casefold())
        if (len(token) >= 2 and token not in _STOP_WORDS)
    }


def build_search_topics(
    research_topic: str,
    expanded_topics: list[str],
) -> list[str]:
    """Create ordered unique topics for scoring."""

    topics: list[str] = []
    seen: set[str] = set()

    for topic in [
        research_topic,
        *expanded_topics,
    ]:
        cleaned = " ".join(topic.split())

        if not cleaned:
            continue

        key = cleaned.casefold()

        if key in seen:
            continue

        seen.add(key)
        topics.append(cleaned)

    return topics


def _text_match_score(
    text: str,
    topics: list[str],
) -> float:
    """Calculate best lexical topic coverage for text."""

    if not text or not topics:
        return 0.0

    normalised_text = _normalise(text)
    text_tokens = _tokenise(text)

    if not text_tokens:
        return 0.0

    best_score = 0.0

    for index, topic in enumerate(topics):
        topic_tokens = _tokenise(topic)

        if not topic_tokens:
            continue

        matched_tokens = topic_tokens & text_tokens

        coverage = len(matched_tokens) / len(topic_tokens)

        normalised_topic = _normalise(topic)

        if normalised_topic and normalised_topic in normalised_text:
            coverage = 1.0

        # Original user topic receives full weight.
        # Expanded topics receive slightly less weight.
        topic_weight = 1.0 if index == 0 else 0.35

        weighted_score = coverage * topic_weight

        best_score = max(
            best_score,
            weighted_score,
        )

    return min(
        best_score,
        1.0,
    )


def _evidence_item_text(
    item: ResearchEvidenceItem,
) -> str:
    """Combine evidence fields for matching."""

    return f"{item.name} {item.evidence_text}"


def _best_group_score(
    texts: list[str],
    topics: list[str],
) -> float:
    """Return the strongest match from a group."""

    if not texts:
        return 0.0

    return max(
        _text_match_score(
            text,
            topics,
        )
        for text in texts
    )


def _weighted_score(
    match_score: float,
    maximum_points: int,
) -> int:
    """Convert a 0–1 match into category points."""

    return round(match_score * maximum_points)


def _collect_matched_terms(
    profile: OrganisedResearcherProfile,
    topics: list[str],
) -> list[str]:
    """Collect matched topic tokens for explanation."""

    candidate = profile.verified_researcher.candidate

    profile_text = " ".join(
        [
            *profile.research_interests,
            *[_evidence_item_text(item) for item in profile.current_projects],
            *[_evidence_item_text(item) for item in profile.previous_projects],
            *[_evidence_item_text(item) for item in profile.unknown_projects],
            *[_evidence_item_text(item) for item in candidate.labs],
            *[_evidence_item_text(item) for item in candidate.publications],
        ]
    )

    profile_tokens = _tokenise(profile_text)

    matched_terms: list[str] = []
    seen: set[str] = set()

    for topic in topics:
        for token in _TOKEN_PATTERN.findall(topic.casefold()):
            if (
                token in _STOP_WORDS
                or len(token) < 2
                or token not in profile_tokens
                or token in seen
            ):
                continue

            seen.add(token)
            matched_terms.append(token)

            if len(matched_terms) >= 20:
                return matched_terms

    return matched_terms


def _build_explanation(
    breakdown: RelevanceScoreBreakdown,
) -> list[str]:
    """Build deterministic score explanations."""

    categories = (
        (
            "Research interests",
            breakdown.research_interests,
            40,
        ),
        (
            "Current projects",
            breakdown.current_projects,
            25,
        ),
        (
            "Publications",
            breakdown.publications,
            15,
        ),
        (
            "Research labs/groups",
            breakdown.labs,
            10,
        ),
        (
            "Previous projects",
            breakdown.previous_projects,
            5,
        ),
        (
            "Projects with unknown status",
            breakdown.unknown_projects,
            5,
        ),
    )

    explanation = [
        (f"{label} contributed {points}/{maximum} points.")
        for label, points, maximum in categories
        if points > 0
    ]

    if not explanation:
        explanation.append(
            "No meaningful lexical overlap was "
            "found between the research topic "
            "and verified researcher evidence."
        )

    return explanation


def score_researcher_profile(
    profile: OrganisedResearcherProfile,
    *,
    research_topic: str,
    expanded_topics: list[str],
) -> ScoredResearcherProfile:
    """Calculate one deterministic relevance score."""

    topics = build_search_topics(
        research_topic=research_topic,
        expanded_topics=expanded_topics,
    )

    candidate = profile.verified_researcher.candidate

    interests_match = _best_group_score(
        profile.research_interests,
        topics,
    )

    current_projects_match = _best_group_score(
        [_evidence_item_text(item) for item in profile.current_projects],
        topics,
    )

    publications_match = _best_group_score(
        [_evidence_item_text(item) for item in candidate.publications],
        topics,
    )

    labs_match = _best_group_score(
        [_evidence_item_text(item) for item in candidate.labs],
        topics,
    )

    previous_projects_match = _best_group_score(
        [_evidence_item_text(item) for item in profile.previous_projects],
        topics,
    )

    unknown_projects_match = _best_group_score(
        [_evidence_item_text(item) for item in profile.unknown_projects],
        topics,
    )

    breakdown = RelevanceScoreBreakdown(
        research_interests=(
            _weighted_score(
                interests_match,
                40,
            )
        ),
        current_projects=(
            _weighted_score(
                current_projects_match,
                25,
            )
        ),
        publications=(
            _weighted_score(
                publications_match,
                15,
            )
        ),
        labs=(
            _weighted_score(
                labs_match,
                10,
            )
        ),
        previous_projects=(
            _weighted_score(
                previous_projects_match,
                5,
            )
        ),
        unknown_projects=(
            _weighted_score(
                unknown_projects_match,
                5,
            )
        ),
    )

    total_score = sum(
        (
            breakdown.research_interests,
            breakdown.current_projects,
            breakdown.publications,
            breakdown.labs,
            breakdown.previous_projects,
            breakdown.unknown_projects,
        )
    )

    return ScoredResearcherProfile(
        profile=profile,
        relevance_score=total_score,
        breakdown=breakdown,
        matched_terms=(
            _collect_matched_terms(
                profile,
                topics,
            )
        ),
        match_explanation=(_build_explanation(breakdown)),
    )


def score_researcher_profiles(
    profiles: list[OrganisedResearcherProfile],
    *,
    research_topic: str,
    expanded_topics: list[str],
) -> list[ScoredResearcherProfile]:
    """Score every organised researcher."""

    return [
        score_researcher_profile(
            profile,
            research_topic=research_topic,
            expanded_topics=expanded_topics,
        )
        for profile in profiles
    ]
