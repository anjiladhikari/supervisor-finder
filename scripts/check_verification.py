from research_finder.researcher_details import (
    EnrichedResearcherCandidate,
)
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


def main() -> None:
    """Run deterministic verification check."""

    url = (
        "https://www.deakin.edu.au/"
        "profile/jane-smith"
    )

    evidence = (
        "Professor Jane Smith is a Professor "
        "of Artificial Intelligence."
    )

    researcher = ResearcherCandidate(
        full_name="Jane Smith",
        academic_title="Professor",
        role=(
            "Professor of Artificial Intelligence"
        ),
        research_interests=[
            "Reinforcement learning"
        ],
        profile_summary=None,
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        source_url=url,
        source_title="Jane Smith",
        evidence_text=evidence,
    )

    enriched = EnrichedResearcherCandidate(
        researcher=researcher,
        public_email=(
            "jane.smith@deakin.edu.au"
        ),
        public_email_source_url=url,
        labs=[],
        projects=[],
        publications=[],
    )

    document = DownloadedWebPage(
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        target=SearchTarget.RESEARCHER,
        source_url=url,
        final_url=url,
        page_title="Jane Smith",
        content=(
            f"{evidence} "
            "Contact jane.smith@deakin.edu.au."
        ),
        content_type="text/html",
        status_code=200,
    )

    outcome = verify_researcher_candidates(
        candidates=[enriched],
        documents=[document],
    )

    print(
        "Candidates checked:",
        outcome.attempted_candidates,
    )

    print(
        "Candidates verified:",
        len(outcome.verified_candidates),
    )

    print(
        "Rejected:",
        outcome.rejected_candidates,
    )

    print(
        "Discarded claims:",
        outcome.discarded_claims,
    )

    if outcome.verified_candidates:
        verified = (
            outcome.verified_candidates[0]
        )

        print(
            "Researcher:",
            verified.candidate.researcher.full_name,
        )

        print(
            "Email:",
            verified.candidate.public_email,
        )

        print(
            "Sources:",
            verified.verified_source_count,
        )

        print(
            "Verified at:",
            verified.verified_at,
        )


if __name__ == "__main__":
    main()