"""
filter.py
---------
Step 3: Relevance Filtering

Sends all retrieved papers to Claude in one call.
Returns only papers that score >= MIN_RELEVANCE_SCORE.
"""

import logging

from config import MAX_TOKENS_FILTER, MIN_RELEVANCE_SCORE
from utils.claude_client import call_claude_json
from utils.models import Paper
from utils.prompts import relevance_filter_prompt

logger = logging.getLogger(__name__)


def filter_relevant_papers(question: str, papers: list[Paper]) -> list[Paper]:
    """
    Filter papers by relevance to the research question.

    Sends all papers to Claude in a single call for efficiency.
    Papers scored below MIN_RELEVANCE_SCORE are discarded.

    Args:
        question: The original research question.
        papers:   List of Paper objects from the retriever.

    Returns:
        Filtered list of Paper objects with relevance_score set.
    """
    if not papers:
        logger.warning("No papers to filter.")
        return []

    logger.info("Filtering %d papers for relevance...", len(papers))

    paper_dicts = [p.to_dict() for p in papers]
    prompt = relevance_filter_prompt(question, paper_dicts)
    result = call_claude_json(prompt, max_tokens=MAX_TOKENS_FILTER)

    # Build a score lookup by paper_id
    score_map: dict[str, dict] = {}
    for evaluation in result.get("evaluations", []):
        score_map[evaluation["paper_id"]] = evaluation

    # Apply scores back to Paper objects
    for paper in papers:
        if paper.paper_id in score_map:
            paper.relevance_score = score_map[paper.paper_id].get("score", 0)
            reason = score_map[paper.paper_id].get("reason", "")
            logger.debug(
                "  [%s] score=%d — %s",
                paper.paper_id[:8], paper.relevance_score, reason
            )
        else:
            paper.relevance_score = 0
            logger.warning("No score returned for paper %s", paper.paper_id)

    # Filter and sort by relevance score descending
    relevant = [p for p in papers if p.relevance_score >= MIN_RELEVANCE_SCORE]
    relevant.sort(key=lambda p: p.relevance_score, reverse=True)

    logger.info(
        "%d of %d papers passed relevance filter (score >= %d).",
        len(relevant), len(papers), MIN_RELEVANCE_SCORE
    )
    return relevant


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level="DEBUG", format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Minimal fake papers to test the filter without running the full pipeline
    from utils.models import SearchQuery, Paper

    test_question = (
        "What are the dominant failure mechanisms in atomic layer deposition "
        "of Al2O3 in high-aspect-ratio silicon trenches at sub-5nm thickness?"
    )

    test_papers = [
        Paper(
            paper_id="abc123",
            title="Conformality of ALD Al2O3 in High Aspect Ratio Structures",
            abstract=(
                "We study atomic layer deposition of Al2O3 in silicon trenches with "
                "aspect ratios up to 50:1. Conformality degrades below 5nm due to "
                "reactant depletion and surface saturation effects."
            ),
            year=2021,
            citation_count=45,
            source_query="ALD conformality high aspect ratio",
        ),
        Paper(
            paper_id="def456",
            title="Machine Learning for Protein Folding",
            abstract=(
                "We present a deep learning approach to predict protein tertiary structure "
                "from primary amino acid sequence."
            ),
            year=2022,
            citation_count=200,
            source_query="ALD Al2O3 failure",
        ),
    ]

    filtered = filter_relevant_papers(test_question, test_papers)
    print(f"\nKept {len(filtered)} papers:")
    for p in filtered:
        print(f"  [score={p.relevance_score}] {p.title}")
