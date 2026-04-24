# AI-Powered Email Assistant

A multi-agent email drafting assistant.
Give it a free-form prompt, a tone, and an optional recipient, and a 7-agent LangGraph pipeline returns an editable, exportable email draft.

The LLM layer uses **Claude as primary with GPT-4 as fallback**, so the MCP / routing requirement is exercised on every run — when Claude fails, GPT-4 takes over and the swap is logged in the agent trace and in LangSmith.

---

## Architecture

```
                      ┌────────────────────┐
                      │   Streamlit UI     │
                      │  (compose / edit)  │
                      └─────────┬──────────┘
                                │ run_pipeline()
                                ▼
┌───────────────────────────────────────────────────────────────┐
│                       LangGraph                               │
│                                                               │
│  input_parser → intent_detection → personalization →          │
│  tone_stylist → draft_writer → review_agent ─┐                │
│                       ▲                      │                │
│                       │  (retry w/ feedback) │                │
│                       └──── ok=false ────────┘                │
│                                              │                │
│                                              ▼                │
│                                       router_agent → END      │
└───────────────────────────────────────────────────────────────┘
                                │
                                ▼
                ┌────────────────────────────┐
                │   LLMRouter (MCP layer)    │
                │  Claude  ─fallback→  GPT-4 │
                └────────────────────────────┘
                                │
                                ▼
                  ┌──────────────────────────┐
                  │ user_profiles.json       │
                  │ (persisted personality + │
                  │  draft history)          │
                  └──────────────────────────┘
```

### The seven agents

| # | Agent | Responsibility |
|---|---|---|
| 1 | `input_parser_agent`     | Validates the prompt; extracts recipient hint, length hint, must-include / must-avoid lists, and a topic summary as structured JSON. |
| 2 | `intent_detection_agent` | Classifies into one of `outreach / follow_up / apology / info_share / internal_update / request / other`. Honored as a no-op if the user passes an explicit override. |
| 3 | `personalization_agent`  | Loads the user profile from `user_profiles.json` and the 3 most recent drafts (intent-matched when possible) so the writer can mirror the user's voice. No LLM call. |
| 4 | `tone_stylist_agent`     | Resolves the final tone (precedence: explicit override > profile default > `friendly`) and loads few-shot exemplars from `data/tone_samples/<tone>.md`. No LLM call. |
| 5 | `draft_writer_agent`     | Produces a structured draft (`subject / greeting / body / closing / signature`) via `LLMRouter`. On a retry, picks up the reviewer's feedback and rewrites accordingly. |
| 6 | `review_agent`           | Strict critic. Scores grammar, tone alignment, and coherence each on 1–5; returns `ok=true` only when all three are ≥ 4. Misbehaving reviewer defaults to `ok=true` rather than looping forever. |
| 7 | `router_agent`           | Terminal node. Promotes the latest draft to `final_email`, persists it to `user_profiles.json`, and finalizes the agent trace. Reached either after a clean review pass or after `MAX_RETRIES` (best-effort delivery). |

### Routing / fallback (the MCP layer)

`src/integrations/llm_router.py` reads `config/mcp.yaml`, which declares a global primary (Claude) and fallback (GPT-4) plus per-agent overrides. On every call:

1. Try the primary model.
2. On any of `{network error, rate limit, empty output, JSON parse failure}`, log the failure and call the fallback model.
3. Record `model_used`, `provider_used`, `fell_back`, and `latency_ms` so the UI can show them in the agent trace.

LangSmith tracing is wired via the `@traceable` decorator on `LLMRouter.generate`. Set `LANGSMITH_API_KEY` and the routing decisions and per-node spans show up in your LangSmith dashboard.

### Memory layers

- **In-session:** LangGraph's `MemorySaver` checkpointer, keyed by `thread_id` (which the UI sets to `<user_id>-<hash(prompt)>`). Survives Streamlit reruns.
- **Cross-session:** `src/memory/profile_store.py` writes `user_profiles.json` atomically. Each user's last 25 drafts are kept and surfaced as soft style anchors to the writer agent.

---

## Repository layout

