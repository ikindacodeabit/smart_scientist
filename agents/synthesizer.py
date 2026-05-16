"""
synthesizer.py
--------------
Steps 5 + 6: Synthesis and Uncertainty Flagging

Step 5: Synthesizes extracted claims into a coherent, cited answer.
Step 6: Assesses the reliability and completeness of that answer.
"""

import logging
from datetime import datetime

from config import (
    ADEQUATE_EVIDENCE_THRESHOLD,
    EVIDENCE_AGE_WARNING_YEARS,
    HEDGE_COUNT_THRESHOLD,
    HEDGE_PHRASES,
    MAX_TOKENS_NO_EVIDENCE,
    MAX_TOKENS_SYNTHESIZE,
    MAX_TOKENS_UNCERTAINTY,
    TEMPERATURE_SYNTHESIS,
)
from utils.claude_client import call_claude, call_claude_json
from utils.models import Claim, Paper, UncertaintyReport
from utils.prompts import (
    no_evidence_prompt,
    synthesis_prompt,
    uncertainty_assessment_prompt,
)

logger = logging.getLogger(__name__)

CURRENT_YEAR = datetime.now().year


def synthesize(
    question: str,
    papers: list[Paper],
    claims: list[Claim],
) -> tuple[str, UncertaintyReport]:
    """
    Synthesize claims into an answer and produce an uncertainty report.

    Args:
        question: The original research question.
        papers:   Filtered relevant papers (used for metadata in uncertainty assessment).
        claims:   All extracted claims from all relevant papers.

    Returns:
        Tuple of (synthesis_text, UncertaintyReport).
    """
    if not papers or not claims:
        return _handle_no_evidence(question, len(papers))

    logger.info("Synthesizing answer from %d claims across %d papers...",
                len(claims), len(papers))

    synthesis = _run_synthesis(question, papers, claims)
    uncertainty = _run_uncertainty_assessment(question, synthesis, papers)

    return synthesis, uncertainty


def _run_synthesis(question: str, papers: list[Paper], claims: list[Claim]) -> str:
    """Call Claude to synthesize the claims into a coherent answer."""

    # Group claims by paper for the prompt
    paper_map = {p.paper_id: p for p in papers}
    claims_by_paper: list[dict] = []

    for paper in papers:
        paper_claims = [c.to_dict() for c in claims if c.paper_id == paper.paper_id]
        if paper_claims:
            claims_by_paper.append({
                "paper_id": paper.paper_id,
                "paper_title": paper.title,
                "year": paper.year,
                "claims": paper_claims,
            })

    prompt = synthesis_prompt(question, claims_by_paper)
    synthesis = call_claude(
        prompt,
        max_tokens=MAX_TOKENS_SYNTHESIZE,
        temperature=TEMPERATURE_SYNTHESIS,
    )

    logger.info("Synthesis complete (%d chars).", len(synthesis))
    return synthesis


def _run_uncertainty_assessment(
    question: str,
    synthesis: str,
    papers: list[Paper],
) -> UncertaintyReport:
    """Call Claude to assess the reliability of the synthesis."""
    logger.info("Running uncertainty assessment...")

    paper_years = [p.year for p in papers if p.year is not None]

    prompt = uncertainty_assessment_prompt(
        question=question,
        synthesis=synthesis,
        evidence_count=len(papers),
        paper_years=paper_years,
    )

    try:
        result = call_claude_json(prompt, max_tokens=MAX_TOKENS_UNCERTAINTY)
    except ValueError:
        logger.warning("Uncertainty assessment parse failed. Using heuristic fallback.")
        return _heuristic_uncertainty(synthesis, papers)

    # Count hedges in synthesis locally as a sanity check
    hedge_count = sum(
        synthesis.lower().count(phrase) for phrase in HEDGE_PHRASES
    )

    report = UncertaintyReport(
        evidence_count=result.get("evidence_count", len(papers)),
        has_conflicting_evidence=result.get("has_conflicting_evidence", False),
        conflicts=result.get("conflicts", []),
        evidence_age_flag=result.get("evidence_age_flag", False),
        age_note=result.get("age_note", ""),
        low_confidence_flag=hedge_count >= HEDGE_COUNT_THRESHOLD,
        hedge_count=hedge_count,
        gaps=result.get("gaps", []),
        overall_confidence=result.get("overall_confidence", "low"),
        summary=result.get("summary", ""),
    )

    logger.info("Uncertainty: %s confidence.", report.overall_confidence)
    return report


def _heuristic_uncertainty(synthesis: str, papers: list[Paper]) -> UncertaintyReport:
    """
    Fallback uncertainty report using only local heuristics.
    Used when the LLM-based assessment fails to parse.
    """
    paper_years = [p.year for p in papers if p.year is not None]
    oldest = min(paper_years) if paper_years else CURRENT_YEAR
    hedge_count = sum(synthesis.lower().count(p) for p in HEDGE_PHRASES)
    age_flag = (CURRENT_YEAR - oldest) > EVIDENCE_AGE_WARNING_YEARS if paper_years else False

    if len(papers) >= ADEQUATE_EVIDENCE_THRESHOLD and hedge_count < HEDGE_COUNT_THRESHOLD:
        confidence = "medium"
    elif len(papers) < 3:
        confidence = "insufficient"
    else:
        confidence = "low"

    return UncertaintyReport(
        evidence_count=len(papers),
        has_conflicting_evidence=False,
        evidence_age_flag=age_flag,
        low_confidence_flag=hedge_count >= HEDGE_COUNT_THRESHOLD,
        hedge_count=hedge_count,
        overall_confidence=confidence,
        summary=(
            f"Heuristic assessment: {len(papers)} papers, "
            f"{hedge_count} hedging phrases in synthesis."
        ),
    )


def _handle_no_evidence(question: str, paper_count: int) -> tuple[str, UncertaintyReport]:
    """Handle the case where no relevant papers were found."""
    logger.warning("No relevant evidence found. Generating no-evidence response.")

    prompt = no_evidence_prompt(question)
    response = call_claude(prompt, max_tokens=MAX_TOKENS_NO_EVIDENCE)

    uncertainty = UncertaintyReport(
        evidence_count=paper_count,
        has_conflicting_evidence=False,
        overall_confidence="insufficient",
        summary="No relevant peer-reviewed evidence was found for this question.",
    )

    return response, uncertainty


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    from utils.models import Claim, Paper

    test_question = (
        "What are the dominant failure mechanisms in atomic layer deposition "
        "of Al2O3 in high-aspect-ratio silicon trenches at sub-5nm thickness?"
    )

    test_papers = [
        Paper(
            paper_id="abc123",
            title="Conformality of ALD Al2O3 in High Aspect Ratio Structures",
            abstract="...",
            year=2021,
            citation_count=45,
            relevance_score=3,
        ),
    ]

    test_claims = [
        Claim(
            claim_text="Conformality degrades below 5nm due to reactant depletion at trench bottoms.",
            direct_quote="At thicknesses below 5nm, conformality degrades significantly due to reactant depletion.",
            paper_id="abc123",
            paper_title="Conformality of ALD Al2O3 in High Aspect Ratio Structures",
            year=2021,
            confidence="direct",
            conditions="Aspect ratios above 20:1",
        ),
    ]

    synthesis, uncertainty = synthesize(test_question, test_papers, test_claims)
    print("\nSYNTHESIS:")
    print(synthesis)
    print(uncertainty.to_display())
