# Research Supervisor and Lab Finder

An evidence-based AI workflow for finding Australian university researchers,
research groups, projects and publications that match a given research topic.

---

## What it does

Given a research topic and an optional Australian state, the workflow:

1. Validates the user's input
2. Uses an LLM to expand the topic into related terms, methods, and keywords
3. Looks up Australian universities from a built-in directory
4. Generates official university-domain search queries for each search target
5. Executes web searches restricted to official university domains
6. Downloads and cleans the discovered pages
7. Extracts structured researcher information *(not yet implemented)*
8. Verifies current affiliation *(placeholder)*
9. Scores, deduplicates and ranks results
10. Returns a structured `SearchResponse`

---

## Current status

The following pipeline steps are fully implemented and tested:

- [x] Input validation
- [x] LLM-based topic expansion (Groq or Ollama)
- [x] Australian university directory lookup
- [x] Official university-domain search query generation
- [x] Web search with bounded retries and duplicate removal (DDGS)
- [x] Official-domain result validation
- [x] Page download and HTML cleaning (httpx + BeautifulSoup)
- [x] Structured researcher extraction from downloaded pages (LLM)
- [x] Researcher detail extraction — emails, labs, projects, publications (LLM)
- [x] Lightweight affiliation verification (deterministic, no extra LLM calls)
- [x] Deterministic relevance scoring
- [x] Partial failure handling at every stage
- [x] Conditional LangGraph routing

The following steps are still placeholders:

- [ ] Duplicate removal and result ranking
- [ ] Streamlit user interface

---

## Inputs

| Field | Required | Description |
|---|---|---|
| `country` | Yes | Must be Australia |
| `country_code` | Yes | ISO 3166-1 alpha-2, e.g. `AU` |
| `state` | No | Australian state name, e.g. `Victoria` |
| `state_code` | No | ISO 3166-2, e.g. `AU-VIC` |
| `research_topic` | Yes | Free-text topic, 3–300 characters |
| `max_results` | No | 1–20, default 5 |

State name and state code must both be present or both absent.

---

## Planned outputs

Each `ResearcherResult` includes:

- Researcher name and university
- Research lab or group
- General research interests
- Current and previous projects
- Relevant publications
- An explainable relevance score (topic similarity, publication relevance,
  project relevance, lab relevance, evidence strength, recency)
- Official profile and lab URLs
- Public university email when verified
- Verification status and notes
- Supporting evidence sources with official domain URLs

---

## Architecture

### LangGraph workflow

```
START
  └─ initialize_workflow
       └─ validate_input
            ├─ [invalid] → generate_final_output → END
            └─ [valid]   → expand_research_topic
                               └─ find_universities
                                    ├─ [none found] → generate_final_output → END
                                    └─ [found]      → generate_search_queries
                                                          ├─ [no queries] → generate_final_output → END
                                                          └─ [queries]    → search_researchers
                                                                                 └─ search_labs
                                                                                      └─ search_projects
                                                                                           └─ search_publications
                                                                                                └─ download_webpage_content
                                                                                                     └─ extract_researcher_information
                                                                                                          └─ extract_researcher_details
                                                                                                               └─ verify_current_affiliation
                                                                                                                    └─ score_relevance
                                                                                                                         └─ remove_duplicates
                                                                                                                              └─ rank_results
                                                                                                                                   └─ generate_final_output → END
```

### Shared state

`ResearchGraphState` carries:

| Field | Type | Description |
|---|---|---|
| `request` | `SearchRequest` | Validated user input |
| `topic_expansion` | `TopicExpansion` | LLM-expanded topics and keywords |
| `expanded_topics` | `list[str]` | Ordered, deduplicated search terms |
| `candidate_universities` | `list[UniversityRecord]` | Matched universities |
| `search_queries` | `list[OfficialSearchQuery]` | Domain-restricted queries |
| `researcher_pages` / `lab_pages` / `project_pages` / `publication_pages` | `list[OfficialSearchPage]` | Search result pages per target |
| `researcher_documents` / `lab_documents` / `project_documents` / `publication_documents` | `list[DownloadedWebPage]` | Cleaned page text per target |
| `extracted_candidates` | `list[ResearcherCandidate]` | Candidates from researcher pages |
| `enriched_candidates` | `list[EnrichedResearcherCandidate]` | Candidates with emails, labs, projects, publications attached |
| `verified_results` | `list[VerifiedResearcherCandidate]` | Candidates that passed deterministic verification |
| `scored_results` / `deduplicated_results` / `ranked_results` | `list[ResearcherResult]` | Intermediate result lists |
| `errors` / `warnings` / `execution_log` | `list[str]` | Append-only message lists |

---

## Lightweight researcher verification

The workflow performs deterministic verification using the official
university pages already downloaded during discovery.

A researcher is retained only when:

- Their profile source belongs to the official university domain
- The downloaded profile contains their name
- Their extraction evidence exists in the downloaded page

Research labs, projects, publications and public email addresses are also
checked against their downloaded official source.

Unsupported claims are removed without rejecting an otherwise valid
researcher.

The verification timestamp and number of verified source pages are stored
for each researcher.

This step does not perform additional web searches or LLM calls.

---

## Research profile organisation

Verified researcher information is separated into:

