from typing import Literal

from research_finder.search_strategy import (
    SearchMode,
    choose_researcher_search_route,
)
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

def route_after_researcher_search(
    state: ResearchGraphState,
) -> Literal[
    "broaden_search",
    "narrow_search",
    "download_webpage_content",
    "generate_final_output",
]:
    """Decide whether researcher search needs retry."""

    request = state.get(
        "request"
    )

    if request is None:
        return "generate_final_output"

    researcher_pages = state.get(
        "researcher_pages",
        [],
    )

    universities = state.get(
        "candidate_universities",
        [],
    )

    raw_mode = state.get(
        "search_mode",
        SearchMode.NORMAL,
    )

    search_mode = SearchMode(
        raw_mode
    )

    return choose_researcher_search_route(
        researcher_page_count=len(
            researcher_pages
        ),
        university_count=len(
            universities
        ),
        max_results=(
            request.max_results
        ),
        search_round=state.get(
            "search_round",
            1,
        ),
        search_mode=search_mode,
        has_errors=bool(
            state.get(
                "errors",
                [],
            )
        ),
    )
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
