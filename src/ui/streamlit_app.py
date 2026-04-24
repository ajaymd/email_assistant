"""Streamlit UI for the AI-Powered Email Assistant.

Layout:
- Sidebar: profile picker / editor, debug toggles
- Main:   prompt + parameters → Generate → preview / editor / actions
- Bottom: collapsible agent trace showing model used and fallback events.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the project root importable when run via ``streamlit run src/ui/streamlit_app.py``.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typing import get_args  # noqa: E402

import streamlit as st  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from src.exporters.pdf_export import draft_to_pdf_bytes  # noqa: E402
from src.memory import profile_store  # noqa: E402
from src.workflow.langgraph_flow import run_pipeline  # noqa: E402
from src.workflow.state import Intent, Tone  # noqa: E402

load_dotenv()


TONES: list[str] = list(get_args(Tone))
INTENTS: list[str] = ["(auto-detect)", *get_args(Intent)]
LENGTHS: list[str] = ["short", "medium", "long"]


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI-Powered Email Assistant",
    page_icon="✉️",
    layout="wide",
)

st.title("AI-Powered Email Assistant")
st.caption(
    "Multi-agent LangGraph pipeline · Claude (primary) → GPT-4 (fallback) · "
    "Personalization persisted to local JSON."
)


# ---------------------------------------------------------------------------
# Sidebar — profile selection & editor
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Profile")

    user_ids = profile_store.list_user_ids() or ["demo"]
    if "active_user" not in st.session_state:
        st.session_state.active_user = user_ids[0]

    selected = st.selectbox(
        "Active profile",
        options=user_ids,
        index=user_ids.index(st.session_state.active_user)
        if st.session_state.active_user in user_ids
        else 0,
    )
    st.session_state.active_user = selected
    profile = profile_store.load_profile(selected)

    with st.expander("Edit profile", expanded=False):
        name = st.text_input("Name", value=profile.get("name", ""))
        company = st.text_input("Company", value=profile.get("company", ""))
        signature = st.text_area(
            "Signature", value=profile.get("signature", ""), height=100
        )
        default_tone = st.selectbox(
            "Default tone",
            options=TONES,
            index=TONES.index(profile.get("default_tone", "friendly"))
            if profile.get("default_tone") in TONES
            else TONES.index("friendly"),
        )
        if st.button("Save profile"):
            profile_store.save_profile(
                {
                    "user_id": selected,
                    "name": name,
                    "company": company,
                    "signature": signature,
                    "default_tone": default_tone,
                    "drafts": profile.get("drafts", []),
                }
            )
            st.success(f"Saved profile for {selected}")

    with st.expander("New profile", expanded=False):
        new_id = st.text_input("New profile id", key="new_profile_id")
        if st.button("Create profile") and new_id.strip():
            profile_store.save_profile(
                {
                    "user_id": new_id.strip(),
                    "name": "",
                    "company": "",
                    "signature": "",
                    "default_tone": "friendly",
                    "drafts": [],
                }
            )
            st.session_state.active_user = new_id.strip()
            st.rerun()

    st.divider()
    st.caption(
        f"Drafts in history: **{len(profile.get('drafts', []))}** "
        f"· max kept: 25"
    )


# ---------------------------------------------------------------------------
# Main panel — input form
# ---------------------------------------------------------------------------
left, right = st.columns([1.1, 1])

with left:
    st.subheader("What should the email say?")
    raw_prompt = st.text_area(
        "Prompt",
        height=140,
        placeholder="e.g. Write a friendly intro to Dana about partnering on warehouse robotics. Mention our pilot results and ask for a 30-min call next week.",
        label_visibility="collapsed",
    )
    recipient = st.text_input(
        "Recipient (name or email)", placeholder="dana@example.com"
    )

    cols = st.columns(3)
    with cols[0]:
        tone = st.selectbox(
            "Tone",
            options=TONES,
            index=TONES.index(profile.get("default_tone", "friendly"))
            if profile.get("default_tone") in TONES
            else TONES.index("friendly"),
        )
    with cols[1]:
        intent_choice = st.selectbox("Intent", options=INTENTS, index=0)
    with cols[2]:
        length = st.select_slider("Length", options=LENGTHS, value="medium")

    generate = st.button("✨ Generate email", type="primary", use_container_width=True)

with right:
    st.subheader("Preview")
    preview_box = st.container(border=True)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
if generate:
    if not raw_prompt.strip():
        st.error("Please enter a prompt first.")
    else:
        with st.spinner("Running multi-agent pipeline…"):
            try:
                result = run_pipeline(
                    raw_prompt=raw_prompt,
                    recipient=recipient,
                    user_id=selected,
                    requested_tone=tone,
                    requested_intent=None
                    if intent_choice == "(auto-detect)"
                    else intent_choice,
                    length=length,
                    thread_id=f"{selected}-{abs(hash(raw_prompt))}",
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Pipeline failed: {exc}")
                result = None

        if result:
            st.session_state.last_result = result

last_result = st.session_state.get("last_result")

with preview_box:
    if not last_result:
        st.info("Your generated email will appear here.")
    elif last_result.get("error"):
        st.error(last_result["error"])
    else:
        draft = last_result.get("final_email") or last_result.get("draft") or {}
        st.markdown(f"**Subject:** {draft.get('subject', '(none)')}")
        st.write(draft.get("greeting", ""))
        st.write(draft.get("body", ""))
        st.write(draft.get("closing", ""))
        st.write(draft.get("signature", ""))


# ---------------------------------------------------------------------------
# Editor + actions
# ---------------------------------------------------------------------------
if last_result and not last_result.get("error"):
    draft = last_result.get("final_email") or {}
    st.divider()
    st.subheader("Edit & export")

    edited_subject = st.text_input("Subject", value=draft.get("subject", ""))
    edited_body = st.text_area(
        "Body",
        value="\n".join(
            filter(
                None,
                [
                    draft.get("greeting", ""),
                    "",
                    draft.get("body", ""),
                    "",
                    draft.get("closing", ""),
                    draft.get("signature", ""),
                ],
            )
        ),
        height=320,
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("💾 Save edits to history"):
            edited_draft = {
                "subject": edited_subject,
                "greeting": "",
                "body": edited_body,
                "closing": "",
                "signature": "",
            }
            profile_store.append_draft(
                selected,
                intent=last_result.get("intent", "other"),
                draft=edited_draft,
                edits="(user-edited final)",
            )
            st.success("Saved — future drafts will mirror this style.")
    with col_b:
        eml_text = (
            f"Subject: {edited_subject}\nTo: {recipient}\n\n{edited_body}\n"
        )
        st.download_button(
            "⬇️ Download .eml",
            data=eml_text.encode("utf-8"),
            file_name="draft.eml",
            mime="message/rfc822",
        )
    with col_c:
        pdf_bytes = draft_to_pdf_bytes(
            {
                "subject": edited_subject,
                "greeting": "",
                "body": edited_body,
                "closing": "",
                "signature": "",
            }
        )
        st.download_button(
            "⬇️ Download .pdf",
            data=pdf_bytes,
            file_name="draft.pdf",
            mime="application/pdf",
        )


# ---------------------------------------------------------------------------
# Agent trace — visible MCP/routing credit
# ---------------------------------------------------------------------------
if last_result:
    with st.expander("🛠 Agent trace (MCP / routing)", expanded=False):
        trace = last_result.get("trace", [])
        if not trace:
            st.write("No trace recorded.")
        else:
            for entry in trace:
                badge = "✅" if entry.get("status") == "ok" else (
                    "⚠️" if entry.get("status") in ("retry", "skipped") else "❌"
                )
                model = entry.get("model_used") or "—"
                provider = entry.get("provider_used") or "—"
                fb = " (fell back)" if entry.get("fell_back") else ""
                latency = entry.get("latency_ms", 0)
                note = entry.get("note") or ""
                st.markdown(
                    f"{badge} **{entry['agent']}** — `{provider}/{model}`{fb}  "
                    f"· {latency} ms"
                    + (f"  \n   _{note}_" if note else "")
                )

        # Surface high-level metadata for the demo video.
        meta_cols = st.columns(3)
        meta_cols[0].metric("Intent", last_result.get("intent", "—"))
        meta_cols[1].metric("Tone", last_result.get("tone", "—"))
        meta_cols[2].metric("Writer attempts", last_result.get("attempts", 0))
