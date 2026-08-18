from research_finder import nodes as nodes_module
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


def create_researcher() -> ResearcherCandidate:
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


def create_profile_document(
    *,
    target: SearchTarget = (
        SearchTarget.RESEARCHER
    ),
) -> DownloadedWebPage:
    return DownloadedWebPage(
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        target=target,
        source_url=PROFILE_URL,
        final_url=PROFILE_URL,
        page_title="Jane Smith",
        content=(
            "Professor Jane Smith is a Professor "
            "of Artificial Intelligence."
        ),
        content_type="text/html",
        status_code=200,
    )


def test_verifies_official_researcher() -> None:
    outcome = verify_researcher_candidates(
        candidates=[
            create_researcher()
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

    verified = (
        outcome.verified_candidates[0]
    )

    assert (
        verified.candidate.full_name
        == "Jane Smith"
    )


def test_rejects_missing_profile_evidence() -> None:
    outcome = verify_researcher_candidates(
        candidates=[
            create_researcher()
        ],
        documents=[],
    )

    assert outcome.rejected_candidates == 1
    assert (
        outcome.verified_candidates
        == ()
    )


def test_records_profile_source() -> None:
    outcome = verify_researcher_candidates(
        candidates=[
            create_researcher()
        ],
        documents=[
            create_profile_document()
        ],
    )

    verified = (
        outcome.verified_candidates[0]
    )

    assert (
        verified.verified_source_count
        == 1
    )


def test_node_handles_no_candidates() -> None:
    result = (
        nodes_module.verify_current_affiliation(
            {
                "extracted_candidates": [],
            }
        )
    )

    assert result[
        "verified_results"
    ] == []

    assert result["execution_log"] == [
        (
            "Researcher verification completed: "
            "0 candidates checked, "
            "0 verified."
        )
    ]