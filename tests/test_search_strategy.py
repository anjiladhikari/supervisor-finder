from research_finder.search_strategy import (
    MAX_SEARCH_ROUNDS,
    SearchMode,
    build_broadened_search_topics,
    build_narrowed_search_topics,
    choose_researcher_search_route,
    researcher_page_narrow_threshold,
)


def test_maximum_search_rounds_is_two() -> None:
    assert MAX_SEARCH_ROUNDS == 2


def test_broaden_search_keeps_original_topic() -> None:
    topics = build_broadened_search_topics(
        original_topic=(
            "Reinforcement learning"
        ),
        topic_expansion=None,
        expanded_topics=[
            "Reinforcement learning",
            "Machine learning",
        ],
    )

    assert topics == [
        "Reinforcement learning",
        "Machine learning",
    ]


def test_narrow_search_uses_original_only() -> None:
    topics = build_narrowed_search_topics(
        original_topic=(
            "Reinforcement learning "
            "for time-series data"
        )
    )

    assert topics == [
        (
            "Reinforcement learning "
            "for time-series data"
        )
    ]


def test_zero_pages_causes_broaden_retry() -> None:
    route = choose_researcher_search_route(
        researcher_page_count=0,
        university_count=12,
        max_results=10,
        search_round=1,
        search_mode=SearchMode.NORMAL,
        has_errors=False,
    )

    assert route == "broaden_search"


def test_zero_pages_after_retry_finishes() -> None:
    route = choose_researcher_search_route(
        researcher_page_count=0,
        university_count=12,
        max_results=10,
        search_round=2,
        search_mode=SearchMode.BROADEN,
        has_errors=False,
    )

    assert route == "generate_final_output"


def test_reasonable_page_count_continues() -> None:
    route = choose_researcher_search_route(
        researcher_page_count=10,
        university_count=12,
        max_results=10,
        search_round=1,
        search_mode=SearchMode.NORMAL,
        has_errors=False,
    )

    assert route == "search_labs"


def test_too_many_pages_causes_narrow_retry() -> None:
    threshold = (
        researcher_page_narrow_threshold(
            university_count=12,
            max_results=5,
        )
    )

    route = choose_researcher_search_route(
        researcher_page_count=(
            threshold + 1
        ),
        university_count=12,
        max_results=5,
        search_round=1,
        search_mode=SearchMode.NORMAL,
        has_errors=False,
    )

    assert route == "narrow_search"


def test_errors_stop_retry() -> None:
    route = choose_researcher_search_route(
        researcher_page_count=0,
        university_count=12,
        max_results=10,
        search_round=1,
        search_mode=SearchMode.NORMAL,
        has_errors=True,
    )

    assert route == "generate_final_output"