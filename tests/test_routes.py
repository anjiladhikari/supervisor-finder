from research_finder.models import SearchRequest
from research_finder.routes import (
    route_after_university_discovery,
    route_after_validation,
)


def test_valid_request_routes_to_topic_expansion() -> None:
    state = {
        "request": SearchRequest(
            country="Australia",
            research_topic="Reinforcement learning",
        ),
        "errors": [],
    }

    destination = route_after_validation(state)

    assert destination == "expand_research_topic"


def test_invalid_request_routes_to_final_output() -> None:
    state = {
        "request": None,
        "errors": ["country: Input should be Australia."],
    }

    destination = route_after_validation(state)

    assert destination == "generate_final_output"


def test_found_universities_route_to_researcher_search() -> None:
    state = {
        "candidate_universities": [
            "Example university candidate"
        ],
        "errors": [],
    }

    destination = route_after_university_discovery(state)

    assert destination == "search_researchers"


def test_no_universities_route_to_final_output() -> None:
    state = {
        "candidate_universities": [],
        "errors": [],
    }

    destination = route_after_university_discovery(state)

    assert destination == "generate_final_output"