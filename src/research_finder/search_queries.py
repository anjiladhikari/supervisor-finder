from __future__ import annotations

from enum import StrEnum

from pydantic import (
    Field,
    field_validator,
    model_validator,
)

from research_finder.models import StrictModel
from research_finder.university_directory import (
    UniversityRecord,
)


class SearchTarget(StrEnum):
    """Official page type searched by the application."""

    RESEARCHER = "researcher"


class OfficialSearchQuery(StrictModel):
    """One university-domain researcher search query."""

    university_name: str = Field(
        min_length=2,
        max_length=200,
    )

    official_domain: str = Field(
        min_length=4,
        max_length=255,
    )

    target: SearchTarget

    topics: list[str] = Field(
        min_length=1,
        max_length=2,
    )

    query: str = Field(
        min_length=10,
        max_length=500,
    )

    @field_validator(
        "university_name",
        "query",
        mode="before",
    )
    @classmethod
    def normalise_text(
        cls,
        value: object,
    ) -> object:
        """Collapse repeated whitespace."""

        if isinstance(value, str):
            return " ".join(
                value.split()
            )

        return value

    @field_validator(
        "official_domain",
        mode="before",
    )
    @classmethod
    def normalise_domain(
        cls,
        value: object,
    ) -> object:
        """Normalise the university domain."""

        if isinstance(value, str):
            return (
                value.strip()
                .casefold()
                .removeprefix("www.")
            )

        return value

    @model_validator(
        mode="after"
    )
    def validate_domain_filter(
        self,
    ) -> OfficialSearchQuery:
        """Require domain-restricted search."""

        expected_prefix = (
            f"site:{self.official_domain} "
        )

        if not self.query.casefold().startswith(
            expected_prefix.casefold()
        ):
            raise ValueError(
                "query must begin with the "
                "official university domain."
            )

        return self


_RESEARCHER_CLAUSE = (
    '(researcher OR professor OR "research profile")'
)


def _clean_topic(
    topic: str,
) -> str:
    """Clean a topic before quoting it."""

    return " ".join(
        topic.replace(
            '"',
            "",
        ).split()
    )


def select_query_topics(
    topics: list[str],
    limit: int = 2,
) -> list[str]:
    """Select unique topics in priority order."""

    selected: list[str] = []
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

        seen.add(
            key
        )

        selected.append(
            cleaned
        )

        if len(selected) >= limit:
            break

    return selected


def build_official_search_query(
    university: UniversityRecord,
    target: SearchTarget,
    topics: list[str],
) -> OfficialSearchQuery:
    """Build one researcher query for a university."""

    selected_topics = (
        select_query_topics(
            topics
        )
    )

    if not selected_topics:
        raise ValueError(
            "At least one research topic is required."
        )

    if len(selected_topics) == 1:
        topic_clause = (
            f'"{selected_topics[0]}"'
        )

    else:
        topic_clause = (
            f'("{selected_topics[0]}" OR '
            f'"{selected_topics[1]}")'
        )

    query = (
        f"site:{university.official_domain} "
        f"{topic_clause} "
        f"{_RESEARCHER_CLAUSE}"
    )

    if len(query) > 500:
        selected_topics = (
            selected_topics[:1]
        )

        query = (
            f"site:{university.official_domain} "
            f'"{selected_topics[0]}" '
            f"{_RESEARCHER_CLAUSE}"
        )

    return OfficialSearchQuery(
        university_name=(
            university.name
        ),
        official_domain=(
            university.official_domain
        ),
        target=target,
        topics=selected_topics,
        query=query,
    )


def generate_official_search_queries(
    universities: list[
        UniversityRecord
    ],
    topics: list[str],
) -> list[
    OfficialSearchQuery
]:
    """Generate one researcher query per university."""

    return [
        build_official_search_query(
            university=university,
            target=(
                SearchTarget.RESEARCHER
            ),
            topics=topics,
        )
        for university in universities
    ]