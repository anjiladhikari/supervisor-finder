from operator import add
from typing import Annotated, TypedDict

from research_finder.models import (
    SearchRequest,
    TopicExpansion,
)
from research_finder.official_page_search import (
    OfficialSearchPage,
)
from research_finder.ranking import (
    RankedResearcherProfile,
)
from research_finder.relevance import (
    ScoredResearcherProfile,
)
from research_finder.researcher_extraction import (
    ResearcherCandidate,
)
from research_finder.search_queries import (
    OfficialSearchQuery,
)
from research_finder.search_strategy import (
    SearchMode,
)
from research_finder.university_directory import (
    UniversityRecord,
)
from research_finder.verification import (
    VerifiedResearcherCandidate,
)
from research_finder.web_content import (
    DownloadedWebPage,
)


class WorkflowMessages(TypedDict, total=False):
    errors: Annotated[list[str], add]
    warnings: Annotated[list[str], add]
    execution_log: Annotated[list[str], add]


class ResearchGraphInput(TypedDict):
    raw_request: dict[str, object]


class ResearchGraphOutput(
    WorkflowMessages,
    total=False,
):
    final_response: dict[str, object] | None


class ResearchGraphState(
    WorkflowMessages,
    total=False,
):
    raw_request: dict[str, object]
    request: SearchRequest | None

    topic_expansion: TopicExpansion | None
    expanded_topics: list[str]

    candidate_universities: list[UniversityRecord]
    search_queries: list[OfficialSearchQuery]

    researcher_pages: list[OfficialSearchPage]
    researcher_documents: list[DownloadedWebPage]

    extracted_candidates: list[ResearcherCandidate]
    verified_results: list[VerifiedResearcherCandidate]

    scored_results: list[ScoredResearcherProfile]
    deduplicated_results: list[ScoredResearcherProfile]
    ranked_results: list[RankedResearcherProfile]

    search_mode: SearchMode
    search_round: int
    active_search_topics: list[str]

    search_attempt_count: int
    download_attempt_count: int

    final_response: dict[str, object] | None