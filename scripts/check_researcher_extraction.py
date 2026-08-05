from research_finder.llm import (
    create_chat_model,
)
from research_finder.official_page_search import (
    execute_official_searches,
)
from research_finder.researcher_extraction import (
    extract_researcher_documents,
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
    """Search, download and extract a small sample."""

    universities = list(
        get_universities(
            country_code="AU",
            state_code="AU-VIC",
        )
    )[:2]

    queries = generate_official_search_queries(
        universities=universities,
        topics=[
            "Reinforcement learning"
        ],
    )

    search_outcome = execute_official_searches(
        search_queries=queries,
        target=SearchTarget.RESEARCHER,
        client=create_search_client(),
        max_results_per_query=2,
    )

    pages = list(search_outcome.pages[:2])

    if not pages:
        print("No official researcher pages found.")
        return

    download_outcome = download_official_pages(
        pages=pages,
        downloader=create_page_downloader(),
    )

    documents = list(
        download_outcome.documents
    )

    if not documents:
        print("No researcher documents downloaded.")
        return

    extraction_outcome = (
        extract_researcher_documents(
            documents=documents,
            model=create_chat_model(),
        )
    )

    print(
        "Documents processed:",
        extraction_outcome.attempted_documents,
    )
    print(
        "Documents failed:",
        extraction_outcome.failed_documents,
    )
    print(
        "Candidates:",
        len(extraction_outcome.candidates),
    )

    for candidate in (
        extraction_outcome.candidates
    ):
        print()
        print(candidate.full_name)
        print(candidate.academic_title)
        print(candidate.role)
        print(candidate.university_name)
        print(candidate.research_interests)
        print(candidate.source_url)
        print(candidate.evidence_text)


if __name__ == "__main__":
    main()