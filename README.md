# Distillery 🜋

A local, distraction-free AI article reader with on-device text-to-speech.

## Quick Start (macOS)

### 1. Download

Go to **[Releases](https://github.com/yourusername/distillery/releases)** and download:
- **macOS:** `Distillery-1.0.0-macOS.zip`

### 2. Install

```bash
# Unzip and move to Applications
unzip ~/Downloads/Distillery-1.0.0-macOS.zip
mv ~/Downloads/Distillery.app /Applications/
```

### 3. Run

Double-click **Distillery** in your Applications folder.

You'll see the 🜋 (alembic) icon appear in your menu bar. The server starts automatically.

### 4. Open Distillery

Click the 🜋 menu bar icon → **"Open Distillery"**

Or visit: http://localhost:8000

### 5. Install Chrome Extension

1. Open Chrome → `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right)
3. Click **"Load unpacked"**
4. Select the `extension/` folder from this repo
5. The extension will auto-detect your running Distillery server

---

## Using Distillery

### From Chrome
- Right-click any link → **"Send to Distillery"**
- Or click the extension icon on any page

### In Distillery
- Paste any URL to extract the article
- Click **"Summarize"** for AI bullet points (requires [OpenRouter](https://openrouter.ai) API key)
- Click **"Listen"** for text-to-speech (downloads ~300MB model on first use)

---

## Features

- **Reader view** — clean extraction from any source
- **Paywall bypass** — automatic fallback sources (12ft.io, archive.ph, etc.)
- **AI summaries** — streamed via OpenRouter (client-side, your API key)
- **On-device TTS** — Kokoro voice synthesis, audio cached locally
- **Chrome extension** — right-click to send articles
- **Dark mode** — toggle in settings

---

## Building from Source

### Requirements
- Python 3.10+
- macOS (for menu bar app)

### Build Steps

```bash
# 1. Clone and setup
git clone https://github.com/yourusername/distillery.git
cd distillery
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Build the menu bar app
./build/build_menu_bar.sh

# 3. Install locally
cp -r build/dist/Distillery.app /Applications/
open /Applications/Distillery.app
```

### Development Mode

```bash
source .venv/bin/activate
uvicorn main:app --reload --port 8000
# Open http://localhost:8000
```

---

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface |
| `/fetch` | POST | Extract article from URL |
| `/tts` | POST | Generate speech (returns MP3) |
| `/extension-download` | GET | Download Chrome extension ZIP |

---

## How It Works

- **Stateless server** — no database, no user accounts
- **API keys in browser** — stored in `localStorage`, never sent to server
- **Client-side AI** — summaries generated directly in browser via OpenRouter
- **Cached audio** — TTS results saved by URL hash for instant replay

---

## Support

Issues: [github.com/yourusername/distillery/issues](https://github.com/yourusername/distillery/issues)
