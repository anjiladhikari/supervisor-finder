from research_finder.official_page_search import (
    execute_official_searches,
)
from research_finder.search_queries import (
    SearchTarget,
    generate_official_search_queries,
)
from research_finder.university_directory import (
    get_universities,
)
from research_finder.web_search import (
    create_search_client,
)


def main() -> None:
    """Search researcher pages for two universities."""

    universities = list(
        get_universities(
            country_code="AU",
            state_code="AU-VIC",
        )
    )[:2]

    queries = generate_official_search_queries(
        universities=universities,
        topics=[
            (
                "Reinforcement learning for "
                "time-series data"
            )
        ],
    )

    outcome = execute_official_searches(
        search_queries=queries,
        target=SearchTarget.RESEARCHER,
        client=create_search_client(),
        max_results_per_query=3,
    )

    print(
        f"Queries attempted: "
        f"{outcome.attempted_queries}"
    )
    print(
        f"Queries failed: "
        f"{outcome.failed_queries}"
    )
    print(
        f"Official pages: "
        f"{len(outcome.pages)}"
    )

    for page in outcome.pages:
        print()
        print(page.university_name)
        print(page.title)
        print(page.url)


if __name__ == "__main__":
    main()