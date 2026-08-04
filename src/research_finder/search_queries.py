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
    """Types of official university pages to search."""

    RESEARCHER = "researcher"
    LAB = "lab"
    PROJECT = "project"
    PUBLICATION = "publication"


class OfficialSearchQuery(StrictModel):
    """One domain-restricted university search query."""

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
            return " ".join(value.split())

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
        """Normalise the official root domain."""

        if isinstance(value, str):
            return value.strip().casefold().removeprefix("www.")

        return value

    @model_validator(mode="after")
    def validate_domain_filter(
        self,
    ) -> OfficialSearchQuery:
        """Ensure the query starts with its official domain."""

        expected_prefix = f"site:{self.official_domain} "

        if not self.query.casefold().startswith(expected_prefix.casefold()):
            raise ValueError("query must begin with the official university domain.")

        return self


_TARGET_CLAUSES = {
    SearchTarget.RESEARCHER: ("(researcher OR professor OR academic OR staff)"),
    SearchTarget.LAB: ('("research group" OR "research lab" OR laboratory)'),
    SearchTarget.PROJECT: ("(project OR grant OR funded)"),
    SearchTarget.PUBLICATION: ("(publication OR paper OR journal)"),
}


def _clean_topic(topic: str) -> str:
    """Clean a topic before placing it inside quotes."""

    return " ".join(topic.replace('"', "").split())


def select_query_topics(
    topics: list[str],
    limit: int = 2,
) -> list[str]:
    """Select the first unique topics in priority order."""

    selected_topics: list[str] = []
    seen_topics: set[str] = set()

    for topic in topics:
        cleaned_topic = _clean_topic(topic)

        if not cleaned_topic:
            continue

        comparison_key = cleaned_topic.casefold()

        if comparison_key in seen_topics:
            continue

        seen_topics.add(comparison_key)
        selected_topics.append(cleaned_topic)

        if len(selected_topics) >= limit:
            break

    return selected_topics


def build_official_search_query(
    university: UniversityRecord,
    target: SearchTarget,
    topics: list[str],
) -> OfficialSearchQuery:
    """Build one query restricted to a university domain."""

    selected_topics = select_query_topics(topics)

    if not selected_topics:
        raise ValueError("At least one research topic is required.")

    if len(selected_topics) == 1:
        topic_clause = f'"{selected_topics[0]}"'
    else:
        topic_clause = f'("{selected_topics[0]}" OR "{selected_topics[1]}")'

    target_clause = _TARGET_CLAUSES[target]

    query = f"site:{university.official_domain} {topic_clause} {target_clause}"

    # A single topic always fits the Step 7
    # WebSearchRequest maximum more safely.
    if len(query) > 500:
        selected_topics = selected_topics[:1]

        query = f'site:{university.official_domain} "{selected_topics[0]}" {target_clause}'

    return OfficialSearchQuery(
        university_name=university.name,
        official_domain=(university.official_domain),
        target=target,
        topics=selected_topics,
        query=query,
    )


def generate_official_search_queries(
    universities: list[UniversityRecord],
    topics: list[str],
) -> list[OfficialSearchQuery]:
    """Generate four official queries per university."""

    queries: list[OfficialSearchQuery] = []

    for university in universities:
        for target in SearchTarget:
            queries.append(
                build_official_search_query(
                    university=university,
                    target=target,
                    topics=topics,
                )
            )

    return queries
