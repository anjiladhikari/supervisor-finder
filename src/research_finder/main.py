from pprint import pprint

from research_finder.graph import graph


def main() -> None:
    """Run the workflow with a temporary local example."""

    output = graph.invoke(
        {
            "raw_request": {
                "country": "Australia",
                "state": "Victoria",
                "research_topic": (
                    "Reinforcement learning for "
                    "early time-series classification"
                ),
                "max_results": 5,
            }
        }
    )

    final_response = output["final_response"]

    if final_response is None:
        print("The workflow could not produce a valid response.")
        pprint(output)
        return

    pprint(final_response.model_dump(mode="json"))

    print("\nExecution log:")

    for message in output["execution_log"]:
        print(f"- {message}")


if __name__ == "__main__":
    main()