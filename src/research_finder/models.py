from __future__ import annotations

from datetime import date,datetime,timezone
from enum import StrEnum
from typing import Literal 
# StrEnum    → defines fixed string options
# Literal    → allows only one or several exact values
from pydantic import(

    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    computed_field,
    filed_validator,
    model_validator

)

class StrictModel(BaseModel):
    """Base configuration shared by application model."""
    model_config=ConfigDict(
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


STATE_ALIASES: dict[str, AustralianState] = {
    "act": AustralianState.AUSTRALIAN_CAPITAL_TERRITORY,
    "australian capital territory": AustralianState.AUSTRALIAN_CAPITAL_TERRITORY,
    "nsw": AustralianState.NEW_SOUTH_WALES,
    "new south wales": AustralianState.NEW_SOUTH_WALES,
    "nt": AustralianState.NORTHERN_TERRITORY,
    "northern territory": AustralianState.NORTHERN_TERRITORY,
    "qld": AustralianState.QUEENSLAND,
    "queensland": AustralianState.QUEENSLAND,
    "sa": AustralianState.SOUTH_AUSTRALIA,
    "south australia": AustralianState.SOUTH_AUSTRALIA,
    "tas": AustralianState.TASMANIA,
    "tasmania": AustralianState.TASMANIA,
    "vic": AustralianState.VICTORIA,
    "victoria": AustralianState.VICTORIA,
    "wa": AustralianState.WESTERN_AUSTRALIA,
    "western australia": AustralianState.WESTERN_AUSTRALIA,
}


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
    """vlidate input submitted by the user"""
    country:Literal["Australia"]="Australia"
    state: AustralianState | None = None 
    research_topic: str=Field(min_length=3,max_length=300)
    max_results: int=Field(default=5,ge=1,le=20)

    @field_validator("country",mode="before")
    @classmethod
    def normalize_country(cls,value:object)->object:
        """accept different capitalisation while allowing australia only."""
        if isinstance(value,str) and value.strip.casefold()=="australia":
            return "Australia"
        return value

    @field_validator("state",mode="before")
    @classmethod
    def normalise_state(cls,value:object)->object:
        """convert state abbreviations and name to one standard value."""
        if value is None or isinstance(value,AustralianState):
            return value

        if not isinstance(value,str):
            return value

        cleaned_value=" ".join(value.split()).casefold()

        if not cleaned_value:
            return None

        return STATE_ALIASES.get(cleaned_value,None)


    @field_validator("research_topic", mode="before")
    @classmethod
    def normalise_research_topic(cls, value: object) -> object:
        """Remove unnecessary repeated whitespace from the topic."""

        if isinstance(value, str):
            return " ".join(value.split())

        return value



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

        current_year = date.today().year

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

        if value is not None and value > date.today().year + 1:
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
            project
            for project in self.current_projects
            if project.status != ProjectStatus.CURRENT
        ]

        if invalid_current_projects:
            raise ValueError(
                "Every project in current_projects must have status='current'."
            )

        invalid_previous_projects = [
            project
            for project in self.previous_projects
            if project.status != ProjectStatus.PREVIOUS
        ]

        if invalid_previous_projects:
            raise ValueError(
                "Every project in previous_projects must have status='previous'."
            )

        return self


class SearchResponse(StrictModel):
    """Complete response returned by the research-finder workflow."""

    request: SearchRequest
    results: list[ResearcherResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

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
