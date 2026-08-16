from research_finder.scholar import (
    find_google_scholar_profile,
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
                title="Jane Smith - Google Scholar",
                url=(
                    "https://scholar.google.com/"
                    "citations?user=abc123"
                ),
                snippet="Jane Smith",
                rank=1,
            )
        ]


def test_finds_google_scholar_profile() -> None:
    profile = find_google_scholar_profile(
        researcher_name="Jane Smith",
        university_name="Deakin University",
        client=FakeSearchClient(),
    )

    assert profile is not None

    assert (
        profile.scholar_url
        == "https://scholar.google.com/"
        "citations?user=abc123"
    )