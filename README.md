# Resume Optimizer

An AI-powered resume optimizer built with FastAPI + Claude (Anthropic API).

Paste a rough resume and a job description → get a match score, keyword gap analysis, and a fully rewritten ATS-friendly resume. **Never fabricates details** — only rewrites what you wrote.

## Features

- Match scoring (overall, skills, experience)
- Keyword gap analysis with color-coded tags
- Full resume rewrite with stronger action verbs and ATS-friendly formatting
- PDF upload or text paste
- Download rewritten resume as .txt

---

## Local Development

```bash
# 1. Clone and enter the project
git clone https://github.com/YOUR_USERNAME/resume-analyzer
cd resume-analyzer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...   # Mac/Linux
set ANTHROPIC_API_KEY=sk-ant-...      # Windows

# 4. Run
uvicorn server:app --reload

# 5. Open http://localhost:8000
```

---

## Deploy to Render (free)

1. Push this repo to GitHub
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo
4. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
   - **Environment variable:** `ANTHROPIC_API_KEY` = your key
5. Click Deploy

Your app will be live at `https://your-app-name.onrender.com`

---

## Project Structure

```
resume-analyzer/
├── server.py          # FastAPI backend — proxies Anthropic API calls
├── requirements.txt
├── Procfile           # For Render deployment
├── README.md
└── static/
    └── index.html     # Full frontend (single file)
```

---

## Tech Stack

- **Backend:** Python, FastAPI, Anthropic SDK
- **Frontend:** Vanilla HTML/CSS/JS (no build step needed)
- **AI:** Claude claude-sonnet-4-20250514 via Anthropic API
- **Hosting:** Render (free tier)

---

## Resume Writing for Your Own Resume

Once deployed, add this to your resume under projects:

> **Resume Optimizer** — Built and deployed a full-stack AI web app using FastAPI and the Anthropic API that analyzes resume–job description match and rewrites resumes for ATS compatibility. Live at: https://your-app.onrender.com
