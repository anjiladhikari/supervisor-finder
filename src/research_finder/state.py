from operator import add
from typing import Annotated,TypedDict

from research_finder.models import(
    ResearcherResult,
    SearchRequest,
    SearchResponse,
)

class ResearchGraphInput(TypedDict):
    """
    Public input accepted when the LangGraph workflow is invoked.

    Keeping the graph input small prevents callers from directly setting
    internal workflow fields such as verified results, scores, or errors.
    """
    raw_request: dict[str,object]


class ResearchGraphOutput(TypedDict):
    """
    Public output returned after the LangGraph workflow finishes.

    Only these fields are exposed to the caller. Internal search pages,
    intermediate candidates, and workflow counters remain private.
    """
    final_response:SearchResponse | None

    error: list[str]
    warnings: list[str]

    execution_log: list[str]


class ResearchGraphState(TypedDict, total=False):
    """Internal shared state passed between all LangGraph nodes.

    Each graph node receives the current state, reads the fields it needs,
    and returns only the fields it created or updated. """
    #original graph input
    raw_request: dict[str,object]
    #validated user request
    request:SearchRequest | None
    #expanding topice for more wide search
    expanded_topics: list[str]
    # uni
    candidate_university: list[str]

    #different raw output
    researcher_pages: list[str]

    #lab
    lab_pages:list[str]

    #different projects
    project_pages:list[str]


    #publication

    publication_pages:list[str]

    # raw extraction
    extracted_candidates:list[dict[str,object]]

    # Candidates whose important claims have been checked against evidence.
    #
    # Verification may include:
    # - Confirming current university affiliation
    # - Confirming research interests
    # - Checking project status
    # - Connecting claims to official sources
    verified_result:list[ResearcherResult]



   # Verified researchers after relevance-score components have been added.
    #
    # Scoring may consider:
    # - Topic similarity
    # - Relevant publications
    # - Current project relevance
    # - Lab relevance
    # - Evidence strength
    # - Information recency

    scored_results:list[ResearcherResult]


    # Scored results after duplicate researcher entries have been merged
    # or removed.
    #
    # Duplicates may appear when the same researcher is found through:
    # - A university profile
    # - A lab page
    # - A project page
    # - A publication page

    deduplicated_results:list[ResearcherResult]


    # Final ordered results after sorting by relevance score and applying
    # the user's `max_results` limit.

    ranked_results:list[ResearcherResult]

    # Number of search attempts performed by the workflow.
    #
    # This can be used to limit retries and prevent an endless search loop
    # when insufficient evidence is found.

    search_attempt_count:int

    # Final validated object returned to the caller.
    #
    # It is normally created from:
    # - The validated request
    # - Ranked researcher results
    # - Collected warnings
    #
    # It remains None until the final response-building node runs.
    final_response: SearchResponse | None


    # Fatal or important errors collected from different workflow nodes.
    errors: Annotated[list[str], add]

    # Non-fatal limitations collected throughout the workflow.
    warnings: Annotated[list[str], add]

    # Sequential record of workflow activity from multiple nodes.
    execution_log: Annotated[list[str], add]