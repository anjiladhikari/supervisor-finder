import pytest

from research_finder import nodes as nodes_module
from research_finder.models import (
    SearchRequest,
    TopicExpansion,
    TopicExpansionDraft,
)
from research_finder.topic_expansion import (
    create_fallback_topic_expansion,
    generate_topic_expansion,
)


class FakeStructuredRunnable:
    """Return a controlled structured-model response."""

    def __init__(self, response: object) -> None:
        self.response = response
        self.messages: object = None

    def invoke(self, messages: object) -> object:
        self.messages = messages

        if isinstance(self.response, Exception):
            raise self.response

        return self.response


class FakeChatModel:
    """Record structured-output configuration without an API."""

    def __init__(self, response: object) -> None:
        self.runnable = FakeStructuredRunnable(response)
        self.schema: object = None
        self.structured_kwargs: dict[str, object] = {}

    def with_structured_output(
        self,
        schema: object,
        **kwargs: object,
    ) -> FakeStructuredRunnable:
        self.schema = schema
        self.structured_kwargs = kwargs

        return self.runnable


def create_test_request() -> SearchRequest:
    """Create one reusable validated request."""

    return SearchRequest(
        country="Australia",
        country_code="AU",
        state="Victoria",
        state_code="AU-VIC",
        research_topic=("Reinforcement learning for time-series data"),
    )


def create_test_draft() -> TopicExpansionDraft:
    """Create one reusable structured LLM response."""

    return TopicExpansionDraft(
        canonical_topic=("Reinforcement learning for time-series analysis"),
        related_topics=[
            "Deep reinforcement learning",
            "Sequential decision-making",
        ],
        broader_topics=[
            "Machine learning",
        ],
        narrower_topics=[
            "Early time-series classification",
            "Adaptive temporal decision systems",
        ],
        methods_and_techniques=[
            "Proximal policy optimization",
            "Actor-critic learning",
        ],
        application_areas=[
            "Sensor analytics",
        ],
        search_keywords=[
            "reinforcement learning time series",
            "temporal policy learning",
        ],
    )


def test_search_terms_preserve_order_and_remove_duplicates() -> None:
    expansion = TopicExpansion(
        original_topic=("Reinforcement learning for time-series data"),
        canonical_topic=("Reinforcement learning for time-series analysis"),
        related_topics=[
            "Deep reinforcement learning",
            "deep reinforcement learning",
        ],
        broader_topics=[
            "Machine learning",
        ],
        narrower_topics=[
            "Early time-series classification",
        ],
        methods_and_techniques=[
            "Proximal policy optimization",
        ],
        application_areas=[
            "Sensor analytics",
        ],
        search_keywords=[
            "Proximal policy optimization",
            "temporal policy learning",
        ],
    )

    assert expansion.to_search_terms() == [
        "Reinforcement learning for time-series data",
        "Reinforcement learning for time-series analysis",
        "Deep reinforcement learning",
        "Early time-series classification",
        "Proximal policy optimization",
        "Sensor analytics",
        "Machine learning",
        "temporal policy learning",
    ]


def test_generate_expansion_uses_json_schema() -> None:
    request = create_test_request()
    fake_model = FakeChatModel(create_test_draft())

    expansion = generate_topic_expansion(
        request=request,
        model=fake_model,
    )

    assert fake_model.schema is TopicExpansionDraft
    assert fake_model.structured_kwargs == {
        "method": "json_schema",
    }
    assert expansion.original_topic == ("Reinforcement learning for time-series data")
    assert expansion.canonical_topic == ("Reinforcement learning for time-series analysis")


def test_generate_expansion_accepts_dictionary_response() -> None:
    request = create_test_request()
    fake_model = FakeChatModel(create_test_draft().model_dump())

    expansion = generate_topic_expansion(
        request=request,
        model=fake_model,
    )

    assert isinstance(expansion, TopicExpansion)
    assert expansion.related_topics == [
        "Deep reinforcement learning",
        "Sequential decision-making",
    ]


def test_node_returns_structured_topic_expansion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = create_test_request()
    fake_model = FakeChatModel(create_test_draft())

    monkeypatch.setattr(
        nodes_module,
        "create_chat_model",
        lambda: fake_model,
    )

    result = nodes_module.expand_research_topic({"request": request})

    expansion = result["topic_expansion"]

    assert isinstance(expansion, TopicExpansion)
    assert result["expanded_topics"][0] == ("Reinforcement learning for time-series data")
    assert result["execution_log"] == ["Structured topic expansion completed."]
    assert "warnings" not in result


def test_node_uses_fallback_when_llm_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = create_test_request()
    fake_model = FakeChatModel(RuntimeError("Simulated API failure"))

    monkeypatch.setattr(
        nodes_module,
        "create_chat_model",
        lambda: fake_model,
    )

    result = nodes_module.expand_research_topic({"request": request})

    expansion = result["topic_expansion"]

    assert isinstance(expansion, TopicExpansion)
    assert result["expanded_topics"] == ["Reinforcement learning for time-series data"]
    assert any("RuntimeError" in warning for warning in result["warnings"])
    assert result["execution_log"] == [("Topic expansion completed with deterministic fallback.")]


def test_node_rejects_missing_validated_request() -> None:
    result = nodes_module.expand_research_topic({})

    assert result["errors"] == [("Topic expansion cannot run without a validated request.")]
    assert result["execution_log"] == ["Topic expansion failed."]


def test_fallback_uses_only_original_topic() -> None:
    request = create_test_request()

    expansion = create_fallback_topic_expansion(request)

    assert expansion.original_topic == (request.research_topic)
    assert expansion.canonical_topic == (request.research_topic)
    assert expansion.related_topics == []
    assert expansion.broader_topics == []
    assert expansion.narrower_topics == []
    assert expansion.methods_and_techniques == []
    assert expansion.application_areas == []
    assert expansion.to_search_terms() == [request.research_topic]
