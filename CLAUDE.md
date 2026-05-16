# AI Scientist PoC — Claude Code Instructions

## What This Project Is

A CLI pipeline that answers highly technical, niche research questions by retrieving academic papers,
extracting specific claims, and synthesizing a cited, uncertainty-aware answer.

This is a **Proof of Concept**. The goal is to validate that the pipeline produces useful answers
on hard niche questions — not to be production-ready. Prefer correctness over cleverness.
Prefer readable code over abstracted code.

---

## Architecture (Read This First)

The pipeline runs sequentially, one question at a time:

```
User question
  → [1] decompose_query     → list of 3–4 search strings
  → [2] retrieve_papers     → list of Paper objects (per query, then deduplicated)
  → [3] filter_relevance    → filtered list of relevant Paper objects
  → [4] extract_claims      → list of Claim objects per paper
  → [5] synthesize          → final answer string with inline [paper_id] citations
  → [6] flag_uncertainty    → UncertaintyReport appended to answer
```

Each step is a separate module in `agents/`. Each module has one job and one job only.
The orchestrator in `main.py` calls them in order and passes results forward.

---

## File Structure

```
ai-scientist-poc/
├── CLAUDE.md               ← you are here
├── main.py                 ← CLI entry point and orchestrator
├── config.py               ← constants, model names, API settings
├── requirements.txt
├── .env                    ← API keys (never commit this)
├── .env.example            ← safe to commit
├── agents/
│   ├── __init__.py
│   ├── decomposer.py       ← step 1: query decomposition
│   ├── retriever.py        ← step 2: Semantic Scholar API calls
│   ├── filter.py           ← step 3: relevance filtering via Claude
│   ├── extractor.py        ← step 4: claim extraction via Claude
│   └── synthesizer.py      ← step 5+6: synthesis + uncertainty flagging
└── utils/
    ├── __init__.py
    ├── models.py            ← shared dataclasses: Paper, Claim, UncertaintyReport
    ├── prompts.py           ← ALL prompt templates live here, nowhere else
    └── claude_client.py     ← single shared Anthropic client + call_claude() helper
```

---

## Data Models (from utils/models.py)

Always use these dataclasses. Do not pass raw dicts between modules.

```
Paper
  paper_id: str           # Semantic Scholar paper ID
  title: str
  abstract: str
  year: int | None
  citation_count: int
  authors: list[str]
  doi: str | None
  open_access_url: str | None
  relevance_score: int    # set by filter.py: 0=irrelevant, 1=tangential, 2=relevant, 3=highly relevant
  source_query: str       # which decomposed query surfaced this paper

Claim
  claim_text: str         # the specific claim, in plain English
  direct_quote: str       # verbatim text from the abstract supporting this claim
  paper_id: str           # references Paper.paper_id
  paper_title: str        # for display convenience
  confidence: str         # "direct" | "indirect" | "tangential"
  conditions: str | None  # conditions under which this claim holds, if specified

UncertaintyReport
  evidence_count: int           # number of relevant papers found
  has_conflicting_evidence: bool
  conflicts: list[str]          # plain English descriptions of each conflict
  evidence_age_flag: bool       # True if all papers older than 10 years
  low_confidence_flag: bool     # True if synthesis has many hedging qualifiers
  overall_confidence: str       # "high" | "medium" | "low" | "insufficient"
  summary: str                  # 1–2 sentence plain English uncertainty summary
```

---

## Conventions

### Claude API Calls
- **All Claude calls go through `utils/claude_client.py`**. Never instantiate `anthropic.Anthropic()`
  directly in agent files.
- **Always use the model name from `config.py`** (`CLAUDE_MODEL`). Never hardcode a model string
  in an agent file.
- **All prompts live in `utils/prompts.py`**. Agent files call prompt functions, they do not
  contain prompt strings.
- Use `temperature=0` for all calls that require structured JSON output (decomposer, filter, extractor).
- Use `temperature=0.3` for synthesis (allows slightly more natural prose).
- Always set `max_tokens` explicitly. See config.py for per-step limits.

