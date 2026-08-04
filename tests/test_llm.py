from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from research_finder.config import Settings
from research_finder.llm import create_chat_model


def test_create_groq_chat_model() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="groq",
        groq_model="openai/gpt-oss-20b",
        groq_api_key="test-groq-key",
    )

    model = create_chat_model(settings)

    assert isinstance(model, ChatGroq)


def test_create_ollama_cloud_chat_model() -> None:
    settings = Settings(
        _env_file=None,
        llm_provider="ollama",
        ollama_model="gpt-oss:20b",
        ollama_base_url="https://ollama.com",
        ollama_api_key="test-ollama-key",
    )

    model = create_chat_model(settings)

    assert isinstance(model, ChatOllama)