from operator import add
from typing import Annotated, TypedDict

from research_finder.models import (
    ResearcherResult,
    SearchRequest,
    SearchResponse,
    TopicExpansion,
)
from research_finder.official_page_search import (
    OfficialSearchPage,
)
from research_finder.researcher_details import (
    EnrichedResearcherCandidate,
)
from research_finder.researcher_extraction import (
    ResearcherCandidate,
)
from research_finder.search_queries import (
    OfficialSearchQuery,
)
from research_finder.university_directory import UniversityRecord
from research_finder.verification import (
    VerifiedResearcherCandidate,
)
from research_finder.web_content import (
    DownloadedWebPage,
)

from research_finder.research_profile import (
    OrganisedResearcherProfile,
)


class WorkflowMessages(TypedDict, total=False):
    """Append-only messages shared by internal and output state."""

    errors: Annotated[list[str], add]
    warnings: Annotated[list[str], add]
    execution_log: Annotated[list[str], add]


class ResearchGraphInput(TypedDict):
    """Information accepted when the graph is invoked."""

    raw_request: dict[str, object]


class ResearchGraphOutput(WorkflowMessages, total=False):
    """Information returned after the graph finishes."""

    final_response: SearchResponse | None


class ResearchGraphState(WorkflowMessages, total=False):
    """Internal shared state used by workflow nodes."""

    raw_request: dict[str, object]
    request: SearchRequest | None

    topic_expansion: TopicExpansion | None
    expanded_topics: list[str]

    candidate_universities: list[UniversityRecord]

    search_queries: list[OfficialSearchQuery]
    researcher_pages: list[OfficialSearchPage]
    lab_pages: list[OfficialSearchPage]
    project_pages: list[OfficialSearchPage]
    publication_pages: list[OfficialSearchPage]

    researcher_documents: list[DownloadedWebPage]
    lab_documents: list[DownloadedWebPage]
    project_documents: list[DownloadedWebPage]
    publication_documents: list[DownloadedWebPage]

    extracted_candidates: list[ResearcherCandidate]

    enriched_candidates: list[EnrichedResearcherCandidate]

    verified_results: list[VerifiedResearcherCandidate]
    organised_results: list[OrganisedResearcherProfile]

    scored_results: list[ResearcherResult]
    deduplicated_results: list[ResearcherResult]
    ranked_results: list[ResearcherResult]

    search_attempt_count: int
    download_attempt_count: int
    final_response: SearchResponse | None
