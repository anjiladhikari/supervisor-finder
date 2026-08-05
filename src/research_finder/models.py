from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from urllib.parse import urlparse

# StrEnum    → defines fixed string options
# Literal    → allows only one or several exact values
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    computed_field,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    """Base configuration shared by application model."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class AustralianState(StrEnum):
    """Australian states and territories supported by the MVP."""

    AUSTRALIAN_CAPITAL_TERRITORY = "Australian Capital Territory"
    NEW_SOUTH_WALES = "New South Wales"
    NORTHERN_TERRITORY = "Northern Territory"
    QUEENSLAND = "Queensland"
    SOUTH_AUSTRALIA = "South Australia"
    TASMANIA = "Tasmania"
    VICTORIA = "Victoria"
    WESTERN_AUSTRALIA = "Western Australia"


class SourceType(StrEnum):
    """Types of sources that may support a researcher result."""

    UNIVERSITY_PROFILE = "university_profile"
    UNIVERSITY_DIRECTORY = "university_directory"
    LAB_PAGE = "lab_page"
    PROJECT_PAGE = "project_page"
    PUBLICATION_PAGE = "publication_page"
    OTHER_OFFICIAL_SOURCE = "other_official_source"


class VerificationStatus(StrEnum):
    """Overall verification level of a researcher result."""

    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNVERIFIED = "unverified"


class ProjectStatus(StrEnum):
    """Whether a research project is current, previous or unclear."""

    CURRENT = "current"
    PREVIOUS = "previous"
    UNKNOWN = "unknown"


class SearchRequest(StrictModel):
    """Validated research-supervisor search input."""

    country: str = Field(
        min_length=2,
        max_length=100,
    )
    country_code: str = Field(
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
    )

    state: str | None = Field(
        default=None,
        max_length=150,
    )
    state_code: str | None = Field(
        default=None,
        pattern=r"^[A-Z]{2}-[A-Z0-9]{1,3}$",
    )

    research_topic: str = Field(
        min_length=3,
        max_length=300,
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
    )

    @field_validator(
        "country",
        "state",
        "research_topic",
        mode="before",
    )
    @classmethod
    def normalise_text(
        cls,
        value: object,
    ) -> object:
        """Remove repeated whitespace."""

        if isinstance(value, str):
            cleaned_value = " ".join(value.split())

            if not cleaned_value:
                return None

            return cleaned_value

        return value

    @field_validator(
        "country_code",
        "state_code",
        mode="before",
    )
    @classmethod
    def normalise_location_codes(
        cls,
        value: object,
    ) -> object:
        """Convert ISO location codes to uppercase."""

        if isinstance(value, str):
            return value.strip().upper()

        return value

    @model_validator(mode="after")
    def validate_state_values(self) -> SearchRequest:
        """Require state name and code together."""

        if (self.state is None) != (self.state_code is None):
            raise ValueError("state and state_code must both be present or both be absent.")

        if self.state_code is not None and not self.state_code.startswith(f"{self.country_code}-"):
            raise ValueError("state_code must belong to country_code.")

        return self


class TopicExpansionDraft(StrictModel):
    """structured topic expansion produced by the LLM."""

    canonical_topic: str = Field(
        min_length=3,
        max_length=300,
        description=("A concise academic formulation of the original research topic."),
    )

    related_topics: list[str] = Field(
        max_length=8,
        description=("Closely related research concepts that preserve the user's intended scope."),
    )
    broader_topics: list[str] = Field(
        max_length=4,
        description=("Broader research fields that may contain relevant research groups."),
    )

    narrower_topics: list[str] = Field(
        max_length=8,
        description=("More specific research directions contained within the original topic."),
    )
    methods_and_techniques: list[str] = Field(
        max_length=8,
        description=(
            "Methods, algorithms, architectures or technical approaches associated with the topic."
        ),
    )
    application_areas: list[str] = Field(
        max_length=6,
        description=("Application areas in which the research topic may be investigated."),
    )
    search_keywords: list[str] = Field(
        max_length=15,
        description=(
            "Short keywords and phrases suitable for official university website searches."
        ),
    )


@field_validator("canonical_topic", mode="before")
@classmethod
def normalise_canonical_topic(
    cls,
    value: object,
) -> object:
    """Normalise whitespace and trailing punctuation."""
    if isinstance(value, str):
        return " ".join(value.split()).strip(" ,.;:")

    return value

    @field_validator(
        "related_topics",
        "broader_topics",
        "narrower_topics",
        "methods_and_techniques",
        "application_areas",
        "search_keywords",
        mode="before",
    )
    @classmethod
    def normalise_topic_lists(
        cls,
        value: object,
    ) -> object:
        """Clean and deduplicate one LLM-generated topic list."""

        if not isinstance(value, list):
            return value

        cleaned_items: list[str] = []
        seen_items: set[str] = set()

        for item in value:
            if not isinstance(item, str):
                continue

            cleaned_item = " ".join(item.split()).strip(" ,.;:")

            if not cleaned_item:
                continue

            comparison_key = cleaned_item.casefold()

            if comparison_key in seen_items:
                continue

            seen_items.add(comparison_key)
            cleaned_items.append(cleaned_item)

        return cleaned_items


class TopicExpansion(TopicExpansionDraft):
    """Validated topic expansion stored in workflow state."""

    original_topic: str = Field(
        min_length=3,
        max_length=300,
    )

    @field_validator("original_topic", mode="before")
    @classmethod
    def normalise_original_topic(
        cls,
        value: object,
    ) -> object:
        """Normalise the preserved user topic."""

        if isinstance(value, str):
            return " ".join(value.split())

        return value

    def to_search_terms(
        self,
        limit: int = 30,
    ) -> list[str]:
        """Create one ordered, duplicate-free search-term list."""

        if limit < 1:
            raise ValueError("Search-term limit must be at least 1.")

        ordered_terms = [
            self.original_topic,
            self.canonical_topic,
            *self.related_topics,
            *self.narrower_topics,
            *self.methods_and_techniques,
            *self.application_areas,
            *self.broader_topics,
            *self.search_keywords,
        ]

        unique_terms: list[str] = []
        seen_terms: set[str] = set()

        for term in ordered_terms:
            comparison_key = term.casefold()

            if comparison_key in seen_terms:
                continue

            seen_terms.add(comparison_key)
            unique_terms.append(term)

            if len(unique_terms) >= limit:
                break

        return unique_terms


class AustralianUniversity(StrictModel):
    """One verified university in the Australian directory."""

    name: str = Field(
        min_length=2,
        max_length=200,
    )
    aliases: list[str] = Field(
        default_factory=list,
        max_length=10,
    )
    official_domain: str = Field(
        min_length=4,
        max_length=255,
    )
    official_website: HttpUrl
    states: list[AustralianState] = Field(
        min_length=1,
        max_length=8,
    )

    @field_validator("name", mode="before")
    @classmethod
    def normalise_university_name(
        cls,
        value: object,
    ) -> object:
        """Normalise repeated whitespace in a university name."""

        if isinstance(value, str):
            return " ".join(value.split())

        return value

    @field_validator("aliases", mode="before")
    @classmethod
    def normalise_university_aliases(
        cls,
        value: object,
    ) -> object:
        """Clean and deduplicate university aliases."""

        if not isinstance(value, list):
            return value

        cleaned_aliases: list[str] = []
        seen_aliases: set[str] = set()

        for alias in value:
            if not isinstance(alias, str):
                continue

            cleaned_alias = " ".join(alias.split())

            if not cleaned_alias:
                continue

            comparison_key = cleaned_alias.casefold()

            if comparison_key in seen_aliases:
                continue

            seen_aliases.add(comparison_key)
            cleaned_aliases.append(cleaned_alias)

        return cleaned_aliases

    @field_validator("official_domain", mode="before")
    @classmethod
    def normalise_official_domain(
        cls,
        value: object,
    ) -> object:
        """Validate and normalise a root university domain."""

        if not isinstance(value, str):
            return value

        cleaned_domain = value.strip().casefold()

        if "://" in cleaned_domain or "/" in cleaned_domain:
            raise ValueError("official_domain must be a domain without a scheme or path.")

        return cleaned_domain.removeprefix("www.")

    @field_validator("states")
    @classmethod
    def remove_duplicate_states(
        cls,
        values: list[AustralianState],
    ) -> list[AustralianState]:
        """Keep each university state only once."""

        return list(dict.fromkeys(values))

    @model_validator(mode="after")
    def validate_official_website_domain(
        self,
    ) -> AustralianUniversity:
        """Ensure the website belongs to the official domain."""

        website_host = urlparse(str(self.official_website)).hostname

        if website_host is None:
            raise ValueError("official_website must contain a valid hostname.")

        normalised_host = website_host.casefold().removeprefix("www.")

        is_root_domain = normalised_host == self.official_domain
        is_subdomain = normalised_host.endswith(f".{self.official_domain}")

        if not is_root_domain and not is_subdomain:
            raise ValueError("official_website must use official_domain or one of its subdomains.")

        return self


class EvidenceSource(StrictModel):
    """A source that supports one or more claims about a researcher."""

    source_type: SourceType
    title: str = Field(min_length=1, max_length=300)
    url: HttpUrl
    supports_claims: list[str] = Field(min_length=1)
    evidence_summary: str | None = Field(default=None, max_length=1000)
    is_official_university_source: bool
    verified_on: date = Field(default_factory=date.today)


class ResearchProject(StrictModel):
    """A current, previous or status-unknown research project."""

    name: str = Field(min_length=2, max_length=300)
    status: ProjectStatus
    description: str | None = Field(default=None, max_length=1500)
    url: HttpUrl | None = None
    start_year: int | None = Field(default=None, ge=1900)
    end_year: int | None = Field(default=None, ge=1900)

    @model_validator(mode="after")
    def validate_project_dates(self) -> ResearchProject:
        """Ensure that project dates follow a sensible order."""

        current_year = datetime.now(UTC).year

        if self.start_year is not None and self.start_year > current_year + 1:
            raise ValueError("Project start year cannot be far in the future.")

        if self.end_year is not None and self.end_year > current_year + 1:
            raise ValueError("Project end year cannot be far in the future.")

        if (
            self.start_year is not None
            and self.end_year is not None
            and self.end_year < self.start_year
        ):
            raise ValueError("Project end year cannot be before its start year.")

        return self


class Publication(StrictModel):
    """A publication that provides evidence of topic relevance."""

    title: str = Field(min_length=2, max_length=500)
    year: int | None = Field(default=None, ge=1900)
    venue: str | None = Field(default=None, max_length=300)
    url: HttpUrl | None = None
    relevance_reason: str = Field(min_length=10, max_length=800)

    @field_validator("year")
    @classmethod
    def validate_publication_year(cls, value: int | None) -> int | None:
        """Prevent clearly impossible future publication years."""

        if value is not None and value > datetime.now(UTC).year + 1:
            raise ValueError("Publication year cannot be far in the future.")

        return value


class RelevanceScore(StrictModel):
    """Explainable relevance-score components with a maximum total of 100."""

    topic_similarity: float = Field(ge=0, le=30)
    publication_relevance: float = Field(ge=0, le=20)
    current_project_relevance: float = Field(ge=0, le=20)
    lab_relevance: float = Field(ge=0, le=10)
    evidence_strength: float = Field(ge=0, le=15)
    information_recency: float = Field(ge=0, le=5)

    @computed_field
    @property
    def total(self) -> float:
        """Calculate the total score from the individual factors."""

        score = (
            self.topic_similarity
            + self.publication_relevance
            + self.current_project_relevance
            + self.lab_relevance
            + self.evidence_strength
            + self.information_recency
        )

        return round(score, 2)


class ResearcherResult(StrictModel):
    """One verified or partially verified researcher result."""

    researcher_name: str = Field(min_length=2, max_length=200)
    university_name: str = Field(min_length=2, max_length=300)

    lab_or_group_name: str | None = Field(default=None, max_length=300)

    general_research_interests: list[str] = Field(default_factory=list)
    current_projects: list[ResearchProject] = Field(default_factory=list)
    previous_projects: list[ResearchProject] = Field(default_factory=list)
    relevant_publications: list[Publication] = Field(default_factory=list)

    match_explanation: str = Field(min_length=20, max_length=1000)
    relevance_score: RelevanceScore

    official_profile_url: HttpUrl | None = None
    lab_or_group_url: HttpUrl | None = None
    public_email: EmailStr | None = None

    current_affiliation_verified: bool
    verification_status: VerificationStatus
    verification_notes: list[str] = Field(default_factory=list)
    verified_on: date = Field(default_factory=date.today)

    sources: list[EvidenceSource] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_project_categories(self) -> ResearcherResult:
        """Ensure projects are stored in their correct current/previous lists."""

        invalid_current_projects = [
            project for project in self.current_projects if project.status != ProjectStatus.CURRENT
        ]

        if invalid_current_projects:
            raise ValueError("Every project in current_projects must have status='current'.")

        invalid_previous_projects = [
            project
            for project in self.previous_projects
            if project.status != ProjectStatus.PREVIOUS
        ]

        if invalid_previous_projects:
            raise ValueError("Every project in previous_projects must have status='previous'.")

        return self


class SearchResponse(StrictModel):
    """Complete response returned by the research-finder workflow."""

    request: SearchRequest
    results: list[ResearcherResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @computed_field
    @property
    def result_count(self) -> int:
        """Return the number of researcher results."""

        return len(self.results)


# ResearcherResult
# │
# ├── Basic researcher information
# │   ├── researcher_name
# │   ├── university_name
# │   └── lab_or_group_name
# │
# ├── Research information
# │   ├── general_research_interests
# │   ├── current_projects ──────→ list[ResearchProject]
# │   ├── previous_projects ─────→ list[ResearchProject]
# │   └── relevant_publications ─→ list[Publication]
# │
# ├── Matching information
# │   ├── match_explanation
# │   └── relevance_score ───────→ RelevanceScore
# │
# ├── Contact and links
# │   ├── official_profile_url
# │   ├── lab_or_group_url
# │   └── public_email
# │
# └── Verification
#     ├── current_affiliation_verified
#     ├── verification_status
#     ├── verification_notes
#     ├── verified_on
#     └── sources ───────────────→ list[EvidenceSource]
