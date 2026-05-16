"""
config.py
---------
All constants and configuration for the AI Scientist PoC.

Change values here. Do not hardcode values in agent files.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
SEMANTIC_SCHOLAR_API_KEY: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

# ---------------------------------------------------------------------------
# Model Configuration
# ---------------------------------------------------------------------------

# The model used for all Claude calls.
# Change this in one place to switch models across the whole pipeline.
CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

# Temperature per step — structured output steps use 0, prose uses 0.3
TEMPERATURE_STRUCTURED: float = 0.0     # decomposer, filter, extractor, uncertainty
TEMPERATURE_SYNTHESIS: float = 0.3     # synthesizer

# Max tokens per step — set conservatively, increase if outputs are getting cut off
MAX_TOKENS_DECOMPOSE: int = 500
MAX_TOKENS_FILTER: int = 1500
MAX_TOKENS_EXTRACT: int = 1000
MAX_TOKENS_SYNTHESIZE: int = 2000
MAX_TOKENS_UNCERTAINTY: int = 800
MAX_TOKENS_NO_EVIDENCE: int = 400

# ---------------------------------------------------------------------------
# Semantic Scholar Configuration
# ---------------------------------------------------------------------------

SEMANTIC_SCHOLAR_BASE_URL: str = "https://api.semanticscholar.org/graph/v1"

# Fields to request from Semantic Scholar paper search
# Do not remove fields that models.py depends on
SEMANTIC_SCHOLAR_FIELDS: str = (
    "paperId,title,abstract,year,citationCount,authors,externalIds,openAccessPdf"
)

# How many papers to retrieve per search query
PAPERS_PER_QUERY: int = 8

# Minimum relevance score to keep a paper after filtering (0–3)
# 2 = keep "relevant" and "highly relevant" papers only
MIN_RELEVANCE_SCORE: int = 2

# ---------------------------------------------------------------------------
# Pipeline Thresholds (for uncertainty flagging)
# ---------------------------------------------------------------------------

# Minimum papers to consider evidence "adequate" (affects uncertainty label)
ADEQUATE_EVIDENCE_THRESHOLD: int = 6

# Papers older than this many years trigger an age warning (for fast-moving fields)
EVIDENCE_AGE_WARNING_YEARS: int = 8

# Maximum number of hedge words before flagging low_confidence_flag
HEDGE_COUNT_THRESHOLD: int = 5

# Words/phrases that count as hedges in the synthesis
HEDGE_PHRASES: list[str] = [
    "may ", "might ", "suggests ", "appears to", "possibly",
    "unclear", "limited evidence", "could ", "uncertain",
    "not well understood", "remains to be", "it is possible",
    "preliminary", "tentative",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
