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


def _render_researcher_card(
    researcher: dict[str, Any],
) -> None:
    """Render one researcher result."""

    with st.container(border=True):
        header_column, score_column = (
            st.columns([4, 1])
        )

        rank = researcher.get(
            "rank",
            "",
        )

        name = researcher.get(
            "researcher_name",
            "Unknown researcher",
        )

        profile_url = researcher.get(
            "official_profile_url"
        )

        with header_column:
            if profile_url:
                st.markdown(
                    f"### #{rank} [{name}]"
                    f"({profile_url})"
                )
            else:
                st.markdown(
                    f"### #{rank} {name}"
                )

            academic_title = (
                researcher.get(
                    "academic_title"
                )
            )

            role = researcher.get(
                "role"
            )

            university = researcher.get(
                "university_name"
            )

            details = [
                value
                for value in [
                    academic_title,
                    role,
                    university,
                ]
                if value
            ]

            if details:
                st.caption(
                    " • ".join(details)
                )

            if researcher.get(
                "verified"
            ):
                st.caption(
                    "Verified from official "
                    "university profile"
                )

        with score_column:
            score = int(
                researcher.get(
                    "relevance_score",
                    0,
                )
            )

            st.metric(
                "Topic match",
                f"{score}/100",
                border=True,
            )

            st.progress(
                min(
                    max(score, 0),
                    100,
                )
                / 100
            )

        interests = researcher.get(
            "research_interests",
            [],
        )

        if interests:
            st.markdown(
                "**Research topics / interests**"
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

            st.write(summary)

        if profile_url:
            st.link_button(
                "Open official university profile",
                profile_url,
                icon=(
                    ":material/"
                    "open_in_new:"
                ),
            )

        with st.expander(
            "Why this researcher matched"
        ):
            keyword_score = int(
                researcher.get(
                    "keyword_score",
                    0,
                )
            )

            semantic_score = int(
                researcher.get(
                    "semantic_score",
                    0,
                )
            )

            score_columns = st.columns(2)

            with score_columns[0]:
                st.metric(
                    "Direct topic match",
                    f"{keyword_score}/100",
                )

            with score_columns[1]:
                st.metric(
                    "Related topic match",
                    f"{semantic_score}/100",
                )

            matched_terms = (
                researcher.get(
                    "matched_terms",
                    [],
                )
            )

            if matched_terms:
                st.markdown(
                    "**Matched terms**"
                )

                st.write(
                    ", ".join(
                        matched_terms
                    )
                )

            explanation = (
                researcher.get(
                    "match_explanation",
                    [],
                )
            )

            if isinstance(
                explanation,
                list,
            ):
                for item in explanation:
                    st.write(
                        f"- {item}"
                    )

            elif explanation:
                st.write(
                    explanation
                )


def _render_response(
    response: dict[str, Any],
) -> None:
    """Render workflow results."""

    errors = response.get(
        "errors",
        [],
    )

    warnings = response.get(
        "warnings",
        [],
    )

    results = response.get(
        "results",
        [],
    )

    if errors:
        st.error(
            "The search completed with errors."
        )

        with st.expander(
            "Error details"
        ):
            for error in errors:
                st.write(
                    f"- {error}"
                )

    if not results:
        st.info(
            "No matching researchers "
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
        f"Found {len(results)} "
        f"researcher"
        f"{'s' if len(results) != 1 else ''}."
    )

    st.header(
        "Researchers"
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


st.set_page_config(
    page_title=(
        "Australian Researcher Finder"
    ),
    page_icon="🔎",
    layout="wide",
)


st.title(
    "Australian Researcher Finder"
)

st.write(
    "Find researchers across Australian "
    "universities by research topic."
)

st.caption(
    "Researcher information is verified "
    "against official university profiles."
)


with st.container(border=True):
    st.header(
        "Find researchers"
    )

    with st.form(
        "research_search_form"
    ):
        country = st.text_input(
            "Country",
            value="Australia",
            disabled=True,
        )

        state = st.selectbox(
            "State",
            AUSTRALIAN_STATES,
            index=6,
        )

        research_topic = (
            st.text_input(
                "Research topic",
                placeholder=(
                    "e.g. Reinforcement learning"
                ),
            )
        )

        max_results = (
            st.number_input(
                "Maximum results",
                min_value=1,
                max_value=20,
                value=5,
                step=1,
            )
        )

        submitted = (
            st.form_submit_button(
                "Search researchers",
                type="primary",
            )
        )


if submitted:
    if not research_topic.strip():
        st.error(
            "Please enter a research topic."
        )

    else:
        selected_state = (
            None
            if state == "All Australia"
            else state
        )

        request = {
            "country": country,
            "state": selected_state,
            "research_topic": (
                research_topic.strip()
            ),
            "max_results": int(
                max_results
            ),
        }

        st.session_state[
            "search_result"
        ] = None

        st.session_state[
            "search_elapsed_seconds"
        ] = None

        start_time = (
            time.perf_counter()
        )

        try:
            with st.spinner(
                (
                    "Searching official "
                    "university researcher "
                    "profiles..."
                ),
                show_time=True,
            ):
                output = graph.invoke(
                    {
                        "raw_request": (
                            request
                        ),
                    }
                )

            elapsed_seconds = (
                time.perf_counter()
                - start_time
            )

        except Exception as exc:
            st.error(
                "Search failed."
            )

            st.exception(exc)

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
    elapsed_seconds = (
        st.session_state.get(
            "search_elapsed_seconds"
        )
    )

    if elapsed_seconds is not None:
        if elapsed_seconds >= 60:
            minutes = int(
                elapsed_seconds // 60
            )

            seconds = int(
                elapsed_seconds % 60
            )

            st.caption(
                "Search completed in "
                f"{minutes}m {seconds}s"
            )

        else:
            st.caption(
                "Search completed in "
                f"{elapsed_seconds:.1f}s"
            )

    _render_response(
        response
    )