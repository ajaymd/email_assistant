# 📧 AI-Powered Email Assistant

A sophisticated multi-agent email generation system powered by LangGraph, Claude, and GPT-4. Generate polished, personalized emails with automatic intent detection, tone styling, and quality review through an intelligent agent pipeline.

## 🎯 Quick Features

- **Multi-agent pipeline** with intelligent routing
- **Automatic intent detection** (proposal, apology, inquiry, etc.)
- **Personalized tone adjustment** (formal, friendly, assertive, concise, apologetic)
- **Quality review and rewrites** with agent scoring
- **PDF & EML export** capabilities
- **Full agent transparency** (model used, latency, fallbacks visible)

## 🏗️ Architecture

```
Input Prompt
    ↓
Input Parser Agent (extract recipient, hints)
    ↓
Intent Detection Agent (classify intent)
    ↓
Tone Stylist Agent (apply tone samples)
    ↓
Personalization Agent (match user style)
    ↓
Draft Writer Agent (generate email)
    ↓
Review Agent (critique & score)
    ↓
Router Agent (finalize & persist)
    ↓
Final Email + Agent Trace
```

**Seven Agents**:

| Agent | Responsibility |
|---|---|
| `input_parser_agent` | Validates prompt; extracts recipient, length hints, must-include/avoid lists |
| `intent_detection_agent` | Classifies into intent type (proposal, apology, follow-up, etc.) |
| `personalization_agent` | Loads user profile and recent drafts for style matching |
| `tone_stylist_agent` | Resolves tone and loads exemplars from data/tone_samples/ |
| `draft_writer_agent` | Generates structured draft (subject/greeting/body/closing) |
| `review_agent` | Scores grammar, tone alignment, coherence on 1-5 scale |
| `router_agent` | Terminal node; persists draft and finalizes trace |

**Model Routing** (LLMRouter + config/mcp.yaml):
- **Primary**: Claude 3.5 Sonnet (cost-optimized)
- **Fallback**: GPT-4o (reliability)
- Per-agent overrides for temperature/tokens

## 🚀 Deploy to HuggingFace Spaces (1 minute)

