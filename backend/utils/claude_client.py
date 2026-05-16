"""
claude_client.py
----------------
Single shared Anthropic client and call_claude() helper.

All agent modules call_claude() from here.
Never instantiate anthropic.Anthropic() directly in agent files.
"""

import json
import logging

import anthropic

from config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    TEMPERATURE_STRUCTURED,
)

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to Railway → Variables."
            )
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def call_claude(
    prompt: str,
    max_tokens: int,
    temperature: float = TEMPERATURE_STRUCTURED,
    system: str | None = None,
) -> str:
    """
    Call Claude and return the response text.

    Args:
        prompt:      The user message to send.
        max_tokens:  Hard limit on response length.
        temperature: Sampling temperature (0 = deterministic, higher = more creative).
        system:      Optional system prompt.

    Returns:
        The text content of Claude's response.

    Raises:
        anthropic.APIError: On any API-level failure. Do not catch this silently.
    """
    messages = [{"role": "user", "content": prompt}]

    kwargs: dict = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }

    if system:
        kwargs["system"] = system

    logger.debug("Calling Claude | model=%s | max_tokens=%d | temp=%.1f",
                 CLAUDE_MODEL, max_tokens, temperature)

    response = _get_client().messages.create(**kwargs)
    text = response.content[0].text

    logger.debug("Claude response (%d chars): %s...", len(text), text[:200])
    return text


def call_claude_json(
    prompt: str,
    max_tokens: int,
    temperature: float = TEMPERATURE_STRUCTURED,
    system: str | None = None,
) -> dict | list:
    """
    Call Claude and parse the response as JSON.

    Strips any accidental markdown fences before parsing.
    Logs the raw response at DEBUG level if parsing fails.

    Raises:
        ValueError: If the response cannot be parsed as JSON.
        anthropic.APIError: On API-level failure.
    """
    raw = call_claude(prompt, max_tokens, temperature, system)

    # Strip markdown fences if present (defensive, shouldn't happen with good prompts)
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning("JSON parse failed. Raw response:\n%s", raw)
        raise ValueError(
            f"Claude returned non-JSON output. Parse error: {e}\n"
            f"Raw response (first 500 chars): {raw[:500]}"
        ) from e
