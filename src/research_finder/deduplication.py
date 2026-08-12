from __future__ import annotations

import re
from collections.abc import Callable
from typing import TypeVar
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
)

from research_finder.relevance import (
    ScoredResearcherProfile,
    score_researcher_profile,
)
from research_finder.research_profile import (
    organise_verified_researcher,
)
from research_finder.researcher_details import (
    EnrichedResearcherCandidate,
    ResearchEvidenceItem,
)
from research_finder.verification import (
    VerifiedResearcherCandidate,
)


T = TypeVar("T")


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
    """Create a deterministic URL key for deduplication."""

    parsed = urlsplit(url)

    hostname = (
        parsed.hostname or ""
    ).casefold()

    hostname = hostname.removeprefix(
        "www."
    )

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
        lowered_key = key.casefold()

        if (
            lowered_key.startswith("utm_")
            or lowered_key
            in _TRACKING_PARAMETERS
        ):
            continue

        query_items.append(
            (
                lowered_key,
                value,
            )
        )

    query = urlencode(
        sorted(query_items)
    )

    key = (
        f"{hostname}{path}"
    )

    if query:
        key = f"{key}?{query}"

    return key


def deduplicate_by_source_url(
    items: list[T],
    *,
    url_getter: Callable[[T], str],
    seen_keys: set[str] | None = None,
) -> tuple[list[T], int]:
    """Remove duplicate objects using canonical URLs."""

    seen = (
        seen_keys
        if seen_keys is not None
        else set()
    )

    unique_items: list[T] = []
    removed = 0

    for item in items:
        key = canonical_source_url_key(
            url_getter(item)
        )

        if key in seen:
            removed += 1
            continue

        seen.add(key)
        unique_items.append(item)

    return unique_items, removed


def _normalise_name(
    value: str,
) -> str:
    """Normalise researcher names."""

    tokens = re.findall(
        r"\w+",
        value.casefold(),
    )

    while (
        tokens
        and tokens[0] in _NAME_PREFIXES
    ):
        tokens.pop(0)

    return " ".join(tokens)


def researcher_deduplication_key(
    result: ScoredResearcherProfile,
) -> str:
    """Build a stable researcher identity key."""

    researcher = (
        result.profile
        .verified_researcher
        .candidate
        .researcher
    )

    return (
        researcher.official_domain.casefold()
        + "|"
        + _normalise_name(
            researcher.full_name
        )
    )


def _unique_strings(
    values: list[str],
) -> list[str]:
    """Deduplicate strings while preserving order."""

    unique: list[str] = []
    seen: set[str] = set()

    for value in values:
        cleaned = " ".join(
            value.split()
        )

        if not cleaned:
            continue

        key = cleaned.casefold()

        if key in seen:
            continue

        seen.add(key)
        unique.append(cleaned)

    return unique


def _evidence_item_key(
    item: ResearchEvidenceItem,
) -> tuple[str, str]:
    """Build a semantic evidence-item key."""

    name = " ".join(
        re.findall(
            r"\w+",
            item.name.casefold(),
        )
    )

    return (
        item.target.value,
        name,
    )


def _evidence_quality(
    item: ResearchEvidenceItem,
) -> tuple[int, int]:
    """Prefer richer duplicate evidence."""

    has_year = int(
        item.publication_year
        is not None
    )

    return (
        has_year,
        len(item.evidence_text),
    )


def deduplicate_evidence_items(
    items: list[ResearchEvidenceItem],
) -> list[ResearchEvidenceItem]:
    """Merge duplicate labs, projects or publications."""

    selected: dict[
        tuple[str, str],
        ResearchEvidenceItem,
    ] = {}

    order: list[
        tuple[str, str]
    ] = []

    for item in items:
        key = _evidence_item_key(
            item
        )

        existing = selected.get(key)

        if existing is None:
            selected[key] = item
            order.append(key)
            continue

        if (
            _evidence_quality(item)
            > _evidence_quality(existing)
        ):
            selected[key] = item

    return [
        selected[key]
        for key in order
    ]


