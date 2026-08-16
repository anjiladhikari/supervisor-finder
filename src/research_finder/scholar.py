from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from research_finder.web_search import (
    WebSearchClient,
    WebSearchRequest,
)


@dataclass(frozen=True)
class ScholarProfile:
    """One discovered Google Scholar profile."""

    researcher_name: str
    scholar_url: str


def _is_google_scholar_profile(
    url: str,
) -> bool:
    """Accept only Google Scholar author-profile URLs."""

    parsed = urlparse(url)

    hostname = (
        parsed.hostname or ""
    ).casefold()

    return (
        hostname == "scholar.google.com"
        and parsed.path.startswith(
            "/citations"
        )
        and "user=" in parsed.query
    )


def find_google_scholar_profile(
    *,
    researcher_name: str,
    university_name: str,
    client: WebSearchClient,
) -> ScholarProfile | None:
    """Find one likely Google Scholar profile."""

    query = (
        f'"{researcher_name}" '
        f'"{university_name}" '
        "site:scholar.google.com/citations"
    )

    results = client.search(
        WebSearchRequest(
            query=query,
            max_results=5,
        )
    )

    for result in results:
        url = str(result.url)

        if not _is_google_scholar_profile(
            url
        ):
            continue

        return ScholarProfile(
            researcher_name=researcher_name,
            scholar_url=url,
        )

    return None