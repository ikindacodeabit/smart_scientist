"""
decomposer.py
-------------
Step 1: Query Decomposition

Takes the user's research question and returns 3–4 distinct
academic search queries, each targeting a different facet.
"""

import logging

from config import MAX_TOKENS_DECOMPOSE
from utils.claude_client import call_claude_json
from utils.models import SearchQuery
from utils.prompts import query_decomposition_prompt

logger = logging.getLogger(__name__)


def decompose_query(question: str) -> list[SearchQuery]:
    """
    Decompose a research question into 3–4 distinct search queries.

    Args:
        question: The user's research question.

    Returns:
        List of SearchQuery objects with query string and rationale.
    """
    logger.info("Decomposing question into search queries...")

    prompt = query_decomposition_prompt(question)
    result = call_claude_json(prompt, max_tokens=MAX_TOKENS_DECOMPOSE)

    queries = []
    for item in result.get("queries", []):
        queries.append(SearchQuery(
            query=item["query"],
            rationale=item["rationale"],
        ))
        logger.info('  Query: "%s" — %s', item["query"], item["rationale"])

    logger.info("Decomposed into %d queries.", len(queries))
    return queries


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import logging
    logging.basicConfig(level="DEBUG", format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    test_question = (
        "What are the dominant failure mechanisms in atomic layer deposition "
        "of Al2O3 in high-aspect-ratio silicon trenches at sub-5nm thickness?"
    )

    queries = decompose_query(test_question)
    print("\nDecomposed queries:")
    for q in queries:
        print(f'  → "{q.query}"')
        print(f'     {q.rationale}')
