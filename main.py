import asyncio
import os
import io
import zipfile
import time
from collections import defaultdict
from functools import wraps
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

load_dotenv()
load_dotenv(".local.env", override=True)

from reader import fetch_article
from tts import generate_audio, hash_url, is_cached

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Distillery")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Simple in-memory rate limiting for TTS (per IP)
# Stores: ip -> list of timestamps
tts_request_log = defaultdict(list)
TTS_RATE_LIMIT = 5  # requests
TTS_RATE_WINDOW = 3600  # 1 hour in seconds


class FetchRequest(BaseModel):
    url: str


class SummarizeRequest(BaseModel):
    text: str


class TTSRequest(BaseModel):
    text: str
    url_hash: str


class ModelRequest(BaseModel):
    model: str


class ApiKeyRequest(BaseModel):
    api_key: str


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/extension-download")
async def extension_download():
    ext_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extension")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(ext_dir):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, ext_dir)
                zf.write(filepath, arcname)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip", headers={
        "Content-Disposition": "attachment; filename=distillery-extension.zip"
    })


@app.get("/models")
async def list_models():
    """
    Fetch models from OpenRouter using a demo/fallback approach.
    Client will provide their own API key for actual usage.
    """
    # Use environment key if available (for server admin), otherwise return popular models
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if api_key:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
        if resp.status_code == 200:
            data = resp.json()
            models = sorted(
                [{"id": m["id"], "name": m.get("name", m["id"])} for m in data.get("data", [])],
                key=lambda m: m["name"].lower(),
            )
            return {"models": models, "source": "openrouter"}
    
    # Fallback: return popular free/cheap models
    fallback_models = [
        {"id": "google/gemini-2.0-flash-001", "name": "Google Gemini 2.0 Flash (Free)"},
        {"id": "meta-llama/llama-3.1-8b-instruct", "name": "Meta Llama 3.1 8B (Cheap)"},
        {"id": "mistralai/mistral-7b-instruct", "name": "Mistral 7B Instruct (Cheap)"},
    ]
    return {"models": fallback_models, "source": "fallback"}


@app.post("/settings/model")
async def set_model(req: ModelRequest):
    """
    DEPRECATED: Model selection now happens client-side.
    This endpoint kept for backward compatibility but does nothing server-side.
    """
    return {"message": "Model selection is now client-side. Set it in the browser.", "model": req.model}


@app.get("/settings/api-key")
async def get_api_key():
    """
    DEPRECATED: API keys are now stored client-side only.
    Returns empty to indicate no server-side key storage.
    """
    return {"api_key": "", "has_key": False, "message": "API keys are now stored client-side only"}


@app.post("/settings/api-key")
async def set_api_key(req: ApiKeyRequest):
    """
    DEPRECATED: API keys are now stored client-side only.
    Client should store in localStorage and use directly with OpenRouter.
    """
    raise HTTPException(
        status_code=410, 
        detail="Server-side API key storage is deprecated. Store your key in browser localStorage and call OpenRouter directly from the client."
    )


@app.post("/settings/refresh-api-key")
async def refresh_api_key():
    """DEPRECATED: No longer needed with client-side API calls."""
    return {"success": True, "message": "Client-side API usage - no server refresh needed"}


@app.post("/fetch")
async def fetch(req: FetchRequest):
    loop = asyncio.get_event_loop()
    try:
        article = await loop.run_in_executor(None, fetch_article, req.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching article: {e}")

    return {
        "title": article.title,
        "author": article.author,
        "date": article.date,
        "text": article.text,
        "word_count": article.word_count,
    }


@app.post("/summarize")
@limiter.limit("10/minute")
async def summarize(req: SummarizeRequest, request: Request):
    """
    DEPRECATED: Summarization now happens client-side.
    This endpoint is rate-limited and returns an error directing users to the new flow.
    """
    raise HTTPException(
        status_code=410,
        detail="Server-side summarization is deprecated. The client now calls OpenRouter directly using your API key. Please update your app or use the web interface."
    )


def check_tts_rate_limit(client_ip: str) -> bool:
    """Check if client has exceeded TTS rate limit."""
    now = time.time()
    # Clean old entries outside the window
    tts_request_log[client_ip] = [
        ts for ts in tts_request_log[client_ip] 
        if now - ts < TTS_RATE_WINDOW
    ]
    # Check limit
    if len(tts_request_log[client_ip]) >= TTS_RATE_LIMIT:
        return False
    # Log this request
    tts_request_log[client_ip].append(now)
    return True


@app.post("/tts")
@limiter.limit("5/minute")
async def tts(req: TTSRequest, request: Request):
    """
    Generate TTS audio with rate limiting.
    Limited to 5 requests per minute per IP, max 5 articles per hour.
    """
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")
    
    # Additional per-IP rate limiting
    client_ip = get_remote_address(request)
    if not check_tts_rate_limit(client_ip):
        raise HTTPException(
            status_code=429, 
            detail=f"TTS rate limit exceeded. Maximum {TTS_RATE_LIMIT} articles per hour. Please try again later."
        )

    url_hash = req.url_hash or hash_url(req.text[:200])

    try:
        audio_path = await asyncio.get_event_loop().run_in_executor(
            None, generate_audio, req.text, url_hash
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {e}")

    return FileResponse(audio_path, media_type="audio/mpeg", filename=f"{url_hash}.mp3")
