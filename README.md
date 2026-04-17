# Distillery

A local, distraction-free AI article reader with on-device TTS.

## Features

- **Reader view** — clean article extraction via trafilatura
- **AI summary** — streamed 5-bullet summary via OpenRouter (Gemini Flash)
- **Text-to-speech** — full article audio via Kokoro, cached on disk

## Setup

### 1. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Kokoro note:** On first use, Kokoro will automatically download its model weights (~300 MB) from Hugging Face. An internet connection is required for this one-time download.

### 2. API key

Copy the example env file and add your [OpenRouter](https://openrouter.ai) API key:

```bash
cp .env.example .env
# then edit .env and set OPENROUTER_API_KEY=sk-or-...
```

### 3. Run the app

```bash
uvicorn main:app --reload --port 8000
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

## Project structure

```
distillery/
├── main.py           # FastAPI app + all endpoints
├── reader.py         # trafilatura extraction logic
├── summarize.py      # OpenRouter streaming summarization
├── tts.py            # Kokoro TTS logic + audio cache
├── audio_cache/      # cached MP3 files (gitignored)
├── static/
│   └── index.html    # entire frontend (vanilla JS)
├── .env.example      # env template
└── requirements.txt
```

## API Endpoints

| Method | Path | Body | Response |
|--------|------|------|----------|
| `POST` | `/fetch` | `{ url }` | `{ title, author, date, text, word_count }` |
| `POST` | `/summarize` | `{ text }` | `text/event-stream` SSE |
| `POST` | `/tts` | `{ text, url_hash }` | `audio/mpeg` |

## Notes

- Audio is cached by `url_hash` (SHA-256 of URL, first 16 hex chars). Repeat TTS requests are instant.
- The AI model can be swapped by changing `OPENROUTER_MODEL` at the top of `summarize.py`.
- No database, no auth — fully stateless.
