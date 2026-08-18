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
                    "https://www.monash.edu/"
                    "medicine/scs/"
                    "available-research-projects"
                ),
                snippet=(
                    "Available PhD and graduate "
                    "research projects."
                ),
                rank=1,
            ),
            WebSearchResult(
                title="Graduate Research",
                url=(
                    "https://www.monash.edu/"
                    "graduate-research"
                ),
                snippet=(
                    "PhD, Master's by Research "
                    "and available projects."
                ),
                rank=2,
            ),
        ]


def test_prefers_central_university_portal() -> None:
    portal = (
        find_research_degree_portal(
            university_name=(
                "Monash University"
            ),
            official_domain=(
                "monash.edu"
            ),
            client=FakeSearchClient(),
        )
    )

    assert portal is not None

    assert (
        portal.title
        == "Graduate Research"
    )

    assert (
        str(portal.url)
        == (
            "https://www.monash.edu/"
            "graduate-research"
        )
    )