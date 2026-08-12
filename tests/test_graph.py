import pytest

from research_finder import nodes as nodes_module
from research_finder.graph import graph
from research_finder.models import TopicExpansionDraft
from research_finder.web_search import (
    WebSearchRequest,
    WebSearchResult,
)


class FakeGraphStructuredModel:
    """Return one controlled topic expansion."""

    def invoke(self, _: object) -> TopicExpansionDraft:
        return TopicExpansionDraft(
            canonical_topic=("Reinforcement learning for time-series analysis"),
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
    """Provide topic expansion without a real LLM API."""

    def with_structured_output(
        self,
        _: object,
        **__: object,
    ) -> FakeGraphStructuredModel:
        return FakeGraphStructuredModel()


class FakeGraphSearchClient:
    """Return no pages without performing real web searches."""

    def search(
        self,
        _: WebSearchRequest,
    ) -> list[WebSearchResult]:
        return []


def test_graph_returns_valid_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Prevent a real Groq/Ollama request.
    monkeypatch.setattr(
        nodes_module,
        "create_chat_model",
        lambda: FakeGraphChatModel(),
    )

    # Prevent real DDGS web searches.
    monkeypatch.setattr(
        nodes_module,
        "create_search_client",
        lambda: FakeGraphSearchClient(),
    )

    output = graph.invoke(
        {
            "raw_request": {
                "country": " australia ",
                "state": "vic",
                "research_topic": ("Reinforcement learning for time-series data"),
            }
        }
    )

    response = output["final_response"]

    assert output["errors"] == []
    assert response is not None

    assert response.request.country == "Australia"
    assert response.request.country_code == "AU"
    assert response.request.state == "Victoria"
    assert response.request.state_code == "AU-VIC"
    assert response.result_count == 0

    assert any(
        "No official researcher pages were found" in warning for warning in response.warnings
    )

    assert output["execution_log"] == [
        "Workflow initialized.",
        "Input validation completed.",
        "Structured topic expansion completed.",
        ("University directory selected 12 candidates for Victoria, Australia."),
        ("Generated 48 official university-domain queries."),
        ("Researcher search completed: 12 queries attempted, 0 official pages found."),
        ("Research-lab search completed: 12 queries attempted, 0 official pages found."),
        ("Research-project search completed: 12 queries attempted, 0 official pages found."),
        ("Publication search completed: 12 queries attempted, 0 official pages found."),
        ("Webpage download completed: 0 pages attempted, 0 documents created."),
        ("Researcher extraction completed: 0 documents processed, 0 candidates created."),
        (
            "Researcher detail extraction completed: "
            "0 documents processed, "
            "0 researchers enriched."
        ),
        ("Affiliation-verification placeholder completed."),
        "Relevance-scoring placeholder completed.",
        "Duplicate removal completed.",
        "Result ranking completed.",
        "Final response generated.",
    ]


def test_graph_stops_after_invalid_input() -> None:
    output = graph.invoke(
        {
            "raw_request": {
                "country": "Canada",
                "state": "Ontario",
                "research_topic": ("Reinforcement learning"),
            }
        }
    )

    assert output["final_response"] is None
    assert output["warnings"] == []

    assert any(error.startswith("country:") for error in output["errors"])

    assert output["execution_log"] == [
        "Workflow initialized.",
        "Input validation failed.",
        ("Final response could not be generated because the request was invalid."),
    ]
