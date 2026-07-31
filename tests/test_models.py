from datetime import date

import pytest
from pydantic import ValidationError

from research_finder.models import (
    AustralianState,
    EvidenceSource,
    ProjectStatus,
    Publication,
    RelevanceScore,
    ResearcherResult,
    ResearchProject,
    SearchRequest,
    SearchResponse,
    SourceType,
    VerificationStatus,
)

def test_search_request_normalize_input()-> None:
    request = SearchRequest(
        country=" austrlia ",
        state="vic",
      research_topic="  reinforcement   learning for time-series data  ",
    )
    assert request.country=="Australia"
    assert request.state==AustralianState.VICTORIA
    assert(
        request.research_topic== "reinforcement learning for time-series data"

    )
    assert request.max_result==5

def test_search_request_rejects_unsupported_country() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(
            country="United States",
            research_topic="Reinforcement learning",
        )

def test_search_request_rejects_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(
            country="Australia",
            research_topic="Reinforcement learning",
            unexpected_field="This must not be accepted",
        )

def test_relevance_score_calculates_total() -> None:
    score = RelevanceScore(
        topic_similarity=30,
        publication_relevance=20,
        current_project_relevance=20,
        lab_relevance=10,
        evidence_strength=15,
        information_recency=5,
    )

    assert score.total == 100


def test_valid_researcher_result() -> None:
    source = EvidenceSource(
        source_type=SourceType.UNIVERSITY_PROFILE,
        title="Official researcher profile",
        url="https://example.edu.au/researcher",
        supports_claims=[
            "Current university affiliation",
            "General research interests",
        ],
        evidence_summary="The university profile identifies the researcher.",
        is_official_university_source=True,
    )

    project = ResearchProject(
        name="Adaptive Sequential Decision Systems",
        status=ProjectStatus.CURRENT,
        description="Research involving sequential decision-making.",
        url="https://example.edu.au/project",
        start_year=2025,
    )

    publication = Publication(
        title="Reinforcement Learning for Early Time-Series Decisions",
        year=date.today().year,
        venue="Example Conference",
        url="https://example.edu.au/publication",
        relevance_reason=(
            "The publication directly combines reinforcement learning "
            "with early time-series decisions."
        ),
    )

    result = ResearcherResult(
        researcher_name="Example Researcher",
        university_name="Example University",
        lab_or_group_name="Example AI Laboratory",
        general_research_interests=[
            "Reinforcement learning",
            "Sequential decision-making",
        ],
        current_projects=[project],
        previous_projects=[],
        relevant_publications=[publication],
        match_explanation=(
            "The researcher has current project and publication evidence "
            "related to the requested topic."
        ),
        relevance_score=RelevanceScore(
            topic_similarity=29,
            publication_relevance=19,
            current_project_relevance=18,
            lab_relevance=8,
            evidence_strength=12,
            information_recency=5,
        ),
        official_profile_url="https://example.edu.au/researcher",
        lab_or_group_url="https://example.edu.au/lab",
        public_email="researcher@example.edu.au",
        current_affiliation_verified=True,
        verification_status=VerificationStatus.VERIFIED,
        verification_notes=["Affiliation confirmed on the university profile."],
        sources=[source],
    )

    response = SearchResponse(
        request=SearchRequest(
            country="Australia",
            state="Victoria",
            research_topic=(
                "Reinforcement learning for early time-series classification"
            ),
        ),
        results=[result],
    )

    assert response.result_count == 1
    assert response.results[0].relevance_score.total == 91
    assert response.results[0].current_affiliation_verified is True

    json_data = response.model_dump(mode="json")

    assert json_data["result_count"] == 1
    assert json_data["results"][0]["public_email"] == (
        "researcher@example.edu.au"
    )


def test_current_project_rejects_previous_status() -> None:
    source = EvidenceSource(
        source_type=SourceType.UNIVERSITY_PROFILE,
        title="Official profile",
        url="https://example.edu.au/profile",
        supports_claims=["Current affiliation"],
        is_official_university_source=True,
    )

    incorrectly_categorised_project = ResearchProject(
        name="Previous Research Project",
        status=ProjectStatus.PREVIOUS,
    )

    with pytest.raises(ValidationError):
        ResearcherResult(
            researcher_name="Example Researcher",
            university_name="Example University",
            current_projects=[incorrectly_categorised_project],
            match_explanation=(
                "This explanation is long enough to satisfy validation."
            ),
            relevance_score=RelevanceScore(
                topic_similarity=10,
                publication_relevance=0,
                current_project_relevance=0,
                lab_relevance=0,
                evidence_strength=5,
                information_recency=1,
            ),
            current_affiliation_verified=False,
            verification_status=VerificationStatus.PARTIALLY_VERIFIED,
            sources=[source],
        )