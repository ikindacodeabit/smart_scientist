"""
models.py
---------
Shared dataclasses for the AI Scientist PoC pipeline.

All data flowing between agents uses these types.
Do not pass raw dicts between modules — always use these classes.
"""

from dataclasses import dataclass, field


@dataclass
class Paper:
    paper_id: str
    title: str
    abstract: str
    year: int | None = None
    citation_count: int = 0
    authors: list[str] = field(default_factory=list)
    doi: str | None = None
    open_access_url: str | None = None
    relevance_score: int = 0        # set by filter.py: 0=irrelevant, 1=tangential, 2=relevant, 3=high
    source_query: str = ""          # which decomposed query surfaced this paper

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "abstract": self.abstract,
            "year": self.year,
            "citation_count": self.citation_count,
            "authors": self.authors,
            "doi": self.doi,
            "open_access_url": self.open_access_url,
            "relevance_score": self.relevance_score,
            "source_query": self.source_query,
        }


@dataclass
class Claim:
    claim_text: str
    direct_quote: str
    paper_id: str
    paper_title: str
    year: int | None = None
    confidence: str = "indirect"    # "direct" | "indirect" | "tangential"
    conditions: str | None = None

    def to_dict(self) -> dict:
        return {
            "claim_text": self.claim_text,
            "direct_quote": self.direct_quote,
            "paper_id": self.paper_id,
            "paper_title": self.paper_title,
            "year": self.year,
            "confidence": self.confidence,
            "conditions": self.conditions,
        }


@dataclass
class SearchQuery:
    query: str
    rationale: str


@dataclass
class UncertaintyReport:
    evidence_count: int
    has_conflicting_evidence: bool
    conflicts: list[str] = field(default_factory=list)
    evidence_age_flag: bool = False
    age_note: str = ""
    low_confidence_flag: bool = False
    hedge_count: int = 0
    gaps: list[str] = field(default_factory=list)
    overall_confidence: str = "low"     # "high" | "medium" | "low" | "insufficient"
    summary: str = ""

    def to_display(self) -> str:
        """Format the uncertainty report for terminal output."""
        lines = [
            "\n" + "─" * 60,
            "UNCERTAINTY REPORT",
            "─" * 60,
            f"Evidence:    {self.evidence_count} relevant papers",
            f"Confidence:  {self.overall_confidence.upper()}",
        ]

        if self.has_conflicting_evidence and self.conflicts:
            lines.append("\nConflicting evidence:")
            for c in self.conflicts:
                lines.append(f"  • {c}")

        if self.evidence_age_flag and self.age_note:
            lines.append(f"\nAge warning: {self.age_note}")

        if self.gaps:
            lines.append("\nGaps in evidence:")
            for g in self.gaps:
                lines.append(f"  • {g}")

        lines.append(f"\n{self.summary}")
        lines.append("─" * 60)

        return "\n".join(lines)


@dataclass
class PipelineResult:
    question: str
    search_queries: list[SearchQuery]
    papers_retrieved: list[Paper]
    papers_filtered: list[Paper]
    claims: list[Claim]
    synthesis: str
    uncertainty: UncertaintyReport

    def to_display(self) -> str:
        """Format the full pipeline result for terminal output."""
        lines = [
            "\n" + "═" * 60,
            "AI SCIENTIST — RESEARCH ANSWER",
            "═" * 60,
            f"\nQUESTION:\n{self.question}",
            "\n" + "─" * 60,
            "SEARCH QUERIES USED:",
        ]

        for sq in self.search_queries:
            lines.append(f'  → "{sq.query}"  ({sq.rationale})')

        lines += [
            f"\nPapers retrieved: {len(self.papers_retrieved)} | "
            f"After filtering: {len(self.papers_filtered)} | "
            f"Claims extracted: {len(self.claims)}",
            "\n" + "─" * 60,
            "RELEVANT PAPERS:",
        ]

        for p in self.papers_filtered:
            score_label = {3: "★★★", 2: "★★", 1: "★"}.get(p.relevance_score, "")
            lines.append(
                f"  [{p.paper_id[:8]}] {score_label} {p.title} "
                f"({p.year or 'n.d.'}, {p.citation_count} citations)"
            )
            if p.open_access_url:
                lines.append(f"    Open access: {p.open_access_url}")

        lines += [
            "\n" + "─" * 60,
            "ANSWER:",
            "",
            self.synthesis,
            self.uncertainty.to_display(),
        ]

        return "\n".join(lines)
