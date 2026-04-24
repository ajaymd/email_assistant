"""Tone Stylist Agent.

Resolves the final tone (precedence: explicit user override > profile default
> inferred default) and loads matching few-shot exemplars from
``data/tone_samples/<tone>.md``. This agent does not call an LLM — it
prepares stylistic context the writer will consume.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, get_args

from ..workflow.state import EmailState, Tone
from ._common import append_trace

VALID_TONES: tuple[str, ...] = get_args(Tone)
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "data" / "tone_samples"


def _load_exemplars(tone: str) -> str:
    path = SAMPLES_DIR / f"{tone}.md"
    if not path.exists():
        return ""
    return path.read_text()


def tone_stylist_agent(state: EmailState) -> dict[str, Any]:
    started = time.perf_counter()
    profile = state.get("user_profile", {}) or {}

    tone = (
        state.get("requested_tone")
        or profile.get("default_tone")
        or "friendly"
    )
    if tone not in VALID_TONES:
        tone = "friendly"

    exemplars = _load_exemplars(tone)
    profile_with_exemplars = {**profile, "tone_exemplars": exemplars}

    return {
        "tone": tone,
        "user_profile": profile_with_exemplars,
        "trace": append_trace(
            state,
            {
                "agent": "tone_stylist_agent",
                "status": "ok",
                "model_used": None,
                "provider_used": None,
                "fell_back": False,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "note": f"resolved tone='{tone}', exemplars={'yes' if exemplars else 'no'}",
            },
        ),
    }
