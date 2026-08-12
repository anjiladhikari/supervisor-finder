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


def main() -> None:
    """Run deterministic relevance scoring."""

    profile_url = (
        "https://www.deakin.edu.au/"
        "profile/jane-smith"
    )

    project_url = (
        "https://www.deakin.edu.au/"
        "research/project"
    )

    researcher = ResearcherCandidate(
        full_name="Jane Smith",
        academic_title="Professor",
        role=(
            "Professor of Artificial Intelligence"
        ),
        research_interests=[
            "Reinforcement learning",
            "Time-series analysis",
        ],
        profile_summary=None,
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        source_url=profile_url,
        source_title="Jane Smith",
        evidence_text=(
            "Professor Jane Smith researches "
            "artificial intelligence."
        ),
    )

    current_project = ResearchEvidenceItem(
        name=(
            "Reinforcement Learning "
            "for Time-Series Project"
        ),
        target=SearchTarget.PROJECT,
        source_url=project_url,
        source_title="Research Project",
        evidence_text=(
            "Jane Smith is currently leading "
            "a reinforcement learning project "
            "for time-series data."
        ),
    )

    publication = ResearchEvidenceItem(
        name=(
            "Deep Reinforcement Learning "
            "for Sequential Data"
        ),
        target=SearchTarget.PUBLICATION,
        publication_year=2025,
        source_url=project_url,
        source_title="Publication",
        evidence_text=(
            "Deep reinforcement learning "
            "for sequential data."
        ),
    )

    enriched = EnrichedResearcherCandidate(
        researcher=researcher,
        labs=[],
        projects=[
            current_project
        ],
        publications=[
            publication
        ],
    )

    verified = VerifiedResearcherCandidate(
        candidate=enriched,
        affiliation_source_url=profile_url,
        verified_source_count=2,
    )

    profile = OrganisedResearcherProfile(
        verified_researcher=verified,
        research_interests=[
            "Reinforcement learning",
            "Time-series analysis",
        ],
        current_projects=[
            current_project
        ],
        previous_projects=[],
        unknown_projects=[],
    )

    result = score_researcher_profile(
        profile,
        research_topic=(
            "Reinforcement learning "
            "for time-series data"
        ),
        expanded_topics=[
            "Reinforcement learning",
            "Time-series analysis",
        ],
    )

    print(
        "Researcher:",
        result.profile
        .verified_researcher
        .candidate
        .researcher
        .full_name,
    )

    print(
        "Score:",
        result.relevance_score,
    )

    print(
        "Matched terms:",
        result.matched_terms,
    )

    print()
    print("Breakdown:")

    print(
        "Research interests:",
        result.breakdown.research_interests,
        "/ 40",
    )

    print(
        "Current projects:",
        result.breakdown.current_projects,
        "/ 25",
    )

    print(
        "Publications:",
        result.breakdown.publications,
        "/ 15",
    )

    print(
        "Labs:",
        result.breakdown.labs,
        "/ 10",
    )

    print(
        "Previous projects:",
        result.breakdown.previous_projects,
        "/ 5",
    )

    print(
        "Unknown projects:",
        result.breakdown.unknown_projects,
        "/ 5",
    )

    print()
    print("Explanation:")

    for line in result.match_explanation:
        print("-", line)


if __name__ == "__main__":
    main()