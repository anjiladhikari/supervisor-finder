from research_finder.research_profile import (
    ProjectStatus,
    classify_project_status,
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

PROFILE_URL = "https://www.deakin.edu.au/profile/jane-smith"

PROJECT_URL = "https://www.deakin.edu.au/research/project"


def create_project(
    evidence: str,
    *,
    name: str = "AI Project",
) -> ResearchEvidenceItem:
    """Create one verified project."""

    return ResearchEvidenceItem(
        name=name,
        target=SearchTarget.PROJECT,
        source_url=PROJECT_URL,
        source_title=name,
        evidence_text=evidence,
    )


def create_verified_candidate(
    projects: list[ResearchEvidenceItem],
) -> VerifiedResearcherCandidate:
    """Create one verified researcher."""

    researcher = ResearcherCandidate(
        full_name="Jane Smith",
        academic_title="Professor",
        role=("Professor of Artificial Intelligence"),
        research_interests=[
            "Reinforcement learning",
            "Time-series analysis",
            "reinforcement learning",
        ],
        profile_summary=None,
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        source_url=PROFILE_URL,
        source_title="Jane Smith",
        evidence_text=("Professor Jane Smith is a Professor of Artificial Intelligence."),
    )

    enriched = EnrichedResearcherCandidate(
        researcher=researcher,
        public_email=None,
        public_email_source_url=None,
        labs=[],
        projects=projects,
        publications=[],
    )

    return VerifiedResearcherCandidate(
        candidate=enriched,
        affiliation_source_url=PROFILE_URL,
        verified_source_count=1,
    )


def test_classifies_current_project_phrase() -> None:
    project = create_project("Jane Smith is currently leading the AI Project.")

    result = classify_project_status(
        project,
        current_year=2026,
    )

    assert result.status == ProjectStatus.CURRENT


def test_classifies_previous_project_phrase() -> None:
    project = create_project("Jane Smith previously worked on the AI Project.")

    result = classify_project_status(
        project,
        current_year=2026,
    )

    assert result.status == ProjectStatus.PREVIOUS


def test_classifies_finished_year_range() -> None:
    project = create_project("The AI Project ran from 2021-2024.")

    result = classify_project_status(
        project,
        current_year=2026,
    )

    assert result.status == ProjectStatus.PREVIOUS


def test_classifies_active_year_range() -> None:
    project = create_project("The AI Project runs from 2024-2027.")

    result = classify_project_status(
        project,
        current_year=2026,
    )

    assert result.status == ProjectStatus.CURRENT


def test_unclear_project_remains_unknown() -> None:
    project = create_project("Jane Smith contributed to the AI Project.")

    result = classify_project_status(
        project,
        current_year=2026,
    )

    assert result.status == ProjectStatus.UNKNOWN


def test_organises_projects_and_interests() -> None:
    verified = create_verified_candidate(
        [
            create_project(
                ("Jane Smith is currently leading Current AI Project."),
                name="Current AI Project",
            ),
            create_project(
                ("Jane Smith previously worked on Previous AI Project."),
                name="Previous AI Project",
            ),
            create_project(
                ("Jane Smith contributed to Research Project."),
                name="Research Project",
            ),
        ]
    )

    result = organise_verified_researcher(
        verified,
        current_year=2026,
    )

    assert len(result.current_projects) == 1

    assert len(result.previous_projects) == 1

    assert len(result.unknown_projects) == 1

    assert result.research_interests == [
        "Reinforcement learning",
        "Time-series analysis",
    ]


from research_finder import nodes as nodes_module


def test_profile_node_handles_no_results() -> None:
    result = nodes_module.organise_researcher_profiles(
        {
            "verified_results": [],
        }
    )

    assert result["organised_results"] == []

    assert result["execution_log"] == [
        ("Researcher profile organisation completed: 0 researchers organised.")
    ]


def test_profile_node_organises_results() -> None:
    verified = create_verified_candidate(
        [create_project("Jane Smith is currently leading the AI Project.")]
    )

    result = nodes_module.organise_researcher_profiles(
        {
            "verified_results": [verified],
        }
    )

    assert len(result["organised_results"]) == 1

    assert len(result["organised_results"][0].current_projects) == 1
