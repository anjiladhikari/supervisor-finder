import pytest

from research_finder import nodes as nodes_module
from research_finder.researcher_details import (
    ResearcherDetailBatch,
    ResearcherDetailDraft,
    enrich_researcher_candidates,
    extract_details_from_document,
    extract_researcher_detail_documents,
)
from research_finder.researcher_extraction import (
    ResearcherCandidate,
)
from research_finder.search_queries import (
    SearchTarget,
)
from research_finder.web_content import (
    DownloadedWebPage,
)


def create_candidate() -> ResearcherCandidate:
    """Create one researcher candidate."""

    return ResearcherCandidate(
        full_name="Jane Smith",
        academic_title="Professor",
        role="Professor of Artificial Intelligence",
        research_interests=[
            "Reinforcement learning"
        ],
        profile_summary=(
            "Artificial intelligence researcher."
        ),
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        source_url=(
            "https://www.deakin.edu.au/"
            "profile/jane-smith"
        ),
        source_title="Jane Smith",
        evidence_text=(
            "Professor Jane Smith is a Professor "
            "of Artificial Intelligence."
        ),
    )


def create_document(
    target: SearchTarget,
    content: str,
) -> DownloadedWebPage:
    """Create a supporting university document."""

    return DownloadedWebPage(
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        target=target,
        source_url=(
            "https://www.deakin.edu.au/"
            f"research/{target.value}"
        ),
        final_url=(
            "https://www.deakin.edu.au/"
            f"research/{target.value}"
        ),
        page_title=(
            f"{target.value.title()} page"
        ),
        content=content,
        content_type="text/html",
        status_code=200,
    )


class FakeStructuredModel:
    """Return one controlled response."""

    def __init__(
        self,
        response: object,
    ) -> None:
        self.response = response

    def invoke(self, _: object) -> object:
        if isinstance(
            self.response,
            Exception,
        ):
            raise self.response

        return self.response


class FakeChatModel:
    """Provide structured responses without an API."""

    def __init__(
        self,
        responses: list[object],
    ) -> None:
        self.responses = responses

    def with_structured_output(
        self,
        _: object,
        **__: object,
    ) -> FakeStructuredModel:
        return FakeStructuredModel(
            self.responses.pop(0)
        )


def test_extracts_official_email() -> None:
    evidence = (
        "Jane Smith can be contacted at "
        "jane.smith@deakin.edu.au."
    )

    batch = ResearcherDetailBatch(
        details=[
            ResearcherDetailDraft(
                researcher_name="Jane Smith",
                public_email=(
                    "jane.smith@deakin.edu.au"
                ),
                evidence_text=evidence,
            )
        ]
    )

    associations = extract_details_from_document(
        document=create_document(
            SearchTarget.RESEARCHER,
            evidence,
        ),
        candidates=[create_candidate()],
        model=FakeChatModel([batch]),
    )

    assert len(associations) == 1
    assert str(
        associations[0].public_email
    ) == "jane.smith@deakin.edu.au"


def test_rejects_external_email() -> None:
    evidence = (
        "Jane Smith can be contacted at "
        "jane@gmail.com."
    )

    batch = ResearcherDetailBatch(
        details=[
            ResearcherDetailDraft(
                researcher_name="Jane Smith",
                public_email="jane@gmail.com",
                evidence_text=evidence,
            )
        ]
    )

    associations = extract_details_from_document(
        document=create_document(
            SearchTarget.RESEARCHER,
            evidence,
        ),
        candidates=[create_candidate()],
        model=FakeChatModel([batch]),
    )

    assert associations == []


def test_extracts_lab_association() -> None:
    evidence = (
        "Jane Smith is a member of the "
        "Centre for AI Research."
    )

    batch = ResearcherDetailBatch(
        details=[
            ResearcherDetailDraft(
                researcher_name="Jane Smith",
                item_name="Centre for AI Research",
                evidence_text=evidence,
            )
        ]
    )

    associations = extract_details_from_document(
        document=create_document(
            SearchTarget.LAB,
            evidence,
        ),
        candidates=[create_candidate()],
        model=FakeChatModel([batch]),
    )

    assert len(associations) == 1
    assert associations[0].item_name == (
        "Centre for AI Research"
    )


def test_rejects_unsupported_evidence() -> None:
    batch = ResearcherDetailBatch(
        details=[
            ResearcherDetailDraft(
                researcher_name="Jane Smith",
                item_name="Fake Research Lab",
                evidence_text=(
                    "This text does not exist "
                    "on the webpage."
                ),
            )
        ]
    )

    associations = extract_details_from_document(
        document=create_document(
            SearchTarget.LAB,
            (
                "Jane Smith works in artificial "
                "intelligence research."
            ),
        ),
        candidates=[create_candidate()],
        model=FakeChatModel([batch]),
    )

    assert associations == []


