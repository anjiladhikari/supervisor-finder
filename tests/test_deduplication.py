from research_finder.deduplication import (
    canonical_source_url_key,
    deduplicate_scored_researchers,
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


def create_result(
    *,
    name: str = "Jane Smith",
    score: int = 80,
) -> ScoredResearcherProfile:
    profile_url = (
        "https://www.deakin.edu.au/"
        "profile/jane-smith"
    )

    candidate = ResearcherCandidate(
        full_name=name,
        academic_title="Professor",
        role="Professor",
        research_interests=[
            "Reinforcement learning"
        ],
        profile_summary=None,
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        source_url=profile_url,
        source_title=name,
        evidence_text=(
            f"{name} researches "
            "reinforcement learning."
        ),
    )

    verified = VerifiedResearcherCandidate(
        candidate=candidate,
        affiliation_source_url=profile_url,
        verified_source_count=1,
    )

    return ScoredResearcherProfile(
        verified_researcher=verified,
        relevance_score=score,
        keyword_score=score,
        semantic_score=score,
        matched_terms=[
            "reinforcement",
            "learning",
        ],
        match_explanation=[
            "Topic match."
        ],
    )


def test_canonical_url_removes_tracking() -> None:
    first = canonical_source_url_key(
        "https://www.deakin.edu.au/profile/jane-smith?utm_source=test"
    )

    second = canonical_source_url_key(
        "https://deakin.edu.au/profile/jane-smith"
    )

    assert first == second


def test_keeps_unique_researchers() -> None:
    first = create_result(
        name="Jane Smith"
    )

    second = create_result(
        name="John Smith"
    )

    result = deduplicate_scored_researchers(
        [first, second]
    )

    assert len(result) == 2


def test_removes_duplicate_researcher() -> None:
    first = create_result(
        name="Jane Smith",
        score=70,
    )

    second = create_result(
        name="Jane Smith",
        score=90,
    )

    result = deduplicate_scored_researchers(
        [first, second]
    )

    assert len(result) == 1
    assert result[0].relevance_score == 90


def test_name_prefix_is_ignored() -> None:
    first = create_result(
        name="Professor Jane Smith",
        score=70,
    )

    second = create_result(
        name="Jane Smith",
        score=90,
    )

    result = deduplicate_scored_researchers(
        [first, second]
    )

    assert len(result) == 1