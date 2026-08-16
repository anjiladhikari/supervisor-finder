from research_finder import nodes as nodes_module
from research_finder.models import SearchRequest
from research_finder.ranking import (
    rank_researcher_results,
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


def create_scored_result(
    *,
    name: str,
    relevance_score: int,
    keyword_score: int | None = None,
    semantic_score: int = 0,
    verified_source_count: int = 1,
) -> ScoredResearcherProfile:
    slug = name.casefold().replace(" ", "-")

    profile_url = (
        "https://www.deakin.edu.au/"
        f"profile/{slug}"
    )

    researcher = ResearcherCandidate(
        full_name=name,
        academic_title="Professor",
        role="Professor",
        research_interests=[
            "Reinforcement learning",
        ],
        profile_summary=None,
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        source_url=profile_url,
        source_title=name,
        evidence_text=(
            f"Professor {name} researches "
            "reinforcement learning."
        ),
    )

    verified = VerifiedResearcherCandidate(
        candidate=researcher,
        affiliation_source_url=profile_url,
        verified_source_count=verified_source_count,
    )

    return ScoredResearcherProfile(
        verified_researcher=verified,
        relevance_score=relevance_score,
        keyword_score=(
            relevance_score
            if keyword_score is None
            else keyword_score
        ),
        semantic_score=semantic_score,
        matched_terms=[
            "reinforcement",
            "learning",
        ],
        match_explanation=[
            "Topic match."
        ],
    )


def test_higher_score_ranks_first() -> None:
    weaker = create_scored_result(
        name="Researcher Two",
        relevance_score=60,
    )

    stronger = create_scored_result(
        name="Researcher One",
        relevance_score=90,
    )

    ranked = rank_researcher_results(
        [weaker, stronger],
        max_results=5,
    )

    assert ranked[0].result == stronger
    assert ranked[0].rank == 1


def test_zero_score_is_excluded() -> None:
    relevant = create_scored_result(
        name="Jane Smith",
        relevance_score=80,
    )

    irrelevant = create_scored_result(
        name="John Smith",
        relevance_score=0,
        keyword_score=0,
        semantic_score=0,
    )

    ranked = rank_researcher_results(
        [irrelevant, relevant],
        max_results=5,
    )

    assert len(ranked) == 1
    assert (
        ranked[0]
        .result
        .verified_researcher
        .candidate
        .full_name
        == "Jane Smith"
    )


def test_respects_max_results() -> None:
    results = [
        create_scored_result(
            name=f"Researcher {index}",
            relevance_score=80,
        )
        for index in range(5)
    ]

    ranked = rank_researcher_results(
        results,
        max_results=2,
    )

    assert len(ranked) == 2


def test_keyword_score_breaks_tie() -> None:
    first = create_scored_result(
        name="Jane Smith",
        relevance_score=70,
        keyword_score=90,
        semantic_score=20,
    )

    second = create_scored_result(
        name="John Smith",
        relevance_score=70,
        keyword_score=70,
        semantic_score=70,
    )

    ranked = rank_researcher_results(
        [second, first],
        max_results=5,
    )

    assert ranked[0].result == first


def test_semantic_score_breaks_tie() -> None:
    first = create_scored_result(
        name="Jane Smith",
        relevance_score=70,
        keyword_score=70,
        semantic_score=90,
    )

    second = create_scored_result(
        name="John Smith",
        relevance_score=70,
        keyword_score=70,
        semantic_score=50,
    )

    ranked = rank_researcher_results(
        [second, first],
        max_results=5,
    )

    assert ranked[0].result == first


def test_verified_sources_break_tie() -> None:
    first = create_scored_result(
        name="Jane Smith",
        relevance_score=70,
        keyword_score=70,
        semantic_score=50,
        verified_source_count=2,
    )

    second = create_scored_result(
        name="John Smith",
        relevance_score=70,
        keyword_score=70,
        semantic_score=50,
        verified_source_count=1,
    )

    ranked = rank_researcher_results(
        [second, first],
        max_results=5,
    )

    assert ranked[0].result == first


def test_empty_results_returns_empty() -> None:
    assert (
        rank_researcher_results(
            [],
            max_results=5,
        )
        == []
    )


def test_node_handles_no_results() -> None:
    request = SearchRequest(
        country="Australia",
        country_code="AU",
        state="Victoria",
        state_code="AU-VIC",
        research_topic="Reinforcement learning",
        max_results=5,
    )

    result = nodes_module.rank_results(
        {
            "request": request,
            "deduplicated_results": [],
        }
    )

    assert result["ranked_results"] == []


def test_node_ranks_results() -> None:
    request = SearchRequest(
        country="Australia",
        country_code="AU",
        state="Victoria",
        state_code="AU-VIC",
        research_topic="Reinforcement learning",
        max_results=5,
    )

    researcher = create_scored_result(
        name="Jane Smith",
        relevance_score=100,
        keyword_score=100,
        semantic_score=100,
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