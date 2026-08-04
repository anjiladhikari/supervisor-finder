from research_finder.web_search import (
    WebSearchRequest,
    create_search_client,
)


def main() -> None:
    """Run one real free web-search request."""

    client = create_search_client()

    request = WebSearchRequest(
        query=(
            "Deakin University reinforcement learning "
            "researcher"
        ),
        max_results=5,
    )

    results = client.search(request)

    print(f"Results: {len(results)}")

    for result in results:
        print()
        print(f"{result.rank}. {result.title}")
        print(result.url)
        print(result.snippet)


if __name__ == "__main__":
    main()