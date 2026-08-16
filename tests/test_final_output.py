from research_finder import nodes as nodes_module
from research_finder.models import SearchRequest
from research_finder.ranking import (
    RankedResearcherProfile,
)
from research_finder.relevance import (
    ScoredResearcherProfile,
)
from research_finder.researcher_extraction import (
    ResearcherCandidate,
)
from research_finder.verification import (
    VerifiedResearcherCandidate,
)


PROFILE_URL = (
    "https://www.deakin.edu.au/"
    "profile/jane-smith"
)


def create_ranked_result(
) -> RankedResearcherProfile:
    researcher = ResearcherCandidate(
        full_name="Jane Smith",
        academic_title="Professor",
        role=(
            "Professor of "
            "Artificial Intelligence"
        ),
        research_interests=[
            "Reinforcement learning",
            "Machine learning",
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
        source_url=PROFILE_URL,
        source_title=(
            "Professor Jane Smith"
        ),
        evidence_text=(
            "Professor Jane Smith "
            "researches reinforcement "
            "learning."
        ),
    )

    verified = (
        VerifiedResearcherCandidate(
            candidate=researcher,
            affiliation_source_url=(
                PROFILE_URL
            ),
            verified_source_count=1,
        )
    )

    scored = ScoredResearcherProfile(
        verified_researcher=verified,
        relevance_score=85,
        keyword_score=100,
        semantic_score=50,
        matched_terms=[
            "reinforcement",
            "learning",
        ],
        match_explanation=[
            (
                "Direct topic match: "
                "100/100."
            ),
            (
                "Semantic related-topic "
                "match: 50/100."
            ),
        ],
    )

    return RankedResearcherProfile(
        rank=1,
        result=scored,
    )


def test_generates_final_response() -> None:
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
                    create_ranked_result()
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

    assert len(
        response["results"]
    ) == 1

    item = response[
        "results"
    ][0]

    assert (
        item["researcher_name"]
        == "Jane Smith"
    )

    assert (
        item["university_name"]
        == "Deakin University"
    )

    assert (
        item["research_interests"]
        == [
            "Reinforcement learning",
            "Machine learning",
        ]
    )

    assert (
        item["relevance_score"]
        == 85
    )

    assert (
        item["keyword_score"]
        == 100
    )

    assert (
        item["semantic_score"]
        == 50
    )

    assert (
        item["official_profile_url"]
        == PROFILE_URL
    )

    assert item["verified"] is True