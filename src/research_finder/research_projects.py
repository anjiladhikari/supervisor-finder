from __future__ import annotations

from urllib.parse import urlparse

from pydantic import HttpUrl

from research_finder.models import StrictModel
from research_finder.web_search import (
    WebSearchClient,
    WebSearchRequest,
)


class ResearchDegreePortal(StrictModel):
    """Central university page for research-degree project opportunities."""

    title: str
    url: HttpUrl


def _is_official_university_url(
    url: str,
    official_domain: str,
) -> bool:
    """Check that a URL belongs to the researcher's university."""

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


def _portal_score(
    *,
    title: str,
    url: str,
    snippet: str,
) -> int:
    """Prefer central pages that list available research projects."""

    text = " ".join(
        [
            title,
            url,
            snippet,
        ]
    ).casefold()

    score = 0

    strong_phrases = {
        "available research projects": 20,
        "available projects": 18,
        "research project opportunities": 18,
        "find a research project": 18,
        "graduate research projects": 16,
        "phd projects": 15,
        "research degree projects": 15,
    }

    supporting_phrases = {
        "higher degree research": 6,
        "graduate research": 6,
        "research degrees": 6,
        "research degree": 5,
        "master by research": 5,
        "masters by research": 5,
        "mres": 4,
        "phd": 3,
    }

    for phrase, points in strong_phrases.items():
        if phrase in text:
            score += points

    for phrase, points in supporting_phrases.items():
        if phrase in text:
            score += points

    return score


def find_research_degree_portal(
    *,
    university_name: str,
    official_domain: str,
    client: WebSearchClient,
) -> ResearchDegreePortal | None:
    """Find one central research-degree projects page for a university."""

    query = (
        f"site:{official_domain} "
        "("
        '"available research projects" OR '
        '"available projects" OR '
        '"research project opportunities" OR '
        '"find a research project" OR '
        '"graduate research projects" OR '
        '"PhD projects"'
        ") "
        "("
        '"research degree" OR '
        '"higher degree research" OR '
        '"graduate research" OR '
        '"PhD" OR '
        '"Master by Research" OR '
        '"Masters by Research"'
        ")"
    )

    # These five results are only candidates.
    # We still return ONE central university page.
    results = client.search(
        WebSearchRequest(
            query=query,
            max_results=5,
        )
    )

    best_result = None
    best_score = 0

    for result in results:
        url = str(result.url)

        if not _is_official_university_url(
            url,
            official_domain,
        ):
            continue

        score = _portal_score(
            title=result.title,
            url=url,
            snippet=result.snippet,
        )

        if score > best_score:
            best_score = score
            best_result = result

    if best_result is None:
        return None

    return ResearchDegreePortal(
        title=(
            best_result.title
            or (
                f"{university_name} "
                "research-degree projects"
            )
        ),
        url=best_result.url,
    )