```
email_assistant/
├── src/
│   ├── agents/              # 7 agent functions (one file each)
│   ├── workflow/
│   │   ├── state.py         # EmailState TypedDict, MAX_RETRIES
│   │   └── langgraph_flow.py# build_graph + run_pipeline
│   ├── ui/streamlit_app.py  # Streamlit UI
│   ├── memory/
│   │   ├── profile_store.py # load/save/append_draft
│   │   └── user_profiles.json
│   ├── integrations/
│   │   ├── llm_router.py    # MCP layer with fallback
│   │   ├── anthropic_client.py
│   │   └── openai_client.py
│   └── exporters/pdf_export.py
├── data/tone_samples/       # few-shot exemplars per tone
├── config/mcp.yaml          # primary / fallback / per-agent overrides
├── tests/test_flow_smoke.py # full graph smoke test (no API keys needed)
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Running it

### 1. Local (recommended for development)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in ANTHROPIC_API_KEY and OPENAI_API_KEY
streamlit run src/ui/streamlit_app.py
```

Open <http://localhost:8501>.

### 2. Docker

```bash
docker build -t email-assistant .
docker run --rm -p 8501:8501 --env-file .env email-assistant
```

### 3. Tests

```bash
pytest tests/test_flow_smoke.py -v
```

The smoke tests stub the router so they run without any API keys. They cover:

- the happy path (writer → reviewer → router, all 7 agents present in the trace in order); and
- the retry loop (reviewer rejects twice, writer runs 3 times, then exits via the router).

---

## Demo checklist (matches the rubric)

| Rubric item | How to demo |
|---|---|
| **Functionality (30%)** | Generate three drafts (cold outreach, apology, internal update) with three different tones; show that each renders, is editable, and exports cleanly. |
| **Agentic architecture (25%)** | Open the *Agent trace* expander — every run shows all 7 agents, their model, and their latency. |
| **UX (20%)** | Walk through profile picker → form → preview → editor → `.eml` / `.pdf` download. |
| **Routing & MCP (10%)** | Temporarily unset `ANTHROPIC_API_KEY`, regenerate, point at the trace row that says `(fell back)` and at the LangSmith run that records the swap. |
| **Innovation (10%)** | Five built-in tones (formal, friendly, assertive, apologetic, concise), per-agent model overrides via `mcp.yaml`, and personalization that mirrors prior drafts. |
| **Documentation (10%)** | This file. |

---

## Configuration reference

### `config/mcp.yaml`

```yaml
primary:
  provider: anthropic
  model: claude-opus-4-5
  max_tokens: 1500
  temperature: 0.6

fallback:
  provider: openai
  model: gpt-4o
  max_tokens: 1500
  temperature: 0.6

agents:
  review_agent:
    primary:  { provider: anthropic, model: claude-opus-4-5, temperature: 0.2 }
    fallback: { provider: openai,    model: gpt-4o,         temperature: 0.2 }
  intent_detection_agent:
    primary:  { provider: anthropic, model: claude-opus-4-5, temperature: 0.0, max_tokens: 200 }
    fallback: { provider: openai,    model: gpt-4o-mini,    temperature: 0.0, max_tokens: 200 }
```

Add a new tone by dropping a `data/tone_samples/<tone>.md` file and adding the literal to `Tone` in `src/workflow/state.py`. Add a new agent override by editing `mcp.yaml` — no code change required.

### Environment variables (`.env`)

| Var | Required? | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY`     | yes | Primary model (Claude) |
| `OPENAI_API_KEY`        | yes | Fallback model (GPT-4) |
| `LANGSMITH_API_KEY`     | no  | Enables LangSmith tracing for the demo |
| `LANGSMITH_PROJECT`     | no  | Project name in LangSmith (default: `email-assistant`) |
| `LANGSMITH_TRACING`     | no  | Set to `true` to actually emit traces |

---

## Prompt design notes

- **Writer (`draft_writer_agent`)** — uses constrained JSON output so the UI can render the subject, body, and signature independently. The system prompt enforces hard rules on length, must-include/must-avoid honoring, and "no invented facts" via bracketed placeholders.
- **Reviewer (`review_agent`)** — three-axis numeric scoring (grammar / tone / coherence) gives a deterministic gate. Defaulting to `ok=true` on a malformed reviewer response prevents the graph from hanging on a flaky critic.
- **Intent classifier** — pinned to `temperature=0.0` and a tight 200-token budget via per-agent overrides in `mcp.yaml`; classification is the one place we want zero creativity.
- **Tone stylist** — does not call an LLM at all. Loading exemplars from disk is faster, cheaper, and easier to extend than asking a model to "be more formal".
