"""
main.py
-------
FastAPI backend for the AI Scientist web app.

Endpoints:
    POST /api/question      → starts pipeline, returns run_id
    GET  /api/stream/{id}   → SSE stream of pipeline events
    GET  /health            → health check
"""

import asyncio
import functools
import json
import logging
import queue as _queue
import threading
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

import os

from pipeline import create_run, run_pipeline_streaming, run_queues

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

if not os.getenv("ANTHROPIC_API_KEY"):
    logger.error("ANTHROPIC_API_KEY is not set — add it to Railway Variables and redeploy.")
    raise SystemExit(1)

app = FastAPI(title="AI Scientist API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QuestionRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/question")
def post_question(req: QuestionRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    run_id = str(uuid.uuid4())
    create_run(run_id)  # create queue before thread starts to avoid race

    thread = threading.Thread(
        target=run_pipeline_streaming,
        args=(req.question, run_id),
        daemon=True,
    )
    thread.start()

    logger.info("Started run %s: %s", run_id, req.question[:80])
    return {"run_id": run_id}


@app.get("/api/stream/{run_id}")
async def stream(run_id: str):
    if run_id not in run_queues:
        raise HTTPException(status_code=404, detail="Run not found")

    q = run_queues[run_id]
    loop = asyncio.get_event_loop()

    async def event_generator():
        while True:
            try:
                event_str = await loop.run_in_executor(
                    None,
                    functools.partial(q.get, block=True, timeout=15.0),
                )
                yield {"data": event_str}
                parsed = json.loads(event_str)
                if parsed.get("type") in ("complete", "error"):
                    break
            except _queue.Empty:
                # Send a keepalive so proxies don't close the connection
                yield {"data": json.dumps({"type": "ping"})}
            except GeneratorExit:
                break
            except Exception:
                logger.exception("SSE stream error for run %s", run_id)
                break

    return EventSourceResponse(event_generator())
