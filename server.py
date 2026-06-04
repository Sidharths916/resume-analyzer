import os
import anthropic
import httpx
import json
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

app = FastAPI(title="Jobify API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*", "X-Api-Key", "X-Tier"],
)

SERVER_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")


class MessageRequest(BaseModel):
    model: str
    max_tokens: int
    messages: list[Any]
    system: str | None = None


def extract_text(messages: list[Any]) -> str:
    """Flatten messages into a single text prompt for Gemini."""
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, str):
            parts.append(f"[{role}]: {content}")
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        parts.append(f"[{role}]: {block['text']}")
                    elif block.get("type") == "document":
                        parts.append(f"[{role}]: [PDF document attached — analyze the resume content within it]")
    return "\n\n".join(parts)


async def call_gemini(req: MessageRequest) -> str:
    key = SERVER_GEMINI_KEY
    if not key:
        raise HTTPException(status_code=503, detail="Free tier temporarily unavailable. Please use Pro (Claude) mode.")

    prompt_text = extract_text(req.messages)
    system_part = f"{req.system}\n\n" if req.system else ""
    full_prompt = system_part + prompt_text

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "maxOutputTokens": req.max_tokens,
            "temperature": 0.3,
        }
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload)

    if resp.status_code != 200:
        detail = resp.json().get("error", {}).get("message", "Gemini API error")
        raise HTTPException(status_code=502, detail=f"Free tier error: {detail}")

    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise HTTPException(status_code=502, detail="Unexpected response from free tier.")


async def call_claude(req: MessageRequest, api_key: str) -> str:
    if not api_key.startswith("sk-ant-"):
        raise HTTPException(status_code=400, detail="Invalid Anthropic key. Keys start with sk-ant-")
    try:
        client = anthropic.Anthropic(api_key=api_key)
        kwargs = dict(model=req.model, max_tokens=req.max_tokens, messages=req.messages)
        if req.system:
            kwargs["system"] = req.system
        response = client.messages.create(**kwargs)
        return response.content[0].text
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid Anthropic key. Check console.anthropic.com.")
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/analyze")
async def analyze(
    req: MessageRequest,
    x_api_key: str | None = Header(default=None),
    x_tier: str | None = Header(default="free"),
):
    tier = (x_tier or "free").lower()

    if tier == "pro":
        if not x_api_key:
            raise HTTPException(status_code=401, detail="Pro mode requires your Anthropic API key.")
        result = await call_claude(req, x_api_key)
    else:
        # Free tier — use server Gemini key, swap model name to gemini
        req.model = "gemini-2.0-flash"
        result = await call_gemini(req)

    return {"content": result}


@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
