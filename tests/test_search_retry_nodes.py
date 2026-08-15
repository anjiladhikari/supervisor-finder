from research_finder import (
    nodes as nodes_module,
)
from research_finder.models import (
    SearchRequest,
)
from research_finder.search_strategy import (
    SearchMode,
)


def create_request() -> SearchRequest:
    """Create one valid search request."""

    return SearchRequest(
        country="Australia",
        country_code="AU",
        state="Victoria",
        state_code="AU-VIC",
        research_topic=(
            "Reinforcement learning"
        ),
        max_results=10,
    )


def test_broaden_node_prepares_retry() -> None:
    result = nodes_module.broaden_search(
        {
            "request": create_request(),
            "search_round": 1,
            "expanded_topics": [
                "Reinforcement learning",
                "Machine learning",
            ],
            "topic_expansion": None,
        }
    )

    assert (
        result["search_mode"]
        == SearchMode.BROADEN
    )

    assert result["search_round"] == 2

    assert result[
        "active_search_topics"
    ] == [
        "Reinforcement learning",
        "Machine learning",
    ]

    assert result[
        "researcher_pages"
    ] == []


def test_narrow_node_prepares_retry() -> None:
    result = nodes_module.narrow_search(
        {
            "request": create_request(),
            "search_round": 1,
        }
    )

    assert (
        result["search_mode"]
        == SearchMode.NARROW
    )

    assert result["search_round"] == 2

    assert result[
        "active_search_topics"
    ] == [
        "Reinforcement learning"
    ]


def test_broaden_requires_request() -> None:
    result = nodes_module.broaden_search(
        {}
    )

    assert result["errors"] == [
        (
            "Broaden search requires "
            "a validated search request."
        )
    ]


def test_narrow_requires_request() -> None:
    result = nodes_module.narrow_search(
        {}
    )

    assert result["errors"] == [
        (
            "Narrow search requires "
            "a validated search request."
        )
    ]