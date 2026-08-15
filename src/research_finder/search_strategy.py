from __future__ import annotations

from enum import StrEnum

from research_finder.models import (
    TopicExpansion,
)


class SearchMode(StrEnum):
    """Search-query strategy used for one search round."""

    NORMAL = "normal"
    BROADEN = "broaden"
    NARROW = "narrow"


MAX_SEARCH_ROUNDS = 2


def _clean_topic(
    value: str,
) -> str:
    """Normalise one research topic."""

    return " ".join(
        value.split()
    )


def _unique_topics(
    topics: list[str],
) -> list[str]:
    """Keep unique topics while preserving order."""

    unique: list[str] = []
    seen: set[str] = set()

    for topic in topics:
        cleaned = _clean_topic(
            topic
        )

        if not cleaned:
            continue

        key = cleaned.casefold()

        if key in seen:
            continue

        seen.add(key)
        unique.append(cleaned)

    return unique


def build_broadened_search_topics(
    *,
    original_topic: str,
    topic_expansion: TopicExpansion | None,
    expanded_topics: list[str],
) -> list[str]:
    """Create a broader two-topic search query."""

    candidates = [
        original_topic,
    ]

    if topic_expansion is not None:
        candidates.extend(
            topic_expansion.broader_topics
        )

        if not topic_expansion.broader_topics:
            candidates.extend(
                topic_expansion.related_topics
            )

    candidates.extend(
        expanded_topics
    )

    return _unique_topics(
        candidates
    )[:2]


def build_narrowed_search_topics(
    *,
    original_topic: str,
) -> list[str]:
    """Use only the user's exact research topic."""

    return [
        _clean_topic(
            original_topic
        )
    ]


def researcher_page_narrow_threshold(
    *,
    university_count: int,
    max_results: int,
) -> int:
    """Calculate when researcher search is too broad."""

    return max(
        8,
        university_count * 2,
        max_results * 3,
    )


def choose_researcher_search_route(
    *,
    researcher_page_count: int,
    university_count: int,
    max_results: int,
    search_round: int,
    search_mode: SearchMode,
    has_errors: bool,
) -> str:
    """Choose what happens after researcher search."""

    if has_errors:
        return "generate_final_output"

    if researcher_page_count == 0:
        if (
            search_round
            < MAX_SEARCH_ROUNDS
            and search_mode
            == SearchMode.NORMAL
        ):
            return "broaden_search"

        return "generate_final_output"

    threshold = (
        researcher_page_narrow_threshold(
            university_count=university_count,
            max_results=max_results,
        )
    )

    if (
        researcher_page_count
        > threshold
        and search_round
        < MAX_SEARCH_ROUNDS
        and search_mode
        != SearchMode.NARROW
    ):
        return "narrow_search"

    return "download_webpage_content"