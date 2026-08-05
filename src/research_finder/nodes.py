from pydantic import ValidationError

from research_finder.llm import create_chat_model
from research_finder.location import (
    LocationLookupError,
    resolve_location,
)
from research_finder.models import SearchRequest, SearchResponse
from research_finder.official_page_search import (
    execute_official_searches,
)
from research_finder.search_queries import (
    SearchTarget,
    generate_official_search_queries,
)
from research_finder.state import ResearchGraphState
from research_finder.topic_expansion import (
    create_fallback_topic_expansion,
    generate_topic_expansion,
)
from research_finder.university_directory import (
    UniversityDirectoryError,
    get_universities,
    supports_country,
)
from research_finder.web_search import (
    create_search_client,
)
from research_finder.web_content import (
    create_page_downloader,
    download_official_pages,
)

def initialize_workflow(_: ResearchGraphState) -> dict[str, object]:
    """Create predictable initial values for the workflow."""

    return {
        "request": None,
        "topic_expansion": None,
        "expanded_topics": [],
        "candidate_universities": [],
        "search_queries": [],
        "researcher_pages": [],
        "lab_pages": [],
        "project_pages": [],
        "publication_pages": [],
        "researcher_documents": [],
        "lab_documents": [],
        "project_documents": [],
        "publication_documents": [],
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


def validate_input(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Resolve location values and validate the request."""

    raw_request = state.get("raw_request")

    if raw_request is None:
        return {
            "request": None,
            "errors": ["raw_request: Graph input is missing."],
            "execution_log": ["Input validation failed."],
        }

    try:
        location = resolve_location(
            country=raw_request.get("country"),
            state=raw_request.get("state"),
        )
    except LocationLookupError as error:
        return {
            "request": None,
            "errors": [f"{error.field}: {error.message}"],
            "execution_log": ["Input validation failed."],
        }

    if not supports_country(location.country_code):
        return {
            "request": None,
            "errors": [(f"country: {location.country} is not supported yet.")],
            "execution_log": ["Input validation failed."],
        }

    request_data = dict(raw_request)
    request_data.update(
        {
            "country": location.country,
            "country_code": location.country_code,
            "state": location.state,
            "state_code": location.state_code,
        }
    )

    try:
        request = SearchRequest.model_validate(request_data)
    except ValidationError as error:
        formatted_errors = []

        for item in error.errors(include_url=False):
            field = ".".join(str(part) for part in item["loc"])
            formatted_errors.append(f"{field}: {item['msg']}")

        return {
            "request": None,
            "errors": formatted_errors,
            "execution_log": ["Input validation failed."],
        }

    return {
        "request": request,
        "execution_log": ["Input validation completed."],
    }


def expand_research_topic(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Generate structured research-topic search vocabulary."""

    request = state.get("request")

    if request is None:
        return {
            "errors": ["Topic expansion cannot run without a validated request."],
            "execution_log": ["Topic expansion failed."],
        }

    try:
        model = create_chat_model()
        expansion = generate_topic_expansion(
            request=request,
            model=model,
        )
    except Exception as error:  # noqa: BLE001
        fallback_expansion = create_fallback_topic_expansion(request)

        return {
            "topic_expansion": fallback_expansion,
            "expanded_topics": (fallback_expansion.to_search_terms()),
            "warnings": [
                (
                    "Structured LLM topic expansion was unavailable "
                    f"({type(error).__name__}); the original "
                    "research topic was used."
                )
            ],
            "execution_log": [("Topic expansion completed with deterministic fallback.")],
        }

    return {
        "topic_expansion": expansion,
        "expanded_topics": expansion.to_search_terms(),
        "execution_log": ["Structured topic expansion completed."],
    }


def find_universities(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Select universities for the optional state."""

    request = state.get("request")

    if request is None:
        return {
            "candidate_universities": [],
            "errors": [("University selection cannot run without a validated request.")],
            "execution_log": ["University-directory selection failed."],
        }

    try:
        candidates = list(
            get_universities(
                country_code=request.country_code,
                state_code=request.state_code,
            )
        )
    except UniversityDirectoryError as error:
        return {
            "candidate_universities": [],
            "errors": [str(error)],
            "execution_log": ["University-directory selection failed."],
        }

    scope = request.country

    if request.state is not None:
        scope = f"{request.state}, {request.country}"

    return {
        "candidate_universities": candidates,
        "execution_log": [
            (f"University directory selected {len(candidates)} candidates for {scope}.")
        ],
    }


def generate_search_queries(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Generate official university-domain queries."""

    universities = state.get(
        "candidate_universities",
        [],
    )
    topics = state.get(
        "expanded_topics",
        [],
    )

    if not universities:
        return {
            "search_queries": [],
            "errors": [("Search queries cannot be generated without candidate universities.")],
            "execution_log": ["Search-query generation failed."],
        }

    if not topics:
        return {
            "search_queries": [],
            "errors": [("Search queries cannot be generated without expanded topics.")],
            "execution_log": ["Search-query generation failed."],
        }

    queries = generate_official_search_queries(
        universities=universities,
        topics=topics,
    )

    return {
        "search_queries": queries,
        "execution_log": [(f"Generated {len(queries)} official university-domain queries.")],
    }


_PAGE_STATE_KEYS = {
    SearchTarget.RESEARCHER: "researcher_pages",
    SearchTarget.LAB: "lab_pages",
    SearchTarget.PROJECT: "project_pages",
    SearchTarget.PUBLICATION: "publication_pages",
}

_PAGE_LABELS = {
    SearchTarget.RESEARCHER: "Researcher",
    SearchTarget.LAB: "Research-lab",
    SearchTarget.PROJECT: "Research-project",
    SearchTarget.PUBLICATION: "Publication",
}


def _search_official_pages(
    state: ResearchGraphState,
    target: SearchTarget,
) -> dict[str, object]:
    """Execute all official queries for one target."""

    search_queries = state.get(
        "search_queries",
        [],
    )
    target_queries = [
        search_query for search_query in search_queries if search_query.target == target
    ]

    state_key = _PAGE_STATE_KEYS[target]
    label = _PAGE_LABELS[target]

    if not target_queries:
        return {
            state_key: [],
            "errors": [(f"No {target.value} search queries were available.")],
            "execution_log": [f"{label} search failed."],
        }

    client = create_search_client()

    outcome = execute_official_searches(
        search_queries=target_queries,
        target=target,
        client=client,
        max_results_per_query=3,
    )

    warnings: list[str] = []

    if outcome.failed_queries:
        warnings.append(
            
                f"{label} search failed for "
                f"{outcome.failed_queries} of "
                f"{outcome.attempted_queries} queries."
            
        )

    if not outcome.pages:
        warnings.append(f"No official {target.value} pages were found.")

    result: dict[str, object] = {
        state_key: list(outcome.pages),
        "search_attempt_count": (state.get("search_attempt_count", 0) + outcome.attempted_queries),
        "execution_log": [
            (
                f"{label} search completed: "
                f"{outcome.attempted_queries} queries "
                f"attempted, {len(outcome.pages)} "
                "official pages found."
            )
        ],
    }

    if warnings:
        result["warnings"] = warnings

    return result


def search_researchers(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Search official researcher-profile pages."""

    return _search_official_pages(
        state,
        SearchTarget.RESEARCHER,
    )


def search_labs(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Search official research-lab pages."""

    return _search_official_pages(
        state,
        SearchTarget.LAB,
    )


def search_projects(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Search official research-project pages."""

    return _search_official_pages(
        state,
        SearchTarget.PROJECT,
    )


def search_publications(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Search official publication pages."""

    return _search_official_pages(
        state,
        SearchTarget.PUBLICATION,
    )
def download_webpage_content(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Download and clean all discovered official pages."""

    page_groups = (
        (
            "researcher_pages",
            "researcher_documents",
        ),
        (
            "lab_pages",
            "lab_documents",
        ),
        (
            "project_pages",
            "project_documents",
        ),
        (
            "publication_pages",
            "publication_documents",
        ),
    )

    all_pages = [
        page
        for page_key, _ in page_groups
        for page in state.get(page_key, [])
    ]

    if not all_pages:
        return {
            "researcher_documents": [],
            "lab_documents": [],
            "project_documents": [],
            "publication_documents": [],
            "download_attempt_count": (
                state.get(
                    "download_attempt_count",
                    0,
                )
            ),
            "warnings": [
                (
                    "No official pages were available "
                    "for webpage download."
                )
            ],
            "execution_log": [
                (
                    "Webpage download completed: "
                    "0 pages attempted, "
                    "0 documents created."
                )
            ],
        }

    downloader = create_page_downloader()

    result: dict[str, object] = {}
    attempted_pages = 0
    failed_pages = 0
    document_count = 0

    for page_key, document_key in page_groups:
        pages = list(
            state.get(page_key, [])
        )

        outcome = download_official_pages(
            pages=pages,
            downloader=downloader,
        )

        result[document_key] = list(
            outcome.documents
        )
        attempted_pages += outcome.attempted_pages
        failed_pages += outcome.failed_pages
        document_count += len(
            outcome.documents
        )

    result["download_attempt_count"] = (
        state.get(
            "download_attempt_count",
            0,
        )
        + attempted_pages
    )

    if failed_pages:
        result["warnings"] = [
            (
                f"Webpage download failed for "
                f"{failed_pages} of "
                f"{attempted_pages} pages."
            )
        ]

    result["execution_log"] = [
        (
            "Webpage download completed: "
            f"{attempted_pages} pages attempted, "
            f"{document_count} documents created."
        )
    ]

    return result

def verify_current_affiliation(
    _: ResearchGraphState,
) -> dict[str, object]:
    """Placeholder for current-university-affiliation verification."""

    return {
        "verified_results": [],
        "warnings": ["Current affiliation verification is not implemented yet."],
        "execution_log": ["Affiliation-verification placeholder completed."],
    }


def score_relevance(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Pass verified results forward until scoring is implemented."""

    verified_results = state.get("verified_results", [])

    return {
        "scored_results": verified_results,
        "warnings": ["Deterministic relevance scoring is not implemented yet."],
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
            or result.relevance_score.total > existing_result.relevance_score.total
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
                ("Final response could not be generated because the request was invalid.")
            ],
        }

    ranked_results = state.get("ranked_results", [])
    workflow_warnings = list(state.get("warnings", []))
    workflow_errors = state.get("errors", [])

    workflow_warnings.extend(f"Workflow error: {error}" for error in workflow_errors)

    response = SearchResponse(
        request=request,
        results=ranked_results[: request.max_results],
        warnings=workflow_warnings,
    )

    return {
        "final_response": response,
        "execution_log": ["Final response generated."],
    }
