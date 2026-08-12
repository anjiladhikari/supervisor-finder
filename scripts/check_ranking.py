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
)
from research_finder.researcher_extraction import (
    ResearcherCandidate,
)
from research_finder.verification import (
    VerifiedResearcherCandidate,
)


def create_result(
    name: str,
    interests: list[str],
):
    """Create one deterministic scoring example."""

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
        research_interests=interests,
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

    enriched = EnrichedResearcherCandidate(
        researcher=researcher,
        labs=[],
        projects=[],
        publications=[],
    )

    verified = VerifiedResearcherCandidate(
        candidate=enriched,
        affiliation_source_url=profile_url,
        verified_source_count=1,
    )

    profile = OrganisedResearcherProfile(
        verified_researcher=verified,
        research_interests=interests,
        current_projects=[],
        previous_projects=[],
        unknown_projects=[],
    )

    return score_researcher_profile(
        profile,
        research_topic=(
            "Reinforcement learning"
        ),
        expanded_topics=[
            "Time-series analysis"
        ],
    )


def main() -> None:
    """Run deterministic ranking check."""

    researchers = [
        create_result(
            "Jane Smith",
            [
                "Reinforcement learning"
            ],
        ),
        create_result(
            "John Brown",
            [
                "Time-series analysis"
            ],
        ),
        create_result(
            "Alice Green",
            [
                "Marine biology"
            ],
        ),
    ]

    print("Before ranking:")

    for result in researchers:
        researcher = (
            result.profile
            .verified_researcher
            .candidate
            .researcher
        )

        print(
            researcher.full_name,
            "-",
            result.relevance_score,
        )

    ranked = rank_researcher_results(
        researchers,
        max_results=5,
    )

    print()
    print("Final ranking:")

    for ranked_result in ranked:
        result = ranked_result.result

        researcher = (
            result.profile
            .verified_researcher
            .candidate
            .researcher
        )

        print(
            ranked_result.rank,
            researcher.full_name,
            "- Score:",
            result.relevance_score,
        )


if __name__ == "__main__":
    main()