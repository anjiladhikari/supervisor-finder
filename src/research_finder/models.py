from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    """Base configuration shared by application models."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class SearchRequest(StrictModel):
    """Validated researcher search input."""

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
            cleaned_value = " ".join(
                value.split()
            )

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

    @model_validator(
        mode="after"
    )
    def validate_state_values(
        self,
    ) -> SearchRequest:
        """Require state name and code together."""

        if (
            self.state is None
        ) != (
            self.state_code is None
        ):
            raise ValueError(
                "state and state_code must both "
                "be present or both be absent."
            )

        if (
            self.state_code is not None
            and not self.state_code.startswith(
                f"{self.country_code}-"
            )
        ):
            raise ValueError(
                "state_code must belong to country_code."
            )

        return self


class TopicExpansionDraft(StrictModel):
    """Structured topic expansion produced by the LLM."""

    canonical_topic: str = Field(
        min_length=3,
        max_length=300,
        description=(
            "A concise academic formulation of "
            "the original research topic."
        ),
    )

    related_topics: list[str] = Field(
        max_length=8,
        description=(
            "Closely related research concepts "
            "that preserve the user's intended scope."
        ),
    )

    broader_topics: list[str] = Field(
        max_length=4,
        description=(
            "Broader research fields that may "
            "contain relevant research groups."
        ),
    )

    narrower_topics: list[str] = Field(
        max_length=8,
        description=(
            "More specific research directions "
            "contained within the original topic."
        ),
    )

    methods_and_techniques: list[str] = Field(
        max_length=8,
        description=(
            "Methods, algorithms, architectures "
            "or technical approaches associated "
            "with the topic."
        ),
    )

    application_areas: list[str] = Field(
        max_length=6,
        description=(
            "Application areas in which the "
            "research topic may be investigated."
        ),
    )

    search_keywords: list[str] = Field(
        max_length=15,
        description=(
            "Short keywords and phrases suitable "
            "for official university website searches."
        ),
    )

    @field_validator(
        "canonical_topic",
        mode="before",
    )
    @classmethod
    def normalise_canonical_topic(
        cls,
        value: object,
    ) -> object:
        """Normalise whitespace and trailing punctuation."""

        if isinstance(value, str):
            return (
                " ".join(
                    value.split()
                )
                .strip(" ,.;:")
            )

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
        """Clean and deduplicate one topic list."""

        if not isinstance(
            value,
            list,
        ):
            return value

        cleaned_items: list[str] = []
        seen_items: set[str] = set()

        for item in value:
            if not isinstance(
                item,
                str,
            ):
                continue

            cleaned_item = (
                " ".join(
                    item.split()
                )
                .strip(" ,.;:")
            )

            if not cleaned_item:
                continue

            comparison_key = (
                cleaned_item.casefold()
            )

            if comparison_key in seen_items:
                continue

            seen_items.add(
                comparison_key
            )

            cleaned_items.append(
                cleaned_item
            )

        return cleaned_items


class TopicExpansion(
    TopicExpansionDraft
):
    """Validated topic expansion stored in workflow state."""

    original_topic: str = Field(
        min_length=3,
        max_length=300,
    )

    @field_validator(
        "original_topic",
        mode="before",
    )
    @classmethod
    def normalise_original_topic(
        cls,
        value: object,
    ) -> object:
        """Normalise the preserved user topic."""

        if isinstance(value, str):
            return " ".join(
                value.split()
            )

        return value

    def to_search_terms(
        self,
        limit: int = 30,
    ) -> list[str]:
        """Create ordered duplicate-free search terms."""

        if limit < 1:
            raise ValueError(
                "Search-term limit must be at least 1."
            )

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
            comparison_key = (
                term.casefold()
            )

            if comparison_key in seen_terms:
                continue

            seen_terms.add(
                comparison_key
            )

            unique_terms.append(
                term
            )

            if (
                len(unique_terms)
                >= limit
            ):
                break

        return unique_terms