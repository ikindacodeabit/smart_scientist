"""
prompts.py
----------
All prompt templates for the AI Scientist PoC pipeline.

Rules:
- Every prompt lives here. No prompt strings in agent files.
- Functions return complete, ready-to-send prompt strings.
- Prompts that expect JSON output always end with the JSON instruction block.
- Keep prompts honest: ask Claude to express uncertainty, not to sound confident.
"""


# ---------------------------------------------------------------------------
# STEP 1 — QUERY DECOMPOSITION
# ---------------------------------------------------------------------------

def query_decomposition_prompt(question: str) -> str:
    return f"""You are a research librarian helping a scientist find academic papers.

A user has asked this research question:
<question>
{question}
</question>

Your task is to decompose this question into 3–4 distinct search queries optimized for
Semantic Scholar, an academic paper search engine. Each query should target a different
facet or angle of the question so that together they provide broad coverage.

Guidelines for good queries:
- Use academic terminology, not conversational language
- Each query should be 3–8 words
- Queries should be complementary, not redundant — avoid overlap
- Think about: core mechanism, failure modes, specific materials/conditions, measurement methods
- Do NOT include author names or years — focus on concepts
- Each query should be independently useful (would surface different papers)

Return a JSON object with this exact structure:
{{
  "queries": [
    {{
      "query": "short academic search string",
      "rationale": "one sentence explaining what angle this query targets"
    }}
  ]
}}

Respond with only a valid JSON object. No markdown. No explanation. No preamble."""


# ---------------------------------------------------------------------------
# STEP 3 — RELEVANCE FILTERING
# ---------------------------------------------------------------------------

def relevance_filter_prompt(question: str, papers: list[dict]) -> str:
    papers_block = "\n\n".join([
        f"PAPER_ID: {p['paper_id']}\n"
        f"TITLE: {p['title']}\n"
        f"YEAR: {p.get('year', 'unknown')}\n"
        f"CITATIONS: {p.get('citation_count', 0)}\n"
        f"ABSTRACT: {p['abstract'] or 'No abstract available.'}"
        for p in papers
    ])

    return f"""You are a domain expert helping evaluate whether academic papers are relevant
to a specific research question.

The research question is:
<question>
{question}
</question>

Below are {len(papers)} candidate papers retrieved from Semantic Scholar.
For each paper, assign a relevance score and a brief reason.

Scoring rubric:
- 3 = Highly relevant: directly addresses the question's core mechanism, phenomenon, or topic
- 2 = Relevant: addresses a significant aspect of the question, useful for synthesis
- 1 = Tangential: loosely related, might provide background but won't answer the question
- 0 = Irrelevant: does not address the question despite superficial keyword overlap

Be conservative. It is better to exclude a borderline paper than to include noise.
A paper with 0 citations is not automatically bad — weight relevance, not prestige.

Papers to evaluate:
<papers>
{papers_block}
</papers>

Return a JSON object with this exact structure:
{{
  "evaluations": [
    {{
      "paper_id": "the paper_id exactly as given",
      "score": 0,
      "reason": "one sentence explaining why this score"
    }}
  ]
}}

Include every paper in the evaluations list, even those scored 0.
Respond with only a valid JSON object. No markdown. No explanation. No preamble."""


# ---------------------------------------------------------------------------
# STEP 4 — CLAIM EXTRACTION
# ---------------------------------------------------------------------------

def claim_extraction_prompt(question: str, paper: dict) -> str:
    return f"""You are extracting specific, verifiable claims from an academic paper abstract
that are relevant to a research question.

The research question is:
<question>
{question}
</question>

The paper is:
<paper>
PAPER_ID: {paper['paper_id']}
TITLE: {paper['title']}
YEAR: {paper.get('year', 'unknown')}
AUTHORS: {', '.join(paper.get('authors', [])) or 'unknown'}
ABSTRACT:
{paper['abstract'] or 'No abstract available.'}
</paper>

Extract every specific claim from this abstract that bears on the research question.

A good claim is:
- Specific and falsifiable (not vague like "X is important")
- Grounded in a direct quote from the abstract
- Accompanied by any conditions or constraints the authors specify
- Correctly classified by how directly it addresses the question

A bad claim is:
- A paraphrase so loose it changes the meaning
- A background statement not connected to the question
- An interpretation you've added that isn't in the abstract

If the abstract is too short, vague, or completely unrelated to the question,
return an empty claims list — do not fabricate claims.

Return a JSON object with this exact structure:
{{
  "claims": [
    {{
      "claim_text": "Plain English statement of the specific finding or claim",
      "direct_quote": "Verbatim text from the abstract that supports this claim",
      "confidence": "direct | indirect | tangential",
      "conditions": "Conditions under which this claim holds, or null if unconditional"
    }}
  ]
}}

Confidence levels:
- "direct": the abstract explicitly answers or addresses the question
- "indirect": the abstract addresses a related mechanism or phenomenon
- "tangential": the abstract is related but only marginally supports the question

Respond with only a valid JSON object. No markdown. No explanation. No preamble."""


# ---------------------------------------------------------------------------
# STEP 5 — SYNTHESIS
# ---------------------------------------------------------------------------

