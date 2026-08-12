from research_finder.research_profile import (
    organise_verified_researcher,
)
from research_finder.researcher_details import (
    EnrichedResearcherCandidate,
    ResearchEvidenceItem,
)
from research_finder.researcher_extraction import (
    ResearcherCandidate,
)
from research_finder.search_queries import (
    SearchTarget,
)
from research_finder.verification import (
    VerifiedResearcherCandidate,
)


def main() -> None:
    """Run deterministic project-status check."""

    profile_url = (
        "https://www.deakin.edu.au/"
        "profile/jane-smith"
    )

    project_url = (
        "https://www.deakin.edu.au/"
        "research/projects"
    )

    researcher = ResearcherCandidate(
        full_name="Jane Smith",
        academic_title="Professor",
        role=(
            "Professor of Artificial Intelligence"
        ),
        research_interests=[
            "Reinforcement learning",
            "Time-series analysis",
        ],
        profile_summary=None,
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        source_url=profile_url,
        source_title="Jane Smith",
        evidence_text=(
            "Professor Jane Smith is a Professor "
            "of Artificial Intelligence."
        ),
    )

    current_project = ResearchEvidenceItem(
        name="Adaptive AI Project",
        target=SearchTarget.PROJECT,
        source_url=project_url,
        source_title="Adaptive AI Project",
        evidence_text=(
            "Jane Smith is currently leading "
            "the Adaptive AI Project."
        ),
    )

    previous_project = ResearchEvidenceItem(
        name="Previous AI Project",
        target=SearchTarget.PROJECT,
        source_url=project_url,
        source_title="Previous AI Project",
        evidence_text=(
            "Jane Smith previously worked on "
            "the Previous AI Project."
        ),
    )

    unknown_project = ResearchEvidenceItem(
        name="Intelligent Systems Project",
        target=SearchTarget.PROJECT,
        source_url=project_url,
        source_title=(
            "Intelligent Systems Project"
        ),
        evidence_text=(
            "Jane Smith contributed to the "
            "Intelligent Systems Project."
        ),
    )

    enriched = EnrichedResearcherCandidate(
        researcher=researcher,
        labs=[],
        projects=[
            current_project,
            previous_project,
            unknown_project,
        ],
        publications=[],
    )

    verified = VerifiedResearcherCandidate(
        candidate=enriched,
        affiliation_source_url=profile_url,
        verified_source_count=2,
    )

    result = organise_verified_researcher(
        verified,
        current_year=2026,
    )

    print(
        "Researcher:",
        result.verified_researcher
        .candidate.researcher.full_name,
    )

    print(
        "Research interests:",
        result.research_interests,
    )

    print(
        "Current projects:",
        [
            project.name
            for project
            in result.current_projects
        ],
    )

    print(
        "Previous projects:",
        [
            project.name
            for project
            in result.previous_projects
        ],
    )

    print(
        "Unknown projects:",
        [
            project.name
            for project
            in result.unknown_projects
        ],
    )


if __name__ == "__main__":
    main()