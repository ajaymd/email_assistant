"""Personalization Agent.

Loads the user's profile and recent drafts so the writer can mirror tone,
sign off correctly, and avoid restating things the user has already covered.
This agent does not call an LLM — it just hits the JSON profile store.
"""
from __future__ import annotations

import time
from typing import Any

from ..memory import profile_store
from ..workflow.state import EmailState
from ._common import append_trace


def personalization_agent(state: EmailState) -> dict[str, Any]:
    started = time.perf_counter()
    user_id = state.get("user_id", "demo")
    profile = profile_store.load_profile(user_id)
    intent = state.get("intent")
    recent = profile_store.recent_drafts(user_id, intent=intent, limit=3)

    profile_with_history = {**profile, "recent_drafts": recent}
    return {
        "user_profile": profile_with_history,
        "trace": append_trace(
            state,
            {
                "agent": "personalization_agent",
                "status": "ok",
                "model_used": None,
                "provider_used": None,
                "fell_back": False,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "note": f"loaded profile '{user_id}' with {len(recent)} prior drafts",
            },
        ),
    }
