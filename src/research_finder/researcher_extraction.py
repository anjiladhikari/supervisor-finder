from __future__ import annotations

import logging
from dataclasses import dataclass

from langchain_core.language_models.chat_models import (
    BaseChatModel,
)
from pydantic import (
    Field,
    HttpUrl,
    field_validator,
)

from research_finder.models import StrictModel
from research_finder.web_content import (
    DownloadedWebPage,
)

logger = logging.getLogger(__name__)
class ResearcherExtractionDraft(StrictModel):
    """One researcher extracted by the LLM."""

    full_name: str = Field(
        min_length=2,
        max_length=200,
    )
    academic_title: str | None = Field(
        default=None,
        max_length=150,
    )
    role: str | None = Field(
        default=None,
        max_length=200,
    )
    research_interests: list[str] = Field(
        default_factory=list,
        max_length=15,
    )
    profile_summary: str | None = Field(
        default=None,
        max_length=1000,
    )
    evidence_text: str = Field(
        min_length=5,
        max_length=500,
        description=("An exact continuous excerpt copied from the supplied webpage."),
    )

    @field_validator(
        "full_name",
        "academic_title",
        "role",
        "profile_summary",
        "evidence_text",
        mode="before",
    )
    @classmethod
    def normalise_text(
        cls,
        value: object,
    ) -> object:
        """Collapse repeated whitespace."""

        if isinstance(value, str):
            cleaned = " ".join(value.split())

            if not cleaned:
                return None

            return cleaned

        return value

    @field_validator(
        "research_interests",
        mode="before",
    )
    @classmethod
    def normalise_interests(
        cls,
        value: object,
    ) -> object:
        """Clean and deduplicate research interests."""

        if not isinstance(value, list):
            return value

        interests: list[str] = []
        seen: set[str] = set()

        for item in value:
            if not isinstance(item, str):
                continue

            cleaned = " ".join(item.split())

            if not cleaned:
                continue

            comparison_key = cleaned.casefold()

            if comparison_key in seen:
                continue

            seen.add(comparison_key)
            interests.append(cleaned)

        return interests


class ResearcherExtractionBatch(StrictModel):
    """Researchers extracted from one webpage."""

    researchers: list[ResearcherExtractionDraft] = Field(
        default_factory=list,
        max_length=20,
    )


class ResearcherCandidate(StrictModel):
    """Grounded researcher candidate stored in graph state."""

    full_name: str = Field(
        min_length=2,
        max_length=200,
    )
    academic_title: str | None = Field(
        default=None,
        max_length=150,
    )
    role: str | None = Field(
        default=None,
        max_length=200,
    )
    research_interests: list[str] = Field(
        default_factory=list,
        max_length=15,
    )
    profile_summary: str | None = Field(
        default=None,
        max_length=1000,
    )

    university_name: str = Field(
        min_length=2,
        max_length=200,
    )
    official_domain: str = Field(
        min_length=4,
        max_length=255,
    )
    source_url: HttpUrl
    source_title: str = Field(
        min_length=1,
        max_length=500,
    )
    evidence_text: str = Field(
        min_length=5,
        max_length=500,
    )


@dataclass(frozen=True)
class ResearcherExtractionOutcome:
    """Result of processing researcher documents."""

    candidates: tuple[ResearcherCandidate, ...]
    attempted_documents: int
    failed_documents: int


_RESEARCHER_EXTRACTION_SYSTEM_PROMPT = """
Extract academic researchers from official university webpage text.

Rules:

1. Include only explicitly named academic or research staff.
2. Include professors, lecturers, research fellows and research academics.
3. Exclude students, administrative staff and unrelated people.
4. Do not invent names, roles, titles or research interests.
5. Use only information explicitly present in the supplied content.
6. If the page contains no researcher information, return an empty list.
7. evidence_text must be an exact continuous excerpt copied from the page.
8. Keep research interests short and specific.
9. Do not extract projects, publications, laboratories or email addresses.
10. Do not treat names in navigation menus or unrelated lists as researchers.
""".strip()


def _normalise_for_matching(value: str) -> str:
    """Normalise text for evidence comparison."""

    return " ".join(value.split()).casefold()


def build_researcher_extraction_messages(
    document: DownloadedWebPage,
    *,
    max_content_characters: int = 12_000,
) -> list[tuple[str, str]]:
    """Create structured researcher-extraction messages."""

    content = document.content[:max_content_characters]

    user_prompt = f"""
University: {document.university_name}
Official domain: {document.official_domain}
Page title: {document.page_title}
Page URL: {document.final_url}

Official webpage content:

{content}
""".strip()

    return [
        (
            "system",
            _RESEARCHER_EXTRACTION_SYSTEM_PROMPT,
        ),
        ("human", user_prompt),
    ]


def extract_researchers_from_document(
    document: DownloadedWebPage,
    model: BaseChatModel,
) -> list[ResearcherCandidate]:
    """Extract grounded candidates from one document."""

    structured_model = model.with_structured_output(
        ResearcherExtractionBatch,
        method="json_schema",
    )

    raw_response = structured_model.invoke(build_researcher_extraction_messages(document))

    if isinstance(
        raw_response,
        ResearcherExtractionBatch,
    ):
        batch = raw_response
    else:
        batch = ResearcherExtractionBatch.model_validate(raw_response)

    normalised_content = _normalise_for_matching(document.content)

    candidates: list[ResearcherCandidate] = []
    seen_names: set[str] = set()

    for researcher in batch.researchers:
        evidence_key = _normalise_for_matching(researcher.evidence_text)

        if evidence_key not in normalised_content:
            continue

        name_key = researcher.full_name.casefold()

        if name_key in seen_names:
            continue

        seen_names.add(name_key)

        candidates.append(
            ResearcherCandidate(
                full_name=researcher.full_name,
                academic_title=(researcher.academic_title),
                role=researcher.role,
                research_interests=(researcher.research_interests),
                profile_summary=(researcher.profile_summary),
                university_name=(document.university_name),
                official_domain=(document.official_domain),
                source_url=document.final_url,
                source_title=document.page_title,
                evidence_text=(researcher.evidence_text),
            )
        )

    return candidates


def extract_researcher_documents(
    documents: list[DownloadedWebPage],
    model: BaseChatModel,
) -> ResearcherExtractionOutcome:
    """Extract candidates while allowing document failures."""

    candidates: list[ResearcherCandidate] = []
    failed_documents = 0

    for document in documents:
        try:
            document_candidates = extract_researchers_from_document(
                document=document,
                model=model,
            )
        except Exception:
            logger.exception("Researcher extraction failed for one document.")
            failed_documents += 1
            continue

        candidates.extend(document_candidates)

    return ResearcherExtractionOutcome(
        candidates=tuple(candidates),
        attempted_documents=len(documents),
        failed_documents=failed_documents,
    )