def synthesis_prompt(question: str, claims_by_paper: list[dict]) -> str:
    claims_block = "\n\n".join([
        f"[{entry['paper_id']}] {entry['paper_title']} ({entry.get('year', 'n.d.')})\n" +
        "\n".join([
            f"  • CLAIM: {c['claim_text']}\n"
            f"    QUOTE: \"{c['direct_quote']}\"\n"
            f"    CONFIDENCE: {c['confidence']}"
            + (f"\n    CONDITIONS: {c['conditions']}" if c.get('conditions') else "")
            for c in entry['claims']
        ])
        for entry in claims_by_paper
        if entry['claims']
    ])

    paper_count = len([e for e in claims_by_paper if e['claims']])

    return f"""You are a research scientist synthesizing evidence from academic papers
to answer a specific technical question.

The question is:
<question>
{question}
</question>

You have {paper_count} papers with extracted claims:
<evidence>
{claims_block}
</evidence>

Write a synthesis that directly answers the question based on this evidence.

Requirements:
1. CITE EVERY FACTUAL CLAIM inline using the paper ID in square brackets, e.g. [ABC123]
2. Do NOT make claims that aren't supported by the evidence above
3. Where papers AGREE, synthesize them together into a coherent finding
4. Where papers DISAGREE or show conflicting results, state this explicitly:
   "Paper [X] found A, while paper [Y] found B under different conditions"
5. Where evidence is missing or thin, say so explicitly: "The evidence does not address..."
6. Use technical language appropriate to the domain
7. Do not pad the answer — if the evidence only supports 2 paragraphs, write 2 paragraphs

Structure:
- Start with a direct answer to the question (1–2 sentences)
- Follow with the key findings grouped by theme or mechanism
- End with what the evidence does NOT cover or where gaps remain

Do not add a bibliography section — citations are inline only.
Do not begin with "Based on the provided evidence" or similar meta-phrases.
Start directly with the answer."""


# ---------------------------------------------------------------------------
# STEP 6 — UNCERTAINTY ASSESSMENT
# ---------------------------------------------------------------------------

def uncertainty_assessment_prompt(
    question: str,
    synthesis: str,
    evidence_count: int,
    paper_years: list[int]
) -> str:
    years_str = ", ".join(str(y) for y in sorted(paper_years)) if paper_years else "unknown"
    oldest = min(paper_years) if paper_years else None
    newest = max(paper_years) if paper_years else None
    year_range = f"{oldest}–{newest}" if oldest and newest else "unknown"

    return f"""You are critically evaluating the reliability of a synthesized research answer.

The original question:
<question>
{question}
</question>

The synthesized answer:
<synthesis>
{synthesis}
</synthesis>

Evidence metadata:
- Number of relevant papers found: {evidence_count}
- Publication years of papers used: {years_str} (range: {year_range})

Evaluate the reliability of this synthesis by checking:

1. EVIDENCE VOLUME: Is {evidence_count} papers sufficient to answer this question confidently?
   (For a niche technical question, 1–2 papers = insufficient, 3–5 = limited, 6+ = adequate)

2. CONFLICTING EVIDENCE: Does the synthesis describe any contradictions or disagreements
   between papers? List each conflict specifically.

3. EVIDENCE AGE: Are the papers recent enough? For fast-moving fields, papers older than
   5–7 years may be superseded. For established physics/chemistry, age matters less.

4. HEDGING LANGUAGE: Count how many times the synthesis uses uncertain language
   ("may", "suggests", "unclear", "appears to", "possible", "limited evidence").
   Many hedges = low synthesis confidence.

5. GAPS: What aspects of the question does the synthesis explicitly NOT address?

Based on this, produce an overall confidence rating:
- "high": strong evidence, no major conflicts, recent papers, few gaps
- "medium": moderate evidence, minor conflicts or gaps, mostly recent
- "low": limited evidence, significant conflicts or gaps
- "insufficient": fewer than 3 relevant papers, or major aspects unanswered

Return a JSON object with this exact structure:
{{
  "evidence_count": {evidence_count},
  "has_conflicting_evidence": true,
  "conflicts": [
    "Description of specific conflict 1",
    "Description of specific conflict 2"
  ],
  "evidence_age_flag": false,
  "age_note": "one sentence about whether age of evidence is a concern",
  "low_confidence_flag": false,
  "hedge_count": 3,
  "gaps": [
    "Aspect of the question not addressed by the evidence"
  ],
  "overall_confidence": "medium",
  "summary": "1-2 sentence plain English summary of the reliability of this answer"
}}

Set has_conflicting_evidence to false and conflicts to [] if there are none.
Set evidence_age_flag to true if the evidence is likely outdated for this domain.
Respond with only a valid JSON object. No markdown. No explanation. No preamble."""


# ---------------------------------------------------------------------------
# FALLBACK — NO EVIDENCE FOUND
# ---------------------------------------------------------------------------

def no_evidence_prompt(question: str) -> str:
    return f"""A user asked this research question:
<question>
{question}
</question>

A search of Semantic Scholar returned no relevant academic papers after filtering.

Write a short, honest response (3–5 sentences) that:
1. Acknowledges that no relevant published evidence was found
2. Suggests 2–3 more specific reformulations of the question that might surface results
3. Recommends specific databases or resources that might be more appropriate
   (e.g. patents, grey literature, specific conference proceedings, proprietary databases)

Do not fabricate findings. Do not answer the question from general knowledge.
Be direct and helpful."""
