"""LangGraph wiring for the email assistant.

The graph is straight-line through the seven agents, with one conditional
edge after the reviewer that either retries the writer (with feedback) or
exits via the router agent. ``MemorySaver`` provides per-user session
checkpointing so a Streamlit rerun does not lose in-flight context.
"""
from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from ..agents.draft_writer_agent import draft_writer_agent
from ..agents.input_parser_agent import input_parser_agent
from ..agents.intent_detection_agent import intent_detection_agent
from ..agents.personalization_agent import personalization_agent
from ..agents.review_agent import review_agent
from ..agents.router_agent import router_agent
from ..agents.tone_stylist_agent import tone_stylist_agent
from .state import MAX_RETRIES, EmailState


def _after_review(state: EmailState) -> str:
    """Conditional router: retry the writer until we hit MAX_RETRIES."""
    if state.get("review_ok"):
        return "router_agent"
    if int(state.get("attempts", 0)) >= MAX_RETRIES + 1:
        # We've already tried writer (1) + retries (MAX_RETRIES). Give up.
        return "router_agent"
    return "draft_writer_agent"


def _after_input_parser(state: EmailState) -> str:
    """Bail out early if the input was empty/unusable."""
    if state.get("error"):
        return END
    return "intent_detection_agent"


def build_graph(checkpointer: MemorySaver | None = None):
    """Build and compile the email-assistant graph."""
    graph = StateGraph(EmailState)

    graph.add_node("input_parser_agent", input_parser_agent)
    graph.add_node("intent_detection_agent", intent_detection_agent)
    graph.add_node("personalization_agent", personalization_agent)
    graph.add_node("tone_stylist_agent", tone_stylist_agent)
    graph.add_node("draft_writer_agent", draft_writer_agent)
    graph.add_node("review_agent", review_agent)
    graph.add_node("router_agent", router_agent)

    graph.add_edge(START, "input_parser_agent")
    graph.add_conditional_edges(
        "input_parser_agent",
        _after_input_parser,
        {
            "intent_detection_agent": "intent_detection_agent",
            END: END,
        },
    )
    graph.add_edge("intent_detection_agent", "personalization_agent")
    graph.add_edge("personalization_agent", "tone_stylist_agent")
    graph.add_edge("tone_stylist_agent", "draft_writer_agent")
    graph.add_edge("draft_writer_agent", "review_agent")
    graph.add_conditional_edges(
        "review_agent",
        _after_review,
        {
            "draft_writer_agent": "draft_writer_agent",
            "router_agent": "router_agent",
        },
    )
    graph.add_edge("router_agent", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())


# Module-level singleton — Streamlit reruns reuse the same compiled graph.
_compiled = None


def get_compiled_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled


def run_pipeline(
    *,
    raw_prompt: str,
    recipient: str = "",
    user_id: str = "demo",
    requested_tone: str | None = None,
    requested_intent: str | None = None,
    length: str = "medium",
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Convenience entry point for the UI and tests.

    ``thread_id`` keys the LangGraph checkpoint — pass a stable id (e.g. the
    user_id) to keep cross-rerun state, or a fresh uuid for a clean run.
    """
    inputs: EmailState = {
        "raw_prompt": raw_prompt,
        "recipient": recipient,
        "user_id": user_id,
        "requested_tone": requested_tone,  # type: ignore[typeddict-item]
        "requested_intent": requested_intent,  # type: ignore[typeddict-item]
        "length": length,  # type: ignore[typeddict-item]
        "attempts": 0,
        "trace": [],
    }
    config = {"configurable": {"thread_id": thread_id or user_id}}
    return get_compiled_graph().invoke(inputs, config=config)
