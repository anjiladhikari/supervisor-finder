from typing import Any

import pytest
from ddgs.exceptions import DDGSException
from pydantic import ValidationError

from research_finder.web_search import (
    DDGSSearchClient,
    WebSearchError,
    WebSearchRequest,
)


class FakeDDGS:
    """Return controlled search responses."""

    def __init__(
        self,
        responses: list[object],
    ) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def text(
        self,
        query: str,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        self.calls.append(
            {
                "query": query,
                **kwargs,
            }
        )

        response = self.responses.pop(0)

        if isinstance(response, Exception):
            raise response

        assert isinstance(response, list)

        return response


def test_search_request_normalises_query() -> None:
    request = WebSearchRequest(query=("  reinforcement   learning researcher  "))

    assert request.query == ("reinforcement learning researcher")


def test_search_request_rejects_empty_query() -> None:
    with pytest.raises(ValidationError):
        WebSearchRequest(query="  ")


def test_search_normalises_and_deduplicates_results() -> None:
    fake_ddgs = FakeDDGS(
        responses=[
            [
                {
                    "title": " Deakin Research ",
                    "href": ("https://www.deakin.edu.au/research"),
                    "body": " Research information. ",
                },
                {
                    "title": "Duplicate",
                    "href": ("https://www.deakin.edu.au/research/"),
                    "body": "Duplicate result.",
                },
                {
                    "title": "Invalid",
                    "href": "not-a-valid-url",
                    "body": "Invalid URL.",
                },
            ]
        ]
    )

    client = DDGSSearchClient(
        ddgs_factory=lambda **_: fake_ddgs,
        sleeper=lambda _: None,
    )

    results = client.search(
        WebSearchRequest(
            query="Deakin research",
            max_results=5,
        )
    )

    assert len(results) == 1
    assert results[0].title == "Deakin Research"
    assert results[0].snippet == ("Research information.")
    assert results[0].rank == 1


def test_search_uses_default_result_limit() -> None:
    fake_ddgs = FakeDDGS(
        responses=[
            [
                {
                    "title": "Result",
                    "href": "https://example.com",
                    "body": "Example result.",
                }
            ]
        ]
    )

    client = DDGSSearchClient(
        default_max_results=7,
        ddgs_factory=lambda **_: fake_ddgs,
        sleeper=lambda _: None,
    )

    client.search(WebSearchRequest(query="Example search"))

    assert fake_ddgs.calls[0]["max_results"] == 7


def test_search_retries_temporary_failure() -> None:
    fake_ddgs = FakeDDGS(
        responses=[
            DDGSException("Temporary failure"),
            [
                {
                    "title": "Successful result",
                    "href": "https://example.com",
                    "body": "Search succeeded.",
                }
            ],
        ]
    )
    delays: list[float] = []

    client = DDGSSearchClient(
        max_retries=1,
        ddgs_factory=lambda **_: fake_ddgs,
        sleeper=delays.append,
    )

    results = client.search(WebSearchRequest(query="Example search"))

    assert len(results) == 1
    assert len(fake_ddgs.calls) == 2
    assert delays == [1]


def test_search_raises_after_all_retries() -> None:
    fake_ddgs = FakeDDGS(
        responses=[
            DDGSException("Failure one"),
            DDGSException("Failure two"),
        ]
    )

    client = DDGSSearchClient(
        max_retries=1,
        ddgs_factory=lambda **_: fake_ddgs,
        sleeper=lambda _: None,
    )

    with pytest.raises(
        WebSearchError,
        match="failed after 2 attempts",
    ):
        client.search(WebSearchRequest(query="Example search"))
