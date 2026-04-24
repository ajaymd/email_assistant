"""End-to-end smoke test for the email-assistant graph.

The router is monkeypatched to return canned JSON so the test runs without
any real API keys, but it exercises the full LangGraph topology — every
agent node and the conditional retry edge.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.integrations.llm_router import LLMResult  # noqa: E402
from src.memory import profile_store  # noqa: E402
from src.workflow import langgraph_flow  # noqa: E402

# Each agent does ``from ..integrations.llm_router import get_router``, which
# binds the symbol into the agent's own module namespace. Patching the source
# module is therefore not enough — we have to replace the binding inside each
# agent module that calls the router.
_AGENT_MODULES_USING_ROUTER = (
    "src.agents.input_parser_agent",
    "src.agents.intent_detection_agent",
    "src.agents.draft_writer_agent",
    "src.agents.review_agent",
)


def _patch_router(monkeypatch, fake_router) -> None:
    for mod_path in _AGENT_MODULES_USING_ROUTER:
        monkeypatch.setattr(f"{mod_path}.get_router", lambda r=fake_router: r)


def _canned(agent_name: str | None) -> LLMResult:
    """Return a deterministic LLMResult for whichever agent is calling."""
    if agent_name == "input_parser_agent":
        text = json.dumps(
            {
                "recipient_hint": "Dana",
                "length_hint": "medium",
                "must_include": ["thirty-minute call"],
                "must_avoid": [],
                "topic_summary": "Intro outreach to Dana about a partnership",
            }
        )
    elif agent_name == "intent_detection_agent":
        text = "outreach"
    elif agent_name == "draft_writer_agent":
        text = json.dumps(
            {
                "subject": "Quick hello from Kaidemark",
                "greeting": "Hi Dana,",
                "body": "Hope your week is off to a good start! I came across your work and would love to set up a thirty-minute call to compare notes.\n\nLet me know if next week works.",
                "closing": "Cheers,",
                "signature": "Ajay M",
            }
        )
    elif agent_name == "review_agent":
        text = json.dumps(
            {
                "ok": True,
                "grammar_score": 5,
                "tone_score": 5,
                "coherence_score": 5,
                "feedback": "",
            }
        )
    else:
        text = "{}"

    return LLMResult(
        text=text,
        model_used="stub-model",
        provider_used="stub",
        fell_back=False,
        latency_ms=1,
        attempts=[{"provider": "stub", "model": "stub-model", "ok": True, "error": None}],
    )


def test_full_pipeline_runs_all_agents(tmp_path, monkeypatch):
    # Redirect the profile store to a temp file so the test does not write
    # to the real user_profiles.json.
    fake_profiles = tmp_path / "user_profiles.json"
    fake_profiles.write_text(
        json.dumps(
            {
                "users": {
                    "demo": {
                        "name": "Ajay M",
                        "company": "Kaidemark Robotics",
                        "signature": "Ajay M\nKaidemark Robotics",
                        "default_tone": "friendly",
                        "drafts": [],
                    }
                }
            }
        )
    )
    monkeypatch.setattr(profile_store, "PROFILE_PATH", fake_profiles)

    # Stub the router so no network calls happen.
    fake_router = mock.Mock()
    fake_router.generate.side_effect = lambda *, system, user, agent_name=None: _canned(
        agent_name
    )
    _patch_router(monkeypatch, fake_router)
    # Reset the compiled graph singleton so it picks up the patched router.
    monkeypatch.setattr(langgraph_flow, "_compiled", None)

    final_state = langgraph_flow.run_pipeline(
        raw_prompt="Write a friendly intro to Dana about partnering on warehouse robotics",
        recipient="dana@example.com",
        user_id="demo",
        requested_tone="friendly",
        length="medium",
        thread_id="test-thread-1",
    )

    # The final email is populated.
    assert final_state.get("final_email"), "expected final_email to be set"
    assert final_state["final_email"]["subject"] == "Quick hello from Kaidemark"

    # All seven agents are present in the trace, in order.
    trace_agents = [entry["agent"] for entry in final_state["trace"]]
    expected_order = [
        "input_parser_agent",
        "intent_detection_agent",
        "personalization_agent",
        "tone_stylist_agent",
        "draft_writer_agent",
        "review_agent",
        "router_agent",
    ]
    assert trace_agents == expected_order, f"trace order mismatch: {trace_agents}"

    # Reviewer approved on the first pass, so attempts should be 1.
    assert final_state["attempts"] == 1
    assert final_state["review_ok"] is True

    # Persistence happened: the user's drafts list now has one entry.
    profile = profile_store.load_profile("demo")
    assert len(profile["drafts"]) == 1
    assert profile["drafts"][0]["intent"] == "outreach"


def test_pipeline_retries_on_reviewer_rejection(tmp_path, monkeypatch):
    """If the reviewer rejects, the writer should run again, then exit."""
    fake_profiles = tmp_path / "user_profiles.json"
    fake_profiles.write_text(json.dumps({"users": {"demo": {"drafts": []}}}))
    monkeypatch.setattr(profile_store, "PROFILE_PATH", fake_profiles)

    review_calls = {"n": 0}

    def canned_with_rejection(*, system, user, agent_name=None):
        if agent_name == "review_agent":
            review_calls["n"] += 1
            # Reject the first two reviews, accept the third.
            ok = review_calls["n"] >= 3
            return LLMResult(
                text=json.dumps(
                    {
                        "ok": ok,
                        "grammar_score": 5 if ok else 2,
                        "tone_score": 5 if ok else 2,
                        "coherence_score": 5 if ok else 2,
                        "feedback": "" if ok else "rewrite this; it's too generic",
                    }
                ),
                model_used="stub-model",
                provider_used="stub",
                fell_back=False,
                latency_ms=1,
            )
        return _canned(agent_name)

    fake_router = mock.Mock()
    fake_router.generate.side_effect = canned_with_rejection
    _patch_router(monkeypatch, fake_router)
    monkeypatch.setattr(langgraph_flow, "_compiled", None)

    final_state = langgraph_flow.run_pipeline(
        raw_prompt="Write a friendly intro to Dana",
        user_id="demo",
        requested_tone="friendly",
        thread_id="test-thread-2",
    )

    # Writer should have run 3 times (initial + 2 retries) per MAX_RETRIES=2.
    writer_runs = [
        e for e in final_state["trace"] if e["agent"] == "draft_writer_agent"
    ]
    assert len(writer_runs) == 3, f"expected 3 writer runs, got {len(writer_runs)}"
    assert final_state["attempts"] == 3
    assert final_state["review_ok"] is True
    assert final_state.get("final_email")
