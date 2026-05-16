"""
main.py
-------
CLI entry point for the AI Scientist PoC.

Usage:
    python main.py
    python main.py "Your research question here"

Runs the full pipeline:
  decompose → retrieve → filter → extract → synthesize → uncertainty
"""

import logging
import sys

from config import LOG_FORMAT, LOG_LEVEL
from agents.decomposer import decompose_query
from agents.retriever import retrieve_papers
from agents.filter import filter_relevant_papers
from agents.extractor import extract_claims
from agents.synthesizer import synthesize
from utils.models import PipelineResult

# Configure logging before anything else
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def run_pipeline(question: str) -> PipelineResult:
    """Run the full AI Scientist pipeline for a research question."""
    logger.info("Starting pipeline for question: %s", question[:100])

    # Step 1: Decompose
    queries = decompose_query(question)

    # Step 2: Retrieve
    papers_retrieved = retrieve_papers(queries)

    # Step 3: Filter
    papers_filtered = filter_relevant_papers(question, papers_retrieved)

    # Step 4: Extract
    claims = extract_claims(question, papers_filtered)

    # Step 5 + 6: Synthesize + Uncertainty
    synthesis, uncertainty = synthesize(question, papers_filtered, claims)

    result = PipelineResult(
        question=question,
        search_queries=queries,
        papers_retrieved=papers_retrieved,
        papers_filtered=papers_filtered,
        claims=claims,
        synthesis=synthesis,
        uncertainty=uncertainty,
    )

    return result


def main():
    # Get question from CLI arg or prompt
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        print("\nAI Scientist PoC")
        print("─" * 40)
        question = input("Enter your research question:\n> ").strip()

    if not question:
        print("No question provided. Exiting.")
        sys.exit(1)

    result = run_pipeline(question)
    print(result.to_display())


if __name__ == "__main__":
    main()
