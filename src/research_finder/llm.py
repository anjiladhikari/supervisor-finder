from langchain_core.language_models.chat_models import BaseChatModel
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from research_finder.config import (
    LLMProvider,
    Settings,
    get_settings,
)


def create_chat_model(
    settings: Settings | None = None,
) -> BaseChatModel:
    """Create the cloud chat model selected in settings."""

    active_settings = settings or get_settings()

    if active_settings.llm_provider == LLMProvider.GROQ:
        if active_settings.groq_api_key is None:
            raise ValueError("A Groq API key is required to create ChatGroq.")

        return ChatGroq(
            model=active_settings.groq_model,
            api_key=(active_settings.groq_api_key.get_secret_value()),
            temperature=active_settings.llm_temperature,
            max_tokens=active_settings.llm_max_output_tokens,
            reasoning_effort="low",
            timeout=active_settings.llm_timeout_seconds,
            max_retries=active_settings.llm_max_retries,
        )

    if active_settings.llm_provider == LLMProvider.OLLAMA:
        if active_settings.ollama_api_key is None:
            raise ValueError("An Ollama API key is required to create ChatOllama.")

        api_key = active_settings.ollama_api_key.get_secret_value()

        return ChatOllama(
            model=active_settings.ollama_model,
            base_url=active_settings.ollama_base_url,
            temperature=active_settings.llm_temperature,
            num_predict=active_settings.llm_max_output_tokens,
            validate_model_on_init=False,
            client_kwargs={
                "headers": {
                    "Authorization": f"Bearer {api_key}",
                },
                "timeout": active_settings.llm_timeout_seconds,
            },
        )

    raise ValueError(f"Unsupported LLM provider: {active_settings.llm_provider}")
