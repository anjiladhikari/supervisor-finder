from research_finder.research_projects import (
    find_research_degree_projects,
)
from research_finder.web_search import (
    WebSearchResult,
)


class FakeSearchClient:
    def search(
        self,
        request,
    ):
        return [
            WebSearchResult(
                title=(
                    "Available PhD Projects"
                ),
                url=(
                    "https://www.deakin.edu.au/"
                    "research/research-degrees/"
                    "available-projects"
                ),
                snippet=(
                    "Available research projects"
                ),
                rank=1,
            ),
            WebSearchResult(
                title="Wrong university",
                url=(
                    "https://example.com/phd"
                ),
                snippet="PhD projects",
                rank=2,
            ),
        ]


def test_finds_only_same_university_projects() -> None:
    projects = (
        find_research_degree_projects(
            research_topic=(
                "Reinforcement learning"
            ),
            university_name=(
                "Deakin University"
            ),
            official_domain=(
                "deakin.edu.au"
            ),
            client=FakeSearchClient(),
        )
    )

    assert len(projects) == 1

    assert (
        projects[0].title
        == "Available PhD Projects"
    )

    assert (
        "deakin.edu.au"
        in projects[0].url
    )