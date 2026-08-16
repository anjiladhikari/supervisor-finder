from __future__ import annotations

import re
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
)

from research_finder.relevance import (
    ScoredResearcherProfile,
)

_TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "msclkid",
}

_NAME_PREFIXES = {
    "dr",
    "prof",
    "professor",
}


def canonical_source_url_key(
    url: str,
) -> str:
    """Create a stable URL key."""

    parsed = urlsplit(url)

    hostname = (
        parsed.hostname or ""
    ).casefold().removeprefix("www.")

    path = re.sub(
        r"/+",
        "/",
        parsed.path,
    )

    if path != "/":
        path = path.rstrip("/")

    query_items = []

    for key, value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):
        lowered = key.casefold()

        if (
            lowered.startswith("utm_")
            or lowered
            in _TRACKING_PARAMETERS
        ):
            continue

        query_items.append(
            (
                lowered,
                value,
            )
        )

    query = urlencode(
        sorted(query_items)
    )

    result = f"{hostname}{path}"

    if query:
        result = f"{result}?{query}"

    return result


def _normalise_name(
    value: str,
) -> str:
    tokens = re.findall(
        r"\w+",
        value.casefold(),
    )

    while (
        tokens
        and tokens[0]
        in _NAME_PREFIXES
    ):
        tokens.pop(0)

    return " ".join(tokens)


def researcher_deduplication_key(
    result: ScoredResearcherProfile,
) -> str:
    researcher = (
        result
        .verified_researcher
        .candidate
    )

    return (
        researcher.official_domain.casefold()
        + "|"
        + _normalise_name(
            researcher.full_name
        )
    )


def deduplicate_scored_researchers(
    results: list[
        ScoredResearcherProfile
    ],
) -> list[
    ScoredResearcherProfile
]:
    """Keep strongest record for each researcher."""

    selected: dict[
        str,
        ScoredResearcherProfile,
    ] = {}

    order: list[str] = []

    for result in results:
        key = researcher_deduplication_key(
            result
        )

        existing = selected.get(
            key
        )

        if existing is None:
            selected[key] = result
            order.append(key)
            continue

        current_priority = (
            result.relevance_score,
            result.keyword_score,
            result.semantic_score,
            (
                result
                .verified_researcher
                .verified_source_count
            ),
        )

        existing_priority = (
            existing.relevance_score,
            existing.keyword_score,
            existing.semantic_score,
            (
                existing
                .verified_researcher
                .verified_source_count
            ),
        )

        if (
            current_priority
            > existing_priority
        ):
            selected[key] = result

    return [
        selected[key]
        for key in order
    ]