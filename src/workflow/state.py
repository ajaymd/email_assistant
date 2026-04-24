"""Shared graph state for the email assistant workflow.

Every node receives an ``EmailState`` and returns a partial dict that
LangGraph merges back in. Keeping the schema explicit (and small) makes the
graph easy to reason about and easy to mock in tests.
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict

# Maximum number of writer→reviewer cycles before we exit gracefully via the
# router agent. Two retries (three writer attempts total) is plenty in
# practice and keeps the worst-case latency bounded.
MAX_RETRIES = 2

Tone = Literal["formal", "friendly", "assertive", "apologetic", "concise"]
Intent = Literal[
    "outreach",
    "follow_up",
    "apology",
    "info_share",
    "internal_update",
    "request",
    "other",
]
Length = Literal["short", "medium", "long"]


class Draft(TypedDict, total=False):
    """Structured email draft produced by the writer agent."""

    subject: str
    greeting: str
    body: str
    closing: str
    signature: str


class TraceEntry(TypedDict, total=False):
    """One row in the agent trace shown in the UI."""

    agent: str
    status: str  # "ok" | "error" | "retry" | "skipped"
    model_used: str | None
    provider_used: str | None
    fell_back: bool
    latency_ms: int
    note: str | None


class EmailState(TypedDict, total=False):
    # Inputs
    raw_prompt: str
    recipient: str
    user_id: str
    requested_tone: Tone | None  # explicit user override
    requested_intent: Intent | None  # explicit user override
    length: Length

    # Derived by the agents
    parsed_constraints: dict[str, Any]
    intent: Intent
    tone: Tone
    user_profile: dict[str, Any]
    draft: Draft
    review_ok: bool
    review_feedback: str
    attempts: int

    # Bookkeeping
    trace: list[TraceEntry]
    final_email: Draft
    error: str | None
