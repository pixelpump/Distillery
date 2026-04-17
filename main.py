import asyncio
import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".local.env", override=True)

from reader import fetch_article
from summarize import stream_summary
import summarize as summarize_module
from tts import generate_audio, hash_url, is_cached

app = FastAPI(title="Distillery")

app.mount("/static", StaticFiles(directory="static"), name="static")


class FetchRequest(BaseModel):
    url: str


class SummarizeRequest(BaseModel):
    text: str


class TTSRequest(BaseModel):
    text: str
    url_hash: str


class ModelRequest(BaseModel):
    model: str


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/models")
async def list_models():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not set.")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch models from OpenRouter.")
    data = resp.json()
    models = sorted(
        [{"id": m["id"], "name": m.get("name", m["id"])} for m in data.get("data", [])],
        key=lambda m: m["name"].lower(),
    )
    return {"models": models, "current": summarize_module.OPENROUTER_MODEL}


@app.post("/settings/model")
async def set_model(req: ModelRequest):
    if not req.model or not req.model.strip():
        raise HTTPException(status_code=400, detail="Model ID is required.")
    summarize_module.OPENROUTER_MODEL = req.model.strip()
    return {"model": summarize_module.OPENROUTER_MODEL}


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
async def summarize(req: SummarizeRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Article text is required.")

    def event_stream():
        try:
            for chunk in stream_summary(req.text):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            yield f"data: [ERROR] {e}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/tts")
async def tts(req: TTSRequest):
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is required.")

    url_hash = req.url_hash or hash_url(req.text[:200])

    try:
        audio_path = await asyncio.get_event_loop().run_in_executor(
            None, generate_audio, req.text, url_hash
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {e}")

    return FileResponse(audio_path, media_type="audio/mpeg", filename=f"{url_hash}.mp3")
