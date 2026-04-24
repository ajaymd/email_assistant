# HuggingFace Spaces Deployment Guide

## Quick Start

### Step 1: Create a HuggingFace Space

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces)
2. Click **"Create new Space"**
3. Fill in the form:
   - **Space name**: `email-assistant` (or your choice)
   - **License**: MIT
   - **Space SDK**: Docker
   - **Visibility**: Public
4. Click **Create Space**

### Step 2: Add Secrets

The application needs API keys to function. In your Space repository (the GitHub-like interface):

1. Navigate to **Settings** → **Secrets and variables**
2. Add these secrets:
   - **ANTHROPIC_API_KEY**: Your Anthropic API key
   - **OPENAI_API_KEY**: Your OpenAI API key

Get your keys from:
- Anthropic: https://console.anthropic.com/account/keys
- OpenAI: https://platform.openai.com/account/api-keys

### Step 3: Deploy

Clone your HuggingFace Space and push this code:

```bash
# 1. Clone your newly created Space
git clone https://huggingface.co/spaces/YOUR_USERNAME/email-assistant
cd email-assistant

# 2. Copy all files from this repo to the space directory
cp -r /path/to/local/email_assistant/* .

# 3. Commit and push
git add .
git commit -m "Deploy: Email Assistant app"
git push
```

The Docker container will automatically build and deploy. You can monitor the build progress in the Space's "Build" tab.

## Docker Configuration

The `Dockerfile` is pre-configured to:
- Use Python 3.11-slim as the base image
- Install all dependencies from `requirements.txt`
- Expose port 8501 (Streamlit default)
- Run Streamlit in headless mode on `0.0.0.0:8501`

## File Structure for HuggingFace

```
your-space/
├── Dockerfile              ← Tells HF to use Docker
├── requirements.txt        ← Python dependencies
├── .streamlit/
│   └── config.toml         ← Streamlit configuration
├── src/                    ← Application code
├── config/
│   └── mcp.yaml           ← Model configuration
├── data/                   ← Tone samples
└── README.md              ← Space documentation
```

## Testing Before Deployment

Test locally first:

```bash
# Build and run the Docker image
docker build -t email-assistant .
docker run -p 8501:8501 \
  -e ANTHROPIC_API_KEY="your-key" \
  -e OPENAI_API_KEY="your-key" \
  email-assistant
```

Then visit: http://localhost:8501

## Troubleshooting

### Space won't start
- Check build logs in Space settings
- Ensure all dependencies are in `requirements.txt`
- Verify Dockerfile syntax

### API Key errors
- Go to Space Settings → Secrets and verify keys are set
- Test keys locally first with `.env` file
- Check API quotas and billing

### Streamlit crashes
- Check Space logs for full error messages
- Verify all imports in `src/ui/streamlit_app.py` are installed
- Test locally with `streamlit run src/ui/streamlit_app.py`

## Performance on HuggingFace

- **Startup time**: 30-60 seconds (first build is slowest)
- **Response time**: 8-15 seconds per email
- **Memory**: ~1-2GB required (HF provides 16GB)
- **Storage**: ~500MB for dependencies

## Important Notes

- ⚠️ Keep API keys **private** (use Secrets, not hardcoded)
- 📌 User profiles are stored in-memory per session
- 🔄 Profiles don't persist across Space restarts
- 🌍 Public spaces mean anyone can use your API quota!

For production, consider:
- Using a database for persistent profiles
- Rate limiting per IP/user
- Monitoring API usage
- Setting monthly budgets on API provider accounts

## Next Steps

- Customize the UX in `src/ui/streamlit_app.py`
- Adjust model selection in `config/mcp.yaml`
- Add your branding to Streamlit config in `.streamlit/config.toml`
- Monitor Space metrics from the HuggingFace dashboard

---

**Questions?** Check the main README.md for architecture details.

