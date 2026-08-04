from operator import add
from typing import Annotated, TypedDict

from research_finder.models import (
    ResearcherResult,
    SearchRequest,
    SearchResponse,
    TopicExpansion,
)
from research_finder.university_directory import UniversityRecord


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

    researcher_pages: list[str]
    lab_pages: list[str]
    project_pages: list[str]
    publication_pages: list[str]

    extracted_candidates: list[dict[str, object]]

    verified_results: list[ResearcherResult]
    scored_results: list[ResearcherResult]
    deduplicated_results: list[ResearcherResult]
    ranked_results: list[ResearcherResult]

    search_attempt_count: int
    final_response: SearchResponse | None