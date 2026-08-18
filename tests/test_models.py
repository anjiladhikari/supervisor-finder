import pytest
from pydantic import ValidationError

from research_finder.models import (
    SearchRequest,
    TopicExpansion,
    TopicExpansionDraft,
)


def test_search_request_normalises_input() -> None:
    request = SearchRequest(
        country=" Australia ",
        country_code="au",
        state=" Victoria ",
        state_code="au-vic",
        research_topic=(
            "  reinforcement   learning "
            "for time-series data  "
        ),
    )

    assert request.country == "Australia"
    assert request.country_code == "AU"
    assert request.state == "Victoria"
    assert request.state_code == "AU-VIC"

    assert request.research_topic == (
        "reinforcement learning "
        "for time-series data"
    )

    assert request.max_results == 5


def test_search_request_requires_country_code() -> None:
    with pytest.raises(
        ValidationError
    ):
        SearchRequest(
            country="Australia",
            state="Victoria",
            state_code="AU-VIC",
            research_topic=(
                "Reinforcement learning"
            ),
        )


def test_search_request_rejects_wrong_state_country() -> None:
    with pytest.raises(
        ValidationError,
        match="state_code must belong",
    ):
        SearchRequest(
            country="Australia",
            country_code="AU",
            state="California",
            state_code="US-CA",
            research_topic=(
                "Reinforcement learning"
            ),
        )


def test_search_request_rejects_unexpected_fields() -> None:
    with pytest.raises(
        ValidationError
    ):
        SearchRequest(
            country="Australia",
            country_code="AU",
            state=None,
            state_code=None,
            research_topic=(
                "Reinforcement learning"
            ),
            unexpected_field=(
                "This must not be accepted"
            ),
        )


def test_topic_expansion_keeps_existing_limits() -> None:
    draft = TopicExpansionDraft(
        canonical_topic=(
            "Reinforcement Learning"
        ),
        related_topics=[
            "Machine Learning"
        ],
        broader_topics=[
            "Artificial Intelligence"
        ],
        narrower_topics=[
            "Deep Reinforcement Learning"
        ],
        methods_and_techniques=[
            "Q-learning"
        ],
        application_areas=[
            "Robotics"
        ],
        search_keywords=[
            "reinforcement learning"
        ],
    )

    assert (
        draft.canonical_topic
        == "Reinforcement Learning"
    )


def test_topic_expansion_search_terms_are_unique() -> None:
    expansion = TopicExpansion(
        original_topic=(
            "Reinforcement learning"
        ),
        canonical_topic=(
            "Reinforcement learning"
        ),
        related_topics=[
            "Machine learning",
            "machine learning",
        ],
        broader_topics=[
            "Artificial intelligence"
        ],
        narrower_topics=[],
        methods_and_techniques=[],
        application_areas=[],
        search_keywords=[],
    )

    assert expansion.to_search_terms() == [
        "Reinforcement learning",
        "Machine learning",
        "Artificial intelligence",
    ]


def test_search_term_limit_is_preserved() -> None:
    expansion = TopicExpansion(
        original_topic="Original topic",
        canonical_topic="Canonical topic",
        related_topics=[
            "Topic one",
            "Topic two",
        ],
        broader_topics=[
            "Broad topic"
        ],
        narrower_topics=[],
        methods_and_techniques=[],
        application_areas=[],
        search_keywords=[],
    )

    assert len(
        expansion.to_search_terms(
            limit=2
        )
    ) == 2