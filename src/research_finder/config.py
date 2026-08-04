from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import (
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(StrEnum):
    """Cloud LLM providers supported by the application."""

    GROQ = "groq"
    OLLAMA = "ollama"


class SearchSafeSearch(StrEnum):
    """safe search levels accepted by the search provider."""

    ON = "on"
    MODERATE = "moderate"
    OFF = "off"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        str_strip_whitespace=True,
    )

    llm_provider: LLMProvider = LLMProvider.GROQ

    groq_model: str = Field(
        default="openai/gpt-oss-20b",
        min_length=1,
    )
    groq_api_key: SecretStr | None = None

    ollama_model: str = Field(
        default="gpt-oss:20b",
        min_length=1,
    )
    ollama_base_url: str = Field(
        default="https://ollama.com",
        min_length=1,
    )
    ollama_api_key: SecretStr | None = None

    llm_temperature: float = Field(
        default=0.0,
        ge=0,
        le=2,
    )
    llm_timeout_seconds: float = Field(
        default=60.0,
        ge=1,
        le=300,
    )
    llm_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
    )
    llm_max_output_tokens: int = Field(
        default=512,
        ge=64,
        le=4096,
    )

    search_region: str = Field(
        default="au-en",
        min_length=2,
        max_length=20,
    )
    search_safesearch: SearchSafeSearch = SearchSafeSearch.MODERATE
    search_timeout_seconds: int = Field(
        default=15,
        ge=5,
        le=60,
    )
    search_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
    )
    search_max_results: int = Field(
        default=10,
        ge=1,
        le=20,
    )

    @field_validator("search_region")
    @classmethod
    def normalise_search_region(
        cls,
        value: str,
    ) -> str:
        """Normalise the search-region value."""

        return value.strip().lower()

    @field_validator(
        "groq_api_key",
        "ollama_api_key",
        mode="before",
    )
    @classmethod
    def convert_blank_api_keys_to_none(
        cls,
        value: object,
    ) -> object:
        """Treat an empty API-key value as missing."""

        if isinstance(value, str) and not value.strip():
            return None

        return value

    @field_validator("ollama_base_url")
    @classmethod
    def normalise_ollama_base_url(cls, value: str) -> str:
        """Remove a trailing slash from the Ollama API URL."""

        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_provider_credentials(self) -> Settings:
        """Require credentials for the selected provider."""

        if self.llm_provider == LLMProvider.GROQ and self.groq_api_key is None:
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq.")

        if self.llm_provider == LLMProvider.OLLAMA and self.ollama_api_key is None:
            raise ValueError("OLLAMA_API_KEY is required when LLM_PROVIDER=ollama.")

        return self


@lru_cache
def get_settings() -> Settings:
    """Load and cache application configuration."""

    return Settings()
