from research_finder.llm import create_chat_model
from research_finder.models import SearchRequest
from research_finder.topic_expansion import (
    generate_topic_expansion,
)


def main() -> None:
    """Run one real structured topic-expansion request."""

    request = SearchRequest(
        country="Australia",
        country_code="AU",
        state="Victoria",
        state_code="AU-VIC",
        research_topic=("Reinforcement learning for time-series data"),
    )

    model = create_chat_model()
    expansion = generate_topic_expansion(
        request=request,
        model=model,
    )

    print("Structured expansion:")
    print(expansion.model_dump_json(indent=2))

    print("\nOrdered search terms:")

    for index, search_term in enumerate(
        expansion.to_search_terms(),
        start=1,
    ):
        print(f"{index}. {search_term}")


if __name__ == "__main__":
    main()
