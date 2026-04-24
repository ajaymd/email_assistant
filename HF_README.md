# 📧 AI-Powered Email Assistant

An intelligent multi-agent email generation system powered by LangGraph, Claude, and GPT-4. Generates polished, personalized emails with automatic intent detection, tone styling, and quality review.

## 🎯 Features

- **Multi-Agent Pipeline**: Input parser → Intent detector → Tone stylist → Draft writer → Reviewer
- **Intelligent Model Routing**: Primary Claude 3.5 Sonnet with GPT-4 fallback for reliability
- **Personalization**: Stores user profiles and writing history for style matching
- **Smart Export**: Download as .eml or .pdf
- **Agent Transparency**: View which models were used and latency metrics
- **Auto-Detection**: Automatically infers email intent (proposal, apology, inquiry, etc.)

## 🚀 Getting Started

### 1. Create HuggingFace Space

Go to [huggingface.co/spaces](https://huggingface.co/spaces) and create a **new Space**:
- **License**: MIT (or your preference)  
- **Space SDK**: Docker
- **Visibility**: Public (for demo)

### 2. Add Your API Keys

In your Space settings → **Secrets and variables**:

Add these secrets:
- **ANTHROPIC_API_KEY**: Your Anthropic API key from [console.anthropic.com](https://console.anthropic.com)
- **OPENAI_API_KEY**: Your OpenAI API key from [platform.openai.com](https://platform.openai.com)

### 3. Clone and Push

```bash
git clone https://huggingface.co/spaces/your-username/email-assistant
cd email-assistant

# Copy all files from this repo into the cloned space directory
git add .
git commit -m "Initial commit: Email Assistant"
git push
```

The Space will automatically build and deploy using the Dockerfile!

## 💻 Local Development

### Prerequisites
- Python 3.11+
- pip

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set API keys (create .env file)
echo "ANTHROPIC_API_KEY=your-key-here" > .env
echo "OPENAI_API_KEY=your-key-here" >> .env
```

### Run Locally

```bash
streamlit run src/ui/streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## 📋 How It Works

### Pipeline Flow

1. **Input Parser**: Extracts recipient and intent hints from your prompt
2. **Intent Detector**: Classifies the email type (proposal, apology, inquiry, etc.)
3. **Tone Stylist**: Applies your chosen tone (formal, friendly, assertive, etc.)
4. **Draft Writer**: Generates a polished first draft
5. **Review Agent**: Critique and score, requesting rewrites for improvement

### Personalization

- Profiles store your name, company, signature, and default tone
- Previous drafts are remembered to match your writing style
- All data stored locally in `src/memory/user_profiles.json`

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Orchestration** | LangGraph 0.2.40+ |
| **LLM Integration** | Anthropic (primary), OpenAI (fallback) |
| **UI** | Streamlit 1.39+ |
| **PDF Export** | ReportLab 4.2+ |
| **Configuration** | YAML, python-dotenv |
| **Tracing** | LangSmith (optional) |

## 📊 Model Configuration

Edit `config/mcp.yaml` to customize:
- Primary and fallback model choices
- Token limits and temperature per agent
- Per-agent model overrides

**Current Setup** (cost-optimized):
- **Primary**: Claude 3.5 Sonnet (~40% cheaper than Opus)
- **Fallback**: GPT-4o for reliability
- **Review Agent**: Lower temperature (0.2) for stricter critique
- **Intent Detection**: Minimal tokens (200) for fast classification

## 🤝 Example Prompts

Try these to see the pipeline in action:

- "Write a friendly intro to Sarah about partnering on warehouse robotics. Mention our pilot results and ask for a 30-min call next week."
- "Send an apology email to our client for the project delay, explain the reasons professionally and offer a revised timeline."
- "Write a formal proposal for a consulting engagement focusing on AI implementation."

## 📦 File Structure

```
email_assistant/
├── config/
│   └── mcp.yaml              # Model routing configuration
├── src/
│   ├── agents/               # 7 specialized agents
│   ├── workflow/             # LangGraph pipeline
│   ├── integrations/         # Anthropic & OpenAI clients
│   ├── memory/               # Profile persistence
│   ├── exporters/            # PDF export
│   └── ui/
│       └── streamlit_app.py  # Main UI
├── data/                      # Tone samples for few-shot learning
├── requirements.txt           # Dependencies
├── Dockerfile                 # Container configuration
└── .streamlit/
    └── config.toml           # Streamlit settings
```

## 🔒 Environment Variables

| Variable | Description | Source |
|----------|-----------|--------|
| `ANTHROPIC_API_KEY` | Anthropic API credential | [console.anthropic.com](https://console.anthropic.com) |
| `OPENAI_API_KEY` | OpenAI API credential | [platform.openai.com](https://platform.openai.com) |
| `LANGSMITH_API_KEY` | (Optional) LangSmith tracing | [smith.langchain.com](https://smith.langchain.com) |

## 🧪 Testing

```bash
pytest tests/
```

## 📈 Performance

- **Median latency**: ~8-12 seconds per email (end-to-end)
- **Fallback rate**: <2% with healthy API keys
- **Concurrency**: Handles 10+ simultaneous users

## 🐛 Troubleshooting

### "AuthenticationError: invalid x-api-key"
→ Check your API keys in Space secrets or .env file

### "Pipeline failed: Both primary and fallback models failed"
→ Verify API keys are valid and have sufficient quota

### "ModuleNotFoundError"
→ Run `pip install -r requirements.txt` again

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Credits

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) for the agentic orchestration
- [Claude](https://anthropic.com) for high-quality generation
- [Streamlit](https://streamlit.io) for rapid UI development

---

**Have questions?** Open an issue or reach out on [GitHub](https://github.com/ajaymd/email_assistant).

**Want to contribute?** Pull requests welcome! 🚀

