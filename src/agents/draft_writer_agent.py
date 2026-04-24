"""Draft Writer Agent.

The centerpiece. Consumes the parsed prompt + intent + tone + personalization
context and emits a structured draft (subject, greeting, body, closing,
signature) so the UI can render and edit each section independently.

When invoked after a failed review pass, it picks up the reviewer's feedback
from state and treats it as a hard rewrite instruction.
"""
from __future__ import annotations

import json
from typing import Any

from ..integrations.llm_router import get_router
from ..workflow.state import Draft, EmailState
from ._common import extract_json, trace_node

SYSTEM_PROMPT = """You are a senior communication coach drafting email replies \
on behalf of a busy professional. You always return a SINGLE JSON object with \
these exact keys and nothing else:

{
  "subject": "concise subject line",
  "greeting": "salutation line, e.g. 'Hi Dana,'",
  "body": "the main body — multiple paragraphs separated by \\n\\n",
  "closing": "sign-off line, e.g. 'Best,'",
  "signature": "the user's signature block"
}

Hard rules:
- Match the requested tone exactly. If exemplars are provided, mirror their cadence and word choice.
- Honor every must_include item and avoid every must_avoid item.
- Length follows the requested length: short ≈ 2-3 sentences, medium ≈ 4-6 sentences, long ≈ 7-10 sentences.
- Use the user's name and signature verbatim if provided.
- Do not invent facts. If information is missing, leave a clearly bracketed placeholder like [confirm date].
- Return ONLY the JSON. No prose, no markdown fences."""


def _build_user_message(state: EmailState) -> str:
    profile = state.get("user_profile", {}) or {}
    constraints = state.get("parsed_constraints", {}) or {}
    payload: dict[str, Any] = {
        "request": state.get("raw_prompt", ""),
        "recipient": state.get("recipient", ""),
        "intent": state.get("intent"),
        "tone": state.get("tone"),
        "length": state.get("length", "medium"),
        "must_include": constraints.get("must_include", []),
        "must_avoid": constraints.get("must_avoid", []),
        "topic_summary": constraints.get("topic_summary", ""),
        "user": {
            "name": profile.get("name", ""),
            "company": profile.get("company", ""),
            "signature": profile.get("signature", ""),
        },
        "tone_exemplars": profile.get("tone_exemplars", ""),
        "recent_drafts": [
            {"intent": d.get("intent"), "draft": d.get("draft")}
            for d in profile.get("recent_drafts", [])
        ],
    }
    feedback = state.get("review_feedback")
    if feedback:
        payload["reviewer_feedback"] = feedback
        payload["instruction"] = (
            "Your previous draft was rejected. Rewrite it to address the "
            "reviewer feedback above while keeping every other constraint."
        )
    return json.dumps(payload, ensure_ascii=False)


def _coerce_draft(parsed: dict[str, Any], fallback_signature: str) -> Draft:
    return {
        "subject": str(parsed.get("subject", "")).strip(),
        "greeting": str(parsed.get("greeting", "")).strip(),
        "body": str(parsed.get("body", "")).strip(),
        "closing": str(parsed.get("closing", "Best,")).strip(),
        "signature": str(parsed.get("signature", fallback_signature)).strip(),
    }


def draft_writer_agent(state: EmailState) -> dict[str, Any]:
    user_msg = _build_user_message(state)
    profile = state.get("user_profile", {}) or {}
    fallback_sig = profile.get("signature", "")

    with trace_node(state, "draft_writer_agent") as ctx:
        result = get_router().generate(
            system=SYSTEM_PROMPT,
            user=user_msg,
            agent_name="draft_writer_agent",
        )
        ctx["llm_result"] = result
        try:
            parsed = extract_json(result.text)
            draft = _coerce_draft(parsed, fallback_sig)
        except (json.JSONDecodeError, ValueError):
            # Last-resort: dump the raw text into the body so the user gets
            # *something* back instead of a hard failure.
            draft = {
                "subject": "(draft)",
                "greeting": "",
                "body": result.text,
                "closing": "Best,",
                "signature": fallback_sig,
            }
            ctx["status"] = "error"
            ctx["note"] = "writer returned non-JSON; using raw body"

        attempts = int(state.get("attempts", 0)) + 1
        if attempts > 1:
            ctx["note"] = (ctx.get("note") or "") + f" (attempt {attempts})"

    return {
        "draft": draft,
        "attempts": attempts,
        "trace": ctx["trace"],
    }
