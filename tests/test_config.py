import pytest
from pydantic import ValidationError

from research_finder.config import (
    LLMProvider,
    Settings,
)


LLM_ENVIRONMENT_VARIABLES = [
    "LLM_PROVIDER",
    "GROQ_MODEL",
    "GROQ_API_KEY",
    "OLLAMA_MODEL",
    "OLLAMA_BASE_URL",
    "OLLAMA_API_KEY",
    "LLM_TEMPERATURE",
    "LLM_TIMEOUT_SECONDS",
    "LLM_MAX_RETRIES",
    "LLM_MAX_OUTPUT_TOKENS",
]


def remove_llm_environment_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Remove LLM variables for isolated settings tests."""

    for variable_name in LLM_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(variable_name, raising=False)


def test_default_settings_use_groq(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remove_llm_environment_variables(monkeypatch)

    settings = Settings(
        _env_file=None,
        groq_api_key="test-groq-key",
    )

    assert settings.llm_provider == LLMProvider.GROQ
    assert settings.groq_model == "openai/gpt-oss-20b"
    assert settings.llm_temperature == 0
    assert settings.llm_max_output_tokens == 512


def test_groq_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remove_llm_environment_variables(monkeypatch)

    with pytest.raises(
        ValidationError,
        match="GROQ_API_KEY is required",
    ):
        Settings(
            _env_file=None,
            llm_provider="groq",
            groq_api_key="",
        )


def test_ollama_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remove_llm_environment_variables(monkeypatch)

    with pytest.raises(
        ValidationError,
        match="OLLAMA_API_KEY is required",
    ):
        Settings(
            _env_file=None,
            llm_provider="ollama",
            ollama_api_key="",
        )


def test_ollama_cloud_settings_are_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remove_llm_environment_variables(monkeypatch)

    settings = Settings(
        _env_file=None,
        llm_provider="ollama",
        ollama_model="gpt-oss:20b",
        ollama_base_url="https://ollama.com/",
        ollama_api_key="test-ollama-key",
    )

    assert settings.llm_provider == LLMProvider.OLLAMA
    assert settings.ollama_model == "gpt-oss:20b"
    assert settings.ollama_base_url == "https://ollama.com"
    assert settings.ollama_api_key is not None