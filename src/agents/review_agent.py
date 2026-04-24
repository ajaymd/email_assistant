"""Review & Validator Agent.

Asks Claude to grade the current draft on three dimensions: grammar/clarity,
tone alignment, and contextual coherence. Returns a strict JSON verdict so the
graph's conditional edge can branch deterministically.
"""
from __future__ import annotations

import json
from typing import Any

from ..integrations.llm_router import get_router
from ..workflow.state import EmailState
from ._common import extract_json, trace_node

SYSTEM_PROMPT = """You are a strict copy editor. You will be shown a draft \
email and the constraints it was supposed to satisfy. Return a SINGLE JSON \
object with these exact keys and nothing else:

{
  "ok": true | false,
  "grammar_score": 1-5,
  "tone_score": 1-5,
  "coherence_score": 1-5,
  "feedback": "actionable rewrite instructions if ok=false; empty string if ok=true"
}

Set ok=true only if ALL of the following hold:
- grammar_score >= 4 (no awkward or ungrammatical sentences)
- tone_score >= 4 (the draft genuinely matches the requested tone)
- coherence_score >= 4 (the draft is clearly about the requested topic, hits every must_include item, and avoids every must_avoid item)

Be honest. If the draft is too short for the requested length, set ok=false and \
say so. If a placeholder like [confirm date] is acceptable for missing info, do \
not penalize it. Return ONLY the JSON."""


def _build_user_message(state: EmailState) -> str:
    constraints = state.get("parsed_constraints", {}) or {}
    return json.dumps(
        {
            "request": state.get("raw_prompt", ""),
            "intent": state.get("intent"),
            "tone": state.get("tone"),
            "length": state.get("length", "medium"),
            "must_include": constraints.get("must_include", []),
            "must_avoid": constraints.get("must_avoid", []),
            "draft": state.get("draft", {}),
        },
        ensure_ascii=False,
    )


def review_agent(state: EmailState) -> dict[str, Any]:
    with trace_node(state, "review_agent") as ctx:
        result = get_router().generate(
            system=SYSTEM_PROMPT,
            user=_build_user_message(state),
            agent_name="review_agent",
        )
        ctx["llm_result"] = result
        try:
            verdict = extract_json(result.text)
        except (json.JSONDecodeError, ValueError):
            # If the reviewer itself misbehaves, accept the draft rather than
            # looping forever — the writer is more important than the critic.
            verdict = {"ok": True, "feedback": ""}
            ctx["note"] = "reviewer returned non-JSON; defaulting to ok=true"

        review_ok = bool(verdict.get("ok"))
        feedback = str(verdict.get("feedback", "")).strip()
        if not review_ok:
            ctx["note"] = (ctx.get("note") or "") + f" rejected: {feedback[:80]}"

    return {
        "review_ok": review_ok,
        "review_feedback": feedback,
        "trace": ctx["trace"],
    }
