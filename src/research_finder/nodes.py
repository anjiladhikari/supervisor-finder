from pydantic import ValidationError

from research_finder.models import SearchRequest, SearchResponse
from research_finder.state import ResearchGraphState

def initialize_workflow(_:ResearchGraphState) -> dict[str,object]:
    """Create predicatble initial for the workflow."""

    return{
        "request": None,
        "expanded_topics": [],
        "candidate_universities": [],
        "researcher_pages": [],
        "lab_pages": [],
        "project_pages": [],
        "publication_pages": [],
        "extracted_candidates": [],
        "verified_results": [],
        "scored_results": [],
        "deduplicated_results": [],
        "ranked_results": [],
        "search_attempt_count": 0,
        "final_response": None,
        "errors": [],
        "warnings": [],
        "execution_log": ["Workflow initialized."],
    }



def validate_input(state:ResearchGraphState)-> dict[str,object]:
    """Validate the raw user request using the searchrequest model."""

    raw_request=state.get("raw_request") 

    if raw_request is None:
        return{
            "request": None,
            "errors":["raw_request: grpah input is missing"],
            "execution_log":["Input validation failed"],
        }

    try:
        request=SearchRequest.model_validate(raw_request)
    except ValidationError as error:
        formatted_errors=[]

        for validation_error in error.errors(include_url=False):
            location=".".join(
                str(part) for part in vlidation_error("loc")

            )
            message=validation_error["msg"]
            formatted_errors.append(f"{location}:{message}")

        return{
            "request":None,
            "errors": formatted_errors,
            "execution_log":["Input validation failed"],
        }

    return{
        "request":request,
    
        "execution_log": ["Input validated successfully"],
    }



def expand_search_topic(state:ResearchGraphState,) -> dict[str,object]:
    """temporaily use only the original topic until LLM is added."""
    request =state.get("request")

    if request is None:
        return{
            "errors":[
                "Topic expansion can not run without a validated request."
            ],
            "execution_log":["Topic expansion failed"],
        }
    return{
        "expanded_topics":[request.research_topic],
        "warnings":[
            "LLM topic expansion not yet implemented; only original topic used."
            "the original research topic was used."
        ],
        "execution_log":["Topic-expansion placeholder completed."],
    }


def find_universities(_:ResearchGraphState,)-> dict[str,object]:
    """placeholder for official Australian university discovery."""
    return{
        "candidate_universities": [],
        "warnings": [
            "University discovery is not implemented yet; "
            "no external search was performed."
        ],
        "execution_log": ["University-discovery placeholder completed."],
    }


 
def search_researchers(_: ResearchGraphState,) -> dict[str, object]:
    """Placeholder for official researcher-profile searches."""

    return {
        "researcher_pages": [],
        "extracted_candidates": [],
        "warnings": [
            "Researcher search is not implemented yet."
        ],
        "execution_log": ["Researcher-search placeholder completed."],
    }


def search_labs(_: ResearchGraphState) -> dict[str, object]:
    """Placeholder for research-lab and research-group searches."""

    return {
        "lab_pages": [],
        "warnings": [
            "Research lab search is not implemented yet."
        ],
        "execution_log": ["Research-lab search placeholder completed."],
    }


def search_projects(_: ResearchGraphState) -> dict[str, object]:
    """Placeholder for current and previous project searches."""

    return {
        "project_pages": [],
        "warnings": [
            "Research project search is not implemented yet."
        ],
        "execution_log": ["Research-project search placeholder completed."],
    }


def search_publications(_: ResearchGraphState,) -> dict[str, object]:
    """Placeholder for publication searches."""

    return {
        "publication_pages": [],
        "warnings": [
            "Publication search is not implemented yet."
        ],
        "execution_log": ["Publication-search placeholder completed."],
    }

def verify_current_affiliation(
    _: ResearchGraphState,
) -> dict[str, object]:
    """Placeholder for current-university-affiliation verification."""

    return {
        "verified_results": [],
        "warnings": [
            "Current affiliation verification is not implemented yet."
        ],
        "execution_log": [
            "Affiliation-verification placeholder completed."
        ],
    }


def score_relevance(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Pass verified results forward until scoring is implemented."""

    verified_results = state.get("verified_results", [])

    return {
        "scored_results": verified_results,
        "warnings": [
            "Deterministic relevance scoring is not implemented yet."
        ],
        "execution_log": ["Relevance-scoring placeholder completed."],
    }


def remove_duplicates(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Keep one result for each researcher-university combination."""

    scored_results = state.get("scored_results", [])
    unique_results = {}

    for result in scored_results:
        key = (
            result.researcher_name.casefold(),
            result.university_name.casefold(),
        )

        existing_result = unique_results.get(key)

        if (
            existing_result is None
            or result.relevance_score.total
            > existing_result.relevance_score.total
        ):
            unique_results[key] = result

    return {
        "deduplicated_results": list(unique_results.values()),
        "execution_log": ["Duplicate removal completed."],
    }


def rank_results(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Rank results from highest to lowest relevance score."""

    deduplicated_results = state.get("deduplicated_results", [])

    ranked_results = sorted(
        deduplicated_results,
        key=lambda result: result.relevance_score.total,
        reverse=True,
    )

    return {
        "ranked_results": ranked_results,
        "execution_log": ["Result ranking completed."],
    }


def generate_final_output(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Build the final validated SearchResponse."""

    request = state.get("request")

    if request is None:
        return {
            "final_response": None,
            "execution_log": [
                "Final response could not be generated because "
                "the request was invalid."
            ],
        }

    ranked_results = state.get("ranked_results", [])
    workflow_warnings = list(state.get("warnings", []))
    workflow_errors = state.get("errors", [])

    workflow_warnings.extend(
        f"Workflow error: {error}" for error in workflow_errors
    )

    response = SearchResponse(
        request=request,
        results=ranked_results[: request.max_results],
        warnings=workflow_warnings,
    )

    return {
        "final_response": response,
        "execution_log": ["Final response generated."],
    }