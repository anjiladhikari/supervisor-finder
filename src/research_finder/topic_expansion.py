from langchain_core.language_models.chat_models import (
    BaseChatModel,
)

from research_finder.models import (
    SearchRequest,
    TopicExpansion,
    TopicExpansionDraft,
)

TOPIC_EXPANSION_SYSTEM_PROMPT = """
You create compact research-topic expansions for an evidence-based
Australian university researcher-discovery system.

Your task is to expand the user's topic into useful academic search
vocabulary without changing the user's intended research scope.

Rules:

1. Use concise academic noun phrases.
2. Preserve the original technical meaning.
3. Do not name researchers.
4. Do not name universities.
5. Do not name laboratories or research groups.
6. Do not invent projects, publications or factual claims.
7. Separate broader fields from narrower research directions.
8. Include methods only when they are reasonably connected to the topic.
9. Include application areas only when they are genuinely relevant.
10. Avoid duplicate concepts and superficial wording variations.
11. Produce search vocabulary, not a research explanation.
""".strip()


def build_topic_expansion_messages(
    request: SearchRequest,
) -> list[tuple[str, str]]:
    """Build provider-independent topic-expansion messages."""

    if request.state is None:
        state_scope = f"All states and territories in {request.country}"
    else:
        state_scope = request.state

    user_prompt = f"""
Country scope: {request.country}
State or territory scope: {state_scope}
Original research topic: {request.research_topic}

Produce a structured expansion containing:

- One concise canonical topic
- Three to eight closely related topics
- One to four broader research fields
- Two to eight narrower research directions
- Two to eight relevant methods or techniques
- Zero to six genuine application areas
- Five to fifteen useful search keywords or phrases

Keep every item concise. Do not include explanations, researcher names,
university names, URLs, citations or unverifiable claims.
""".strip()

    return [
        ("system", TOPIC_EXPANSION_SYSTEM_PROMPT),
        ("human", user_prompt),
    ]


def generate_topic_expansion(
    request: SearchRequest,
    model: BaseChatModel,
) -> TopicExpansion:
    """Generate and validate one structured topic expansion."""

    structured_model = model.with_structured_output(
        TopicExpansionDraft,
        method="json_schema",
    )

    raw_response = structured_model.invoke(
        build_topic_expansion_messages(request)
    )

    if isinstance(raw_response, TopicExpansionDraft):
        draft = raw_response
    else:
        draft = TopicExpansionDraft.model_validate(
            raw_response
        )

    return TopicExpansion(
        original_topic=request.research_topic,
        **draft.model_dump(),
    )


def create_fallback_topic_expansion(
    request: SearchRequest,
) -> TopicExpansion:
    """Create a deterministic expansion without an LLM."""

    return TopicExpansion(
        original_topic=request.research_topic,
        canonical_topic=request.research_topic,
        related_topics=[],
        broader_topics=[],
        narrower_topics=[],
        methods_and_techniques=[],
        application_areas=[],
        search_keywords=[request.research_topic],
    )