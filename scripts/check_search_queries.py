from collections import Counter

from research_finder.search_queries import (
    generate_official_search_queries,
)
from research_finder.university_directory import (
    get_universities,
)


def main() -> None:
    """Display generated official-domain queries."""

    universities = list(
        get_universities(
            country_code="AU",
            state_code="AU-VIC",
        )
    )

    queries = generate_official_search_queries(
        universities=universities,
        topics=[
            ("Reinforcement learning for time-series data"),
            "Early time-series classification",
        ],
    )

    target_counts = Counter(query.target.value for query in queries)

    print(f"Universities: {len(universities)}")
    print(f"Queries: {len(queries)}")
    print(f"Targets: {dict(target_counts)}")

    print("\nFirst eight queries:")

    for query in queries[:8]:
        print()
        print(f"{query.university_name} [{query.target.value}]")
        print(query.query)


if __name__ == "__main__":
    main()
