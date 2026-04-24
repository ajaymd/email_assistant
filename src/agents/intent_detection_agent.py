"""Intent Detection Agent.

Classifies the user's request into one of seven canonical intents. The
classifier is forced to return a single label so downstream agents can rely on
it without further parsing.
"""
from __future__ import annotations

from typing import Any, get_args

from ..integrations.llm_router import get_router
from ..workflow.state import EmailState, Intent
from ._common import trace_node

VALID_INTENTS: tuple[str, ...] = get_args(Intent)

SYSTEM_PROMPT = f"""You classify email-writing requests into exactly one \
intent label. Allowed labels: {', '.join(VALID_INTENTS)}.

Definitions:
- outreach: cold or warm first-contact email (sales, networking, partnership)
- follow_up: a nudge or reminder about a prior conversation/thread
- apology: expressing regret or making amends
- info_share: sharing information, an update, or a heads-up (no action required)
- internal_update: status update sent to colleagues or a team
- request: asking for something (info, time, a favor, approval)
- other: anything that does not fit the categories above

Return ONLY the label — a single word, lowercase, no punctuation, no prose."""


def intent_detection_agent(state: EmailState) -> dict[str, Any]:
    # Honor explicit user override if provided.
    requested = state.get("requested_intent")
    if requested:
        return {
            "intent": requested,
            "trace": list(state.get("trace") or [])
            + [
                {
                    "agent": "intent_detection_agent",
                    "status": "skipped",
                    "model_used": None,
                    "provider_used": None,
                    "fell_back": False,
                    "latency_ms": 0,
                    "note": f"user override: {requested}",
                }
            ],
        }

    user_msg = state.get("raw_prompt", "")

    with trace_node(state, "intent_detection_agent") as ctx:
        result = get_router().generate(
            system=SYSTEM_PROMPT,
            user=user_msg,
            agent_name="intent_detection_agent",
        )
        ctx["llm_result"] = result
        label = result.text.strip().lower().split()[0] if result.text.strip() else "other"
        # Strip stray punctuation just in case.
        label = label.strip(".,!?:;\"'")
        if label not in VALID_INTENTS:
            ctx["note"] = f"unrecognized label '{label}', defaulting to 'other'"
            label = "other"

    return {
        "intent": label,
        "trace": ctx["trace"],
    }
