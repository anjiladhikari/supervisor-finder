from research_finder.main import graph


def test_health_graph() -> None:
    result = graph.invoke({"message": "Testing"})

    assert result["message"] == "Testing | LangGraph is ready"