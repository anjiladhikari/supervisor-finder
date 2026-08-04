# Research Supervisor and Lab Finder

An evidence-based AI workflow for finding Australian university researchers,
research groups, projects and publications related to a user's research topic.

## Current status

The project foundation, validated Pydantic data models and initial LangGraph
workflow skeleton are complete.

The graph currently validates user input, follows conditional routes and safely
returns an empty result with clear warnings. LLM integration and external search
have not yet been implemented.

## MVP scope
## Free web search

The project uses DDGS for free text-based web search.

The search layer provides:

- Configurable region and safe-search settings
- Request timeouts
- Bounded retries
- Result limits
- URL validation
- Duplicate removal
- Normalised titles and snippets
- A reusable client interface

Search is not connected to the LangGraph workflow yet. Official
university-domain query generation will be implemented next.
### Inputs

* Country: Australia
* State or region: optional
* Research topic: required
* Maximum number of results: optional, default 5

### Planned outputs

* Researcher name
* University
* Research lab or group
* Current and previous projects
* Research interests
* Relevant publications
* Match explanation
* Explainable relevance score
* Official source links
* Public university email, when verified
* Verification date
* Verification status and notes

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

* Python
* LangGraph
* Pydantic
* Streamlit
* SQLite
* Pytest
* Ruff
* Docker

The LLM provider will be configurable so the project can support Groq,
Ollama or another compatible provider.

## Data-model design

The application uses Pydantic models for:

* User search requests
* Researchers
* Research projects
* Publications
* Evidence sources
* Verification status
* Explainable relevance scoring
* Final search responses

Unknown information is represented explicitly rather than invented.
Every researcher result must include at least one supporting source.

## Current LangGraph workflow

The initial workflow contains nodes for:

1. Workflow initialization
2. Input validation
3. Topic expansion
4. University discovery
5. Researcher search
6. Research lab search
7. Research project search
8. Publication search
9. Current-affiliation verification
10. Relevance scoring
11. Duplicate removal
12. Result ranking
13. Final response generation

External searches and LLM calls are not implemented yet.

The current graph safely stops when input is invalid or when no universities
are found. It returns warnings instead of generating unsupported researcher
information.

- [x] Free web-search dependency
- [x] Search configuration
- [x] Search request model
- [x] Search result model
- [x] DDGS search client
- [x] Search timeout
- [x] Bounded retry behaviour
- [x] Search result limits
- [x] URL validation
- [x] Duplicate-result removal
- [x] Web-search unit tests
- [x] Manual web-search check
- [ ] Official university-domain query generation
- [ ] Researcher and lab page search