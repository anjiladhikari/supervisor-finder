from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from pydantic import Field, HttpUrl

from research_finder.models import StrictModel
from research_finder.researcher_extraction import (
    ResearcherCandidate,
)
from research_finder.search_queries import SearchTarget
from research_finder.web_content import (
    DownloadedWebPage,
)


class VerifiedResearcherCandidate(StrictModel):
    """Researcher verified using an official university profile."""

    candidate: ResearcherCandidate

    affiliation_source_url: HttpUrl

    verified_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    verified_source_count: int = Field(
        ge=1,
    )


@dataclass(frozen=True)
class VerificationOutcome:
    """Result of researcher-profile verification."""

    verified_candidates: tuple[
        VerifiedResearcherCandidate,
        ...
    ]

    attempted_candidates: int
    rejected_candidates: int
    discarded_claims: int = 0


def _normalise(value: str) -> str:
    return " ".join(value.split()).casefold()


def _normalise_url(value: str) -> str:
    return value.rstrip("/").casefold()


def _uses_official_domain(
    url: str,
    official_domain: str,
) -> bool:
    hostname = urlparse(url).hostname

    if hostname is None:
        return False

    hostname = (
        hostname.casefold()
        .removeprefix("www.")
    )

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


def _find_document(
    url: HttpUrl,
    documents: list[DownloadedWebPage],
) -> DownloadedWebPage | None:
    expected_url = _normalise_url(
        str(url)
    )

    for document in documents:
        if (
            _normalise_url(
                str(document.final_url)
            )
            == expected_url
        ):
            return document

    return None


def _verify_researcher_profile(
    candidate: ResearcherCandidate,
    documents: list[DownloadedWebPage],
) -> DownloadedWebPage | None:
    if not _uses_official_domain(
        str(candidate.source_url),
        candidate.official_domain,
    ):
        return None

    document = _find_document(
        candidate.source_url,
        documents,
    )

    if document is None:
        return None

    if (
        document.target
        != SearchTarget.RESEARCHER
    ):
        return None

    if (
        document.official_domain.casefold()
        != candidate.official_domain.casefold()
    ):
        return None

    content = _normalise(
        document.content
    )

    if (
        _normalise(candidate.full_name)
        not in content
    ):
        return None

    if (
        _normalise(candidate.evidence_text)
        not in content
    ):
        return None

    return document


def verify_researcher_candidates(
    candidates: list[ResearcherCandidate],
    documents: list[DownloadedWebPage],
) -> VerificationOutcome:
    verified_candidates: list[
        VerifiedResearcherCandidate
    ] = []

    rejected_candidates = 0

    for candidate in candidates:
        profile_document = (
            _verify_researcher_profile(
                candidate=candidate,
                documents=documents,
            )
        )

        if profile_document is None:
            rejected_candidates += 1
            continue

        verified_candidates.append(
            VerifiedResearcherCandidate(
                candidate=candidate,
                affiliation_source_url=(
                    profile_document.final_url
                ),
                verified_source_count=1,
            )
        )

    return VerificationOutcome(
        verified_candidates=tuple(
            verified_candidates
        ),
        attempted_candidates=len(
            candidates
        ),
        rejected_candidates=(
            rejected_candidates
        ),
        discarded_claims=0,
    )