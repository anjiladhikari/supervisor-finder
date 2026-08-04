import pytest

from research_finder import nodes as nodes_module
from research_finder.graph import graph
from research_finder.models import (
    AustralianState,
    TopicExpansionDraft,
)


class FakeGraphStructuredModel:
    """Return one controlled graph topic expansion."""

    def invoke(self, _: object) -> TopicExpansionDraft:
        return TopicExpansionDraft(
            canonical_topic=(
                "Reinforcement learning for "
                "time-series analysis"
            ),
            related_topics=[
                "Deep reinforcement learning",
            ],
            broader_topics=[
                "Machine learning",
            ],
            narrower_topics=[
                "Early time-series classification",
            ],
            methods_and_techniques=[
                "Actor-critic learning",
            ],
            application_areas=[
                "Sensor analytics",
            ],
            search_keywords=[
                "reinforcement learning time series",
            ],
        )


class FakeGraphChatModel:
    """Provide structured output without a real API."""

    def with_structured_output(
        self,
        _: object,
        **__: object,
    ) -> FakeGraphStructuredModel:
        return FakeGraphStructuredModel()


def test_graph_returns_valid_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        nodes_module,
        "create_chat_model",
        lambda: FakeGraphChatModel(),
    )

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
    assert (
        response.request.state
        == AustralianState.VICTORIA
    )
    assert response.result_count == 0

    assert any(
        "University discovery is not implemented"
        in warning
        for warning in response.warnings
    )

    assert output["execution_log"] == [
        "Workflow initialized.",
        "Input validation completed.",
        "Structured topic expansion completed.",
        "University-discovery placeholder completed.",
        "Final response generated.",
    ]


def test_graph_stops_after_invalid_input() -> None:
    output = graph.invoke(
        {
            "raw_request": {
                "country": "Canada",
                "state": "Ontario",
                "research_topic": (
                    "Reinforcement learning"
                ),
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