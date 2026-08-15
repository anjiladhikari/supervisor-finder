from __future__ import annotations
import time
from typing import Any

import streamlit as st

from research_finder.graph import graph

AUSTRALIAN_STATES = [
    "All Australia",
    "Australian Capital Territory",
    "New South Wales",
    "Northern Territory",
    "Queensland",
    "South Australia",
    "Tasmania",
    "Victoria",
    "Western Australia",
]


st.set_page_config(
    page_title="Research Supervisor Finder",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _render_evidence_items(
    title: str,
    items: list[dict[str, Any]],
) -> None:
    """Render project, lab or publication links."""

    if not items:
        return

    st.markdown(f"**{title}**")

    for item in items:
        name = item.get(
            "name",
            "Official source",
        )

        url = item.get(
            "url"
        )

        year = item.get(
            "year"
        )

        label = (
            f"{name} ({year})"
            if year
            else str(name)
        )

        if url:
            st.markdown(
                f"- [{label}]({url})"
            )
        else:
            st.markdown(
                f"- {label}"
            )


def _render_researcher_card(
    researcher: dict[str, Any],
) -> None:
    """Render one ranked researcher."""

    rank = researcher.get(
        "rank",
        "-",
    )

    name = researcher.get(
        "researcher_name",
        "Unknown researcher",
    )

    university = researcher.get(
        "university_name",
        "Unknown university",
    )

    academic_title = researcher.get(
        "academic_title"
    )

    role = researcher.get(
        "role"
    )

    score = int(
        researcher.get(
            "relevance_score",
            0,
        )
    )

    with st.container(
        border=True,
    ):
        header_col, score_col = (
            st.columns(
                [4, 1]
            )
        )

        with header_col:
            st.subheader(
                f"#{rank} {name}"
            )

            identity_parts = [
                part
                for part in [
                    academic_title,
                    role,
                    university,
                ]
                if part
            ]

            if identity_parts:
                st.caption(
                    " • ".join(
                        identity_parts
                    )
                )

            if researcher.get(
                "verified"
            ):
                st.success(
                    (
                        "Verified using official "
                        "university evidence."
                    ),
                    icon=":material/verified:",
                )

        with score_col:
            st.metric(
                "Relevance",
                f"{score}/100",
                border=True,
            )

            st.progress(
                min(
                    max(
                        score / 100,
                        0.0,
                    ),
                    1.0,
                )
            )

        interests = researcher.get(
            "research_interests",
            [],
        )

        if interests:
            st.markdown(
                "**Research interests**"
            )

            st.write(
                " • ".join(
                    interests
                )
            )

        summary = researcher.get(
            "profile_summary"
        )

        if summary:
            st.markdown(
                "**Profile summary**"
            )

            st.write(
                summary
            )

        st.divider()

        left_col, right_col = (
            st.columns(
                [2, 1]
            )
        )

        with left_col:
            _render_evidence_items(
                "Current projects",
                researcher.get(
                    "current_projects",
                    [],
                ),
            )

            _render_evidence_items(
                "Previous projects",
                researcher.get(
                    "previous_projects",
                    [],
                ),
            )

            _render_evidence_items(
                (
                    "Projects with "
                    "unknown status"
                ),
                researcher.get(
                    "unknown_projects",
                    [],
                ),
            )

            _render_evidence_items(
                "Publications",
                researcher.get(
                    "publications",
                    [],
                ),
            )

            _render_evidence_items(
                "Labs and research groups",
                researcher.get(
                    "labs",
                    [],
                ),
            )

        with right_col:
            st.markdown(
                "**Contact & sources**"
            )

            public_email = researcher.get(
                "public_email"
            )

            if public_email:
                st.markdown(
                    
                        "**University email**  \n"
                        f"`{public_email}`"
                    
                )
            else:
                st.caption(
                    
                        "No verified public "
                        "university email found."
                    
                )

            profile_url = researcher.get(
                "official_profile_url"
            )

            if profile_url:
                st.link_button(
                    "Official university profile",
                    profile_url,
                    icon=(
                        ":material/"
                        "open_in_new:"
                    ),
                    width="stretch",
                )

        explanations = researcher.get(
            "match_explanation",
            [],
        )

        matched_terms = researcher.get(
            "matched_terms",
            [],
        )

        if (
            explanations
            or matched_terms
        ):
            with st.expander(
                "Why this researcher matched"
            ):
                if matched_terms:
                    st.markdown(
                        "**Matched terms**"
                    )

                    st.write(
                        ", ".join(
                            matched_terms
                        )
                    )

                if explanations:
                    st.markdown(
                        "**Score explanation**"
                    )

                    for explanation in (
                        explanations
                    ):
                        st.write(
                            f"- {explanation}"
                        )

                breakdown = researcher.get(
                    "score_breakdown",
                    {},
                )

                if breakdown:
                    st.markdown(
                        "**Score breakdown**"
                    )

                    score_labels = {
                        "research_interests": (
                            "Research interests"
                        ),
                        "current_projects": (
                            "Current projects"
                        ),
                        "publications": (
                            "Publications"
                        ),
                        "labs": (
                            "Labs/groups"
                        ),
                        "previous_projects": (
                            "Previous projects"
                        ),
                        "unknown_projects": (
                            "Unknown-status projects"
                        ),
                    }

                    for key, label in (
                        score_labels.items()
                    ):
                        points = (
                            breakdown.get(
                                key,
                                0,
                            )
                        )

                        st.write(
                            f"- {label}: "
                            f"{points} points"
                        )

        verified_at = researcher.get(
            "verified_at"
        )

        if verified_at:
            with st.expander(
                "Verification details"
            ):
                st.caption(
                    
                        "Verification timestamp: "
                        f"{verified_at}"
                    
                )


def _render_response(
    response: dict[str, Any],
) -> None:
    """Render the complete workflow response."""

    results = response.get(
        "results",
        [],
    )

    result_count = response.get(
        "result_count",
        len(results),
    )

    errors = response.get(
        "errors",
        [],
    )

    warnings = response.get(
        "warnings",
        [],
    )

    if errors:
        st.error(
            "The workflow completed with errors."
        )

        with st.expander(
            "Errors",
        ):
            for error in errors:
                st.write(
                    f"- {error}"
                )

    if not results:
        st.info(
            
                "Search completed, but no "
                "strong matching researchers "
                "were found."
            
        )

        if warnings:
            with st.expander(
                "Search details"
            ):
                for warning in warnings:
                    st.write(
                        f"- {warning}"
                    )

        return

    st.success(
        
            f"Search complete — "
            f"{result_count} researcher"
            f"{'s' if result_count != 1 else ''} "
            "found."
        
    )

    st.subheader(
        "Strongest matches"
    )

    for researcher in results:
        _render_researcher_card(
            researcher
        )

    if warnings:
        with st.expander(
            "Search warnings"
        ):
            for warning in warnings:
                st.write(
                    f"- {warning}"
                )


st.title(
    "Research Supervisor & Lab Finder"
)

st.write(
    
        "Find Australian university researchers, "
        "labs, projects and publications related "
        "to your research topic."
    
)

st.caption(
    "Results are based on official university sources."
)


with st.container(
    border=True,
):
    st.subheader(
        "Find researchers"
    )

    with st.form(
        "research_search_form",
    ):
        location_col, results_col = (
            st.columns(2)
        )

        with location_col:
            country = st.selectbox(
                "Country",
                options=[
                    "Australia"
                ],
                disabled=True,
            )

            state = st.selectbox(
                "State or territory",
                options=(
                    AUSTRALIAN_STATES
                ),
                help=(
                    "Choose All Australia "
                    "to search every "
                    "supported university."
                ),
            )

        with results_col:
            max_results = (
                st.number_input(
                    "Maximum results",
                    min_value=1,
                    max_value=20,
                    value=5,
                    step=1,
                    help=(
                        "Only the strongest "
                        "matching researchers "
                        "will be returned."
                    ),
                )
            )

        research_topic = (
            st.text_area(
                "Research topic",
                placeholder=(
                    "Example: Reinforcement "
                    "learning for early "
                    "time-series classification"
                ),
                height=120,
                max_chars=300,
                help=(
                    "Describe the research "
                    "area you want to find "
                    "researchers for."
                ),
            )
        )

        submitted = (
            st.form_submit_button(
                "Find researchers",
                type="primary",
                icon=(
                    ":material/search:"
                ),
                width="stretch",
            )
        )


if submitted:
    cleaned_topic = " ".join(
        research_topic.split()
    )

    if len(cleaned_topic) < 3:
        st.error(
            
                "Please enter a research topic "
                "with at least 3 characters."
            
        )

    else:
        selected_state = (
            None
            if state
            == "All Australia"
            else state
        )

        request = {
            "country": country,
            "state": selected_state,
            "research_topic": (
                cleaned_topic
            ),
            "max_results": int(
                max_results
            ),
        }

        st.session_state[
            "search_request"
        ] = request

        st.session_state.pop(
            "search_result",
            None,
        )

        try:
            start_time = time.perf_counter()
            with st.spinner(
                
                    "Searching official "
                    "university sources..."
                
            ):
                output = graph.invoke(
                    {
                        "raw_request": (
                            request
                        ),
                    }
                )

            elapsed_seconds = (time.perf_counter() - start_time)
            

          

        except Exception:
            st.error(
                
                    "The search could not "
                    "be completed. "
                    "Please try again."
                
            )

        else:
            st.session_state[
                "search_result"
            ] = output.get(
                "final_response"
            )
            st.session_state[
                "search_elapsed_seconds"
            ] = elapsed_seconds


response = st.session_state.get(
    "search_result"
)

if response is not None:
    elapsed_seconds = st.session_state.get(
        "search_elapsed_seconds"
    )

    if elapsed_seconds is not None:
        if elapsed_seconds >= 60:
            minutes = int(
                elapsed_seconds // 60
            )

            seconds = int(
                elapsed_seconds % 60
            )

            st.info(
                f"Search time: "
                f"{minutes}m {seconds}s"
            )
        else:
            st.info(
                f"Search time: "
                f"{elapsed_seconds:.1f}s"
            )

    _render_response(
        response
    )


st.divider()

st.caption(
    
        "Research Supervisor & Lab Finder • "
        "Built with LangGraph and Streamlit"
    
)