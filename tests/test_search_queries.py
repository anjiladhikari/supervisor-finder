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


def test_generates_four_queries_per_university() -> None:
    queries = generate_official_search_queries(
        universities=[create_test_university()],
        topics=[
            "Reinforcement learning",
            "Early time-series classification",
        ],
    )

    assert len(queries) == 4

    assert {query.target for query in queries} == set(SearchTarget)


def test_every_query_uses_official_domain() -> None:
    queries = generate_official_search_queries(
        universities=[create_test_university()],
        topics=[
            "Reinforcement learning",
            "Early time-series classification",
        ],
    )

    assert all(query.query.startswith("site:deakin.edu.au ") for query in queries)

    assert all(query.official_domain == "deakin.edu.au" for query in queries)


def test_query_topics_are_deduplicated() -> None:
    queries = generate_official_search_queries(
        universities=[create_test_university()],
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


def test_node_generates_queries() -> None:
    result = generate_search_queries(
        {
            "candidate_universities": [create_test_university()],
            "expanded_topics": [
                "Reinforcement learning",
                "Time-series classification",
            ],
        }
    )

    assert len(result["search_queries"]) == 4

    assert result["execution_log"] == [("Generated 4 official university-domain queries.")]


def test_node_requires_universities() -> None:
    result = generate_search_queries(
        {
            "candidate_universities": [],
            "expanded_topics": ["Reinforcement learning"],
        }
    )

    assert result["search_queries"] == []

    assert result["errors"] == [
        ("Search queries cannot be generated without candidate universities.")
    ]
