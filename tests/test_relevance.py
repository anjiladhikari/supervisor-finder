from research_finder import nodes as nodes_module
from research_finder.models import (
    SearchRequest,
)
from research_finder.relevance import (
    build_search_topics,
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


PROFILE_URL = (
    "https://www.deakin.edu.au/"
    "profile/jane-smith"
)

SOURCE_URL = (
    "https://www.deakin.edu.au/"
    "research/example"
)


def create_item(
    name: str,
    target: SearchTarget,
    evidence: str,
) -> ResearchEvidenceItem:
    """Create one evidence item."""

    return ResearchEvidenceItem(
        name=name,
        target=target,
        source_url=SOURCE_URL,
        source_title=name,
        evidence_text=evidence,
    )


def create_profile(
    *,
    interests: list[str] | None = None,
    current_projects: list[
        ResearchEvidenceItem
    ] | None = None,
    previous_projects: list[
        ResearchEvidenceItem
    ] | None = None,
    unknown_projects: list[
        ResearchEvidenceItem
    ] | None = None,
    labs: list[
        ResearchEvidenceItem
    ] | None = None,
    publications: list[
        ResearchEvidenceItem
    ] | None = None,
) -> OrganisedResearcherProfile:
    """Create one organised researcher."""

    researcher = ResearcherCandidate(
        full_name="Jane Smith",
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
        source_url=PROFILE_URL,
        source_title="Jane Smith",
        evidence_text=(
            "Professor Jane Smith is a Professor "
            "of Artificial Intelligence."
        ),
    )

    enriched = EnrichedResearcherCandidate(
        researcher=researcher,
        labs=labs or [],
        projects=[
            *(current_projects or []),
            *(previous_projects or []),
            *(unknown_projects or []),
        ],
        publications=(
            publications or []
        ),
    )

    verified = VerifiedResearcherCandidate(
        candidate=enriched,
        affiliation_source_url=PROFILE_URL,
        verified_source_count=1,
    )

    return OrganisedResearcherProfile(
        verified_researcher=verified,
        research_interests=(
            interests or []
        ),
        current_projects=(
            current_projects or []
        ),
        previous_projects=(
            previous_projects or []
        ),
        unknown_projects=(
            unknown_projects or []
        ),
    )


def test_build_search_topics_deduplicates() -> None:
    topics = build_search_topics(
        research_topic=(
            "Reinforcement learning"
        ),
        expanded_topics=[
            "reinforcement learning",
            "Time-series analysis",
        ],
    )

    assert topics == [
        "Reinforcement learning",
        "Time-series analysis",
    ]


def test_exact_interest_match_scores_40() -> None:
    profile = create_profile(
        interests=[
            "Reinforcement learning"
        ]
    )

    result = score_researcher_profile(
        profile,
        research_topic=(
            "Reinforcement learning"
        ),
        expanded_topics=[],
    )

    assert (
        result.breakdown.research_interests
        == 40
    )

    assert result.relevance_score == 40


def test_current_project_scores_25() -> None:
    project = create_item(
        name="Reinforcement Learning Project",
        target=SearchTarget.PROJECT,
        evidence=(
            "Jane Smith is currently leading "
            "the Reinforcement Learning Project."
        ),
    )

    profile = create_profile(
        current_projects=[project]
    )

    result = score_researcher_profile(
        profile,
        research_topic=(
            "Reinforcement learning"
        ),
        expanded_topics=[],
    )

    assert (
        result.breakdown.current_projects
        == 25
    )


def test_expanded_topic_receives_reduced_weight() -> None:
    profile = create_profile(
        interests=[
            "Time-series analysis"
        ]
    )

    result = score_researcher_profile(
        profile,
        research_topic="Robotics",
        expanded_topics=[
            "Time-series analysis"
        ],
    )

    assert (
        result.breakdown.research_interests
        == 36
    )


def test_unrelated_researcher_scores_zero() -> None:
    profile = create_profile(
        interests=[
            "Marine biology"
        ]
    )

    result = score_researcher_profile(
        profile,
        research_topic=(
            "Reinforcement learning"
        ),
        expanded_topics=[],
    )

    assert result.relevance_score == 0

    assert result.match_explanation == [
        (
            "No meaningful lexical overlap was "
            "found between the research topic "
            "and verified researcher evidence."
        )
    ]


def test_score_can_reach_100() -> None:
    topic = "Reinforcement learning"

    current_project = create_item(
        "Reinforcement learning project",
        SearchTarget.PROJECT,
        (
            "Current reinforcement learning "
            "research project."
        ),
    )

    previous_project = create_item(
        "Previous reinforcement learning project",
        SearchTarget.PROJECT,
        (
            "Previous reinforcement learning "
            "research project."
        ),
    )

    unknown_project = create_item(
        "Reinforcement learning study",
        SearchTarget.PROJECT,
        (
            "Reinforcement learning "
            "research study."
        ),
    )

    lab = create_item(
        "Reinforcement Learning Lab",
        SearchTarget.LAB,
        (
            "Research group specialising in "
            "reinforcement learning."
        ),
    )

    publication = create_item(
        "Advances in Reinforcement Learning",
        SearchTarget.PUBLICATION,
        (
            "Publication about "
            "reinforcement learning."
        ),
    )

    profile = create_profile(
        interests=[topic],
        current_projects=[
            current_project
        ],
        previous_projects=[
            previous_project
        ],
        unknown_projects=[
            unknown_project
        ],
        labs=[lab],
        publications=[
            publication
        ],
    )

    result = score_researcher_profile(
        profile,
        research_topic=topic,
        expanded_topics=[],
    )

    assert result.relevance_score == 100


def test_matched_terms_are_recorded() -> None:
    profile = create_profile(
        interests=[
            (
                "Reinforcement learning "
                "and time-series analysis"
            )
        ]
    )

    result = score_researcher_profile(
        profile,
        research_topic=(
            "Reinforcement learning "
            "for time-series data"
        ),
        expanded_topics=[],
    )

    assert "reinforcement" in (
        result.matched_terms
    )

    assert "learning" in (
        result.matched_terms
    )


def test_node_handles_no_profiles() -> None:
    result = nodes_module.score_relevance(
        {
            "organised_results": [],
        }
    )

    assert result["scored_results"] == []

    assert result["execution_log"] == [
        (
            "Relevance scoring completed: "
            "0 researchers scored."
        )
    ]


def test_node_scores_profiles() -> None:
    profile = create_profile(
        interests=[
            "Reinforcement learning"
        ]
    )

    request = SearchRequest(
        country="Australia",
        country_code="AU",
        state="Victoria",
        state_code="AU-VIC",
        research_topic=(
            "Reinforcement learning"
        ),
    )

    result = nodes_module.score_relevance(
        {
            "organised_results": [
                profile
            ],
            "request": request,
            "expanded_topics": [],
        }
    )

    assert len(
        result["scored_results"]
    ) == 1

    assert (
        result[
            "scored_results"
        ][0].relevance_score
        == 40
    )

    assert result["execution_log"] == [
        (
            "Relevance scoring completed: "
            "1 researchers scored."
        )
    ]