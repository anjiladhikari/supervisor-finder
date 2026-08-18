from __future__ import annotations

import logging
from dataclasses import dataclass

from groq import RateLimitError
from langchain_core.language_models.chat_models import (
    BaseChatModel,
)
from pydantic import (
    Field,
    HttpUrl,
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
        max_length=150,
    )
    role: str | None = Field(
        max_length=200,
    )
    research_interests: list[str] = Field(
        max_length=15,
    )
    profile_summary: str | None = Field(
        max_length=1000,
    )
    evidence_text: str = Field(
        min_length=5,
        description=(
            "An exact continuous excerpt copied from the supplied webpage. "
            "Keep it concise, preferably under  short."
        ),
    )

    profile_state: str | None = Field(
        max_length=100,
        description=(
            "Current Australian state of the researcher's "
            "university affiliation, only when explicitly "
            "supported by the page. Otherwise null."
        ),
    )

    profile_country: str | None = Field(
        max_length=100,
        description=(
            "Current country of the researcher's university "
            "affiliation, only when explicitly supported by "
            "the page. Otherwise null."
    ),
)

class ResearcherExtractionBatch(StrictModel):
    """Researcher extracted from one personal university profile page."""

    is_researcher_profile: bool
    researchers: list[ResearcherExtractionDraft]


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
    profile_state: str | None = Field(
        
        default=None,
        max_length=100,
    )

    profile_country: str | None = Field(
        default=None,
        max_length=100,
    )

@dataclass(frozen=True)
class ResearcherExtractionOutcome:
    """Result of processing researcher documents."""

    candidates: tuple[ResearcherCandidate, ...]
    attempted_documents: int
    failed_documents: int
    rate_limited: bool = False


_RESEARCHER_EXTRACTION_SYSTEM_PROMPT = """
Determine whether the supplied official university webpage is a PERSONAL
RESEARCHER PROFILE PAGE.

A valid researcher profile page is mainly about one academic or researcher
and contains information such as their name, academic role, biography,
research interests, expertise, or research areas.

Reject pages whose main purpose is:
- a publication or paper
- a publication list
- a project page
- a research group or lab page
- a staff directory or researcher search-results page
- a news page
- an event page
- a student profile
- an author list

Rules:

1. If this is NOT a personal researcher profile page:
   - is_researcher_profile = false
   - researchers = []

2. If this IS a personal researcher profile page:
   - is_researcher_profile = true
   - extract ONLY the person whose profile the page belongs to
   - never extract co-authors, collaborators or other people mentioned

3. Include only academic or research staff.

4. Do not invent names, titles, roles, research interests or summaries.

5. Research interests must come from information explicitly present on
   the profile page.

6. evidence_text must be an exact continuous excerpt from the supplied page
   proving the researcher's identity and research information.

7. Keep research interests short and specific.

8. Do not extract projects, publications, labs or email addresses here.
11. Extract the researcher's current institutional state and country only when the page explicitly supports them.
12. Location must refer to the profile owner's current affiliation, not another campus or university mentioned on the page.
13. For Australian states, use the full state name such as Victoria, New South Wales or Tasmania.
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
        strict=True,
    )

    raw_response = structured_model.invoke(build_researcher_extraction_messages(document))

    if isinstance(
        raw_response,
        ResearcherExtractionBatch,
    ):
        batch = raw_response
    else:
        batch = ResearcherExtractionBatch.model_validate(raw_response)
    if not batch.is_researcher_profile:
        return []

    normalised_content = _normalise_for_matching(document.content)

    candidates: list[ResearcherCandidate] = []
    seen_names: set[str] = set()

    for researcher in batch.researchers[:1]:
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
    academic_title=researcher.academic_title,
    role=researcher.role,
    research_interests=researcher.research_interests,
    profile_summary=researcher.profile_summary,

    profile_state=researcher.profile_state,
    profile_country=researcher.profile_country,

    university_name=document.university_name,
    official_domain=document.official_domain,
    source_url=document.url,
    evidence_text=researcher.evidence_text,
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
    attempted_documents = 0
    rate_limited = False

    for document in documents:
        attempted_documents += 1

        try:
            document_candidates = (
                extract_researchers_from_document(
                    document=document,
                    model=model,
                )
            )

        except RateLimitError:
            logger.warning(
                "Groq rate limit reached. "
                "Stopping researcher extraction."
            )

            failed_documents += 1
            rate_limited = True
            break

        except Exception:
            logger.exception(
                "Researcher extraction failed "
                "for one document."
            )

            failed_documents += 1
            continue

        candidates.extend(
            document_candidates
        )

    return ResearcherExtractionOutcome(
        candidates=tuple(candidates),
        attempted_documents=attempted_documents,
        failed_documents=failed_documents,
        rate_limited=rate_limited,
    )