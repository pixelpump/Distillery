# Distillery 🜋

**Distillery transforms cluttered web articles into clean, focused reading experiences — then reads them to you.**

No ads. No popups. No paywalls. No cloud subscriptions. Just pure content, distilled.

Distillery is a local, open-source article reader that strips away the noise of the modern web. Paste any URL and get instant, beautifully formatted text. Hit a paywall? Distillery automatically tries multiple fallback sources to extract the content. Want the TL;DR? AI summaries stream directly in your browser using your own API key — we never see it. Prefer to listen? Our on-device text-to-speech generates natural-sounding audio using Kokoro, completely offline after the initial model download. Need to power through a long read? The built-in speed reader presents words one at a time in RSVP format, letting you read at 400+ WPM.

Everything happens on your machine. No tracking. No accounts. No monthly fees. Your reading history stays yours.

---

## Features

### Article Extraction & Reading

- **Clean reader view** — extracts article text from any URL, stripping ads, navigation, popups, and clutter using Trafilatura
- **Multi-source fallback** — if the original URL is paywalled or blocked, Distillery automatically cycles through fallback extractors:
  - 12ft.io (paywall bypass)
  - jina.ai (text extraction API)
  - Bing cache
  - archive.ph / archive.today
  - Wayback Machine
- **Beautiful typography** — articles rendered in EB Garamond with comfortable line-height and max-width for readability
- **Adjustable font size** — increase or decrease article text size from the toolbar

### AI Summarization

- **Streamed bullet-point summaries** — powered by OpenRouter (supports Google Gemini, Llama, Mistral, and hundreds of other models)
- **Client-side API calls** — your OpenRouter API key is stored in browser `localStorage` and never touches the server
- **Model selection** — choose any model available on OpenRouter from the settings panel

### Text-to-Speech (On-Device)

- **Kokoro TTS engine** — high-quality neural voice synthesis using the Kokoro-82M model from HuggingFace
- **Fully offline** — after the one-time ~313 MB model download, TTS works without any internet connection
- **Audio player** — built-in player with play/pause, seek bar, time display, and playback speed controls (1×, 1.5×, 2×)
- **Audio caching** — generated audio is cached locally by URL hash for instant replay on subsequent visits
- **Progress streaming** — SSE-based real-time progress updates during audio generation

### Speed Reader (RSVP)

- **Rapid Serial Visual Presentation** — displays words one at a time for 400+ WPM reading speeds
- **Adjustable WPM** — control reading speed to match your comfort level
- **Play/pause controls** — start, stop, and resume at any point

### Chrome Extension

- **Context menu integration** — right-click any link → "Send to Distillery"
- **Auto-detection** — extension automatically finds your running Distillery server on localhost (scans ports 8000, 8001, 8080, 3000)
- **Reading queue** — articles sent from Chrome are queued and opened in the Distillery interface
- **Manifest V3** — modern Chrome extension architecture

### Interface & Settings

- **Dark mode** — full dark theme toggle, persisted across sessions
- **Settings panel** — configure OpenRouter API key, select AI model, and manage TTS model downloads
- **Onboarding overlay** — guided first-use walkthrough
- **Responsive layout** — works on various screen sizes

### Architecture & Privacy

- **Stateless server** — no database, no user accounts, no analytics
- **Local-only** — everything runs on `localhost:8000`
- **No tracking** — zero telemetry, no external requests except those you explicitly trigger (article fetching, OpenRouter API)
- **Rate limiting** — built-in protection (60 TTS requests/minute, 100 articles/hour per IP) via slowapi
- **CORS enabled** — allows communication between the Chrome extension and the local server
- **macOS menu bar app** — native menu bar icon (🜋) with server start/stop, status display, and log viewer

---

## Installation

### Option A: Pre-Built App (macOS)

