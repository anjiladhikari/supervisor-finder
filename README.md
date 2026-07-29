# Research Supervisor and Lab Finder

An evidence-based AI workflow for finding Australian university researchers,
research groups, projects and publications related to a user's research topic.

## Current status

Project foundation created. Search and LLM functionality have not yet been implemented.

## MVP scope

### Inputs

- Country: Australia
- State or region: optional
- Research topic: required

### Planned outputs

- Researcher name
- University
- Research lab or group
- Current and previous projects
- Research interests
- Relevant publications
- Match explanation
- Relevance score
- Official source links
- Public university email, when verified
- Verification date

## Planned workflow

1. Validate input
2. Expand the research topic
3. Find relevant universities
4. Search official university sources
5. Extract structured evidence
6. Verify current affiliation
7. Score relevance
8. Remove duplicates
9. Rank results
10. Present the final output

## Initial technology choices

- Python
- LangGraph
- Pydantic
- Streamlit
- SQLite
- Pytest
- Ruff
- Docker

The LLM provider will be configurable so the project can support Groq,
Ollama or another compatible provider.

## Development status

- [x] Project foundation
- [ ] Input and output models
- [ ] LangGraph state
- [ ] Input-validation node
- [ ] Topic-expansion node
- [ ] Search integration
- [ ] Evidence extraction
- [ ] Verification
- [ ] Relevance scoring
- [ ] Streamlit interface
- [ ] SQLite persistence
- [ ] Docker deployment