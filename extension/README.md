# Distillery Browser Extension

Sends article links directly to your local Distillery instance for reading.

## Installation

### Chrome/Edge/Brave
1. Open `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select this `extension` folder

### Firefox
1. Open `about:debugging`
2. Click "This Firefox" → "Load Temporary Add-on"
3. Select `manifest.json` from this folder

## Usage
1. Start Distillery: `uvicorn main:app --reload` (in main project folder)
2. Right-click any link on a webpage
3. Click "Send to Distillery"
4. The article opens in a new tab, cleaned and ready to read

## Icons
The extension expects icon files in `icons/`:
- `icon16.png` - 16x16px (toolbar)
- `icon48.png` - 48x48px (extensions page)
- `icon128.png` - 128x128px (Chrome Web Store)

You can copy `distillerylogo2.png` from the main project and resize it, or use any PNGs.

## Troubleshooting
- **"Cannot connect to Distillery"** - Make sure the server is running on `localhost:8000`
- Check that you're using `http://` not `https://` for local development
