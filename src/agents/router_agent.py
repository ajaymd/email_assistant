"""Routing & Memory Agent.

Terminal node. Promotes the latest draft to ``final_email``, persists it to
the user profile store so future generations can mirror the user's recent
style, and finalizes the trace. This is also where we land when the writer
hits ``MAX_RETRIES`` without the reviewer signing off — we still return the
best-effort draft rather than failing.
"""
from __future__ import annotations

import time
from typing import Any

from ..memory import profile_store
from ..workflow.state import EmailState
from ._common import append_trace


def router_agent(state: EmailState) -> dict[str, Any]:
    started = time.perf_counter()
    draft = state.get("draft") or {}
    user_id = state.get("user_id", "demo")
    intent = state.get("intent", "other")

    note_parts: list[str] = []
    if not state.get("review_ok"):
        note_parts.append(
            f"best-effort delivery after {state.get('attempts', 0)} attempts"
        )
    else:
        note_parts.append(f"reviewer approved on attempt {state.get('attempts', 1)}")

    # Persist the draft so subsequent generations can learn the user's style.
    try:
        profile_store.append_draft(user_id, intent=intent, draft=draft)
        note_parts.append("persisted to profile store")
    except Exception as exc:  # noqa: BLE001
        note_parts.append(f"persistence failed: {exc}")

    return {
        "final_email": draft,
        "trace": append_trace(
            state,
            {
                "agent": "router_agent",
                "status": "ok",
                "model_used": None,
                "provider_used": None,
                "fell_back": False,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "note": "; ".join(note_parts),
            },
        ),
    }
