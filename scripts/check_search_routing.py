from research_finder.search_strategy import (
    SearchMode,
    choose_researcher_search_route,
)


def main() -> None:
    """Show deterministic search routing."""

    no_results = (
        choose_researcher_search_route(
            researcher_page_count=0,
            university_count=12,
            max_results=10,
            search_round=1,
            search_mode=(
                SearchMode.NORMAL
            ),
            has_errors=False,
        )
    )

    enough_results = (
        choose_researcher_search_route(
            researcher_page_count=10,
            university_count=12,
            max_results=10,
            search_round=1,
            search_mode=(
                SearchMode.NORMAL
            ),
            has_errors=False,
        )
    )

    too_many_results = (
        choose_researcher_search_route(
            researcher_page_count=50,
            university_count=12,
            max_results=5,
            search_round=1,
            search_mode=(
                SearchMode.NORMAL
            ),
            has_errors=False,
        )
    )

    retry_failed = (
        choose_researcher_search_route(
            researcher_page_count=0,
            university_count=12,
            max_results=10,
            search_round=2,
            search_mode=(
                SearchMode.BROADEN
            ),
            has_errors=False,
        )
    )

    print(
        "No results:",
        no_results,
    )

    print(
        "Good result count:",
        enough_results,
    )

    print(
        "Too many results:",
        too_many_results,
    )

    print(
        "Retry still empty:",
        retry_failed,
    )


if __name__ == "__main__":
    main()