1. Go to **[Releases](https://github.com/yourusername/distillery/releases)** and download `Distillery-1.0.0-macOS.zip`

2. Unzip and move to Applications:
   ```bash
   unzip ~/Downloads/Distillery-1.0.0-macOS.zip
   mv ~/Downloads/Distillery.app /Applications/
   ```

3. Double-click **Distillery** in your Applications folder. The 🜋 icon will appear in your menu bar and the server starts automatically.

4. Click the 🜋 menu bar icon → **"Open Distillery"**, or visit http://localhost:8000

### Option B: Run from Source (Development)

#### Prerequisites

- **Python 3.10+** (check with `python3 --version`)
- **pip** (comes with Python)
- **macOS** (for the menu bar app; the server itself runs on any OS)
- **Git**

#### Step-by-step

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/distillery.git
cd distillery

# 2. Create a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Run the development server
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000 in your browser. That's it — Distillery is running.

#### Running as a menu bar app (macOS)

```bash
source .venv/bin/activate
python menu_bar.py
```

This launches the server in the background with a native macOS menu bar icon for start/stop control and quick access.

### Option C: Build the Tauri Desktop App

The project includes a [Tauri v2](https://tauri.app) wrapper that bundles the Python backend as a sidecar binary for a native desktop experience.

#### Prerequisites

- Everything from Option B
- **Rust** (install via [rustup.rs](https://rustup.rs))
- **PyInstaller** (`pip install pyinstaller`)
- **Node.js** (for Tauri CLI, if using npm-based tooling)
- **Tauri CLI** (`cargo install tauri-cli`)

#### Build Steps

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Build the Python backend into a standalone binary
python build_backend.py

# This creates: src-tauri/binaries/distillery-server-<target-triple>

# 3. Build the Tauri app
cd src-tauri
cargo tauri build
```

The built `.app` bundle will be in `src-tauri/target/release/bundle/`.

---

## Installing the Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in the top-right corner)
3. Click **"Load unpacked"**
4. Select the `extension/` folder from this repository
5. The extension icon will appear in your Chrome toolbar

The extension auto-detects your running Distillery server. Right-click any link on the web and choose **"Send to Distillery"** to extract and read the article.

Alternatively, download the extension as a ZIP from the running server at http://localhost:8000/extension-download.

---

## Usage

### From Chrome
- Right-click any link → **"Send to Distillery"**
- Or click the extension icon on any page to send the current page

### In the Web Interface
1. **Paste a URL** into the input bar and press Enter
2. **Read** — the cleaned article text appears immediately
3. **Summarize** — click the summarize button for AI-generated bullet points (requires OpenRouter API key configured in Settings)
4. **Listen** — click the listen button to generate audio (first use requires a one-time ~313 MB model download via Settings)
5. **Speed Read** — click the speed read button for RSVP-style rapid reading

### Settings (⚙️ gear icon)
- **OpenRouter API Key** — paste your key from [openrouter.ai/keys](https://openrouter.ai/keys). Stored in your browser only.
- **AI Model** — select which model to use for summarization
- **TTS Model** — download or check status of the Kokoro voice model
- **Dark Mode** — toggle light/dark theme

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve the web interface |
| `/health` | GET | Health check — returns `{"status": "ok", "version": "1.0.0"}` |
| `/fetch` | POST | Extract full article text from a URL |
| `/queue` | POST | Fetch article metadata only (title, author, date, word count) |
| `/tts` | POST | Generate TTS audio (returns MP3). Requires model to be installed. |
| `/tts/model-status` | GET | Check if Kokoro TTS model is downloaded |
| `/tts/download-model` | POST | Download Kokoro model (SSE progress stream) |
| `/tts/progress/{url_hash}` | GET | SSE stream of TTS generation progress |
| `/models` | GET | List available OpenRouter models |
| `/extension-download` | GET | Download Chrome extension as ZIP |
| `/settings/model` | POST | *(Deprecated)* Model selection is now client-side |
| `/settings/api-key` | GET/POST | *(Deprecated)* API key storage is now client-side |

### Example: Fetch an article

```bash
curl -X POST http://localhost:8000/fetch \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/article"}'
```

Response:
```json
{
  "title": "Article Title",
  "author": "Author Name",
  "date": "2024-01-15",
  "text": "Full extracted article text...",
  "word_count": 1423
}
```

---

## Project Structure

```
distillery/
├── main.py              # FastAPI server — all endpoints
├── reader.py            # Article extraction with multi-source fallback
├── tts.py               # Kokoro TTS generation and audio caching
├── summarize.py         # OpenRouter summarization (legacy server-side module)
├── menu_bar.py          # macOS menu bar app using rumps
├── sidecar_main.py      # Entry point for Tauri sidecar binary
├── build_backend.py     # PyInstaller build script for sidecar
├── requirements.txt     # Python dependencies
├── static/
│   └── index.html       # Single-page web interface (HTML/CSS/JS)
├── extension/
│   ├── manifest.json    # Chrome extension manifest (V3)
│   ├── background.js    # Service worker — context menus & server detection
│   └── icons/           # Extension icons
├── src-tauri/           # Tauri v2 desktop wrapper
│   ├── Cargo.toml       # Rust dependencies
│   ├── tauri.conf.json  # Tauri configuration
│   ├── frontend/        # Tauri frontend entry
│   └── binaries/        # Sidecar binary output (generated by build_backend.py)
└── audio_cache/         # Cached TTS audio files (generated at runtime)
```

---

## Dependencies

### Python (requirements.txt)

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework / API server |
| `uvicorn` | ASGI server |
| `trafilatura` | Article text extraction from HTML |
| `httpx` | HTTP client for fetching web pages |
| `kokoro` | On-device neural TTS engine |
| `soundfile` | Audio file writing (MP3 output) |
| `numpy` | Audio array manipulation |
| `python-dotenv` | Environment variable loading |
| `python-multipart` | Form data parsing |
| `slowapi` | Rate limiting middleware |
| `rumps` | macOS menu bar app framework |
| `openai` | OpenRouter API client (OpenAI-compatible) |

### System (for Tauri build only)

| Dependency | Install |
|------------|---------|
| Rust | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| PyInstaller | `pip install pyinstaller` |
| Tauri CLI | `cargo install tauri-cli` |

---

## How It Works

1. **Article extraction** — Fetches the URL, runs Trafilatura to strip HTML down to readable text. If that fails (paywall, bot detection), cascades through 7+ fallback sources until content is found.
2. **Summarization** — The browser calls OpenRouter directly using your API key. The server is never involved — your key stays in `localStorage`.
3. **Text-to-speech** — The server splits article text into paragraphs, feeds each through Kokoro-82M, concatenates the audio chunks, and returns a single MP3. Results are cached by URL hash.
4. **Chrome extension** — Adds a context menu item. On click, it POSTs the URL to `/queue`, then opens a Distillery tab with the article loaded.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "TTS model not installed" | Open Settings (⚙️) and click "Download Model" (~313 MB one-time download) |
| Extension can't connect | Make sure the server is running (`uvicorn main:app --port 8000`) |
| Summarize does nothing | Check that your OpenRouter API key is set in Settings and has credit |
| Port 8000 already in use | Kill the existing process (`lsof -ti:8000 \| xargs kill`) or change port |
| Extraction returns short text | Some sites aggressively block scrapers. Distillery tries 7+ fallbacks but some may still fail. |

---

## License

Open-source. See repository for license details.

## Support

Issues: [github.com/yourusername/distillery/issues](https://github.com/yourusername/distillery/issues)
