from research_finder import (
    nodes as nodes_module,
)
from research_finder.models import (
    SearchRequest,
)
from research_finder.ranking import (
    rank_researcher_results,
)
from research_finder.relevance import (
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


def create_scored_result(
    *,
    name: str,
    interests: list[str] | None = None,
    current_projects: list[
        ResearchEvidenceItem
    ] | None = None,
    publications: list[
        ResearchEvidenceItem
    ] | None = None,
    verified_source_count: int = 1,
):
    """Create one scored researcher."""

    slug = (
        name.casefold()
        .replace(" ", "-")
    )

    profile_url = (
        "https://www.deakin.edu.au/"
        f"profile/{slug}"
    )

    researcher = ResearcherCandidate(
        full_name=name,
        academic_title="Professor",
        role=(
            "Professor of Artificial Intelligence"
        ),
        research_interests=(
            interests or []
        ),
        profile_summary=None,
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        source_url=profile_url,
        source_title=name,
        evidence_text=(
            f"Professor {name} is an "
            "artificial intelligence researcher."
        ),
    )

    projects = (
        current_projects or []
    )

    publication_items = (
        publications or []
    )

    enriched = EnrichedResearcherCandidate(
        researcher=researcher,
        labs=[],
        projects=projects,
        publications=publication_items,
    )

    verified = VerifiedResearcherCandidate(
        candidate=enriched,
        affiliation_source_url=(
            profile_url
        ),
        verified_source_count=(
            verified_source_count
        ),
    )

    profile = OrganisedResearcherProfile(
        verified_researcher=verified,
        research_interests=(
            interests or []
        ),
        current_projects=projects,
        previous_projects=[],
        unknown_projects=[],
    )

    return score_researcher_profile(
        profile,
        research_topic=(
            "Reinforcement learning"
        ),
        expanded_topics=[],
    )


def create_project(
    name: str,
) -> ResearchEvidenceItem:
    """Create matching project evidence."""

    return ResearchEvidenceItem(
        name=name,
        target=SearchTarget.PROJECT,
        source_url=(
            "https://www.deakin.edu.au/"
            f"research/{name.casefold().replace(' ', '-')}"
        ),
        source_title=name,
        evidence_text=(
            f"{name} uses reinforcement learning."
        ),
    )


def create_publication(
    name: str,
) -> ResearchEvidenceItem:
    """Create matching publication evidence."""

    return ResearchEvidenceItem(
        name=name,
        target=SearchTarget.PUBLICATION,
        source_url=(
            "https://www.deakin.edu.au/"
            f"research/{name.casefold().replace(' ', '-')}"
        ),
        source_title=name,
        evidence_text=(
            f"{name} studies reinforcement learning."
        ),
        publication_year=2025,
    )


def test_higher_score_ranks_first() -> None:
    stronger = create_scored_result(
        name="Jane Smith",
        interests=[
            "Reinforcement learning"
        ],
        current_projects=[
            create_project(
                "Reinforcement Learning Project"
            )
        ],
    )

    weaker = create_scored_result(
        name="John Brown",
        interests=[
            "Reinforcement learning"
        ],
    )

    ranked = rank_researcher_results(
        [
            weaker,
            stronger,
        ],
        max_results=10,
    )

    assert ranked[0].result == stronger
    assert ranked[0].rank == 1
    assert ranked[1].rank == 2


def test_zero_score_is_excluded() -> None:
    relevant = create_scored_result(
        name="Jane Smith",
        interests=[
            "Reinforcement learning"
        ],
    )

    unrelated = create_scored_result(
        name="John Brown",
        interests=[
            "Marine biology"
        ],
    )

    assert unrelated.relevance_score == 0

    ranked = rank_researcher_results(
        [
            unrelated,
            relevant,
        ],
        max_results=10,
    )

    assert len(ranked) == 1

    assert (
        ranked[0]
        .result
        .profile
        .verified_researcher
        .candidate
        .researcher
        .full_name
        == "Jane Smith"
    )


def test_respects_max_results() -> None:
    results = [
        create_scored_result(
            name=f"Researcher {index}",
            interests=[
                "Reinforcement learning"
            ],
        )
        for index in range(5)
    ]

    ranked = rank_researcher_results(
        results,
        max_results=3,
    )

    assert len(ranked) == 3


def test_current_projects_break_score_tie() -> None:
    no_project = create_scored_result(
        name="Jane Smith",
        interests=[
            "Reinforcement learning"
        ],
    )

    with_project = create_scored_result(
        name="John Brown",
        interests=[],
        current_projects=[
            create_project(
                "Reinforcement Learning Project"
            )
        ],
    )

    # Force equal scores so we can test the
    # deterministic ranking tie-breaker.
    with_project = (
        with_project.model_copy(
            update={
                "relevance_score": (
                    no_project.relevance_score
                )
            }
        )
    )

    ranked = rank_researcher_results(
        [
            no_project,
            with_project,
        ],
        max_results=10,
    )

    assert (
        ranked[0]
        .result
        .profile
        .verified_researcher
        .candidate
        .researcher
        .full_name
        == "John Brown"
    )


def test_publications_break_project_tie() -> None:
    without_publication = (
        create_scored_result(
            name="Jane Smith",
            interests=[
                "Reinforcement learning"
            ],
        )
    )

    with_publication = (
        create_scored_result(
            name="John Brown",
            interests=[
                "Reinforcement learning"
            ],
            publications=[
                create_publication(
                    "RL Publication"
                )
            ],
        )
    )

    with_publication = (
        with_publication.model_copy(
            update={
                "relevance_score": (
                    without_publication
                    .relevance_score
                )
            }
        )
    )

    ranked = rank_researcher_results(
        [
            without_publication,
            with_publication,
        ],
        max_results=10,
    )

    assert (
        ranked[0]
        .result
        .profile
        .verified_researcher
        .candidate
        .researcher
        .full_name
        == "John Brown"
    )


def test_verified_sources_break_tie() -> None:
    first = create_scored_result(
        name="Jane Smith",
        interests=[
            "Reinforcement learning"
        ],
        verified_source_count=1,
    )

    second = create_scored_result(
        name="John Brown",
        interests=[
            "Reinforcement learning"
        ],
        verified_source_count=4,
    )

    ranked = rank_researcher_results(
        [
            first,
            second,
        ],
        max_results=10,
    )

    assert (
        ranked[0]
        .result
        .profile
        .verified_researcher
        .candidate
        .researcher
        .full_name
        == "John Brown"
    )


def test_empty_results_returns_empty() -> None:
    assert (
        rank_researcher_results(
            [],
            max_results=10,
        )
        == []
    )


def test_node_handles_no_results() -> None:
    result = nodes_module.rank_results(
        {
            "deduplicated_results": [],
        }
    )

    assert result["ranked_results"] == []

    assert result["execution_log"] == [
        (
            "Result ranking completed: "
            "0 researchers ranked."
        )
    ]


def test_node_ranks_results() -> None:
    request = SearchRequest(
        country="Australia",
        country_code="AU",
        state="Victoria",
        state_code="AU-VIC",
        research_topic=(
            "Reinforcement learning"
        ),
        max_results=5,
    )

    researcher = create_scored_result(
        name="Jane Smith",
        interests=[
            "Reinforcement learning"
        ],
    )

    result = nodes_module.rank_results(
        {
            "request": request,
            "deduplicated_results": [
                researcher
            ],
        }
    )

    assert len(
        result["ranked_results"]
    ) == 1

    assert (
        result["ranked_results"][0].rank
        == 1
    )

    assert result["execution_log"] == [
        (
            "Result ranking completed: "
            "1 unique researchers evaluated, "
            "1 strongest matches retained."
        )
    ]