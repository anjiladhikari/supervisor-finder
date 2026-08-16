from research_finder.research_projects import (
    find_research_degree_portal,
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
                    "Available research projects"
                ),
                url=(
                    "https://www.utas.edu.au/"
                    "research/degrees/"
                    "available-projects"
                ),
                snippet=(
                    "Explore available PhD "
                    "and research degree projects."
                ),
                rank=1,
            ),
            WebSearchResult(
                title=(
                    "One individual PhD project"
                ),
                url=(
                    "https://www.utas.edu.au/"
                    "research/project/example"
                ),
                snippet=(
                    "Individual PhD project."
                ),
                rank=2,
            ),
            WebSearchResult(
                title=(
                    "Wrong university"
                ),
                url=(
                    "https://example.com/"
                    "available-projects"
                ),
                snippet=(
                    "Available research projects."
                ),
                rank=3,
            ),
        ]


def test_finds_central_research_degree_portal() -> None:
    portal = (
        find_research_degree_portal(
            university_name=(
                "University of Tasmania"
            ),
            official_domain=(
                "utas.edu.au"
            ),
            client=FakeSearchClient(),
        )
    )

    assert portal is not None

    assert (
        portal.title
        == "Available research projects"
    )

    assert (
        str(portal.url)
        == (
            "https://www.utas.edu.au/"
            "research/degrees/"
            "available-projects"
        )
    )