### JSON Outputs
- When a step returns structured data, ask Claude to return **only valid JSON with no preamble,
  no markdown fences, no explanation**. The phrase to use in prompts:
  `"Respond with only a valid JSON object. No markdown. No explanation. No preamble."`
- Always wrap `json.loads()` in a try/except. On parse failure, log the raw response and
  raise a descriptive error — do not silently return empty results.

### Error Handling
- Semantic Scholar API: on HTTP error or timeout, log and return empty list (don't crash the pipeline).
- Claude API: on error, raise — do not swallow errors silently.
- If filter_relevance returns 0 papers, the pipeline should still complete — synthesizer should
  produce a "no relevant evidence found" output rather than crashing.

### Logging
- Use Python's `logging` module, not `print()`.
- Log at INFO level: each step starting, how many papers/claims were found.
- Log at DEBUG level: raw API responses (for prompt debugging).
- Log at WARNING level: empty results, parse failures, rate limit hits.
- Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`

### Testing
- Each agent module should have a simple `if __name__ == "__main__":` block that runs it
  standalone with a hardcoded test question. This is how you test modules in isolation.
- No pytest required for the PoC. Quick manual runs are fine.

---

## Key Constraints — Do Not Violate These

1. **No full PDF parsing in the PoC.** Abstracts only from Semantic Scholar. If open_access_url
   is available, note it but don't fetch it. This is Tier 2 work.

2. **No UI.** Output goes to stdout. A clean formatted terminal output is fine. No Streamlit yet.

3. **No memory/sessions.** Each run of `main.py` is stateless. No database, no cache.

4. **No parallelism yet.** Run retrieval queries sequentially. Adding async is Tier 2.
   The exception: if you need to fetch multiple papers, sequential is fine.

5. **Keep prompts in prompts.py.** If you find yourself writing a prompt string in an agent file,
   stop and move it to prompts.py.

6. **Do not retry failed Claude calls automatically.** Log the error and raise. Automatic retries
   with bad prompts waste money.

---

## Semantic Scholar API Notes

Base URL: `https://api.semanticscholar.org/graph/v1`

Key endpoints:
- Paper search: `GET /paper/search?query=<q>&fields=paperId,title,abstract,year,citationCount,authors,externalIds,openAccessPdf&limit=10`
- Paper details: `GET /paper/{paper_id}?fields=...` (not needed for PoC)

Rate limits:
- Without API key: 100 requests per 5 minutes
- With free API key (get at semanticscholar.org/product/api): 1 request/second

Set the API key as `SEMANTIC_SCHOLAR_API_KEY` in .env. The retriever should work without it
(just slower) but log a warning if it's missing.

The `fields` parameter is mandatory — Semantic Scholar returns minimal data by default.
Always specify the fields you need explicitly.

---

## Prompt Debugging Workflow

When a step produces bad output:
1. Set logging to DEBUG to see the raw Claude response
2. Copy the prompt + response into a fresh Claude.ai chat
3. Iterate on the prompt there (faster feedback loop than running the full pipeline)
4. Once the prompt works in chat, update `prompts.py`
5. Re-run the standalone `if __name__ == "__main__":` test for that module

This is faster than running `main.py` for every prompt iteration.

---

## Environment Variables

Required:
```
ANTHROPIC_API_KEY=sk-ant-...
```

Optional but recommended:
```
SEMANTIC_SCHOLAR_API_KEY=...
LOG_LEVEL=INFO       # or DEBUG for prompt debugging
```

---

## What "Done" Looks Like for the PoC

Run `python main.py` with a hard niche question. The output should:
1. Show which papers were retrieved and which survived filtering
2. List the key claims extracted, with paper IDs
3. Produce a 3–6 paragraph answer with inline [paper_id] citations
4. End with an uncertainty summary that honestly flags thin or conflicting evidence

If it does all four, the PoC is done. Do not add features — move to Tier 2 planning.