def test_enriches_candidate_with_all_details() -> None:
    candidate = create_candidate()

    documents = [
        create_document(
            SearchTarget.RESEARCHER,
            (
                "Jane Smith email "
                "jane.smith@deakin.edu.au."
            ),
        ),
        create_document(
            SearchTarget.LAB,
            (
                "Jane Smith is a member of the "
                "Centre for AI Research."
            ),
        ),
        create_document(
            SearchTarget.PROJECT,
            (
                "Jane Smith leads the "
                "Adaptive Learning Project."
            ),
        ),
        create_document(
            SearchTarget.PUBLICATION,
            (
                "Jane Smith authored "
                "Learning from Time Series in 2025."
            ),
        ),
    ]

    responses = [
        ResearcherDetailBatch(
            details=[
                ResearcherDetailDraft(
                    researcher_name="Jane Smith",
                    public_email=(
                        "jane.smith@deakin.edu.au"
                    ),
                    evidence_text=documents[0].content,
                )
            ]
        ),
        ResearcherDetailBatch(
            details=[
                ResearcherDetailDraft(
                    researcher_name="Jane Smith",
                    item_name=(
                        "Centre for AI Research"
                    ),
                    evidence_text=documents[1].content,
                )
            ]
        ),
        ResearcherDetailBatch(
            details=[
                ResearcherDetailDraft(
                    researcher_name="Jane Smith",
                    item_name=(
                        "Adaptive Learning Project"
                    ),
                    evidence_text=documents[2].content,
                )
            ]
        ),
        ResearcherDetailBatch(
            details=[
                ResearcherDetailDraft(
                    researcher_name="Jane Smith",
                    item_name=(
                        "Learning from Time Series"
                    ),
                    publication_year=2025,
                    evidence_text=documents[3].content,
                )
            ]
        ),
    ]

    outcome = (
        extract_researcher_detail_documents(
            documents=documents,
            candidates=[candidate],
            model=FakeChatModel(responses),
        )
    )

    enriched = enrich_researcher_candidates(
        candidates=[candidate],
        associations=list(
            outcome.associations
        ),
    )

    assert len(enriched) == 1

    researcher = enriched[0]

    assert str(
        researcher.public_email
    ) == "jane.smith@deakin.edu.au"

    assert len(researcher.labs) == 1
    assert len(researcher.projects) == 1
    assert len(researcher.publications) == 1

    assert (
        researcher.publications[0]
        .publication_year
        == 2025
    )


def test_batch_continues_after_failure() -> None:
    documents = [
        create_document(
            SearchTarget.LAB,
            "First page.",
        ),
        create_document(
            SearchTarget.LAB,
            (
                "Jane Smith is a member of "
                "AI Research Lab."
            ),
        ),
    ]

    valid_batch = ResearcherDetailBatch(
        details=[
            ResearcherDetailDraft(
                researcher_name="Jane Smith",
                item_name="AI Research Lab",
                evidence_text=documents[1].content,
            )
        ]
    )

    model = FakeChatModel(
        [
            RuntimeError(
                "Simulated failure"
            ),
            valid_batch,
        ]
    )

    outcome = (
        extract_researcher_detail_documents(
            documents=documents,
            candidates=[create_candidate()],
            model=model,
        )
    )

    assert outcome.attempted_documents == 2
    assert outcome.failed_documents == 1
    assert len(outcome.associations) == 1


def test_node_handles_missing_candidates() -> None:
    result = (
        nodes_module.extract_researcher_details(
            {
                "extracted_candidates": [],
            }
        )
    )

    assert result["enriched_candidates"] == []

    assert result["execution_log"] == [
        (
            "Researcher detail extraction completed: "
            "0 documents processed, "
            "0 researchers enriched."
        )
    ]


def test_node_stores_enriched_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = create_candidate()

    evidence = (
        "Jane Smith can be contacted at "
        "jane.smith@deakin.edu.au."
    )

    batch = ResearcherDetailBatch(
        details=[
            ResearcherDetailDraft(
                researcher_name="Jane Smith",
                public_email=(
                    "jane.smith@deakin.edu.au"
                ),
                evidence_text=evidence,
            )
        ]
    )

    monkeypatch.setattr(
        nodes_module,
        "create_chat_model",
        lambda: FakeChatModel([batch]),
    )

    result = (
        nodes_module.extract_researcher_details(
            {
                "extracted_candidates": [
                    candidate
                ],
                "researcher_documents": [
                    create_document(
                        SearchTarget.RESEARCHER,
                        evidence,
                    )
                ],
                "lab_documents": [],
                "project_documents": [],
                "publication_documents": [],
            }
        )
    )

    assert len(
        result["enriched_candidates"]
    ) == 1

    assert str(
        result[
            "enriched_candidates"
        ][0].public_email
    ) == "jane.smith@deakin.edu.au"