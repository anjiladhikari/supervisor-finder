import httpx
import pytest

from research_finder import nodes as nodes_module
from research_finder.official_page_search import (
    OfficialSearchPage,
)
from research_finder.search_queries import (
    SearchTarget,
)
from research_finder.web_content import (
    DownloadedWebPage,
    WebPageDownloader,
    WebPageDownloadError,
    clean_html_content,
    download_official_pages,
)


def create_page(
    url: str = ("https://www.deakin.edu.au/research/profile"),
) -> OfficialSearchPage:
    """Create one official search page."""

    return OfficialSearchPage(
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        target=SearchTarget.RESEARCHER,
        title="Research profile",
        url=url,
        snippet="Research information.",
        result_rank=1,
        search_query=('site:deakin.edu.au "reinforcement learning" researcher'),
    )


def create_document() -> DownloadedWebPage:
    """Create one downloaded document."""

    return DownloadedWebPage(
        university_name="Deakin University",
        official_domain="deakin.edu.au",
        target=SearchTarget.RESEARCHER,
        source_url=("https://www.deakin.edu.au/research/profile"),
        final_url=("https://www.deakin.edu.au/research/profile"),
        page_title="Research profile",
        content=("Dr Example researches reinforcement learning."),
        content_type="text/html",
        status_code=200,
    )


def test_clean_html_removes_navigation_and_scripts() -> None:
    html = """
    <html>
      <head>
        <title> Example Profile </title>
        <script>bad script</script>
      </head>
      <body>
        <header>University menu</header>
        <main>
          <h1>Dr Example</h1>
          <p>Reinforcement learning research.</p>
        </main>
        <footer>Footer links</footer>
      </body>
    </html>
    """

    title, content = clean_html_content(html)

    assert title == "Example Profile"
    assert "Dr Example" in content
    assert "Reinforcement learning research." in content
    assert "bad script" not in content
    assert "University menu" not in content
    assert "Footer links" not in content


def test_downloader_returns_clean_document() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            headers={"content-type": ("text/html; charset=utf-8")},
            text="""
                <html>
                  <title>Research profile</title>
                  <body>
                    <main>
                      Dr Example studies reinforcement learning.
                    </main>
                  </body>
                </html>
            """,
        )

    downloader = WebPageDownloader(
        transport=httpx.MockTransport(handler),
        sleeper=lambda _: None,
    )

    document = downloader.download(create_page())

    assert document.status_code == 200
    assert document.page_title == "Research profile"
    assert "Dr Example" in document.content
    assert document.official_domain == ("deakin.edu.au")


def test_downloader_rejects_non_html() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            request=request,
            headers={"content-type": "application/pdf"},
            content=b"%PDF-example",
        )

    downloader = WebPageDownloader(
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        WebPageDownloadError,
        match="Unsupported content type",
    ):
        downloader.download(create_page())


def test_downloader_rejects_external_redirect() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        if request.url.host == ("www.deakin.edu.au"):
            return httpx.Response(
                302,
                request=request,
                headers={"location": ("https://example.com/profile")},
            )

        return httpx.Response(
            200,
            request=request,
            headers={"content-type": "text/html"},
            text="<main>External content</main>",
        )

    downloader = WebPageDownloader(
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        WebPageDownloadError,
        match="redirected outside",
    ):
        downloader.download(create_page())


def test_batch_continues_after_one_failure() -> None:
    class FakeDownloader:
        def __init__(self) -> None:
            self.calls = 0

        def download(
            self,
            _: OfficialSearchPage,
        ) -> DownloadedWebPage:
            self.calls += 1

            if self.calls == 1:
                raise WebPageDownloadError("Simulated failure")

            return create_document()

    outcome = download_official_pages(
        pages=[
            create_page("https://www.deakin.edu.au/page-one"),
            create_page("https://www.deakin.edu.au/page-two"),
        ],
        downloader=FakeDownloader(),
    )

    assert outcome.attempted_pages == 2
    assert outcome.failed_pages == 1
    assert len(outcome.documents) == 1


def test_download_node_stores_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeDownloader:
        def download(
            self,
            _: OfficialSearchPage,
        ) -> DownloadedWebPage:
            return create_document()

    monkeypatch.setattr(
        nodes_module,
        "create_page_downloader",
        lambda: FakeDownloader(),
    )

    result = nodes_module.download_webpage_content(
        {
            "researcher_pages": [create_page()],
            "lab_pages": [],
            "project_pages": [],
            "publication_pages": [],
            "download_attempt_count": 0,
        }
    )

    assert len(result["researcher_documents"]) == 1
    assert result["download_attempt_count"] == 1
    assert result["execution_log"] == [
        ("Webpage download completed: 1 pages attempted, 1 documents created.")
    ]
