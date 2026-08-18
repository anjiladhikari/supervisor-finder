from __future__ import annotations

from urllib.parse import urlparse

from pydantic import HttpUrl

from research_finder.models import StrictModel
from research_finder.web_search import (
    WebSearchClient,
    WebSearchRequest,
)


class ResearchDegreePortal(StrictModel):
    """Central university research-degree page."""

    title: str
    url: HttpUrl


def _is_official_university_url(
    url: str,
    official_domain: str,
) -> bool:
    """Accept only the university's official domain."""

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
    """Prefer central university research-degree pages."""

    title_text = title.casefold()

    parsed = urlparse(url)

    path = (
        parsed.path.casefold()
        .replace("_", "-")
    )

    snippet_text = snippet.casefold()

    score = 0

    # Strong central university signals.
    if "graduate research" in title_text:
        score += 50

    if "research degrees" in title_text:
        score += 45

    if "research degree" in title_text:
        score += 40

    if "higher degree research" in title_text:
        score += 40

    if "available research projects" in title_text:
        score += 25

    if "available projects" in title_text:
        score += 20

    # Strong URL signals.
    if "/graduate-research" in path:
        score += 50

    if "research-degrees" in path:
        score += 40

    if "higher-degree-research" in path:
        score += 40

    if "available-projects" in path:
        score += 25

    if "available-research-projects" in path:
        score += 20

    # Small supporting evidence only.
    if "phd" in snippet_text:
        score += 5

    if (
        "master by research" in snippet_text
        or "masters by research" in snippet_text
        or "master's by research" in snippet_text
    ):
        score += 5

    # Penalise faculty / school / clinical pages.
    non_central_markers = (
        "clinical",
        "faculty of",
        "school of",
        "department of",
        "institute",
        "hospital",
        "/medicine/",
        "/engineering/",
        "/business/",
        "/faculty/",
        "/school/",
        "/department/",
    )

    combined = (
        f"{title_text} {path}"
    )

    for marker in non_central_markers:
        if marker in combined:
            score -= 40

    return score


def find_research_degree_portal(
    *,
    university_name: str,
    official_domain: str,
    client: WebSearchClient,
) -> ResearchDegreePortal | None:
    """Find one main university research-degree portal."""

    query = (
        f"site:{official_domain} "
        "("
        '"graduate research" OR '
        '"research degrees" OR '
        '"higher degree research"'
        ") "
        "("
        '"available projects" OR '
        '"available research projects" OR '
        '"find a project" OR '
        '"PhD" OR '
        '"Master by Research" OR '
        '"Masters by Research"'
        ")"
    )

    results = client.search(
        WebSearchRequest(
            query=query,
            max_results=5,
        )
    )

    best_result = None
    best_score = 0

    for result in results:
        url = str(
            result.url
        )

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

    # Better to show "not found"
    # than return an unrelated page.
    if (
        best_result is None
        or best_score < 30
    ):
        return None

    return ResearchDegreePortal(
        title=(
            best_result.title
            or (
                f"{university_name} "
                "Graduate Research"
            )
        ),
        url=best_result.url,
    )