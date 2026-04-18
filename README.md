# Distillery

A local, distraction-free AI article reader with on-device TTS.

## Features

- **Reader view** — clean article extraction via multiple fallback sources (trafilatura, jina.ai, 12ft.io, archive.ph, Wayback Machine)
- **Paywall bypass** — automatically tries multiple sources to extract content from paywalled articles
- **AI summary** — streamed bullet-point summaries via OpenRouter (client-side, bring your own API key)
- **Text-to-speech** — full article audio via Kokoro, cached on disk
- **Chrome extension** — right-click any link to send directly to Distillery
- **Rate limiting** — TTS limited to 5 requests/minute and 5 articles/hour per IP
- **Dark mode** — toggle between light and dark themes

## Setup

### 1. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Kokoro note:** On first use, Kokoro will automatically download its model weights (~300 MB) from Hugging Face. An internet connection is required for this one-time download.

### 2. Run the app

```bash
uvicorn main:app --reload --port 8000
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

### 3. (Optional) Install Chrome extension

Download the extension as a ZIP and load it in Chrome's developer mode:

```bash
curl -O http://localhost:8000/extension-download
```

Or navigate to `chrome://extensions/`, enable Developer mode, click "Load unpacked", and select the `extension/` folder.

### 4. API Key (client-side)

Enter your [OpenRouter](https://openrouter.ai) API key directly in the web interface. Keys are stored in browser `localStorage` — never sent to the server.

## Project structure

```
distillery/
├── main.py              # FastAPI app + all endpoints
├── reader.py            # Multi-source article extraction
├── summarize.py         # OpenRouter streaming logic (client-side now)
├── tts.py               # Kokoro TTS logic + audio cache
├── audio_cache/         # cached MP3 files (gitignored)
├── static/
│   └── index.html       # entire frontend (vanilla JS)
├── extension/
│   ├── manifest.json    # Chrome extension manifest (v3)
│   ├── background.js    # Extension service worker
│   └── icons/           # Extension icons
├── .local.env           # local overrides (optional)
└── requirements.txt
```

## API Endpoints

| Method | Path | Body | Response | Notes |
|--------|------|------|----------|-------|
| `GET` | `/` | — | HTML | Serves the web interface |
| `GET` | `/extension-download` | — | `application/zip` | Download Chrome extension |
| `POST` | `/fetch` | `{ url }` | `{ title, author, date, text, word_count }` | Article extraction |
| `GET` | `/models` | — | `{ models, source }` | List available AI models |
| `POST` | `/tts` | `{ text, url_hash }` | `audio/mpeg` | Generate speech (rate-limited) |
| `POST` | `/summarize` | `{ text }` | — | **Deprecated** — client-side only now |
| `POST` | `/settings/api-key` | `{ api_key }` | — | **Deprecated** — keys stored client-side |

## Architecture Notes

- **Client-side API keys:** OpenRouter API keys are stored in browser `localStorage` and used directly from the frontend. The server never sees your key.
- **Client-side summarization:** AI summaries are generated directly in the browser using your API key, not proxied through the server.
- **Audio caching:** TTS audio is cached by `url_hash` (SHA-256 of URL, first 16 hex chars). Repeat requests are instant.
- **Rate limiting:** TTS endpoints use `slowapi` (5/min) plus additional per-IP limiting (5/hour).
- **Article extraction:** Uses a cascade of sources: direct fetch → 12ft.io → jina.ai → archive.ph → Wayback Machine → textise dot iitty dot iitty.
- **No database, no auth:** Fully stateless server. All user state is in the browser.
