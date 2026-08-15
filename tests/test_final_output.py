from research_finder import (
    nodes as nodes_module,
)
from research_finder.models import (
    SearchRequest,
)
from research_finder.ranking import (
    RankedResearcherProfile,
)
from research_finder.relevance import (
    RelevanceScoreBreakdown,
    ScoredResearcherProfile,
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


def test_final_output_flattens_ranked_result() -> None:
    profile_url = (
        "https://www.deakin.edu.au/"
        "profile/jane-smith"
    )

    project = ResearchEvidenceItem(
        name="Adaptive RL Project",
        target=SearchTarget.PROJECT,
        source_url=(
            "https://www.deakin.edu.au/"
            "research/adaptive-rl"
        ),
        source_title="Adaptive RL Project",
        evidence_text=(
            "Jane Smith currently leads "
            "the Adaptive RL Project."
        ),
    )

    researcher = ResearcherCandidate(
        full_name="Jane Smith",
        academic_title="Professor",
        role="Professor of AI",
        research_interests=[
            "Reinforcement learning"
        ],
        profile_summary=(
            "Researcher in artificial "
            "intelligence."
        ),
        university_name=(
            "Deakin University"
        ),
        official_domain=(
            "deakin.edu.au"
        ),
        source_url=profile_url,
        source_title="Jane Smith",
        evidence_text=(
            "Professor Jane Smith "
            "researches AI."
        ),
    )

    enriched = EnrichedResearcherCandidate(
        researcher=researcher,
        public_email=(
            "jane.smith@deakin.edu.au"
        ),
        public_email_source_url=(
            profile_url
        ),
        labs=[],
        projects=[project],
        publications=[],
    )

    verified = VerifiedResearcherCandidate(
        candidate=enriched,
        affiliation_source_url=(
            profile_url
        ),
        verified_source_count=2,
    )

    organised = OrganisedResearcherProfile(
        verified_researcher=verified,
        research_interests=[
            "Reinforcement learning"
        ],
        current_projects=[
            project
        ],
        previous_projects=[],
        unknown_projects=[],
    )

    scored = ScoredResearcherProfile(
        profile=organised,
        relevance_score=65,
        breakdown=(
            RelevanceScoreBreakdown(
                research_interests=40,
                current_projects=25,
                publications=0,
                labs=0,
                previous_projects=0,
                unknown_projects=0,
            )
        ),
        matched_terms=[
            "reinforcement",
            "learning",
        ],
        match_explanation=[
            (
                "Research interests "
                "contributed 40/40 points."
            ),
            (
                "Current projects "
                "contributed 25/25 points."
            ),
        ],
    )

    ranked = RankedResearcherProfile(
        rank=1,
        result=scored,
    )

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

    result = (
        nodes_module.generate_final_output(
            {
                "request": request,
                "ranked_results": [
                    ranked
                ],
                "warnings": [],
                "errors": [],
            }
        )
    )

    response = result[
        "final_response"
    ]

    assert response is not None

    assert response[
        "result_count"
    ] == 1

    researcher_result = (
        response["results"][0]
    )

    assert (
        researcher_result[
            "rank"
        ]
        == 1
    )

    assert (
        researcher_result[
            "researcher_name"
        ]
        == "Jane Smith"
    )

    assert (
        researcher_result[
            "university_name"
        ]
        == "Deakin University"
    )

    assert (
        researcher_result[
            "relevance_score"
        ]
        == 65
    )

    assert (
        researcher_result[
            "current_projects"
        ][0]["name"]
        == "Adaptive RL Project"
    )

    assert (
        researcher_result[
            "public_email"
        ]
        == "jane.smith@deakin.edu.au"
    )

    assert (
        researcher_result[
            "verified"
        ]
        is True
    )