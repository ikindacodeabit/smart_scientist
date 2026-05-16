"""
pipeline.py
-----------
Thin orchestration wrapper around the existing agent pipeline.
Emits SSE events to a per-run queue as each step completes.
"""

import json
import logging
import queue
import threading
import time
from datetime import datetime

from agents.decomposer import decompose_query
from agents.retriever import retrieve_papers
from agents.filter import filter_relevant_papers
from agents.extractor import extract_claims
from agents.synthesizer import synthesize

logger = logging.getLogger(__name__)

run_queues: dict[str, queue.Queue] = {}
_completion_timestamps: dict[str, datetime] = {}
_lock = threading.Lock()


def create_run(run_id: str) -> None:
    """Initialize a queue for a new pipeline run before starting the thread."""
    run_queues[run_id] = queue.Queue()


def _emit(run_id: str, event: dict) -> None:
    data = json.dumps(event)
    if run_id in run_queues:
        run_queues[run_id].put(data)
    if event.get("type") in ("complete", "error"):
        with _lock:
            _completion_timestamps[run_id] = datetime.now()


def run_pipeline_streaming(question: str, run_id: str) -> None:
    """Run the full pipeline in a background thread, emitting SSE events."""
    try:
        _emit(run_id, {
            "type": "progress",
            "step": "decomposing",
            "message": "Breaking down your question into search queries...",
        })
        queries = decompose_query(question)

        _emit(run_id, {
            "type": "progress",
            "step": "retrieving",
            "message": f"Searching across {len(queries)} queries...",
        })
        papers_retrieved = retrieve_papers(queries)

        _emit(run_id, {
            "type": "progress",
            "step": "filtering",
            "message": f"Found {len(papers_retrieved)} papers. Filtering for relevance...",
        })
        papers_filtered = filter_relevant_papers(question, papers_retrieved)

        _emit(run_id, {
            "type": "progress",
            "step": "extracting",
            "message": f"Extracting claims from {len(papers_filtered)} relevant papers...",
        })
        claims = extract_claims(question, papers_filtered)

        _emit(run_id, {
            "type": "progress",
            "step": "synthesizing",
            "message": "Writing answer...",
        })
        synthesis, uncertainty = synthesize(question, papers_filtered, claims)

        result = {
            "question": question,
            "search_queries": [{"query": q.query, "rationale": q.rationale} for q in queries],
            "papers_retrieved": [p.to_dict() for p in papers_retrieved],
            "papers_filtered": [p.to_dict() for p in papers_filtered],
            "claims": [c.to_dict() for c in claims],
            "synthesis": synthesis,
            "uncertainty": {
                "evidence_count": uncertainty.evidence_count,
                "has_conflicting_evidence": uncertainty.has_conflicting_evidence,
                "conflicts": uncertainty.conflicts,
                "evidence_age_flag": uncertainty.evidence_age_flag,
                "age_note": uncertainty.age_note,
                "low_confidence_flag": uncertainty.low_confidence_flag,
                "hedge_count": uncertainty.hedge_count,
                "gaps": uncertainty.gaps,
                "overall_confidence": uncertainty.overall_confidence,
                "summary": uncertainty.summary,
            },
        }

        _emit(run_id, {"type": "complete", "result": result})

    except Exception as e:
        logger.exception("Pipeline failed for run %s", run_id)
        _emit(run_id, {"type": "error", "message": str(e)})


def _cleanup_worker() -> None:
    """Remove completed run queues after 5 minutes."""
    while True:
        time.sleep(60)
        now = datetime.now()
        with _lock:
            stale = [
                rid for rid, ts in _completion_timestamps.items()
                if (now - ts).total_seconds() > 300
            ]
            for rid in stale:
                run_queues.pop(rid, None)
                _completion_timestamps.pop(rid, None)
            if stale:
                logger.info("Cleaned up %d stale run queue(s).", len(stale))


_cleanup_thread = threading.Thread(target=_cleanup_worker, daemon=True)
_cleanup_thread.start()
