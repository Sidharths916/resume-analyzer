import os
import re
import time
import httpx
import anthropic
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import Any
from datetime import date
from collections import defaultdict

app = FastAPI(title="Jobsy API", docs_url=None, redoc_url=None)  # disable public docs in prod

# ── CORS ────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "X-Api-Key", "X-Tier"],
)

# ── SECURITY HEADERS middleware ──────────────────────────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

# ── RATE LIMITING ─────────────────────────────────────────────────────────────
# Per-IP: max 30 requests per 15 minutes across all endpoints
_rate_store: dict[str, list[float]] = defaultdict(list)
RATE_WINDOW  = 15 * 60   # 15 minutes in seconds
RATE_MAX     = 30        # max requests per window per IP

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def is_rate_limited(ip: str) -> bool:
    now = time.time()
    window_start = now - RATE_WINDOW
    # Keep only timestamps within the current window
    _rate_store[ip] = [t for t in _rate_store[ip] if t > window_start]
    if len(_rate_store[ip]) >= RATE_MAX:
        return True
    _rate_store[ip].append(now)
    return False

# ── DAILY CAP (free tier) ────────────────────────────────────────────────────
SERVER_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
DAILY_CAP = 200
_usage: dict[str, int] = defaultdict(int)

def check_and_increment() -> bool:
    today = str(date.today())
    if _usage[today] >= DAILY_CAP:
        return False
    _usage[today] += 1
    return True

def get_usage_today() -> int:
    return _usage[str(date.today())]

# ── INPUT VALIDATION ─────────────────────────────────────────────────────────
MAX_PROMPT_CHARS = 40_000   # ~10k tokens — enough for any resume+JD combo
MAX_TOKENS_CAP   = 6_000    # never let client request more than this

ALLOWED_MODELS = {
    "gemini-2.0-flash",
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
}

def sanitize_text(text: str) -> str:
    """Strip null bytes and control characters that could cause issues."""
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

class MessageRequest(BaseModel):
    model: str
    max_tokens: int
    messages: list[Any]
    system: str | None = None

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        # Accept any gemini or claude model — flexible for future
        if not (v.startswith("gemini-") or v.startswith("claude-")):
            raise ValueError("Invalid model identifier")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        if v < 1 or v > MAX_TOKENS_CAP:
            raise ValueError(f"max_tokens must be between 1 and {MAX_TOKENS_CAP}")
        return v

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: list) -> list:
        if not v or len(v) > 50:
            raise ValueError("messages must have 1–50 items")
        total_chars = 0
        for m in v:
            if not isinstance(m, dict):
                raise ValueError("Each message must be an object")
            if m.get("role") not in ("user", "assistant"):
                raise ValueError("Message role must be 'user' or 'assistant'")
            content = m.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        total_chars += len(block.get("text", ""))
            if total_chars > MAX_PROMPT_CHARS:
                raise ValueError(f"Total prompt exceeds {MAX_PROMPT_CHARS} character limit")
        return v

    @field_validator("system")
    @classmethod
    def validate_system(cls, v: str | None) -> str | None:
        if v and len(v) > 8_000:
            raise ValueError("System prompt too long")
        return v

# ── TEXT EXTRACTION ──────────────────────────────────────────────────────────
def extract_text(messages: list[Any]) -> str:
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, str):
            parts.append(f"[{role}]: {sanitize_text(content)}")
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(f"[{role}]: {sanitize_text(block.get('text', ''))}")
                    elif block.get("type") == "document":
                        parts.append(f"[{role}]: [PDF resume uploaded]")
    return "\n\n".join(parts)

# ── GEMINI (free tier) ───────────────────────────────────────────────────────
async def call_gemini(req: MessageRequest) -> str:
    if not SERVER_GEMINI_KEY:
        raise HTTPException(503, "Free tier temporarily unavailable. Please use Pro mode.")
    if not check_and_increment():
        raise HTTPException(429, f"Free tier daily limit reached ({DAILY_CAP}/day). Try tomorrow or switch to Pro.")

    prompt = (f"{sanitize_text(req.system)}\n\n" if req.system else "") + extract_text(req.messages)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={SERVER_GEMINI_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": req.max_tokens, "temperature": 0.3},
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload)

    if resp.status_code != 200:
        err = resp.json().get("error", {})
        raise HTTPException(502, f"Free tier error: {err.get('message', 'Unknown error')}")
    try:
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise HTTPException(502, "Unexpected response from free tier.")

# ── CLAUDE (pro tier) ────────────────────────────────────────────────────────
async def call_claude(req: MessageRequest, api_key: str) -> str:
    if not api_key.startswith("sk-ant-"):
        raise HTTPException(400, "Invalid Anthropic key — must start with sk-ant-")
    try:
        client = anthropic.Anthropic(api_key=api_key)
        kwargs: dict[str, Any] = dict(model=req.model, max_tokens=req.max_tokens, messages=req.messages)
        if req.system:
            kwargs["system"] = req.system
        response = client.messages.create(**kwargs)
        return response.content[0].text
    except anthropic.AuthenticationError:
        raise HTTPException(401, "Invalid Anthropic key. Check console.anthropic.com.")
    except anthropic.RateLimitError:
        raise HTTPException(429, "Anthropic rate limit hit. Wait a moment and try again.")
    except anthropic.APIError as e:
        raise HTTPException(502, f"Claude API error: {str(e)[:200]}")

# ── MAIN ENDPOINT ─────────────────────────────────────────────────────────────
@app.post("/api/analyze")
async def analyze(
    request: Request,
    req: MessageRequest,
    x_api_key: str | None = Header(default=None),
    x_tier: str | None = Header(default="free"),
):
    # Rate limiting
    ip = get_client_ip(request)
    if is_rate_limited(ip):
        raise HTTPException(429, "Too many requests. Please slow down — max 30 per 15 minutes.")

    tier = (x_tier or "free").strip().lower()
    if tier not in ("free", "pro"):
        raise HTTPException(400, "Invalid tier. Must be 'free' or 'pro'.")

    if tier == "pro":
        if not x_api_key:
            raise HTTPException(401, "Pro mode requires your Anthropic API key in X-Api-Key header.")
        # Sanitize key — no injection possible but trim whitespace
        x_api_key = x_api_key.strip()
        result = await call_claude(req, x_api_key)
    else:
        req.model = "gemini-2.0-flash"
        result = await call_gemini(req)

    return {"content": result}

# ── HEALTH ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "free_used_today": get_usage_today(),
        "daily_cap": DAILY_CAP,
    }

# ── STATIC FILES ──────────────────────────────────────────────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")
