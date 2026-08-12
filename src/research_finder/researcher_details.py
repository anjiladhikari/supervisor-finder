from __future__ import annotations

from dataclasses import dataclass

from langchain_core.language_models.chat_models import (
    BaseChatModel,
)
from pydantic import (
    EmailStr,
    Field,
    HttpUrl,
    model_validator,
)

from research_finder.models import StrictModel
from research_finder.researcher_extraction import (
    ResearcherCandidate,
)
from research_finder.search_queries import (
    SearchTarget,
)
from research_finder.web_content import (
    DownloadedWebPage,
)


class ResearcherDetailDraft(StrictModel):
    """One researcher-detail association returned by the LLM."""

    researcher_name: str = Field(
        min_length=2,
        max_length=200,
    )
    public_email: EmailStr | None = None

    item_name: str | None = Field(
        default=None,
        max_length=500,
    )
    publication_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
    )

    evidence_text: str = Field(
        min_length=5,
        max_length=700,
        description=(
            "Exact continuous excerpt copied "
            "from the supplied webpage."
        ),
    )


class ResearcherDetailBatch(StrictModel):
    """Details extracted from one webpage."""

    details: list[ResearcherDetailDraft] = Field(
        default_factory=list,
        max_length=50,
    )


class ResearcherDetailAssociation(StrictModel):
    """One grounded association between a researcher and a detail."""

    researcher_name: str
    university_name: str
    official_domain: str

    target: SearchTarget

    public_email: EmailStr | None = None
    item_name: str | None = None
    publication_year: int | None = None

    source_url: HttpUrl
    source_title: str

    evidence_text: str


class ResearchEvidenceItem(StrictModel):
    """One grounded lab, project or publication."""

    name: str = Field(
        min_length=2,
        max_length=500,
    )
    target: SearchTarget

    publication_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
    )

    source_url: HttpUrl
    source_title: str

    evidence_text: str = Field(
        min_length=5,
        max_length=700,
    )

    @model_validator(mode="after")
    def reject_researcher_target(
        self,
    ) -> ResearchEvidenceItem:
        """Researcher target is reserved for email extraction."""

        if self.target == SearchTarget.RESEARCHER:
            raise ValueError(
                "ResearchEvidenceItem cannot use "
                "the researcher target."
            )

        return self


class EnrichedResearcherCandidate(StrictModel):
    """Researcher plus extracted supporting information."""

    researcher: ResearcherCandidate

    public_email: EmailStr | None = None
    public_email_source_url: HttpUrl | None = None

    labs: list[ResearchEvidenceItem] = Field(
        default_factory=list
    )
    projects: list[ResearchEvidenceItem] = Field(
        default_factory=list
    )
    publications: list[ResearchEvidenceItem] = Field(
        default_factory=list
    )


@dataclass(frozen=True)
class ResearcherDetailExtractionOutcome:
    """Result of processing supporting documents."""

    associations: tuple[
        ResearcherDetailAssociation,
        ...,
    ]
    attempted_documents: int
    failed_documents: int


_SYSTEM_PROMPT = """
Extract evidence that explicitly connects known researchers to information
on an official university webpage.

Important rules:

1. researcher_name MUST exactly match one of the provided researcher names.
2. Never invent a researcher.
3. Never infer an association that is not explicitly stated.
4. evidence_text must be an exact continuous excerpt from the page.
5. For researcher-profile pages:
   - extract only a public university email clearly belonging to that person.
6. For lab pages:
   - extract the lab, centre, institute or research-group name.
7. For project pages:
   - extract the project name only when the researcher is explicitly connected.
8. For publication pages:
   - extract the publication title only when the researcher is explicitly
     connected.
   - include publication_year only when explicitly shown.
9. Do not infer current or previous project status.
10. Return an empty list when the page contains no supported association.
""".strip()


def _normalise(value: str) -> str:
    """Normalise text for grounded comparisons."""

    return " ".join(
        value.split()
    ).casefold()


def _email_uses_official_domain(
    email: str,
    official_domain: str,
) -> bool:
    """Check whether an email belongs to the university domain."""

    email_domain = (
        email.rsplit("@", maxsplit=1)[-1]
        .casefold()
        .removeprefix("www.")
    )

    domain = (
        official_domain.casefold()
        .removeprefix("www.")
    )

    return (
        email_domain == domain
        or email_domain.endswith(
            f".{domain}"
        )
    )


def build_detail_extraction_messages(
    document: DownloadedWebPage,
    candidates: list[ResearcherCandidate],
    *,
    max_content_characters: int = 12_000,
) -> list[tuple[str, str]]:
    """Create grounded extraction messages."""

    candidate_names = "\n".join(
        f"- {candidate.full_name}"
        for candidate in candidates
    )

    content = document.content[
        :max_content_characters
    ]

    human_prompt = f"""
University: {document.university_name}
Page type: {document.target.value}
Page title: {document.page_title}
Page URL: {document.final_url}

Allowed researcher names:

{candidate_names}

Official webpage content:

{content}
""".strip()

    return [
        (
            "system",
            _SYSTEM_PROMPT,
        ),
        (
            "human",
            human_prompt,
        ),
    ]


