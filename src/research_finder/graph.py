from langgraph.graph import END, START, StateGraph

from research_finder.nodes import (
    broaden_search,
    download_webpage_content,
    expand_research_topic,
    extract_researcher_information,
    find_universities,
    generate_final_output,
    generate_search_queries,
    initialize_workflow,
    narrow_search,
    rank_results,
    remove_duplicates,
    score_relevance,
    search_researchers,
    validate_input,
    verify_current_affiliation,
    find_scholar_profiles,
)
from research_finder.routes import (
    route_after_researcher_search,
    route_after_search_query_generation,
    route_after_university_discovery,
    route_after_validation,
)
from research_finder.state import (
    ResearchGraphInput,
    ResearchGraphOutput,
    ResearchGraphState,
)


def build_research_graph():
    """Build and compile the research-supervisor workflow."""

    builder = StateGraph(
        ResearchGraphState,
        input_schema=ResearchGraphInput,
        output_schema=ResearchGraphOutput,
    )

    builder.add_node("initialize_workflow", initialize_workflow)
    builder.add_node("validate_input", validate_input)
    builder.add_node("expand_research_topic", expand_research_topic)
    builder.add_node("find_universities", find_universities)
    builder.add_node("generate_search_queries", generate_search_queries)
    builder.add_node(
    "broaden_search",
    broaden_search,
)

    builder.add_node(
        "narrow_search",
        narrow_search,
    )
    builder.add_node("search_researchers", search_researchers)
    builder.add_node(
        "verify_current_affiliation",
        verify_current_affiliation,
    )
    builder.add_node(
        "download_webpage_content",
        download_webpage_content,
    )
  

    builder.add_node(
        "extract_researcher_information",
        extract_researcher_information,
    )
 
    builder.add_node("score_relevance", score_relevance)
    builder.add_node("find_scholar_profiles", find_scholar_profiles)
    builder.add_edge("score_relevance", "find_scholar_profiles")
    builder.add_edge("find_scholar_profiles", "remove_duplicates")
    builder.add_node("remove_duplicates", remove_duplicates)


    builder.add_node("rank_results", rank_results)
    builder.add_node("generate_final_output", generate_final_output)

    builder.add_edge(START, "initialize_workflow")
    builder.add_edge("initialize_workflow", "validate_input")

    builder.add_conditional_edges(
        "validate_input",
        route_after_validation,
    )

    builder.add_edge(
        "expand_research_topic",
        "find_universities",
    )

    builder.add_conditional_edges(
        "find_universities",
        route_after_university_discovery,
    )
    builder.add_conditional_edges(
        "generate_search_queries",
        route_after_search_query_generation,
    )
    builder.add_conditional_edges(
    "search_researchers",
    route_after_researcher_search,
)

    builder.add_edge(
    "broaden_search",
    "generate_search_queries",
)

    builder.add_edge(
    "narrow_search",
    "generate_search_queries",
)



    builder.add_edge(
        "download_webpage_content",
        "extract_researcher_information",
    )

  
    builder.add_edge(
        "extract_researcher_information",
        "verify_current_affiliation",
    )

    builder.add_edge(
    "verify_current_affiliation",
    "score_relevance",
)

    builder.add_edge("score_relevance", "remove_duplicates")
    builder.add_edge("remove_duplicates", "rank_results")
    
    builder.add_edge("rank_results", "generate_final_output")
    builder.add_edge("generate_final_output", END)

    return builder.compile()


graph = build_research_graph()
