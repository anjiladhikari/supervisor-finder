from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from pydantic import (
    Field,
    HttpUrl,
    ValidationError,
    field_validator,
    model_validator,
)

from research_finder.models import StrictModel
from research_finder.search_queries import (
    OfficialSearchQuery,
    SearchTarget,
)
from research_finder.web_search import (
    WebSearchClient,
    WebSearchError,
    WebSearchRequest,
)


class OfficialSearchPage(StrictModel):
    """One search result from an official university domain."""

    university_name: str = Field(
        min_length=2,
        max_length=200,
    )
    official_domain: str = Field(
        min_length=4,
        max_length=255,
    )
    target: SearchTarget

    title: str = Field(
        min_length=1,
        max_length=500,
    )
    url: HttpUrl
    snippet: str = Field(
        default="",
        max_length=3000,
    )
    result_rank: int = Field(
        ge=1,
    )
    search_query: str = Field(
        min_length=3,
        max_length=500,
    )

    @field_validator(
        "university_name",
        "title",
        "snippet",
        "search_query",
        mode="before",
    )
    @classmethod
    def normalise_text(
        cls,
        value: object,
    ) -> object:
        """Collapse repeated whitespace."""

        if isinstance(value, str):
            return " ".join(value.split())

        return value

    @field_validator(
        "official_domain",
        mode="before",
    )
    @classmethod
    def normalise_domain(
        cls,
        value: object,
    ) -> object:
        """Normalise the official root domain."""

        if isinstance(value, str):
            return value.strip().casefold().removeprefix("www.")

        return value

    @model_validator(mode="after")
    def validate_official_url(
        self,
    ) -> OfficialSearchPage:
        """Require the result URL to use the official domain."""

        hostname = urlparse(str(self.url)).hostname

        if hostname is None:
            raise ValueError("Search result URL must have a hostname.")

        normalised_hostname = hostname.casefold().removeprefix("www.")

        is_root_domain = normalised_hostname == self.official_domain
        is_subdomain = normalised_hostname.endswith(f".{self.official_domain}")

        if not is_root_domain and not is_subdomain:
            raise ValueError("Search result must use the official university domain.")

        return self


@dataclass(frozen=True)
class SearchBatchOutcome:
    """Results and counts from one target search batch."""

    pages: tuple[OfficialSearchPage, ...]
    attempted_queries: int
    failed_queries: int


def execute_official_searches(
    search_queries: list[OfficialSearchQuery],
    target: SearchTarget,
    client: WebSearchClient,
    max_results_per_query: int = 3,
) -> SearchBatchOutcome:
    """Execute one target's official-domain queries."""

    target_queries = [
        search_query for search_query in search_queries if search_query.target == target
    ]

    pages: list[OfficialSearchPage] = []
    seen_urls: set[str] = set()
    failed_queries = 0

    for search_query in target_queries:
        try:
            results = client.search(
                WebSearchRequest(
                    query=search_query.query,
                    max_results=max_results_per_query,
                )
            )
        except WebSearchError:
            failed_queries += 1
            continue

        for result in results:
            try:
                page = OfficialSearchPage(
                    university_name=(search_query.university_name),
                    official_domain=(search_query.official_domain),
                    target=search_query.target,
                    title=result.title,
                    url=result.url,
                    snippet=result.snippet,
                    result_rank=result.rank,
                    search_query=search_query.query,
                )
            except ValidationError:
                continue

            url_key = str(page.url).rstrip("/").casefold()

            if url_key in seen_urls:
                continue

            seen_urls.add(url_key)
            pages.append(page)

    return SearchBatchOutcome(
        pages=tuple(pages),
        attempted_queries=len(target_queries),
        failed_queries=failed_queries,
    )
