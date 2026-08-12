from research_finder import (
    nodes as nodes_module,
)
from research_finder.deduplication import (
    canonical_source_url_key,
    deduplicate_by_source_url,
    deduplicate_scored_researchers,
)
from research_finder.models import (
    SearchRequest,
)
from research_finder.relevance import (
    ScoredResearcherProfile,
    score_researcher_profile,
)
from research_finder.research_profile import (
    OrganisedResearcherProfile,
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

PROJECT_URL = "https://www.deakin.edu.au/research/ai-project"


def create_scored_result(
    *,
    interests: list[str] | None = None,
    projects: list[ResearchEvidenceItem] | None = None,
    university: str = "Deakin University",
    domain: str = "deakin.edu.au",
) -> ScoredResearcherProfile:
    """Create one scored researcher."""

    researcher = ResearcherCandidate(
        full_name="Jane Smith",
        academic_title="Professor",
        role=("Professor of Artificial Intelligence"),
        research_interests=(interests or []),
        profile_summary=None,
        university_name=university,
        official_domain=domain,
        source_url=(
            PROFILE_URL
            if domain == "deakin.edu.au"
            else ("https://example.edu.au/profile/jane-smith")
        ),
        source_title="Jane Smith",
        evidence_text=("Professor Jane Smith is a researcher."),
    )

    enriched = EnrichedResearcherCandidate(
        researcher=researcher,
        labs=[],
        projects=projects or [],
        publications=[],
    )

    verified = VerifiedResearcherCandidate(
        candidate=enriched,
        affiliation_source_url=(researcher.source_url),
        verified_source_count=1,
    )

    profile = OrganisedResearcherProfile(
        verified_researcher=verified,
        research_interests=(interests or []),
        current_projects=(projects or []),
        previous_projects=[],
        unknown_projects=[],
    )

    return score_researcher_profile(
        profile,
        research_topic=("Reinforcement learning"),
        expanded_topics=[],
    )


def create_project() -> ResearchEvidenceItem:
    """Create one matching project."""

    return ResearchEvidenceItem(
        name=("Reinforcement Learning Project"),
        target=SearchTarget.PROJECT,
        source_url=PROJECT_URL,
        source_title=("Reinforcement Learning Project"),
        evidence_text=("Jane Smith is currently leading the Reinforcement Learning Project."),
    )


def test_canonical_url_removes_tracking() -> None:
    first = canonical_source_url_key("https://www.deakin.edu.au/research/?utm_source=test#top")

    second = canonical_source_url_key("https://deakin.edu.au/research")

    assert first == second


def test_deduplicates_source_urls() -> None:
    urls = [
        ("https://www.deakin.edu.au/research"),
        ("https://deakin.edu.au/research/"),
    ]

    unique, removed = deduplicate_by_source_url(
        urls,
        url_getter=lambda value: value,
    )

    assert len(unique) == 1
    assert removed == 1


def test_merges_duplicate_researchers() -> None:
    first = create_scored_result(interests=["Reinforcement learning"])

    second = create_scored_result(interests=["Time-series analysis"])

    results = deduplicate_scored_researchers(
        [first, second],
        research_topic=("Reinforcement learning"),
        expanded_topics=["Time-series analysis"],
    )

    assert len(results) == 1

    interests = results[0].profile.research_interests

    assert interests == [
        "Reinforcement learning",
        "Time-series analysis",
    ]


def test_same_name_different_university_is_kept() -> None:
    first = create_scored_result()

    second = create_scored_result(
        university="Example University",
        domain="example.edu.au",
    )

    results = deduplicate_scored_researchers(
        [first, second],
        research_topic=("Reinforcement learning"),
        expanded_topics=[],
    )

    assert len(results) == 2


def test_duplicate_projects_are_removed() -> None:
    project_one = create_project()

    project_two = project_one.model_copy()

    first = create_scored_result(projects=[project_one])

    second = create_scored_result(projects=[project_two])

    results = deduplicate_scored_researchers(
        [first, second],
        research_topic=("Reinforcement learning"),
        expanded_topics=[],
    )

    projects = results[0].profile.verified_researcher.candidate.projects

    assert len(projects) == 1


def test_merged_researcher_is_rescored() -> None:
    first = create_scored_result(interests=["Reinforcement learning"])

    second = create_scored_result(projects=[create_project()])

    assert first.relevance_score == 40
    assert second.relevance_score == 25

    results = deduplicate_scored_researchers(
        [first, second],
        research_topic=("Reinforcement learning"),
        expanded_topics=[],
    )

    assert len(results) == 1

    assert results[0].relevance_score == 65


def test_node_handles_no_results() -> None:
    result = nodes_module.remove_duplicates(
        {
            "scored_results": [],
            "researcher_pages": [],
            "lab_pages": [],
            "project_pages": [],
            "publication_pages": [],
            "researcher_documents": [],
            "lab_documents": [],
            "project_documents": [],
            "publication_documents": [],
        }
    )

    assert result["deduplicated_results"] == []

    assert result["execution_log"] == [
        (
            "Deduplication completed: "
            "0 scored researchers -> "
            "0 unique researchers; "
            "0 duplicate source pages and "
            "0 duplicate documents removed."
        )
    ]


def test_node_merges_duplicate_results() -> None:
    request = SearchRequest(
        country="Australia",
        country_code="AU",
        state="Victoria",
        state_code="AU-VIC",
        research_topic=("Reinforcement learning"),
    )

    first = create_scored_result(interests=["Reinforcement learning"])

    second = create_scored_result(projects=[create_project()])

    result = nodes_module.remove_duplicates(
        {
            "request": request,
            "expanded_topics": [],
            "scored_results": [
                first,
                second,
            ],
            "researcher_pages": [],
            "lab_pages": [],
            "project_pages": [],
            "publication_pages": [],
            "researcher_documents": [],
            "lab_documents": [],
            "project_documents": [],
            "publication_documents": [],
        }
    )

    assert len(result["deduplicated_results"]) == 1

    assert result["deduplicated_results"][0].relevance_score == 65
