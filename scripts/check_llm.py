from research_finder.config import (
    LLMProvider,
    get_settings,
)
from research_finder.llm import create_chat_model


def main() -> None:
    """Send one small request to the selected cloud provider."""

    settings = get_settings()
    model = create_chat_model(settings)

    if settings.llm_provider == LLMProvider.GROQ:
        model_name = settings.groq_model
    else:
        model_name = settings.ollama_model

    print(f"Provider: {settings.llm_provider.value}")
    print(f"Model: {model_name}")
    print("Sending API connection-check request...")

    response = model.invoke(
        [
            (
                "system",
                (
                    "You are performing an API connection test. "
                    "Reply briefly and do not add an explanation."
                ),
            ),
            (
                "human",
                "Reply with exactly: LLM provider is ready.",
            ),
        ]
    )

    content = response.content

    if isinstance(content, str):
        response_text = content.strip()
    else:
        response_text = str(content).strip()

    if not response_text:
        raise RuntimeError("The LLM API returned an empty response.")

    print(f"Response: {response_text}")


if __name__ == "__main__":
    main()
