"""Input Parsing Agent.

Validates the prompt is non-empty and pulls out structured constraints
(recipient, length hints, must-include / must-avoid phrases) so the
downstream agents do not all need to re-parse free text.
"""
from __future__ import annotations

import json
from typing import Any

from ..integrations.llm_router import get_router
from ..workflow.state import EmailState
from ._common import extract_json, trace_node

SYSTEM_PROMPT = """You are an input parser for an email-drafting assistant. \
Given a free-form user request, return a JSON object with the following \
fields (use empty strings or empty lists when unknown):

{
  "recipient_hint": "name or role of the recipient if mentioned, else ''",
  "length_hint": "one of: short, medium, long, ''",
  "must_include": ["list of phrases or facts the email must contain"],
  "must_avoid": ["list of things to avoid"],
  "topic_summary": "one-sentence summary of what the email is about"
}

Return ONLY the JSON object — no prose, no markdown fences."""


def input_parser_agent(state: EmailState) -> dict[str, Any]:
    raw_prompt = (state.get("raw_prompt") or "").strip()
    if not raw_prompt:
        return {
            "error": "Prompt is empty.",
            "trace": list(state.get("trace") or [])
            + [
                {
                    "agent": "input_parser_agent",
                    "status": "error",
                    "model_used": None,
                    "provider_used": None,
                    "fell_back": False,
                    "latency_ms": 0,
                    "note": "empty prompt",
                }
            ],
        }

    user_msg = json.dumps(
        {
            "request": raw_prompt,
            "recipient_field": state.get("recipient", ""),
        }
    )

    with trace_node(state, "input_parser_agent") as ctx:
        result = get_router().generate(
            system=SYSTEM_PROMPT,
            user=user_msg,
            agent_name="input_parser_agent",
        )
        ctx["llm_result"] = result
        try:
            parsed = extract_json(result.text)
        except json.JSONDecodeError:
            parsed = {
                "recipient_hint": "",
                "length_hint": "",
                "must_include": [],
                "must_avoid": [],
                "topic_summary": raw_prompt[:160],
            }
            ctx["note"] = "fell back to heuristic parse (JSON decode failed)"

    return {
        "parsed_constraints": parsed,
        "trace": ctx["trace"],
    }
