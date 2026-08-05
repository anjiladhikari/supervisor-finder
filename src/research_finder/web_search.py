from __future__ import annotations

import time
from collections.abc import Callable
from html import unescape
from typing import Any, Protocol

from ddgs import DDGS
from ddgs.exceptions import DDGSException
from pydantic import Field, HttpUrl, ValidationError, field_validator

from research_finder.config import Settings, get_settings
from research_finder.models import StrictModel


class WebSearchError(RuntimeError):
    """A web-search request failed after all retries."""


class WebSearchRequest(StrictModel):
    """One validated text-search request."""

    query: str = Field(
        min_length=3,
        max_length=500,
    )
    max_results: int | None = Field(
        default=None,
        ge=1,
        le=20,
    )

    @field_validator("query", mode="before")
    @classmethod
    def normalise_query(
        cls,
        value: object,
    ) -> object:
        """Collapse repeated query whitespace."""

        if isinstance(value, str):
            return " ".join(value.split())

        return value


class WebSearchResult(StrictModel):
    """One normalised result returned by web search."""

    title: str = Field(
        min_length=1,
        max_length=500,
    )
    url: HttpUrl
    snippet: str = Field(
        default="",
        max_length=3000,
    )
    rank: int = Field(
        ge=1,
    )


class WebSearchClient(Protocol):
    """Interface used by future search nodes."""

    def search(
        self,
        request: WebSearchRequest,
    ) -> list[WebSearchResult]:
        """Run one web-search request."""


class DDGSLike(Protocol):
    """Small portion of DDGS used by this application."""

    def text(
        self,
        query: str,
        *,
        region: str,
        safesearch: str,
        max_results: int,
        backend: str,
    ) -> list[dict[str, Any]]:
        """Return raw text-search results."""


DDGSFactory = Callable[..., DDGSLike]
Sleeper = Callable[[float], None]


def _clean_text(value: object) -> str:
    """Normalise text returned by the search provider."""

    if not isinstance(value, str):
        return ""

    return " ".join(unescape(value).split())


class DDGSSearchClient:
    """Free text-search client backed by DDGS."""

    def __init__(
        self,
        *,
        region: str = "au-en",
        safesearch: str = "moderate",
        timeout_seconds: int = 15,
        max_retries: int = 2,
        default_max_results: int = 10,
        ddgs_factory: DDGSFactory = DDGS,
        sleeper: Sleeper = time.sleep,
    ) -> None:
        self.region = region
        self.safesearch = safesearch
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.default_max_results = default_max_results
        self.ddgs_factory = ddgs_factory
        self.sleeper = sleeper

    def search(
        self,
        request: WebSearchRequest,
    ) -> list[WebSearchResult]:
        """Search the web with bounded retry behaviour."""

        max_results = (
            request.max_results if request.max_results is not None else self.default_max_results
        )

        raw_results = self._search_with_retries(
            query=request.query,
            max_results=max_results,
        )

        return self._normalise_results(
            raw_results,
            max_results=max_results,
        )

    def _search_with_retries(
        self,
        *,
        query: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Run DDGS and retry temporary provider failures."""

        last_error: DDGSException | None = None

        for attempt in range(self.max_retries + 1):
            try:
                searcher = self.ddgs_factory(timeout=self.timeout_seconds)

                return searcher.text(
                    query,
                    region=self.region,
                    safesearch=self.safesearch,
                    max_results=max_results,
                    backend="auto",
                )
            except DDGSException as error:
                last_error = error

                if attempt >= self.max_retries:
                    break

                retry_delay = min(
                    2**attempt,
                    4,
                )
                self.sleeper(retry_delay)

        raise WebSearchError(
            f"Web search failed after {self.max_retries + 1} attempts."
        ) from last_error

    @staticmethod
    def _normalise_results(
        raw_results: list[dict[str, Any]],
        *,
        max_results: int,
    ) -> list[WebSearchResult]:
        """Validate, deduplicate and rank raw results."""

        results: list[WebSearchResult] = []
        seen_urls: set[str] = set()

        for raw_result in raw_results:
            title = _clean_text(raw_result.get("title"))
            url = _clean_text(raw_result.get("href"))
            snippet = _clean_text(raw_result.get("body"))

            try:
                result = WebSearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    rank=len(results) + 1,
                )
            except ValidationError:
                continue

            url_key = str(result.url).rstrip("/").casefold()

            if url_key in seen_urls:
                continue

            seen_urls.add(url_key)
            results.append(result)

            if len(results) >= max_results:
                break

        return results


def create_search_client(
    settings: Settings | None = None,
) -> DDGSSearchClient:
    """Create the configured free web-search client."""

    resolved_settings = settings or get_settings()

    return DDGSSearchClient(
        region=resolved_settings.search_region,
        safesearch=(resolved_settings.search_safesearch.value),
        timeout_seconds=(resolved_settings.search_timeout_seconds),
        max_retries=(resolved_settings.search_max_retries),
        default_max_results=(resolved_settings.search_max_results),
    )
