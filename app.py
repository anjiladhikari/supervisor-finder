from __future__ import annotations

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


st.title(
    "Research Supervisor & Lab Finder"
)

st.write(
    "Find Australian university researchers, labs, "
    "projects and publications related to your research topic."
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
                options=["Australia"],
                disabled=True,
            )

            state = st.selectbox(
                "State or territory",
                options=AUSTRALIAN_STATES,
                help=(
                    "Choose All Australia to "
                    "search every supported university."
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
                        "Only the strongest matching "
                        "researchers will be returned."
                    ),
                )
            )

        research_topic = st.text_area(
            "Research topic",
            placeholder=(
                "Example: Reinforcement learning "
                "for early time-series classification"
            ),
            height=120,
            max_chars=300,
            help=(
                "Describe the research area you want "
                "to find researchers for."
            ),
        )

        submitted = (
            st.form_submit_button(
                "Find researchers",
                type="primary",
                icon=":material/search:",
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
            if state == "All Australia"
            else state
        )

        request = {
            "country": country,
            "state": selected_state,
            "research_topic": cleaned_topic,
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
            with st.spinner(
                "Searching official university sources..."
            ):
                output = graph.invoke(
                    {
                        "raw_request": request,
                    }
                )

        except Exception:
            st.error(
                "The search could not be completed. "
                "Please try again."
            )

        else:
            st.session_state[
                "search_result"
            ] = output.get(
                "final_response"
            )


response = st.session_state.get(
    "search_result"
)

if response is not None:
    result_count = response.get(
        "result_count",
        0,
    )

    if result_count:
        st.success(
            
                f"Search complete — "
                f"{result_count} researcher"
                f"{'s' if result_count != 1 else ''} found."
            
        )

    else:
        st.info(
            "Search completed, but no matching "
            "researchers were found."
        )

    with st.expander(
        "Workflow result",
    ):
        st.json(response)


st.divider()

st.caption(
    "Research Supervisor & Lab Finder • "
    "Built with LangGraph and Streamlit"
)