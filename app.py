from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
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


def _render_evidence_items(
    title: str,
    items: list[dict[str, Any]],
) -> None:
    if not items:
        return

    st.markdown(f"**{title}**")

    for item in items:
        name = item.get("name") or "Untitled"
        url = item.get("url")
        year = item.get("year")

        label = name

        if year:
            label = f"{name} ({year})"

        if url:
            st.markdown(f"- [{label}]({url})")
        else:
            st.markdown(f"- {label}")


def _render_researcher_card(
    researcher: dict[str, Any],
) -> None:
    with st.container(border=True):
        header_column, score_column = st.columns(
            [4, 1]
        )

        with header_column:
            rank = researcher.get(
                "rank",
                "",
            )

            name = researcher.get(
                "researcher_name",
                "Unknown researcher",
            )

            st.subheader(
                f"#{rank} {name}"
            )

            academic_title = researcher.get(
                "academic_title"
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

            if researcher.get("verified"):
                st.success(
                    "Verified using official "
                    "university evidence."
                )

        with score_column:
            score = int(
                researcher.get(
                    "relevance_score",
                    0,
                )
            )

            st.metric(
                "Relevance",
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

        research_interests = researcher.get(
            "research_interests",
            [],
        )

        if research_interests:
            st.markdown(
                "**Research interests**"
            )

            st.write(
                " • ".join(
                    research_interests
                )
            )

        profile_summary = researcher.get(
            "profile_summary"
        )

        if profile_summary:
            st.markdown(
                "**Profile summary**"
            )

            st.write(
                profile_summary
            )

        evidence_column, source_column = (
            st.columns(2)
        )

        with evidence_column:
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
                "Other projects",
                researcher.get(
                    "unknown_projects",
                    [],
                ),
            )

            _render_evidence_items(
                "Relevant publications",
                researcher.get(
                    "publications",
                    [],
                ),
            )

            _render_evidence_items(
                "Labs / research groups",
                researcher.get(
                    "labs",
                    [],
                ),
            )

        with source_column:
            st.markdown(
                "**Contact & sources**"
            )

            email = researcher.get(
                "public_email"
            )

            if email:
                st.code(email)
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

        with st.expander(
            "Why this researcher matched"
        ):
            matched_terms = researcher.get(
                "matched_terms",
                [],
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

            explanation = researcher.get(
                "match_explanation"
            )

            if explanation:
                st.markdown(
                    "**Explanation**"
                )

                st.write(
                    explanation
                )

            breakdown = researcher.get(
                "score_breakdown",
                {},
            )

            if breakdown:
                st.markdown(
                    "**Score breakdown**"
                )

                labels = {
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
                        "Labs / groups"
                    ),
                    "previous_projects": (
                        "Previous projects"
                    ),
                    "unknown_projects": (
                        "Other projects"
                    ),
                }

                for key, value in (
                    breakdown.items()
                ):
                    label = labels.get(
                        key,
                        key.replace(
                            "_",
                            " ",
                        ).title(),
                    )

                    st.write(
                        f"{label}: {value}"
                    )

        with st.expander(
            "Verification details"
        ):
            verified_at = researcher.get(
                "verified_at"
            )

            if verified_at:
                st.write(
                    f"Verified at: "
                    f"{verified_at}"
                )

            else:
                st.write(
                    "Verification timestamp "
                    "not available."
                )


def _render_response(
    response: dict[str, Any],
) -> None:
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
            "The search completed with "
            "errors."
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
        f"Found {len(results)} "
        f"researcher"
        f"{'s' if len(results) != 1 else ''}."
    )

    st.header(
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


st.set_page_config(
    page_title=(
        "Research Supervisor "
        "and Lab Finder"
    ),
    page_icon="🔎",
    layout="wide",
)


st.title(
    "Research Supervisor "
    "and Lab Finder"
)

st.write(
    "Find Australian university "
    "researchers related to your "
    "research topic using official "
    "university evidence."
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

    research_topic = st.text_input(
        "Research topic",
        placeholder=(
            "e.g. Reinforcement learning"
        ),
    )

    max_results = st.number_input(
        "Maximum results",
        min_value=1,
        max_value=20,
        value=3,
        step=1,
    )

    submitted = st.form_submit_button(
        "Search researchers",
        type="primary",
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

        timer = st.empty()

        start_time = (
            time.perf_counter()
        )

        try:
            with ThreadPoolExecutor(
                max_workers=1
            ) as executor:
                future = executor.submit(
                    graph.invoke,
                    {
                        "raw_request": request,
                    },
                )

                while not future.done():
                    elapsed = int(
                        time.perf_counter()
                        - start_time
                    )

                    timer.markdown(
                        f"### {elapsed}s"
                    )

                    time.sleep(1)

                output = future.result()

            elapsed_seconds = (
                time.perf_counter()
                - start_time
            )

        except Exception as exc:
            timer.empty()

            st.error(
                "Search failed."
            )

            st.exception(
                exc
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

            timer.success(
                f"Completed in "
                f"{elapsed_seconds:.1f}s"
            )


response = st.session_state.get(
    "search_result"
)

if response is not None:
    elapsed_seconds = (
        st.session_state.get(
            "search_elapsed_seconds"
        )
    )

    if (
        elapsed_seconds is not None
        and not submitted
    ):
        st.caption(
            f"Search time: "
            f"{elapsed_seconds:.1f}s"
        )

    _render_response(
        response
    )