- General research interests
- Current projects
- Previous projects
- Projects with unknown status

Project status is determined only from explicit evidence in official
university content.

Current-status phrases such as "currently", "ongoing" and "is leading" are
treated as current evidence.

Previous-status phrases such as "previously", "completed" and "concluded"
are treated as previous evidence.

Explicit project year ranges may also be used.

When the evidence does not clearly establish project status, the project is
stored as unknown rather than guessed.

---

## Deterministic relevance scoring

Verified researcher profiles receive a relevance score from 0 to 100.

The scoring weights are:

- Research interests: 40 points
- Current projects: 25 points
- Publications: 15 points
- Research labs/groups: 10 points
- Previous projects: 5 points
- Projects with unknown status: 5 points

The original user research topic receives full matching weight.

Expanded topics are also considered but receive slightly lower weight to
reduce broad-topic false positives.

Scoring is deterministic and does not use an LLM.

Each result stores:

- Total relevance score
- Category score breakdown
- Matched topic terms
- Human-readable scoring explanation

---

## Key modules

| Module | Purpose |
|---|---|
| `models.py` | Pydantic data models (`SearchRequest`, `ResearcherResult`, `RelevanceScore`, etc.) |
| `config.py` | Environment-based settings (`LLM_PROVIDER`, API keys, search parameters) |
| `llm.py` | LangChain chat model factory (Groq or Ollama) |
| `university_directory.py` | Australian university lookup from a bundled JSON directory |
| `topic_expansion.py` | LLM-based research topic expansion with fallback |
| `search_queries.py` | Official university-domain query generation (`OfficialSearchQuery`) |
| `web_search.py` | DDGS-backed free web search client with retries and deduplication |
| `official_page_search.py` | Executes search queries, filters results to official domains |
| `web_content.py` | Downloads and cleans official pages with httpx and BeautifulSoup |
| `researcher_extraction.py` | LLM-based structured extraction of researcher candidates from pages |
| `researcher_details.py` | LLM-based extraction of emails, labs, projects and publications; candidate enrichment |
| `verification.py` | Deterministic verification of candidates against downloaded evidence |
| `research_profile.py` | Deterministic project status classification and researcher profile organisation |
| `relevance.py` | Deterministic relevance scoring of profiles using weighted lexical intersection |
| `nodes.py` | LangGraph node functions |
| `routes.py` | Conditional routing functions |
| `graph.py` | LangGraph graph assembly and compilation |
| `state.py` | `ResearchGraphState`, `ResearchGraphInput`, `ResearchGraphOutput` |

---

## Technology stack

| Tool | Role |
|---|---|
| Python 3.12 | Language |
| LangGraph | Workflow orchestration |
| Pydantic | Data validation and modelling |
| LangChain (Groq / Ollama) | LLM integration |
| DDGS | Free web search |
| httpx | HTTP page downloads |
| BeautifulSoup4 | HTML cleaning and text extraction |
| pycountry | ISO country and state validation |
| Pytest | Testing |
| Ruff | Linting and formatting |

---

## Configuration

Copy `.env.example` to `.env` and set:

```ini
LLM_PROVIDER=groq          # or ollama
GROQ_API_KEY=your-key-here

# Optional overrides
GROQ_MODEL=openai/gpt-oss-20b
LLM_TEMPERATURE=0.0
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2

SEARCH_REGION=au-en
SEARCH_SAFESEARCH=moderate
SEARCH_TIMEOUT_SECONDS=15
SEARCH_MAX_RETRIES=2
SEARCH_MAX_RESULTS=10
```

---

## Development

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run tests

```bash
pytest
```

### Diagnostic scripts

Run any script directly to verify a specific layer against real APIs:

| Script | What it checks |
|---|---|
| `scripts/check_llm.py` | LLM connection and topic expansion |
| `scripts/check_web_search.py` | DDGS web search |
| `scripts/check_search_queries.py` | Query generation for Victorian universities |
| `scripts/check_official_page_search.py` | End-to-end search for official researcher pages |
| `scripts/check_web_content.py` | Page download and text extraction |
| `scripts/check_topic_expansion.py` | Full topic expansion via LLM |
| `scripts/check_researcher_extraction.py` | Structured researcher extraction from a real page |
| `scripts/check_researcher_details.py` | Detail extraction and enrichment for Deakin University |
| `scripts/check_verification.py` | Deterministic verification against a fixed candidate and document |

```bash
python scripts/check_web_content.py
```

---

## Data model overview

```
ResearcherResult
├── researcher_name, university_name, lab_or_group_name
├── general_research_interests
├── current_projects  ──→ list[ResearchProject]
├── previous_projects ──→ list[ResearchProject]
├── relevant_publications ──→ list[Publication]
├── match_explanation
├── relevance_score ──→ RelevanceScore
│     (topic_similarity + publication_relevance +
│      current_project_relevance + lab_relevance +
│      evidence_strength + information_recency)
├── official_profile_url, lab_or_group_url, public_email
└── sources ──→ list[EvidenceSource]
      (university_profile | lab_page | project_page |
       publication_page | university_directory | other_official_source)
```

Unknown fields are left `None` rather than invented. Every result must have
at least one supporting `EvidenceSource` from an official university domain.