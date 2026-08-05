import pytest

from research_finder import nodes as nodes_module
from research_finder.official_page_search import (
    execute_official_searches,
)
from research_finder.search_queries import (
    OfficialSearchQuery,
    SearchTarget,
)
from research_finder.web_search import (
    WebSearchError,
    WebSearchRequest,
    WebSearchResult,
)


class FakeSearchClient:
    """Return controlled search responses."""

    def __init__(
        self,
        responses: list[object],
    ) -> None:
        self.responses = responses
        self.requests: list[WebSearchRequest] = []

    def search(
        self,
        request: WebSearchRequest,
    ) -> list[WebSearchResult]:
        self.requests.append(request)

        response = self.responses.pop(0)

        if isinstance(response, Exception):
            raise response

        assert isinstance(response, list)

        return response


def create_query(
    target: SearchTarget,
    suffix: str = "",
) -> OfficialSearchQuery:
    """Create one official-domain query."""

    return OfficialSearchQuery(
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        target=target,
        topics=["Reinforcement learning"],
        query=(f'site:deakin.edu.au "Reinforcement learning" {suffix}'),
    )


def create_result(
    url: str,
    rank: int = 1,
) -> WebSearchResult:
    """Create one normalised web result."""

    return WebSearchResult(
        title="Research page",
        url=url,
        snippet="Research information.",
        rank=rank,
    )


def test_keeps_only_official_domain_results() -> None:
    client = FakeSearchClient(
        responses=[
            [
                create_result("https://www.deakin.edu.au/research/profile"),
                create_result(
                    "https://www.linkedin.com/in/example",
                    rank=2,
                ),
            ]
        ]
    )

    outcome = execute_official_searches(
        search_queries=[
            create_query(
                SearchTarget.RESEARCHER,
                "researcher",
            )
        ],
        target=SearchTarget.RESEARCHER,
        client=client,
    )

    assert len(outcome.pages) == 1
    assert outcome.pages[0].official_domain == ("deakin.edu.au")
    assert outcome.attempted_queries == 1
    assert outcome.failed_queries == 0


def test_removes_duplicate_page_urls() -> None:
    client = FakeSearchClient(
        responses=[
            [
                create_result("https://www.deakin.edu.au/research/profile"),
                create_result(
                    "https://www.deakin.edu.au/research/profile/",
                    rank=2,
                ),
            ]
        ]
    )

    outcome = execute_official_searches(
        search_queries=[
            create_query(
                SearchTarget.RESEARCHER,
                "researcher",
            )
        ],
        target=SearchTarget.RESEARCHER,
        client=client,
    )

    assert len(outcome.pages) == 1


def test_search_continues_after_query_failure() -> None:
    client = FakeSearchClient(
        responses=[
            WebSearchError("Temporary failure"),
            [create_result("https://research.deakin.edu.au/project")],
        ]
    )

    outcome = execute_official_searches(
        search_queries=[
            create_query(
                SearchTarget.PROJECT,
                "project one",
            ),
            create_query(
                SearchTarget.PROJECT,
                "project two",
            ),
        ],
        target=SearchTarget.PROJECT,
        client=client,
    )

    assert outcome.attempted_queries == 2
    assert outcome.failed_queries == 1
    assert len(outcome.pages) == 1


def test_executes_only_requested_target() -> None:
    client = FakeSearchClient(
        responses=[[create_result("https://www.deakin.edu.au/research/profile")]]
    )

    outcome = execute_official_searches(
        search_queries=[
            create_query(
                SearchTarget.RESEARCHER,
                "researcher",
            ),
            create_query(
                SearchTarget.LAB,
                "laboratory",
            ),
        ],
        target=SearchTarget.RESEARCHER,
        client=client,
    )

    assert outcome.attempted_queries == 1
    assert len(client.requests) == 1


def test_researcher_node_stores_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeSearchClient(
        responses=[[create_result("https://www.deakin.edu.au/research/profile")]]
    )

    monkeypatch.setattr(
        nodes_module,
        "create_search_client",
        lambda: client,
    )

    result = nodes_module.search_researchers(
        {
            "search_queries": [
                create_query(
                    SearchTarget.RESEARCHER,
                    "researcher",
                )
            ],
            "search_attempt_count": 0,
        }
    )

    assert len(result["researcher_pages"]) == 1
    assert result["search_attempt_count"] == 1
    assert result["execution_log"] == [
        ("Researcher search completed: 1 queries attempted, 1 official pages found.")
    ]
