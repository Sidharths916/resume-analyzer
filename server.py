import os
import anthropic
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

app = FastAPI(title="Resume Optimizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*", "X-Api-Key"],
)

# Optional server-side fallback key (can be left unset)
SERVER_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


class MessageRequest(BaseModel):
    model: str
    max_tokens: int
    messages: list[Any]
    system: str | None = None


@app.post("/api/analyze")
async def analyze(req: MessageRequest, x_api_key: str | None = Header(default=None)):
    # Prefer the user-supplied key; fall back to server key if set
    api_key = x_api_key or SERVER_API_KEY

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="No API key provided. Please enter your Anthropic API key."
        )

    if not api_key.startswith("sk-ant-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid API key format. Anthropic keys start with sk-ant-"
        )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        kwargs = dict(
            model=req.model,
            max_tokens=req.max_tokens,
            messages=req.messages,
        )
        if req.system:
            kwargs["system"] = req.system

        response = client.messages.create(**kwargs)
        return {"content": response.content[0].text}

    except anthropic.AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid API key. Check it at console.anthropic.com.")
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve frontend — must be last so /api routes take priority
app.mount("/", StaticFiles(directory="static", html=True), name="static")
