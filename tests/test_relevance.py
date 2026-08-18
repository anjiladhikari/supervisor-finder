from research_finder import nodes as nodes_module
from research_finder.models import SearchRequest
from research_finder.relevance import (
    score_researcher_profile,
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


def create_verified(
    interests: list[str],
) -> VerifiedResearcherCandidate:
    researcher = ResearcherCandidate(
        full_name="Jane Smith",
        academic_title="Professor",
        role="Professor of Artificial Intelligence",
        research_interests=interests,
        profile_summary=None,
        profile_state="Victoria",
        profile_country="Australia",
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        source_url=PROFILE_URL,
        source_title="Jane Smith",
        evidence_text=(
            "Professor Jane Smith is a researcher."
        ),
    )

    return VerifiedResearcherCandidate(
        candidate=researcher,
        affiliation_source_url=PROFILE_URL,
        verified_source_count=1,
    )


def test_exact_topic_match_scores_70() -> None:
    verified = create_verified(
        ["Reinforcement learning"]
    )

    result = score_researcher_profile(
        verified,
        research_topic="Reinforcement learning",
        expanded_topics=[],
    )

    assert result.keyword_score == 100
    assert result.semantic_score == 0
    assert result.relevance_score == 70


def test_direct_and_related_match_scores_100() -> None:
    verified = create_verified(
        [
            "Reinforcement learning",
            "Artificial intelligence",
        ]
    )

    result = score_researcher_profile(
        verified,
        research_topic="Reinforcement learning",
        expanded_topics=[
            "Artificial intelligence",
        ],
    )

    assert result.keyword_score == 100
    assert result.semantic_score == 100
    assert result.relevance_score == 100


def test_unrelated_researcher_scores_zero() -> None:
    verified = create_verified(
        ["Marine biology"]
    )

    result = score_researcher_profile(
        verified,
        research_topic="Reinforcement learning",
        expanded_topics=[
            "Artificial intelligence",
        ],
    )

    assert result.relevance_score == 0


def test_matched_terms_are_recorded() -> None:
    verified = create_verified(
        [
            "Reinforcement learning "
            "and time-series analysis"
        ]
    )

    result = score_researcher_profile(
        verified,
        research_topic=(
            "Reinforcement learning"
        ),
        expanded_topics=[],
    )

    assert "reinforcement" in result.matched_terms
    assert "learning" in result.matched_terms


def test_node_handles_no_verified_results() -> None:
    result = nodes_module.score_relevance(
        {
            "verified_results": [],
        }
    )

    assert result["scored_results"] == []


def test_node_scores_verified_researcher() -> None:
    verified = create_verified(
        ["Reinforcement learning"]
    )

    request = SearchRequest(
        country="Australia",
        country_code="AU",
        state="Victoria",
        state_code="AU-VIC",
        research_topic="Reinforcement learning",
    )

    result = nodes_module.score_relevance(
        {
            "verified_results": [
                verified,
            ],
            "request": request,
            "expanded_topics": [],
        }
    )

    assert len(
        result["scored_results"]
    ) == 1

    assert (
        result["scored_results"][0]
        .relevance_score
        == 70
    )