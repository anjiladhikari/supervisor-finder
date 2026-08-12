from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from pydantic import Field, HttpUrl

from research_finder.models import StrictModel
from research_finder.researcher_details import (
    EnrichedResearcherCandidate,
    ResearchEvidenceItem,
)
from research_finder.search_queries import (
    SearchTarget,
)
from research_finder.web_content import (
    DownloadedWebPage,
)


class VerifiedResearcherCandidate(StrictModel):
    """Researcher whose official affiliation was verified."""

    candidate: EnrichedResearcherCandidate

    affiliation_source_url: HttpUrl

    verified_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC)
    )

    verified_source_count: int = Field(
        ge=1,
    )


@dataclass(frozen=True)
class VerificationOutcome:
    """Result of lightweight researcher verification."""

    verified_candidates: tuple[
        VerifiedResearcherCandidate,
        ...,
    ]
    attempted_candidates: int
    rejected_candidates: int
    discarded_claims: int


def _normalise(value: str) -> str:
    """Normalise text for evidence comparison."""

    return " ".join(
        value.split()
    ).casefold()


def _normalise_url(
    value: str,
) -> str:
    """Normalise a URL for comparison."""

    return value.rstrip("/").casefold()


def _uses_official_domain(
    url: str,
    official_domain: str,
) -> bool:
    """Check whether a URL belongs to a university."""

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
    """Find the downloaded document for a source URL."""

    expected_url = _normalise_url(
        str(url)
    )

    for document in documents:
        if _normalise_url(
            str(document.final_url)
        ) == expected_url:
            return document

    return None


def _verify_researcher_profile(
    candidate: EnrichedResearcherCandidate,
    documents: list[DownloadedWebPage],
) -> DownloadedWebPage | None:
    """Verify researcher evidence against official profile."""

    researcher = candidate.researcher

    if not _uses_official_domain(
        str(researcher.source_url),
        researcher.official_domain,
    ):
        return None

    document = _find_document(
        researcher.source_url,
        documents,
    )

    if document is None:
        return None

    if document.target != SearchTarget.RESEARCHER:
        return None

    if (
        document.official_domain.casefold()
        != researcher.official_domain.casefold()
    ):
        return None

    content = _normalise(
        document.content
    )

    if (
        _normalise(researcher.full_name)
        not in content
    ):
        return None

    if (
        _normalise(researcher.evidence_text)
        not in content
    ):
        return None

    return document


def _verify_evidence_item(
    item: ResearchEvidenceItem,
    official_domain: str,
    documents: list[DownloadedWebPage],
) -> bool:
    """Verify one lab, project or publication."""

    if not _uses_official_domain(
        str(item.source_url),
        official_domain,
    ):
        return False

    document = _find_document(
        item.source_url,
        documents,
    )

    if document is None:
        return False

    if document.target != item.target:
        return False

    if (
        document.official_domain.casefold()
        != official_domain.casefold()
    ):
        return False

    content = _normalise(
        document.content
    )

    return (
        _normalise(item.evidence_text)
        in content
    )


def _verify_public_email(
    candidate: EnrichedResearcherCandidate,
    documents: list[DownloadedWebPage],
) -> bool:
    """Verify public email using downloaded evidence."""

    if candidate.public_email is None:
        return False

    if candidate.public_email_source_url is None:
        return False

    researcher = candidate.researcher

    email = str(
        candidate.public_email
    )

    email_domain = (
        email.rsplit("@", maxsplit=1)[-1]
        .casefold()
    )

    official_domain = (
        researcher.official_domain
        .casefold()
        .removeprefix("www.")
    )

    if not (
        email_domain == official_domain
        or email_domain.endswith(
            f".{official_domain}"
        )
    ):
        return False

    document = _find_document(
        candidate.public_email_source_url,
        documents,
    )

    if document is None:
        return False

    if not _uses_official_domain(
        str(document.final_url),
        researcher.official_domain,
    ):
        return False

    return (
        email.casefold()
        in document.content.casefold()
    )


def verify_researcher_candidates(
    candidates: list[
        EnrichedResearcherCandidate
    ],
    documents: list[DownloadedWebPage],
) -> VerificationOutcome:
    """Verify researchers and remove unsupported claims."""

    verified_candidates: list[
        VerifiedResearcherCandidate
    ] = []

    rejected_candidates = 0
    discarded_claims = 0

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

        researcher = candidate.researcher

        if _verify_public_email(
            candidate,
            documents,
        ):
            public_email = (
                candidate.public_email
            )
            public_email_source_url = (
                candidate.public_email_source_url
            )
        else:
            public_email = None
            public_email_source_url = None

            if candidate.public_email is not None:
                discarded_claims += 1

        verified_labs = [
            item
            for item in candidate.labs
            if _verify_evidence_item(
                item=item,
                official_domain=(
                    researcher.official_domain
                ),
                documents=documents,
            )
        ]

        verified_projects = [
            item
            for item in candidate.projects
            if _verify_evidence_item(
                item=item,
                official_domain=(
                    researcher.official_domain
                ),
                documents=documents,
            )
        ]

        verified_publications = [
            item
            for item in candidate.publications
            if _verify_evidence_item(
                item=item,
                official_domain=(
                    researcher.official_domain
                ),
                documents=documents,
            )
        ]

        discarded_claims += (
            len(candidate.labs)
            - len(verified_labs)
        )
        discarded_claims += (
            len(candidate.projects)
            - len(verified_projects)
        )
        discarded_claims += (
            len(candidate.publications)
            - len(verified_publications)
        )

        cleaned_candidate = (
            EnrichedResearcherCandidate(
                researcher=researcher,
                public_email=public_email,
                public_email_source_url=(
                    public_email_source_url
                ),
                labs=verified_labs,
                projects=verified_projects,
                publications=(
                    verified_publications
                ),
            )
        )

        source_urls = {
            _normalise_url(
                str(researcher.source_url)
            )
        }

        if public_email_source_url is not None:
            source_urls.add(
                _normalise_url(
                    str(public_email_source_url)
                )
            )

        for item in [
            *verified_labs,
            *verified_projects,
            *verified_publications,
        ]:
            source_urls.add(
                _normalise_url(
                    str(item.source_url)
                )
            )

        verified_candidates.append(
            VerifiedResearcherCandidate(
                candidate=cleaned_candidate,
                affiliation_source_url=(
                    profile_document.final_url
                ),
                verified_source_count=len(
                    source_urls
                ),
            )
        )

    return VerificationOutcome(
        verified_candidates=tuple(
            verified_candidates
        ),
        attempted_candidates=len(candidates),
        rejected_candidates=(
            rejected_candidates
        ),
        discarded_claims=discarded_claims,
    )