def _choose_representative(
    results: list[
        ScoredResearcherProfile
    ],
) -> ScoredResearcherProfile:
    """Select the strongest duplicate record."""

    return max(
        results,
        key=lambda result: (
            result.relevance_score,
            (
                result.profile
                .verified_researcher
                .verified_source_count
            ),
        ),
    )


def _merge_researcher_group(
    results: list[
        ScoredResearcherProfile
    ],
    *,
    research_topic: str,
    expanded_topics: list[str],
) -> ScoredResearcherProfile:
    """Merge duplicate researcher records and rescore."""

    representative = (
        _choose_representative(
            results
        )
    )

    representative_verified = (
        representative.profile
        .verified_researcher
    )

    representative_candidate = (
        representative_verified.candidate
    )

    researcher = (
        representative_candidate.researcher
    )

    interests = _unique_strings(
        [
            interest
            for result in results
            for interest in (
                result.profile
                .verified_researcher
                .candidate
                .researcher
                .research_interests
            )
        ]
    )

    merged_researcher = (
        researcher.model_copy(
            update={
                "research_interests": (
                    interests
                )
            }
        )
    )

    labs = deduplicate_evidence_items(
        [
            item
            for result in results
            for item in (
                result.profile
                .verified_researcher
                .candidate
                .labs
            )
        ]
    )

    projects = deduplicate_evidence_items(
        [
            item
            for result in results
            for item in (
                result.profile
                .verified_researcher
                .candidate
                .projects
            )
        ]
    )

    publications = (
        deduplicate_evidence_items(
            [
                item
                for result in results
                for item in (
                    result.profile
                    .verified_researcher
                    .candidate
                    .publications
                )
            ]
        )
    )

    public_email = None
    public_email_source_url = None

    ordered_results = sorted(
        results,
        key=lambda result: (
            result.relevance_score,
            (
                result.profile
                .verified_researcher
                .verified_source_count
            ),
        ),
        reverse=True,
    )

    for result in ordered_results:
        candidate = (
            result.profile
            .verified_researcher
            .candidate
        )

        if candidate.public_email is None:
            continue

        public_email = (
            candidate.public_email
        )
        public_email_source_url = (
            candidate.public_email_source_url
        )
        break

    merged_candidate = (
        EnrichedResearcherCandidate(
            researcher=merged_researcher,
            public_email=public_email,
            public_email_source_url=(
                public_email_source_url
            ),
            labs=labs,
            projects=projects,
            publications=publications,
        )
    )

    source_keys = {
        canonical_source_url_key(
            str(
                merged_researcher.source_url
            )
        )
    }

    if public_email_source_url is not None:
        source_keys.add(
            canonical_source_url_key(
                str(
                    public_email_source_url
                )
            )
        )

    for item in [
        *labs,
        *projects,
        *publications,
    ]:
        source_keys.add(
            canonical_source_url_key(
                str(item.source_url)
            )
        )

    latest_verified_at = max(
        result.profile
        .verified_researcher
        .verified_at
        for result in results
    )

    merged_verified = (
        VerifiedResearcherCandidate(
            candidate=merged_candidate,
            affiliation_source_url=(
                representative_verified
                .affiliation_source_url
            ),
            verified_at=(
                latest_verified_at
            ),
            verified_source_count=(
                len(source_keys)
            ),
        )
    )

    organised = (
        organise_verified_researcher(
            merged_verified
        )
    )

    return score_researcher_profile(
        organised,
        research_topic=research_topic,
        expanded_topics=expanded_topics,
    )


def deduplicate_scored_researchers(
    results: list[
        ScoredResearcherProfile
    ],
    *,
    research_topic: str,
    expanded_topics: list[str],
) -> list[ScoredResearcherProfile]:
    """Merge duplicate researchers and rescore them."""

    groups: dict[
        str,
        list[ScoredResearcherProfile],
    ] = {}

    order: list[str] = []

    for result in results:
        key = researcher_deduplication_key(
            result
        )

        if key not in groups:
            groups[key] = []
            order.append(key)

        groups[key].append(result)

    return [
        _merge_researcher_group(
            groups[key],
            research_topic=research_topic,
            expanded_topics=(
                expanded_topics
            ),
        )
        for key in order
    ]