from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from research_finder.web_search import (
    WebSearchClient,
    WebSearchRequest,
)


@dataclass(frozen=True)
class ResearchProjectLink:
    """One research-degree opportunity."""

    title: str
    url: str


def _is_official_university_url(
    url: str,
    official_domain: str,
) -> bool:
    hostname = (
        urlparse(url).hostname or ""
    ).casefold().removeprefix("www.")

    domain = (
        official_domain.casefold()
        .removeprefix("www.")
    )

    return (
        hostname == domain
        or hostname.endswith(
            f".{domain}"
        )
    )


def find_research_degree_projects(
    *,
    research_topic: str,
    university_name: str,
    official_domain: str,
    client: WebSearchClient,
    max_results: int = 3,
) -> list[ResearchProjectLink]:
    """Find relevant research-degree project pages."""

    query = (
        f'site:{official_domain} '
        f'"{research_topic}" '
        "("
        '"PhD" OR '
        '"MRes" OR '
        '"Master by Research" OR '
        '"Masters by Research" OR '
        '"research project" OR '
        '"available projects"'
        ")"
    )

    results = client.search(
        WebSearchRequest(
            query=query,
            max_results=max_results,
        )
    )

    projects: list[
        ResearchProjectLink
    ] = []

    seen_urls: set[str] = set()

    for result in results:
        url = str(result.url)

        if not _is_official_university_url(
            url,
            official_domain,
        ):
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        projects.append(
            ResearchProjectLink(
                title=result.title,
                url=url,
            )
        )

    return projects