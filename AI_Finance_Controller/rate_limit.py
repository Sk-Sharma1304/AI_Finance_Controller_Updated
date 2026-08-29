"""
Rate limiting
================

In-memory sliding-window rate limiter. Deliberately simple: no
external dependency (Redis) needed to run this. This DOES NOT work
across multiple server processes/replicas -- each process has its
own counters, so the effective limit multiplies by however many
replicas you run. For real production scale, move this to Redis
(``INCR`` + ``EXPIRE``, or a proper library like ``slowapi`` /
``fastapi-limiter``) so limits are enforced globally.

Two limits are applied:
  - Uploads per actor per hour (protects the scoring pipeline /
    IsolationForest inference from being hammered).
  - LLM-eligible rows per actor per day (protects against runaway
    OpenAI spend -- separate from the existing per-run MAX_LLM_CALLS
    cap in llm_investigation_agent.py, which limits cost *within*
    one run but not across many runs).
"""

from __future__ import annotations

import os
import time
from collections import defaultdict

UPLOADS_PER_HOUR = int(os.environ.get("RATE_LIMIT_UPLOADS_PER_HOUR", "30"))
LLM_ROWS_PER_DAY = int(os.environ.get("RATE_LIMIT_LLM_ROWS_PER_DAY", "500"))

_upload_events: dict[str, list[float]] = defaultdict(list)
_llm_row_events: dict[str, list[tuple[float, int]]] = defaultdict(list)


class RateLimitExceeded(Exception):
    def __init__(self, message: str, retry_after_seconds: int):
        self.message = message
        self.retry_after_seconds = retry_after_seconds
        super().__init__(message)


def _prune(events: list[float], window_seconds: int, now: float) -> list[float]:
    return [t for t in events if now - t < window_seconds]


def check_upload_rate_limit(actor: str) -> None:
    now = time.time()
    window = 3600
    events = _prune(_upload_events[actor], window, now)
    _upload_events[actor] = events

    if len(events) >= UPLOADS_PER_HOUR:
        oldest = min(events)
        retry_after = int(window - (now - oldest))
        raise RateLimitExceeded(
            f"Upload rate limit exceeded ({UPLOADS_PER_HOUR}/hour for '{actor}'). "
            f"Try again in {retry_after}s.",
            retry_after_seconds=max(retry_after, 1),
        )

    _upload_events[actor].append(now)


def check_and_consume_llm_budget(actor: str, row_count: int) -> bool:
    """Returns True if there's daily LLM budget remaining for this
    actor. Does not raise -- callers should degrade gracefully
    (skip LLM enrichment) rather than fail the whole upload just
    because the LLM budget ran out."""

    now = time.time()
    window = 86400
    events = [(t, n) for t, n in _llm_row_events[actor] if now - t < window]
    _llm_row_events[actor] = events

    used = sum(n for _, n in events)
    if used >= LLM_ROWS_PER_DAY:
        return False

    _llm_row_events[actor].append((now, row_count))
    return True
