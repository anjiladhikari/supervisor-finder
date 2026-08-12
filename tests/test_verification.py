from research_finder import nodes as nodes_module
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
    verify_researcher_candidates,
)
from research_finder.web_content import (
    DownloadedWebPage,
)


PROFILE_URL = (
    "https://www.deakin.edu.au/"
    "profile/jane-smith"
)

PROJECT_URL = (
    "https://www.deakin.edu.au/"
    "research/adaptive-learning"
)


def create_researcher() -> ResearcherCandidate:
    """Create one researcher."""

    return ResearcherCandidate(
        full_name="Jane Smith",
        academic_title="Professor",
        role=(
            "Professor of Artificial Intelligence"
        ),
        research_interests=[
            "Reinforcement learning"
        ],
        profile_summary=(
            "Artificial intelligence researcher."
        ),
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        source_url=PROFILE_URL,
        source_title="Jane Smith",
        evidence_text=(
            "Professor Jane Smith is a Professor "
            "of Artificial Intelligence."
        ),
    )


def create_profile_document() -> DownloadedWebPage:
    """Create official researcher-profile evidence."""

    return DownloadedWebPage(
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        target=SearchTarget.RESEARCHER,
        source_url=PROFILE_URL,
        final_url=PROFILE_URL,
        page_title="Jane Smith",
        content=(
            "Professor Jane Smith is a Professor "
            "of Artificial Intelligence. "
            "Contact jane.smith@deakin.edu.au."
        ),
        content_type="text/html",
        status_code=200,
    )


def create_project_document() -> DownloadedWebPage:
    """Create project evidence."""

    return DownloadedWebPage(
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        target=SearchTarget.PROJECT,
        source_url=PROJECT_URL,
        final_url=PROJECT_URL,
        page_title="Adaptive Learning Project",
        content=(
            "Jane Smith leads the "
            "Adaptive Learning Project."
        ),
        content_type="text/html",
        status_code=200,
    )


def create_candidate(
    *,
    include_project: bool = False,
) -> EnrichedResearcherCandidate:
    """Create an enriched researcher."""

    projects = []

    if include_project:
        projects.append(
            ResearchEvidenceItem(
                name="Adaptive Learning Project",
                target=SearchTarget.PROJECT,
                source_url=PROJECT_URL,
                source_title=(
                    "Adaptive Learning Project"
                ),
                evidence_text=(
                    "Jane Smith leads the "
                    "Adaptive Learning Project."
                ),
            )
        )

    return EnrichedResearcherCandidate(
        researcher=create_researcher(),
        public_email=(
            "jane.smith@deakin.edu.au"
        ),
        public_email_source_url=PROFILE_URL,
        labs=[],
        projects=projects,
        publications=[],
    )


def test_verifies_official_researcher() -> None:
    outcome = verify_researcher_candidates(
        candidates=[
            create_candidate()
        ],
        documents=[
            create_profile_document()
        ],
    )

    assert outcome.attempted_candidates == 1
    assert outcome.rejected_candidates == 0
    assert len(
        outcome.verified_candidates
    ) == 1

    verified = outcome.verified_candidates[0]

    assert (
        verified.candidate.researcher.full_name
        == "Jane Smith"
    )

    assert str(
        verified.candidate.public_email
    ) == "jane.smith@deakin.edu.au"


def test_rejects_missing_profile_evidence() -> None:
    outcome = verify_researcher_candidates(
        candidates=[
            create_candidate()
        ],
        documents=[],
    )

    assert outcome.rejected_candidates == 1
    assert outcome.verified_candidates == ()


def test_keeps_grounded_project() -> None:
    outcome = verify_researcher_candidates(
        candidates=[
            create_candidate(
                include_project=True
            )
        ],
        documents=[
            create_profile_document(),
            create_project_document(),
        ],
    )

    verified = outcome.verified_candidates[0]

    assert len(
        verified.candidate.projects
    ) == 1

    assert (
        verified.candidate.projects[0].name
        == "Adaptive Learning Project"
    )


def test_discards_unsupported_project() -> None:
    outcome = verify_researcher_candidates(
        candidates=[
            create_candidate(
                include_project=True
            )
        ],
        documents=[
            create_profile_document()
        ],
    )

    verified = outcome.verified_candidates[0]

    assert verified.candidate.projects == []
    assert outcome.discarded_claims == 1


def test_verification_records_source_count() -> None:
    outcome = verify_researcher_candidates(
        candidates=[
            create_candidate(
                include_project=True
            )
        ],
        documents=[
            create_profile_document(),
            create_project_document(),
        ],
    )

    verified = outcome.verified_candidates[0]

    assert verified.verified_source_count == 2


def test_node_handles_no_candidates() -> None:
    result = (
        nodes_module.verify_current_affiliation(
            {
                "enriched_candidates": [],
            }
        )
    )

    assert result["verified_results"] == []

    assert result["execution_log"] == [
        (
            "Researcher verification completed: "
            "0 candidates checked, "
            "0 verified."
        )
    ]