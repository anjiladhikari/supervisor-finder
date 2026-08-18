from research_finder.nodes import (
    generate_search_queries,
)
from research_finder.search_queries import (
    SearchTarget,
    generate_official_search_queries,
)
from research_finder.university_directory import (
    UniversityRecord,
)


def create_test_university() -> UniversityRecord:
    """Create one university for query tests."""

    return UniversityRecord(
        name="Deakin University",
        aliases=["Deakin"],
        country_code="AU",
        state_codes=["AU-VIC"],
        official_domain="deakin.edu.au",
    )


def test_generates_one_query_per_university() -> None:
    queries = generate_official_search_queries(
        universities=[
            create_test_university()
        ],
        topics=[
            "Reinforcement learning",
            "Early time-series classification",
        ],
    )

    assert len(queries) == 1

    assert (
        queries[0].target
        == SearchTarget.RESEARCHER
    )


def test_query_uses_official_domain() -> None:
    queries = generate_official_search_queries(
        universities=[
            create_test_university()
        ],
        topics=[
            "Reinforcement learning",
        ],
    )

    query = queries[0]

    assert query.query.startswith(
        "site:deakin.edu.au "
    )

    assert (
        query.official_domain
        == "deakin.edu.au"
    )


def test_query_topics_are_deduplicated() -> None:
    queries = generate_official_search_queries(
        universities=[
            create_test_university()
        ],
        topics=[
            "Reinforcement learning",
            "reinforcement learning",
            "Time-series classification",
        ],
    )

    assert queries[0].topics == [
        "Reinforcement learning",
        "Time-series classification",
    ]


def test_node_generates_researcher_query() -> None:
    result = generate_search_queries(
        {
            "candidate_universities": [
                create_test_university()
            ],
            "expanded_topics": [
                "Reinforcement learning",
                "Time-series classification",
            ],
        }
    )

    queries = result[
        "search_queries"
    ]

    assert len(queries) == 1

    assert queries[0].topics == [
        "Reinforcement learning"
    ]

    assert (
        queries[0].target
        == SearchTarget.RESEARCHER
    )

    assert result["execution_log"] == [
        (
            "Generated 1 official "
            "university-domain queries "
            "for normal search round 1."
        )
    ]


def test_node_requires_universities() -> None:
    result = generate_search_queries(
        {
            "candidate_universities": [],
            "expanded_topics": [
                "Reinforcement learning"
            ],
        }
    )

    assert (
        result["search_queries"]
        == []
    )


def test_node_uses_active_retry_topics() -> None:
    result = generate_search_queries(
        {
            "candidate_universities": [
                create_test_university()
            ],
            "expanded_topics": [
                "Reinforcement learning",
                "Machine learning",
            ],
            "active_search_topics": [
                "Exact specialised topic"
            ],
            "search_mode": "narrow",
            "search_round": 2,
        }
    )

    queries = result[
        "search_queries"
    ]

    assert len(queries) == 1

    assert queries[0].topics == [
        "Exact specialised topic"
    ]