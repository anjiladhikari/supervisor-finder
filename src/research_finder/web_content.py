from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from html import unescape
from typing import Protocol
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import Field, HttpUrl

from research_finder.models import StrictModel
from research_finder.official_page_search import (
    OfficialSearchPage,
)
from research_finder.search_queries import SearchTarget


class WebPageDownloadError(RuntimeError):
    """An official webpage could not be downloaded."""


class DownloadedWebPage(StrictModel):
    """Clean webpage content ready for extraction."""

    university_name: str = Field(
        min_length=2,
        max_length=200,
    )
    official_domain: str = Field(
        min_length=4,
        max_length=255,
    )
    target: SearchTarget

    source_url: HttpUrl
    final_url: HttpUrl

    page_title: str = Field(
        min_length=1,
        max_length=500,
    )
    content: str = Field(
        min_length=1,
        max_length=50_000,
    )
    content_type: str = Field(
        min_length=1,
        max_length=100,
    )
    status_code: int = Field(
        ge=200,
        lt=400,
    )
    downloaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class PageDownloadOutcome:
    """Results from downloading a group of pages."""

    documents: tuple[DownloadedWebPage, ...]
    attempted_pages: int
    failed_pages: int


class PageDownloader(Protocol):
    """Interface used by the LangGraph node."""

    def download(
        self,
        page: OfficialSearchPage,
    ) -> DownloadedWebPage:
        """Download and clean one official webpage."""


Sleeper = Callable[[float], None]


_BLOCKED_TAGS = (
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "svg",
    "canvas",
    "iframe",
)


def _normalise_text(value: str) -> str:
    """Collapse repeated whitespace."""

    return " ".join(unescape(value).split())


def _uses_official_domain(
    url: str,
    official_domain: str,
) -> bool:
    """Check whether a URL belongs to a university domain."""

    hostname = urlparse(url).hostname

    if hostname is None:
        return False

    normalised_hostname = hostname.casefold().removeprefix("www.")
    normalised_domain = official_domain.casefold().removeprefix("www.")

    return normalised_hostname == normalised_domain or normalised_hostname.endswith(
        f".{normalised_domain}"
    )


def clean_html_content(
    html: str,
    *,
    max_characters: int = 30_000,
) -> tuple[str, str]:
    """Extract a clean title and readable webpage text."""

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    if soup.title is not None:
        title = _normalise_text(soup.title.get_text(" ", strip=True))
    else:
        title = ""

    for tag in soup.find_all(_BLOCKED_TAGS):
        tag.decompose()

    content_root = soup.find("main") or soup.find("article") or soup.body or soup

    lines: list[str] = []
    previous_line: str | None = None

    for item in content_root.stripped_strings:
        line = _normalise_text(str(item))

        if not line or line == previous_line:
            continue

        lines.append(line)
        previous_line = line

    content = "\n".join(lines)
    content = content[:max_characters].strip()

    return title, content


class WebPageDownloader:
    """Download and clean official university webpages."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 20,
        max_retries: int = 2,
        max_bytes: int = 2_000_000,
        max_text_characters: int = 30_000,
        transport: httpx.BaseTransport | None = None,
        sleeper: Sleeper = time.sleep,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.max_bytes = max_bytes
        self.max_text_characters = max_text_characters
        self.transport = transport
        self.sleeper = sleeper

    def download(
        self,
        page: OfficialSearchPage,
    ) -> DownloadedWebPage:
        """Download one page with bounded retries."""

        last_error: httpx.HTTPError | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return self._download_once(page)
            except httpx.HTTPError as error:
                last_error = error

                if attempt >= self.max_retries:
                    break

                self.sleeper(min(2**attempt, 4))

        raise WebPageDownloadError(
            f"Webpage download failed after {self.max_retries + 1} attempts."
        ) from last_error

    def _download_once(
        self,
        page: OfficialSearchPage,
    ) -> DownloadedWebPage:
        """Perform and validate one HTTP request."""

        with httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": ("ResearchSupervisorFinder/0.1 (academic research discovery)")},
            transport=self.transport,
        ) as client:
            response = client.get(str(page.url))
            response.raise_for_status()

        final_url = str(response.url)

        if not _uses_official_domain(
            final_url,
            page.official_domain,
        ):
            raise WebPageDownloadError(
                "The webpage redirected outside the official university domain."
            )

        content_type = response.headers.get("content-type", "").split(";")[0].strip().casefold()

        if content_type and content_type not in {
            "text/html",
            "application/xhtml+xml",
        }:
            raise WebPageDownloadError(f"Unsupported content type: {content_type}.")

        if response.content.startswith(b"%PDF"):
            raise WebPageDownloadError("PDF content is not handled in Step 10.")

        content_length = response.headers.get("content-length")

        if (
            content_length is not None
            and content_length.isdigit()
            and int(content_length) > self.max_bytes
        ):
            raise WebPageDownloadError("Webpage exceeds the download limit.")

        if len(response.content) > self.max_bytes:
            raise WebPageDownloadError("Webpage exceeds the download limit.")

        page_title, clean_content = clean_html_content(
            response.text,
            max_characters=(self.max_text_characters),
        )

        if not clean_content:
            raise WebPageDownloadError("Webpage did not contain readable text.")

        return DownloadedWebPage(
            university_name=page.university_name,
            official_domain=page.official_domain,
            target=page.target,
            source_url=page.url,
            final_url=final_url,
            page_title=page_title or page.title,
            content=clean_content,
            content_type=(content_type or "text/html"),
            status_code=response.status_code,
        )


def download_official_pages(
    pages: list[OfficialSearchPage],
    downloader: PageDownloader,
) -> PageDownloadOutcome:
    """Download pages while allowing individual failures."""

    documents: list[DownloadedWebPage] = []
    failed_pages = 0
    seen_urls: set[str] = set()

    for page in pages:
        try:
            document = downloader.download(page)
        except WebPageDownloadError:
            failed_pages += 1
            continue

        url_key = str(document.final_url).rstrip("/").casefold()

        if url_key in seen_urls:
            continue

        seen_urls.add(url_key)
        documents.append(document)

    return PageDownloadOutcome(
        documents=tuple(documents),
        attempted_pages=len(pages),
        failed_pages=failed_pages,
    )


def create_page_downloader() -> WebPageDownloader:
    """Create the default webpage downloader."""

    return WebPageDownloader()
