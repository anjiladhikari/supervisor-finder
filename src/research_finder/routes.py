from typing import Literal

from research_finder.state import ResearchGraphState


def route_after_validation(
    state: ResearchGraphState,
) -> Literal["expand_research_topic", "generate_final_output"]:
    """Continue only when input validation succeeds."""

    request = state.get("request")
    errors = state.get("errors", [])

    if request is None or errors:
        return "generate_final_output"

    return "expand_research_topic"


def route_after_university_discovery(
    state: ResearchGraphState,
) -> Literal["generate_search_queries", "generate_final_output"]:
    """Continue only when at least one university has been found."""

    candidate_universities = state.get("candidate_universities", [])
    errors = state.get("errors", [])

    if errors or not candidate_universities:
        return "generate_final_output"

    return "generate_search_queries"


def route_after_search_query_generation(
    state: ResearchGraphState,
) -> Literal[
    "search_researchers",
    "generate_final_output",
]:
    """Continue only when search queries were created."""

    search_queries = state.get(
        "search_queries",
        [],
    )
    errors = state.get("errors", [])

    if errors or not search_queries:
        return "generate_final_output"

    return "search_researchers"