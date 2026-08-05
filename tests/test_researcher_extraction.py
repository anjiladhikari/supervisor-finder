import pytest

from research_finder import nodes as nodes_module
from research_finder.researcher_extraction import (
    ResearcherCandidate,
    ResearcherExtractionBatch,
    ResearcherExtractionDraft,
    extract_researcher_documents,
    extract_researchers_from_document,
)
from research_finder.search_queries import (
    SearchTarget,
)
from research_finder.web_content import (
    DownloadedWebPage,
)


def create_document(
    content: str = (
        "Professor Jane Smith is a Professor of "
        "Artificial Intelligence. Her research "
        "interests include reinforcement learning "
        "and time-series analysis."
    ),
) -> DownloadedWebPage:
    """Create one downloaded researcher page."""

    return DownloadedWebPage(
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        target=SearchTarget.RESEARCHER,
        source_url=(
            "https://www.deakin.edu.au/"
            "research/profile/jane-smith"
        ),
        final_url=(
            "https://www.deakin.edu.au/"
            "research/profile/jane-smith"
        ),
        page_title="Professor Jane Smith",
        content=content,
        content_type="text/html",
        status_code=200,
    )


def create_batch(
    evidence_text: str,
) -> ResearcherExtractionBatch:
    """Create one controlled structured response."""

    return ResearcherExtractionBatch(
        researchers=[
            ResearcherExtractionDraft(
                full_name="Jane Smith",
                academic_title="Professor",
                role=(
                    "Professor of "
                    "Artificial Intelligence"
                ),
                research_interests=[
                    "Reinforcement learning",
                    "Time-series analysis",
                ],
                profile_summary=(
                    "Researcher in artificial "
                    "intelligence."
                ),
                evidence_text=evidence_text,
            )
        ]
    )


class FakeStructuredModel:
    """Return one controlled extraction response."""

    def __init__(
        self,
        response: object,
    ) -> None:
        self.response = response

    def invoke(self, _: object) -> object:
        if isinstance(self.response, Exception):
            raise self.response

        return self.response


class FakeChatModel:
    """Provide structured output without an API."""

    def __init__(
        self,
        response: object,
    ) -> None:
        self.response = response

    def with_structured_output(
        self,
        _: object,
        **__: object,
    ) -> FakeStructuredModel:
        return FakeStructuredModel(
            self.response
        )


def test_extracts_grounded_researcher() -> None:
    evidence = (
        "Professor Jane Smith is a Professor of "
        "Artificial Intelligence."
    )

    candidates = extract_researchers_from_document(
        document=create_document(),
        model=FakeChatModel(
            create_batch(evidence)
        ),
    )

    assert len(candidates) == 1

    candidate = candidates[0]

    assert isinstance(
        candidate,
        ResearcherCandidate,
    )
    assert candidate.full_name == "Jane Smith"
    assert candidate.university_name == (
        "Deakin University"
    )
    assert candidate.research_interests == [
        "Reinforcement learning",
        "Time-series analysis",
    ]


def test_rejects_unsupported_evidence() -> None:
    candidates = extract_researchers_from_document(
        document=create_document(),
        model=FakeChatModel(
            create_batch(
                "This sentence is not on the webpage."
            )
        ),
    )

    assert candidates == []


def test_accepts_dictionary_response() -> None:
    evidence = (
        "Professor Jane Smith is a Professor of "
        "Artificial Intelligence."
    )

    candidates = extract_researchers_from_document(
        document=create_document(),
        model=FakeChatModel(
            create_batch(
                evidence
            ).model_dump()
        ),
    )

    assert len(candidates) == 1


def test_batch_continues_after_failure() -> None:
    class MixedModel:
        def __init__(self) -> None:
            self.calls = 0

        def with_structured_output(
            self,
            _: object,
            **__: object,
        ) -> FakeStructuredModel:
            self.calls += 1

            if self.calls == 1:
                return FakeStructuredModel(
                    RuntimeError(
                        "Simulated failure"
                    )
                )

            evidence = (
                "Professor Jane Smith is a "
                "Professor of Artificial Intelligence."
            )

            return FakeStructuredModel(
                create_batch(evidence)
            )

    outcome = extract_researcher_documents(
        documents=[
            create_document(),
            create_document(),
        ],
        model=MixedModel(),
    )

    assert outcome.attempted_documents == 2
    assert outcome.failed_documents == 1
    assert len(outcome.candidates) == 1


def test_node_stores_extracted_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = (
        "Professor Jane Smith is a Professor of "
        "Artificial Intelligence."
    )

    monkeypatch.setattr(
        nodes_module,
        "create_chat_model",
        lambda: FakeChatModel(
            create_batch(evidence)
        ),
    )

    result = (
        nodes_module.extract_researcher_information(
            {
                "researcher_documents": [
                    create_document()
                ]
            }
        )
    )

    assert len(
        result["extracted_candidates"]
    ) == 1

    assert result["execution_log"] == [
        (
            "Researcher extraction completed: "
            "1 documents processed, "
            "1 candidates created."
        )
    ]


def test_node_handles_missing_documents() -> None:
    result = (
        nodes_module.extract_researcher_information(
            {
                "researcher_documents": []
            }
        )
    )

    assert result["extracted_candidates"] == []

    assert result["execution_log"] == [
        (
            "Researcher extraction completed: "
            "0 documents processed, "
            "0 candidates created."
        )
    ]