# Jobsy — AI Resume Optimizer

> Turn a rough resume into an ATS-ready one. Free, no sign-up required.

**Live at:** [jobsy-g0xw.onrender.com](https://jobsy-g0xw.onrender.com)

---

## What it does

Jobsy runs your resume through a 4-stage AI pipeline modelled on how real recruiters and ATS systems evaluate candidates:

**Stage 1 — Senior recruiter scan**
Match score out of 100, top 10 missing keywords with placement suggestions, 5 red flags a hiring manager spots in the first 10 seconds, section-by-section scores (Summary, Experience, Skills, Education), and the single most important ATS change you can make right now.

**Stage 2 — Google XYZ rewrite**
Every bullet rewritten using the formula: *Accomplished [X] as measured by [Y] by doing [Z].* Missing keywords woven in naturally. Every vague phrase made specific. Summary rewritten as a 3-sentence pitch. Skills updated to match the JD. Nothing fabricated — only rewrites what you wrote.

**Stage 3 — ATS simulation + 7-second scan**
New match score after rewrite. Formatting issues flagged. Sections that would get skipped identified. Repetitive bullets called out. First-2-words rewrites provided for bullets that don't stop the scroll.

**Stage 4 — Mock interview** *(optional)*
7 questions: opening, 3 technical, 2 behavioural (STAR), 1 curveball. Each answer scored out of 10 with a rewritten 9/10 version. Final interview score and top 3 things to practice.

---

## Other tools

| Tool | What it does |
|---|---|
| Cover Letter | Tailored, tone-selectable, non-generic. Sounds like you wrote it. |
| LinkedIn | Rewrites headline, about section, and featured skills for your target role |
| Job Match | Live job search via Adzuna API ranked by resume keyword match |
| Skill Gap | Prioritised gaps with specific free learning resources |

---

## Tiers

| | Free | Pro |
|---|---|---|
| Model | Google Gemini 2.0 Flash | Anthropic Claude Sonnet |
| Cost to user | Nothing | ~$0.02/analysis (own API key) |
| Sign-up | No | No |
| Daily limit | 200 analyses/day | Unlimited |

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla HTML/CSS/JS — Instrument Serif, Inter, cinematic dark UI |
| Backend | Python, FastAPI, uvicorn |
| Free AI | Google Gemini 2.0 Flash (server-side key, rate-limited) |
| Pro AI | Anthropic Claude Sonnet (user's own key, never stored) |
| Hosting | Render free tier |
| Version control | GitHub |

---

## Security

- No database — no user data stored anywhere
- API keys never logged or persisted — Claude keys live only in the user's browser session
- Gemini key stored as Render environment variable, never in source code
- HTTPS enforced by Render
- 200 requests/day cap on free tier to prevent abuse

---

*Built by [Shanhe96](https://ko-fi.com/shanhe96)*
