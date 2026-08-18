import pytest
from pydantic import ValidationError

from research_finder.models import (
    SearchRequest,
)


def test_search_request_normalises_input() -> None:
    request = SearchRequest(
        country=" Australia ",
        country_code="au",
        state=" Victoria ",
        state_code="au-vic",
        research_topic=(
            "  reinforcement   learning  "
        ),
    )

    assert request.country == "Australia"
    assert request.country_code == "AU"
    assert request.state == "Victoria"
    assert request.state_code == "AU-VIC"
    assert (
        request.research_topic
        == "reinforcement learning"
    )
    assert request.max_results == 5


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
            unexpected_field="not allowed",
        )