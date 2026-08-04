from research_finder.graph import graph
from research_finder.models import AustralianState


def test_graph_returns_valid_empty_response() -> None:
    output = graph.invoke(
        {
            "raw_request": {
                "country": " australia ",
                "state": "vic",
                "research_topic": (
                    "Reinforcement learning for time-series data"
                ),
            }
        }
    )

    response = output["final_response"]

    assert output["errors"] == []
    assert response is not None
    assert response.request.country == "Australia"
    assert response.request.state == AustralianState.VICTORIA
    assert response.result_count == 0

    assert any(
        "University discovery is not implemented"
        in warning
        for warning in response.warnings
    )

    assert output["execution_log"] == [
        "Workflow initialized.",
        "Input validation completed.",
        "Topic-expansion placeholder completed.",
        "University-discovery placeholder completed.",
        "Final response generated.",
    ]


def test_graph_stops_after_invalid_input() -> None:
    output = graph.invoke(
        {
            "raw_request": {
                "country": "Canada",
                "state": "Ontario",
                "research_topic": "Reinforcement learning",
            }
        }
    )

    assert output["final_response"] is None
    assert output["warnings"] == []

    assert any(
        error.startswith("country:")
        for error in output["errors"]
    )

    assert output["execution_log"] == [
        "Workflow initialized.",
        "Input validation failed.",
        (
            "Final response could not be generated because "
            "the request was invalid."
        ),
    ]