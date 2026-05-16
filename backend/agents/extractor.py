"""
extractor.py
------------
Step 4: Claim Extraction

For each relevant paper, asks Claude to extract specific, quoted claims
that bear on the research question.

Runs one Claude call per paper (abstracts are short enough to be efficient).
"""

import logging

from config import MAX_TOKENS_EXTRACT
from utils.claude_client import call_claude_json
from utils.models import Claim, Paper
from utils.prompts import claim_extraction_prompt

logger = logging.getLogger(__name__)


def extract_claims(question: str, papers: list[Paper]) -> list[Claim]:
    """
    Extract specific claims from each relevant paper's abstract.

    Args:
        question: The original research question.
        papers:   Filtered, relevant Paper objects.

    Returns:
        Flat list of all Claim objects across all papers.
    """
    if not papers:
        return []

    logger.info("Extracting claims from %d papers...", len(papers))

    all_claims: list[Claim] = []

    for paper in papers:
        if not paper.abstract:
            logger.warning("Skipping paper %s — no abstract.", paper.paper_id)
            continue

        claims = _extract_from_paper(question, paper)
        logger.info(
            "  [%s] %d claims extracted from '%s'",
            paper.paper_id[:8], len(claims), paper.title[:60]
        )
        all_claims.extend(claims)

    logger.info("Extracted %d claims total.", len(all_claims))
    return all_claims


def _extract_from_paper(question: str, paper: Paper) -> list[Claim]:
    """Extract claims from a single paper. Returns [] if none found."""
    prompt = claim_extraction_prompt(question, paper.to_dict())

    try:
        result = call_claude_json(prompt, max_tokens=MAX_TOKENS_EXTRACT)
    except ValueError as e:
        logger.warning("Claim extraction failed for paper %s: %s", paper.paper_id, e)
        return []

    claims = []
    for item in result.get("claims", []):
        claim = Claim(
            claim_text=item.get("claim_text", ""),
            direct_quote=item.get("direct_quote", ""),
            paper_id=paper.paper_id,
            paper_title=paper.title,
            year=paper.year,
            confidence=item.get("confidence", "indirect"),
            conditions=item.get("conditions"),
        )
        # Skip empty claims (Claude sometimes returns placeholders)
        if claim.claim_text and claim.direct_quote:
            claims.append(claim)

    return claims


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level="DEBUG", format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    test_question = (
        "What are the dominant failure mechanisms in atomic layer deposition "
        "of Al2O3 in high-aspect-ratio silicon trenches at sub-5nm thickness?"
    )

    test_paper = Paper(
        paper_id="abc123",
        title="Conformality of ALD Al2O3 in High Aspect Ratio Structures",
        abstract=(
            "We investigate atomic layer deposition (ALD) of Al2O3 in silicon "
            "trenches with aspect ratios up to 50:1. At thicknesses below 5nm, "
            "conformality degrades significantly due to reactant depletion in "
            "the trench bottom and precursor sticking coefficient effects. "
            "Surface hydroxyl density is found to be the primary determinant "
            "of nucleation uniformity. These failure modes become dominant at "
            "aspect ratios above 20:1."
        ),
        year=2021,
        citation_count=45,
        relevance_score=3,
        source_query="ALD conformality high aspect ratio",
    )

    claims = extract_claims(test_question, [test_paper])
    print(f"\nExtracted {len(claims)} claims:")
    for c in claims:
        print(f"\n  CLAIM [{c.confidence}]: {c.claim_text}")
        print(f'  QUOTE: "{c.direct_quote}"')
        if c.conditions:
            print(f"  CONDITIONS: {c.conditions}")
