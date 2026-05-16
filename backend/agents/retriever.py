"""
retriever.py
------------
Step 2: Paper Retrieval

Queries Semantic Scholar for each decomposed search query.
Returns deduplicated list of Paper objects.
"""

import logging
import os
import sys
import time

# Allow running this file directly (python agents/retriever.py)
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from config import (
    PAPERS_PER_QUERY,
    SEMANTIC_SCHOLAR_API_KEY,
    SEMANTIC_SCHOLAR_BASE_URL,
    SEMANTIC_SCHOLAR_FIELDS,
)
from utils.models import Paper, SearchQuery

logger = logging.getLogger(__name__)

# Request headers — include API key if available
def _get_headers() -> dict:
    if SEMANTIC_SCHOLAR_API_KEY:
        return {"x-api-key": SEMANTIC_SCHOLAR_API_KEY}
    logger.warning(
        "No SEMANTIC_SCHOLAR_API_KEY set. Using unauthenticated access (lower rate limits)."
    )
    return {}


def retrieve_papers(queries: list[SearchQuery]) -> list[Paper]:
    """
    Retrieve papers from Semantic Scholar for a list of search queries.

    Deduplicates by paper_id across all queries.
    On HTTP error or timeout, logs warning and continues to next query.

    Args:
        queries: List of SearchQuery objects from the decomposer.

    Returns:
        Deduplicated list of Paper objects.
    """
    logger.info("Retrieving papers for %d queries...", len(queries))

    seen_ids: set[str] = set()
    all_papers: list[Paper] = []

    for sq in queries:
        papers = _search_one_query(sq)
        new_papers = [p for p in papers if p.paper_id not in seen_ids]
        seen_ids.update(p.paper_id for p in new_papers)
        all_papers.extend(new_papers)
        logger.info('  Query "%s" → %d new papers', sq.query, len(new_papers))

        # Be polite to the API — 1 second between requests
        time.sleep(1.0)

    logger.info("Retrieved %d unique papers total.", len(all_papers))
    return all_papers


def _search_one_query(sq: SearchQuery) -> list[Paper]:
    """Execute a single Semantic Scholar search query. Returns [] on failure."""
    url = f"{SEMANTIC_SCHOLAR_BASE_URL}/paper/search"
    params = {
        "query": sq.query,
        "fields": SEMANTIC_SCHOLAR_FIELDS,
        "limit": PAPERS_PER_QUERY,
    }

    try:
        response = requests.get(url, params=params, headers=_get_headers(), timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.warning("Semantic Scholar request failed for query '%s': %s", sq.query, e)
        return []

    papers = []
    for item in data.get("data", []):
        # Skip papers with no abstract — not useful for claim extraction
        if not item.get("abstract"):
            continue

        paper = Paper(
            paper_id=item["paperId"],
            title=item.get("title", "Untitled"),
            abstract=item.get("abstract", ""),
            year=item.get("year"),
            citation_count=item.get("citationCount", 0),
            authors=[a["name"] for a in item.get("authors", [])],
            doi=item.get("externalIds", {}).get("DOI"),
            open_access_url=(
                item.get("openAccessPdf", {}) or {}
            ).get("url"),
            source_query=sq.query,
        )
        papers.append(paper)

    return papers


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level="INFO", format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    test_queries = [
        SearchQuery(
            query="ALD conformality high aspect ratio silicon",
            rationale="Tests retrieval on a specific materials science query"
        ),
        SearchQuery(
            query="atomic layer deposition Al2O3 failure mechanisms",
            rationale="Tests a different angle of the same topic"
        ),
    ]

    papers = retrieve_papers(test_queries)
    print(f"\nRetrieved {len(papers)} papers:")
    for p in papers:
        print(f"  [{p.paper_id[:8]}] {p.title} ({p.year}, {p.citation_count} citations)")
        if p.open_access_url:
            print(f"    Open access: {p.open_access_url}")