def extract_details_from_document(
    document: DownloadedWebPage,
    candidates: list[ResearcherCandidate],
    model: BaseChatModel,
) -> list[ResearcherDetailAssociation]:
    """Extract grounded details from one official document."""

    if not candidates:
        return []

    structured_model = model.with_structured_output(
        ResearcherDetailBatch,
        method="json_schema",
    )

    response = structured_model.invoke(
        build_detail_extraction_messages(
            document=document,
            candidates=candidates,
        )
    )

    if isinstance(
        response,
        ResearcherDetailBatch,
    ):
        batch = response
    else:
        batch = (
            ResearcherDetailBatch.model_validate(
                response
            )
        )

    candidate_names = {
        _normalise(candidate.full_name):
        candidate.full_name
        for candidate in candidates
    }

    normalised_content = _normalise(
        document.content
    )

    associations: list[
        ResearcherDetailAssociation
    ] = []

    for detail in batch.details:
        researcher_key = _normalise(
            detail.researcher_name
        )

        canonical_name = candidate_names.get(
            researcher_key
        )

        if canonical_name is None:
            continue

        evidence_key = _normalise(
            detail.evidence_text
        )

        if evidence_key not in normalised_content:
            continue

        if document.target == SearchTarget.RESEARCHER:
            if detail.public_email is None:
                continue

            email = str(
                detail.public_email
            )

            if not _email_uses_official_domain(
                email,
                document.official_domain,
            ):
                continue

            if (
                email.casefold()
                not in detail.evidence_text.casefold()
            ):
                continue

            associations.append(
                ResearcherDetailAssociation(
                    researcher_name=canonical_name,
                    university_name=(
                        document.university_name
                    ),
                    official_domain=(
                        document.official_domain
                    ),
                    target=document.target,
                    public_email=detail.public_email,
                    source_url=document.final_url,
                    source_title=document.page_title,
                    evidence_text=(
                        detail.evidence_text
                    ),
                )
            )

            continue

        if detail.item_name is None:
            continue

        item_key = _normalise(
            detail.item_name
        )

        if item_key not in evidence_key:
            continue

        if (
            document.target
            == SearchTarget.PUBLICATION
            and detail.publication_year is not None
            and str(detail.publication_year)
            not in detail.evidence_text
        ):
            continue

        associations.append(
            ResearcherDetailAssociation(
                researcher_name=canonical_name,
                university_name=(
                    document.university_name
                ),
                official_domain=(
                    document.official_domain
                ),
                target=document.target,
                item_name=detail.item_name,
                publication_year=(
                    detail.publication_year
                ),
                source_url=document.final_url,
                source_title=document.page_title,
                evidence_text=(
                    detail.evidence_text
                ),
            )
        )

    return associations


def extract_researcher_detail_documents(
    documents: list[DownloadedWebPage],
    candidates: list[ResearcherCandidate],
    model: BaseChatModel,
) -> ResearcherDetailExtractionOutcome:
    """Extract details while allowing individual failures."""

    associations: list[
        ResearcherDetailAssociation
    ] = []

    failed_documents = 0

    for document in documents:
        try:
            document_associations = (
                extract_details_from_document(
                    document=document,
                    candidates=candidates,
                    model=model,
                )
            )
        except Exception:  # noqa: BLE001
            failed_documents += 1
            continue

        associations.extend(
            document_associations
        )

    return ResearcherDetailExtractionOutcome(
        associations=tuple(associations),
        attempted_documents=len(documents),
        failed_documents=failed_documents,
    )


def enrich_researcher_candidates(
    candidates: list[ResearcherCandidate],
    associations: list[
        ResearcherDetailAssociation
    ],
) -> list[EnrichedResearcherCandidate]:
    """Attach extracted evidence to researchers."""

    enriched: list[
        EnrichedResearcherCandidate
    ] = []

    for candidate in candidates:
        candidate_associations = [
            association
            for association in associations
            if (
                association.researcher_name.casefold()
                == candidate.full_name.casefold()
                and association.official_domain.casefold()
                == candidate.official_domain.casefold()
            )
        ]

        public_email: EmailStr | None = None
        public_email_source_url: (
            HttpUrl | None
        ) = None

        labs: list[ResearchEvidenceItem] = []
        projects: list[ResearchEvidenceItem] = []
        publications: list[
            ResearchEvidenceItem
        ] = []

        seen_items: set[
            tuple[str, str]
        ] = set()

        for association in candidate_associations:
            if (
                association.target
                == SearchTarget.RESEARCHER
            ):
                if (
                    public_email is None
                    and association.public_email
                    is not None
                ):
                    public_email = (
                        association.public_email
                    )
                    public_email_source_url = (
                        association.source_url
                    )

                continue

            if association.item_name is None:
                continue

            item_key = (
                association.target.value,
                association.item_name.casefold(),
            )

            if item_key in seen_items:
                continue

            seen_items.add(item_key)

            item = ResearchEvidenceItem(
                name=association.item_name,
                target=association.target,
                publication_year=(
                    association.publication_year
                ),
                source_url=(
                    association.source_url
                ),
                source_title=(
                    association.source_title
                ),
                evidence_text=(
                    association.evidence_text
                ),
            )

            if (
                association.target
                == SearchTarget.LAB
            ):
                labs.append(item)

            elif (
                association.target
                == SearchTarget.PROJECT
            ):
                projects.append(item)

            elif (
                association.target
                == SearchTarget.PUBLICATION
            ):
                publications.append(item)

        enriched.append(
            EnrichedResearcherCandidate(
                researcher=candidate,
                public_email=public_email,
                public_email_source_url=(
                    public_email_source_url
                ),
                labs=labs,
                projects=projects,
                publications=publications,
            )
        )

    return enriched