from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import Field

from research_finder.models import StrictModel
from research_finder.researcher_details import (
    ResearchEvidenceItem,
)
from research_finder.verification import (
    VerifiedResearcherCandidate,
)


class ProjectStatus(StrEnum):
    """Supported project-status categories."""

    CURRENT = "current"
    PREVIOUS = "previous"
    UNKNOWN = "unknown"


class ClassifiedProject(StrictModel):
    """One project with deterministic status."""

    project: ResearchEvidenceItem
    status: ProjectStatus
    status_reason: str = Field(
        min_length=2,
        max_length=300,
    )


class OrganisedResearcherProfile(StrictModel):
    """Verified researcher organised for scoring and output."""

    verified_researcher: VerifiedResearcherCandidate

    research_interests: list[str] = Field(
        default_factory=list,
    )

    current_projects: list[ResearchEvidenceItem] = Field(
        default_factory=list,
    )
    previous_projects: list[ResearchEvidenceItem] = Field(
        default_factory=list,
    )
    unknown_projects: list[ResearchEvidenceItem] = Field(
        default_factory=list,
    )


_CURRENT_PHRASES = (
    "currently",
    "current project",
    "ongoing",
    "is leading",
    "leads the",
    "is working on",
    "works on",
    "is developing",
    "active project",
    "in progress",
)

_PREVIOUS_PHRASES = (
    "previously",
    "former project",
    "completed",
    "was completed",
    "concluded",
    "past project",
    "formerly",
    "was involved",
    "worked on",
    "was funded",
)


_YEAR_RANGE_PATTERN = re.compile(
    r"\b(19\d{2}|20\d{2})\s*[-–—]\s*"
    r"(19\d{2}|20\d{2})\b"
)


def _normalise(value: str) -> str:
    """Normalise text for deterministic matching."""

    return " ".join(
        value.split()
    ).casefold()


def classify_project_status(
    project: ResearchEvidenceItem,
    *,
    current_year: int | None = None,
) -> ClassifiedProject:
    """Classify a project using explicit evidence only."""

    resolved_year = (
        current_year
        if current_year is not None
        else datetime.now(UTC).year
    )

    evidence = _normalise(
        project.evidence_text
    )

    for phrase in _CURRENT_PHRASES:
        if phrase in evidence:
            return ClassifiedProject(
                project=project,
                status=ProjectStatus.CURRENT,
                status_reason=(
                    f"Evidence contains current-status "
                    f"phrase: '{phrase}'."
                ),
            )

    for phrase in _PREVIOUS_PHRASES:
        if phrase in evidence:
            return ClassifiedProject(
                project=project,
                status=ProjectStatus.PREVIOUS,
                status_reason=(
                    f"Evidence contains previous-status "
                    f"phrase: '{phrase}'."
                ),
            )

    year_ranges = _YEAR_RANGE_PATTERN.findall(
        project.evidence_text
    )

    for _, end_year_text in year_ranges:
        end_year = int(end_year_text)

        if end_year < resolved_year:
            return ClassifiedProject(
                project=project,
                status=ProjectStatus.PREVIOUS,
                status_reason=(
                    "Evidence contains a completed "
                    f"year range ending in {end_year}."
                ),
            )

        if end_year >= resolved_year:
            return ClassifiedProject(
                project=project,
                status=ProjectStatus.CURRENT,
                status_reason=(
                    "Evidence contains a project "
                    f"year range ending in {end_year}."
                ),
            )

    return ClassifiedProject(
        project=project,
        status=ProjectStatus.UNKNOWN,
        status_reason=(
            "Official evidence does not explicitly "
            "show whether the project is current "
            "or previous."
        ),
    )


def organise_verified_researcher(
    verified: VerifiedResearcherCandidate,
    *,
    current_year: int | None = None,
) -> OrganisedResearcherProfile:
    """Separate projects and research interests."""

    candidate = verified.candidate
    researcher = candidate.researcher

    current_projects: list[
        ResearchEvidenceItem
    ] = []
    previous_projects: list[
        ResearchEvidenceItem
    ] = []
    unknown_projects: list[
        ResearchEvidenceItem
    ] = []

    for project in candidate.projects:
        classified = classify_project_status(
            project,
            current_year=current_year,
        )

        if classified.status == ProjectStatus.CURRENT:
            current_projects.append(project)

        elif (
            classified.status
            == ProjectStatus.PREVIOUS
        ):
            previous_projects.append(project)

        else:
            unknown_projects.append(project)

    interests: list[str] = []
    seen_interests: set[str] = set()

    for interest in researcher.research_interests:
        cleaned = " ".join(
            interest.split()
        )

        if not cleaned:
            continue

        key = cleaned.casefold()

        if key in seen_interests:
            continue

        seen_interests.add(key)
        interests.append(cleaned)

    return OrganisedResearcherProfile(
        verified_researcher=verified,
        research_interests=interests,
        current_projects=current_projects,
        previous_projects=previous_projects,
        unknown_projects=unknown_projects,
    )


def organise_verified_researchers(
    verified_results: list[
        VerifiedResearcherCandidate
    ],
    *,
    current_year: int | None = None,
) -> list[OrganisedResearcherProfile]:
    """Organise every verified researcher."""

    return [
        organise_verified_researcher(
            verified,
            current_year=current_year,
        )
        for verified in verified_results
    ]