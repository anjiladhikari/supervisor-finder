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
from research_finder.web_content import (
    create_page_downloader,
    download_official_pages,
)
from research_finder.web_search import (
    create_search_client,
)


def main() -> None:
    """Search and download a small official-page sample."""

    universities = list(
        get_universities(
            country_code="AU",
            state_code="AU-VIC",
        )
    )[:2]

    queries = generate_official_search_queries(
        universities=universities,
        topics=["Reinforcement learning"],
    )

    search_outcome = execute_official_searches(
        search_queries=queries,
        target=SearchTarget.RESEARCHER,
        client=create_search_client(),
        max_results_per_query=2,
    )

    pages = list(search_outcome.pages[:3])

    if not pages:
        print("No official pages were found.")
        return

    download_outcome = download_official_pages(
        pages=pages,
        downloader=create_page_downloader(),
    )

    print(f"Pages attempted: {download_outcome.attempted_pages}")
    print(f"Pages failed: {download_outcome.failed_pages}")
    print(f"Documents created: {len(download_outcome.documents)}")

    for document in download_outcome.documents:
        print()
        print(document.university_name)
        print(document.page_title)
        print(document.final_url)
        print(f"Characters: {len(document.content)}")
        print(document.content[:500])


if __name__ == "__main__":
    main()