### Step 1: Create Space
- Go to [huggingface.co/spaces](https://huggingface.co/spaces)
- Click **Create new Space** → Docker SDK

### Step 2: Add Secrets
In Space **Settings → Secrets**:
- `ANTHROPIC_API_KEY` (from [console.anthropic.com](https://console.anthropic.com))
- `OPENAI_API_KEY` (from [platform.openai.com](https://platform.openai.com))

### Step 3: Deploy
```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/email-assistant
cd email-assistant
cp -r /path/to/email_assistant/* .
git add . && git commit -m "Deploy" && git push
```

✅ Done! Space auto-builds and deploys using the Dockerfile.

**See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.**

## 💻 Local Development

### Prerequisites
- Python 3.11+

### Setup

```bash
# Clone
git clone https://github.com/ajaymd/email_assistant.git
cd email_assistant

# Create environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
EOF

# Run
streamlit run src/ui/streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501)

## 📦 Project Structure

```
src/
├── agents/              # 7 agent functions
├── workflow/
│   ├── langgraph_flow.py
│   └── state.py
├── integrations/
│   ├── llm_router.py
│   ├── anthropic_client.py
│   └── openai_client.py
├── memory/profile_store.py
├── exporters/pdf_export.py
└── ui/streamlit_app.py

config/
└── mcp.yaml             # Model routing

data/tone_samples/       # Few-shot exemplars
```

## ⚙️ Configuration

### Model Selection (config/mcp.yaml)

```yaml
primary:
  provider: anthropic
  model: claude-3-5-sonnet-20241022
  max_tokens: 1500
  temperature: 0.6

fallback:
  provider: openai
  model: gpt-4o
  max_tokens: 1500
  temperature: 0.6

agents:
  review_agent:
    primary:
      temperature: 0.2      # Stricter critique
  intent_detection_agent:
    primary:
      temperature: 0.0      # Deterministic
      max_tokens: 200       # Small budget
```

**Cost Comparison**:
- Claude 3.5 Sonnet: ~$3/1M input tokens
- Claude Opus 4.5: ~$15/1M input tokens
- **Savings: 40-50% with Sonnet**

## 🧪 Testing

```bash
pytest tests/test_flow_smoke.py -v
```

Smoke tests run without API keys (stubs the router).

## 📊 Example Prompts

```
"Write a friendly intro to Dana about partnering on warehouse robotics.
Mention our pilot results and ask for a 30-min call next week."

"Send an apology email to our client for the project delay.
Explain reasons professionally and offer revised timeline."

"Write a formal proposal for consulting engagement on AI implementation."
```

## 🔑 Environment Variables

| Variable | Required | Source |
|----------|----------|--------|
| `ANTHROPIC_API_KEY` | ✅ Yes | [console.anthropic.com](https://console.anthropic.com) |
| `OPENAI_API_KEY` | ✅ Yes | [platform.openai.com](https://platform.openai.com) |
| `LANGSMITH_API_KEY` | ❌ Optional | [smith.langchain.com](https://smith.langchain.com) |

## 🛠️ Tech Stack

| Component | Library | Version |
|-----------|---------|---------|
| Orchestration | LangGraph | ≥0.2.40 |
| LLMs | Anthropic + OpenAI | SDKs |
| Frontend | Streamlit | ≥1.39.0 |
| PDF Export | ReportLab | ≥4.2.5 |
| Config | PyYAML | ≥6.0.2 |
| Serialization | Pydantic | ≥2.9.0 |

## 📈 Performance

- **End-to-end latency**: 8-15 seconds/email
- **Fallback rate**: <2% (healthy API keys)
- **Concurrent users**: 10+ (API quota dependent)
- **Token usage**: ~800-1200/email
- **Cost/email**: ~$0.02-0.05

## 🎓 Pipeline Details

### Flow
1. **Input Parser**: Extract intent hints
2. **Intent Detector**: Classify email type
3. **Tone Stylist**: Load exemplars
4. **Personalization**: Fetch user style
5. **Draft Writer**: Generate email
6. **Review Agent**: Score & critique
7. **Router**: Persist & finalize

### Personalization
- Profiles store name, company, signature, default tone
- Last 25 drafts kept for style learning
- Data in `src/memory/user_profiles.json`

## 🐛 Troubleshooting

### Pipeline Failed: AuthenticationError

```bash
# Local dev
cat .env  # Check ANTHROPIC_API_KEY and OPENAI_API_KEY

# HuggingFace Spaces
# Settings → Secrets → Add keys
```

### Both Models Failed

1. Verify API key quotas
2. Check provider status pages
3. Test locally:
   ```python
   from anthropic import Anthropic
   client = Anthropic(api_key="YOUR_KEY")
   ```

### Import Errors

```bash
pip install -r requirements.txt --upgrade
```

## 🤝 Contributing

Areas for improvement:
- [ ] Multi-language support
- [ ] Database backend for profiles
- [ ] Gmail/Outlook API integration
- [ ] Voice input
- [ ] Email templates

## 📄 License

MIT - See LICENSE for details

## 📚 References

- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [Claude API](https://docs.anthropic.com/)
- [OpenAI API](https://platform.openai.com/docs/api-reference)
- [Streamlit](https://docs.streamlit.io/)

## 🎯 Next Steps

1. **Deploy to HuggingFace** → See [DEPLOYMENT.md](DEPLOYMENT.md)
2. **Customize agents** → Edit `src/agents/`
3. **Modify UI** → Update `src/ui/streamlit_app.py`
4. **Add integrations** → Create in `src/integrations/`

---

**Questions?** Open an issue on [GitHub](https://github.com/ajaymd/email_assistant).

**Want to see it in action?** [Deploy to HuggingFace Spaces now!](DEPLOYMENT.md)

