"""Shared helpers used by every agent: tracing, JSON parsing."""
from __future__ import annotations

import json
import re
import time
from contextlib import contextmanager
from typing import Any, Iterator

from ..integrations.llm_router import LLMResult
from ..workflow.state import EmailState, TraceEntry


def append_trace(state: EmailState, entry: TraceEntry) -> list[TraceEntry]:
    """Return a new trace list with ``entry`` appended."""
    existing = list(state.get("trace") or [])
    existing.append(entry)
    return existing


@contextmanager
def trace_node(state: EmailState, agent: str) -> Iterator[dict[str, Any]]:
    """Time an agent and append a trace entry on exit.

    Usage:
        with trace_node(state, "draft_writer_agent") as ctx:
            ctx["llm_result"] = router.generate(...)
            ctx["note"] = "regenerated with reviewer feedback"
        # On exit, the trace entry is appended to ``ctx['trace']``.
    """
    started = time.perf_counter()
    ctx: dict[str, Any] = {"status": "ok", "note": None, "llm_result": None}
    try:
        yield ctx
    except Exception as exc:  # noqa: BLE001
        ctx["status"] = "error"
        ctx["note"] = f"{type(exc).__name__}: {exc}"
        ctx["trace"] = append_trace(
            state,
            {
                "agent": agent,
                "status": "error",
                "model_used": None,
                "provider_used": None,
                "fell_back": False,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "note": ctx["note"],
            },
        )
        raise

    llm_result: LLMResult | None = ctx.get("llm_result")
    ctx["trace"] = append_trace(
        state,
        {
            "agent": agent,
            "status": ctx["status"],
            "model_used": llm_result.model_used if llm_result else None,
            "provider_used": llm_result.provider_used if llm_result else None,
            "fell_back": bool(llm_result.fell_back) if llm_result else False,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "note": ctx.get("note"),
        },
    )


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(text: str) -> dict[str, Any]:
    """Best-effort extraction of a JSON object from a model response.

    LLMs occasionally wrap JSON in ```json fences or add prose before/after.
    We strip both, then fall back to a greedy ``{...}`` match.
    """
    cleaned = text.strip()
    # Remove ``` fences if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(cleaned)
        if not match:
            raise
        return json.loads(match.group(0))
