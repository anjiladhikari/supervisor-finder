

from pydantic import ValidationError
from research_finder.scholar import (
    find_google_scholar_profile,
)
from research_finder.research_projects import (
    ResearchDegreePortal,
    find_research_degree_portal,
)
from research_finder.researcher_extraction import (
    extract_researcher_documents,
)
from research_finder.deduplication import (
    deduplicate_scored_researchers,
)

from research_finder.llm import create_chat_model
from research_finder.location import (
    LocationLookupError,
    resolve_location,
)
from research_finder.models import SearchRequest
from research_finder.official_page_search import (
    execute_official_searches,
)
from research_finder.ranking import (
    RankedResearcherProfile,
    rank_researcher_results,
)
from research_finder.relevance import (
    score_researcher_profiles,
)



from research_finder.search_queries import (
    SearchTarget,
    generate_official_search_queries,
)
from research_finder.search_strategy import (
    SearchMode,
    build_broadened_search_topics,
    build_narrowed_search_topics,
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
from research_finder.verification import (
    verify_researcher_candidates,
)
from research_finder.web_content import (
    create_page_downloader,
    download_official_pages,
)
from research_finder.web_search import (
    create_search_client,
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
        "enriched_candidates": [],
        "verified_results": [],
        "organised_results": [],
        "scored_results": [],
        "deduplicated_results": [],
        "ranked_results": [],
        "search_mode": SearchMode.NORMAL,
        "search_round": 1,
        "active_search_topics": [],
        "search_attempt_count": 0,
        "download_attempt_count": 0,

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
    search_mode = SearchMode(
        state.get(
            "search_mode",
            SearchMode.NORMAL,
        )
    )

    search_round = state.get(
        "search_round",
        1,
    )

    universities = state.get(
        "candidate_universities",
        [],
    )

    active_topics = list(
        state.get(
            "active_search_topics",
            [],
        )
    )

    expanded_topics = list(
        state.get(
            "expanded_topics",
            [],
        )
    )

    if active_topics:
        topics = active_topics

    elif search_mode == SearchMode.NORMAL:
        topics = expanded_topics[:1]

    else:
        topics = expanded_topics





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
    "execution_log": [
        (
            f"Generated {len(queries)} "
            "official university-domain queries "
            f"for {search_mode.value} search "
            f"round {search_round}."
        )
    ],
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

    # First select queries for this target.
    target_queries = [
        search_query
        for search_query in search_queries
        if search_query.target == target
    ]

    # Speed optimisation:
    # after researcher search, only search labs/projects/publications
    # for universities where a researcher page was found.
    if target != SearchTarget.RESEARCHER:
        researcher_universities = {
            page.university_name
            for page in state.get(
                "researcher_pages",
                [],
            )
        }

        target_queries = [
            search_query
            for search_query in target_queries
            if search_query.university_name
            in researcher_universities
        ]

    state_key = _PAGE_STATE_KEYS[target]
    label = _PAGE_LABELS[target]

    if not target_queries:
        return {
            state_key: [],
            "errors": [
                (
                    f"No {target.value} search "
                    "queries were available."
                )
            ],
            "execution_log": [
                f"{label} search failed."
            ],
        }

    client = create_search_client()

    




    outcome = execute_official_searches(
        search_queries=target_queries,
        target=target,
        client=client,
        max_results_per_query=1,
       
)

    warnings: list[str] = []

    if outcome.failed_queries:
        warnings.append(
            
                f"{label} search failed for "
                f"{outcome.failed_queries} of "
                f"{outcome.attempted_queries} queries."
            
        )

    if not outcome.pages:
        warnings.append(
            
                f"No official {target.value} "
                "pages were found."
            
        )

    result: dict[str, object] = {
        state_key: list(
            outcome.pages
        ),
        "search_attempt_count": (
            state.get(
                "search_attempt_count",
                0,
            )
            + outcome.attempted_queries
        ),
        "execution_log": [
            (
                f"{label} search completed: "
                f"{outcome.attempted_queries} queries "
                f"attempted, "
                f"{len(outcome.pages)} official "
                "pages found."
            )
        ],
    }

    if warnings:
        result["warnings"] = warnings

    return result


def broaden_search(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Prepare one broader researcher-search retry."""

    request = state.get(
        "request"
    )

    if request is None:
        return {
            "errors": [
                (
                    "Broaden search requires "
                    "a validated search request."
                )
            ],
            "execution_log": [
                "Broaden search preparation failed."
            ],
        }

    current_round = state.get(
        "search_round",
        1,
    )

    topics = build_broadened_search_topics(
        original_topic=(
            request.research_topic
        ),
        topic_expansion=state.get(
            "topic_expansion"
        ),
        expanded_topics=list(
            state.get(
                "expanded_topics",
                [],
            )
        ),
    )

    next_round = (
        current_round + 1
    )

    return {
        "search_mode": SearchMode.BROADEN,
        "search_round": next_round,
        "active_search_topics": topics,
        "search_queries": [],
        "researcher_pages": [],
        "execution_log": [
            (
                "Search retry prepared: "
                f"round {next_round} using "
                "broaden mode."
            )
        ],
    }
def narrow_search(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Prepare one narrower researcher-search retry."""

    request = state.get(
        "request"
    )

    if request is None:
        return {
            "errors": [
                (
                    "Narrow search requires "
                    "a validated search request."
                )
            ],
            "execution_log": [
                "Narrow search preparation failed."
            ],
        }

    current_round = state.get(
        "search_round",
        1,
    )

    topics = build_narrowed_search_topics(
        original_topic=(
            request.research_topic
        ),
    )

    next_round = (
        current_round + 1
    )

    return {
        "search_mode": SearchMode.NARROW,
        "search_round": next_round,
        "active_search_topics": topics,
        "search_queries": [],
        "researcher_pages": [],
        "execution_log": [
            (
                "Search retry prepared: "
                f"round {next_round} using "
                "narrow mode."
            )
        ],
    }

def search_researchers(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Search official researcher-profile pages."""

    return _search_official_pages(
        state,
        SearchTarget.RESEARCHER,
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
)

    all_pages = [page for page_key, _ in page_groups for page in state.get(page_key, [])]

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
            "warnings": [("No official pages were available for webpage download.")],
            "execution_log": [
                ("Webpage download completed: 0 pages attempted, 0 documents created.")
            ],
        }

    downloader = create_page_downloader()

    result: dict[str, object] = {}
    attempted_pages = 0
    failed_pages = 0
    document_count = 0

    for page_key, document_key in page_groups:
        pages = list(state.get(page_key, []))

        outcome = download_official_pages(
            pages=pages,
            downloader=downloader,
        )

        result[document_key] = list(outcome.documents)
        attempted_pages += outcome.attempted_pages
        failed_pages += outcome.failed_pages
        document_count += len(outcome.documents)

    result["download_attempt_count"] = (
        state.get(
            "download_attempt_count",
            0,
        )
        + attempted_pages
    )

    if failed_pages:
        result["warnings"] = [
            (f"Webpage download failed for {failed_pages} of {attempted_pages} pages.")
        ]

    result["execution_log"] = [
        (
            "Webpage download completed: "
            f"{attempted_pages} pages attempted, "
            f"{document_count} documents created."
        )
    ]

    return result

def extract_researcher_information(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Extract structured researchers from downloaded pages."""

    documents = list(
        state.get(
            "researcher_documents",
            [],
        )
    )

    if not documents:
        return {
            "extracted_candidates": [],
            "warnings": [
                "No researcher documents were available for structured extraction."
            ],
            "execution_log": [
                (
                    "Researcher extraction completed: "
                    "0 documents processed, "
                    "0 candidates created."
                )
            ],
        }

    model = create_chat_model()

    outcome = extract_researcher_documents(
        documents=documents,
        model=model,
    )

    candidates = list(
        outcome.candidates
    )

    request = state.get(
        "request"
    )

    if request is not None:
        filtered_candidates = []

        for candidate in candidates:
            if (
                candidate.profile_country
                and candidate.profile_country.casefold()
                != request.country.casefold()
            ):
                continue

            if (
                request.state
                and candidate.profile_state
                and candidate.profile_state.casefold()
                != request.state.casefold()
            ):
                continue

            filtered_candidates.append(
                candidate
            )

        candidates = filtered_candidates

    result: dict[str, object] = {
        "extracted_candidates": candidates,
        "execution_log": [
            (
                "Researcher extraction completed: "
                f"{outcome.attempted_documents} "
                "documents processed, "
                f"{len(candidates)} "
                "candidates retained."
            )
        ],
    }

    if outcome.rate_limited:
        result["warnings"] = [
            (
                "Groq rate limit was reached. "
                "Researcher extraction stopped early; "
                "please try again after the API limit resets."
            )
        ]

    elif outcome.failed_documents:
        result["warnings"] = [
            (
                "Researcher extraction failed for "
                f"{outcome.failed_documents} of "
                f"{outcome.attempted_documents} "
                "attempted documents."
            )
        ]

    return result


def verify_current_affiliation(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Verify researchers using downloaded official evidence."""

    candidates = list(
        state.get(
            "extracted_candidates",
            [],
        )
    )

    if not candidates:
        return {
            "verified_results": [],
            "warnings": [("No researcher candidates were available for verification.")],
            "execution_log": [
                ("Researcher verification completed: 0 candidates checked, 0 verified.")
            ],
        }

    documents = [
        *state.get(
            "researcher_documents",
            [],
        ),
        *state.get(
            "lab_documents",
            [],
        ),
        *state.get(
            "project_documents",
            [],
        ),
        *state.get(
            "publication_documents",
            [],
        ),
    ]

    outcome = verify_researcher_candidates(
        candidates=candidates,
        documents=documents,
    )

    result: dict[str, object] = {
        "verified_results": list(outcome.verified_candidates),
        "execution_log": [
            (
                "Researcher verification completed: "
                f"{outcome.attempted_candidates} "
                "candidates checked, "
                f"{len(outcome.verified_candidates)} "
                "verified."
            )
        ],
    }

    warnings: list[str] = []

    if outcome.rejected_candidates:
        warnings.append(
            f"{outcome.rejected_candidates} "
            "researcher candidates were rejected "
            "because current official affiliation "
            "could not be verified."
        )

    if outcome.discarded_claims:
        warnings.append(f"{outcome.discarded_claims} unsupported researcher claims were discarded.")

    if warnings:
        result["warnings"] = warnings

    return result




def remove_duplicates(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Remove duplicate researcher results."""

    scored_results = list(
        state.get(
            "scored_results",
            [],
        )
    )

    if not scored_results:
        return {
            "deduplicated_results": [],
            "execution_log": [
                (
                    "Deduplication completed: "
                    "0 researchers."
                )
            ],
        }

    deduplicated = (
        deduplicate_scored_researchers(
            scored_results
        )
    )

    removed = (
        len(scored_results)
        - len(deduplicated)
    )

    return {
        "deduplicated_results": (
            deduplicated
        ),
        "execution_log": [
            (
                "Deduplication completed: "
                f"{len(scored_results)} scored "
                "researchers -> "
                f"{len(deduplicated)} unique "
                f"researchers; {removed} "
                "duplicates removed."
            )
        ],
    }

def score_relevance(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Score verified researchers against the topic."""

    profiles = list(
        state.get(
            "verified_results",
            [],
        )
    )

    if not profiles:
        return {
            "scored_results": [],
            "warnings": [
                "No verified researchers were available for relevance scoring."
            ],
            "execution_log": [
                "Relevance scoring completed: 0 researchers scored."
            ],
        }

    request = state.get("request")

    if request is None:
        return {
            "scored_results": [],
            "errors": [
                "Relevance scoring requires a validated search request."
            ],
            "execution_log": [
                "Relevance scoring failed."
            ],
        }

    expanded_topics = list(
        state.get(
            "expanded_topics",
            [],
        )
    )

    scored_results = score_researcher_profiles(
        profiles,
        research_topic=request.research_topic,
        expanded_topics=expanded_topics,
    )

    return {
        "scored_results": scored_results,
        "execution_log": [
            (
                "Relevance scoring completed: "
                f"{len(scored_results)} researchers scored."
            )
        ],
    }

def rank_results(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Rank deduplicated researchers."""

    results = list(
        state.get(
            "deduplicated_results",
            [],
        )
    )

    if not results:
        return {
            "ranked_results": [],
            "warnings": [("No deduplicated researchers were available for ranking.")],
            "execution_log": [("Result ranking completed: 0 researchers ranked.")],
        }

    request = state.get("request")

    if request is None:
        return {
            "ranked_results": [],
            "errors": [("Result ranking requires a validated search request.")],
            "execution_log": ["Result ranking failed."],
        }

    ranked_results = rank_researcher_results(
        results,
        max_results=(request.max_results),
    )

    excluded_results = len(results) - len(
        [result for result in results if result.relevance_score > 0]
    )

    response: dict[str, object] = {
        "ranked_results": ranked_results,
        "execution_log": [
            (
                "Result ranking completed: "
                f"{len(results)} unique researchers "
                f"evaluated, "
                f"{len(ranked_results)} strongest "
                "matches retained."
            )
        ],
    }

    if excluded_results:
        response["warnings"] = [
            (f"{excluded_results} researchers were excluded because their relevance score was 0.")
        ]

    return response





def _ranked_result_to_output(
    ranked: RankedResearcherProfile,
) -> dict[str, object]:
    """Flatten one researcher for the UI."""

    scored = ranked.result
    verified = (
        scored.verified_researcher
    )
    researcher = (
        verified.candidate
    )

    portal = (
        scored.research_degree_portal
    )

    return {
        "rank": ranked.rank,

        "researcher_name": (
            researcher.full_name
        ),

        "university_name": (
            researcher.university_name
        ),

        "academic_title": (
            researcher.academic_title
        ),

        "role": (
            researcher.role
        ),

        "profile_summary": (
            researcher.profile_summary
        ),

        "research_interests": list(
            researcher.research_interests
        ),

        "relevance_score": (
            scored.relevance_score
        ),

        "keyword_score": (
            scored.keyword_score
        ),

        "semantic_score": (
            scored.semantic_score
        ),

        "matched_terms": list(
            scored.matched_terms
        ),

        "match_explanation": list(
            scored.match_explanation
        ),

        "official_profile_url": str(
            researcher.source_url
        ),

        "google_scholar_url": (
            str(
                scored.google_scholar_url
            )
            if scored.google_scholar_url
            else None
        ),

        "research_degree_portal": (
            {
                "title": (
                    portal.title
                ),
                "url": str(
                    portal.url
                ),
            }
            if portal is not None
            else None
        ),

        "verified": True,

        "verified_at": (
            verified
            .verified_at
            .isoformat()
        ),
    }


def generate_final_output(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Build a clean website-ready response."""

    request = state.get(
        "request"
    )

    if request is None:
        return {
            "final_response": None,
            "execution_log": [
                (
                    "Final response could not be "
                    "generated because the request "
                    "was invalid."
                )
            ],
        }

    ranked_results = list(
        state.get(
            "ranked_results",
            [],
        )
    )

    final_results = [
        _ranked_result_to_output(
            ranked
        )
        for ranked
        in ranked_results[
            : request.max_results
        ]
    ]

    response = {
        "request": (
            request.model_dump(
                mode="json"
            )
        ),

        "result_count": len(
            final_results
        ),

        "results": final_results,

        "warnings": list(
            state.get(
                "warnings",
                [],
            )
        ),

        "errors": list(
            state.get(
                "errors",
                [],
            )
        ),
    }

    return {
        "final_response": response,
        "execution_log": [
            "Final response generated."
        ],
    }

def find_scholar_profiles(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Find Google Scholar profiles for scored researchers."""

    scored_results = list(
        state.get(
            "scored_results",
            [],
        )
    )

    if not scored_results:
        return {
            "scored_results": [],
            "execution_log": [
                (
                    "Google Scholar search completed: "
                    "0 researchers checked."
                )
            ],
        }

    client = create_search_client()

    updated_results = []
    found_count = 0
    failed_searches = 0

    for scored in scored_results:
        researcher = (
            scored
            .verified_researcher
            .candidate
        )

        try:
            scholar = (
                find_google_scholar_profile(
                    researcher_name=(
                        researcher.full_name
                    ),
                    university_name=(
                        researcher.university_name
                    ),
                    client=client,
                )
            )

        except Exception:
            scholar = None
            failed_searches += 1

        scholar_url = (
            scholar.scholar_url
            if scholar is not None
            else None
        )

        if scholar_url:
            found_count += 1

        updated_results.append(
            scored.model_copy(
                update={
                    "google_scholar_url": (
                        scholar_url
                    )
                }
            )
        )

    result: dict[str, object] = {
        "scored_results": (
            updated_results
        ),
        "execution_log": [
            (
                "Google Scholar search "
                f"completed: {found_count} "
                f"of {len(scored_results)} "
                "profiles found."
            )
        ],
    }

    if failed_searches:
        result["warnings"] = [
            (
                "Google Scholar search "
                f"failed for {failed_searches} "
                "researchers."
            )
        ]

    return result


def find_research_projects(
    state: ResearchGraphState,
) -> dict[str, object]:
    """Find one central research-degree portal per university."""

    scored_results = list(
        state.get(
            "scored_results",
            [],
        )
    )

    if not scored_results:
        return {
            "scored_results": [],
            "execution_log": [
                (
                    "Research-degree portal search "
                    "completed: 0 universities checked."
                )
            ],
        }

    client = create_search_client()

    portal_cache: dict[
        str,
        ResearchDegreePortal | None,
    ] = {}

    updated_results = []

    found_count = 0
    failed_searches = 0

    for scored in scored_results:
        researcher = (
            scored
            .verified_researcher
            .candidate
        )

        domain = (
            researcher
            .official_domain
            .casefold()
        )

        if domain not in portal_cache:
            try:
                portal = (
                    find_research_degree_portal(
                        university_name=(
                            researcher.university_name
                        ),
                        official_domain=(
                            researcher.official_domain
                        ),
                        client=client,
                    )
                )

            except Exception:
                portal = None
                failed_searches += 1

            portal_cache[domain] = portal

            if portal is not None:
                found_count += 1

        updated_results.append(
            scored.model_copy(
                update={
                    "research_degree_portal": (
                        portal_cache[domain]
                    )
                }
            )
        )

    result: dict[str, object] = {
        "scored_results": updated_results,
        "execution_log": [
            (
                "Research-degree portal search "
                f"completed: {len(portal_cache)} "
                "universities checked, "
                f"{found_count} portals found."
            )
        ],
    }

    if failed_searches:
        result["warnings"] = [
            (
                "Research-degree portal search "
                f"failed for {failed_searches} "
                "universities."
            )
        ]

    return result