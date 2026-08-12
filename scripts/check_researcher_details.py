from research_finder.llm import (
    create_chat_model,
)
from research_finder.official_page_search import (
    execute_official_searches,
)
from research_finder.researcher_details import (
    enrich_researcher_candidates,
    extract_researcher_detail_documents,
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
    """Run a small real Step 12 check."""

    universities = [
        university
        for university in get_universities(
            country_code="AU",
            state_code="AU-VIC",
        )
        if university.name == "Deakin University"
    ]

    queries = generate_official_search_queries(
        universities=universities,
        topics=["Reinforcement learning"],
    )

    search_client = create_search_client()

    all_documents = []

    for target in SearchTarget:
        search_outcome = execute_official_searches(
            search_queries=queries,
            target=target,
            client=search_client,
            max_results_per_query=3,
        )

        download_outcome = download_official_pages(
            pages=list(search_outcome.pages),
            downloader=create_page_downloader(),
        )

        all_documents.extend(download_outcome.documents)

    researcher_documents = [
        document for document in all_documents if (document.target == SearchTarget.RESEARCHER)
    ]

    if not researcher_documents:
        print("No researcher documents found.")
        return

    model = create_chat_model()

    researcher_outcome = extract_researcher_documents(
        documents=researcher_documents,
        model=model,
    )

    candidates = list(researcher_outcome.candidates)

    if not candidates:
        print("No researcher candidates found.")
        return

    detail_outcome = extract_researcher_detail_documents(
        documents=all_documents,
        candidates=candidates,
        model=model,
    )

    enriched = enrich_researcher_candidates(
        candidates=candidates,
        associations=list(detail_outcome.associations),
    )

    print(f"Researchers: {len(enriched)}")

    for researcher in enriched:
        print()
        print(researcher.researcher.full_name)
        print(
            "University:",
            researcher.researcher.university_name,
        )
        print(
            "Email:",
            researcher.public_email,
        )

        print(
            "Labs:",
            [item.name for item in researcher.labs],
        )

        print(
            "Projects:",
            [item.name for item in researcher.projects],
        )

        print(
            "Publications:",
            [item.name for item in researcher.publications],
        )


if __name__ == "__main__":
    main()
