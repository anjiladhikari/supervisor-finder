from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class HealthState(TypedDict):
    """State used only to confirm that LangGraph is working."""

    message: str


def health_check(state: HealthState) -> HealthState:
    """Return an updated health-check message."""

    return {
        "message": f"{state['message']} | LangGraph is ready",
    }


def build_health_graph():
    """Build and compile the temporary health-check graph."""

    builder = StateGraph(HealthState)

    builder.add_node("health_check", health_check)

    builder.add_edge(START, "health_check")
    builder.add_edge("health_check", END)

    return builder.compile()


graph = build_health_graph()


if __name__ == "__main__":
    result = graph.invoke({"message": "Project foundation"})
    print(result)