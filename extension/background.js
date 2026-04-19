// Default ports to try for binary detection
const DEFAULT_PORTS = [8000, 8001, 8080, 3000];
let DISTILLERY_URL = 'http://localhost:8000';

// Try to auto-detect a running Distillery binary
async function detectDistilleryBinary() {
  for (const port of DEFAULT_PORTS) {
    for (const host of ['localhost', '127.0.0.1']) {
      const url = `http://${host}:${port}`;
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 500);
        const response = await fetch(`${url}/health`, {
          signal: controller.signal
        });
        clearTimeout(timeout);
        if (response.ok) {
          return url;
        }
      } catch {
        // Continue to next port
      }
    }
  }
  return null;
}

// Load saved URL or auto-detect binary
chrome.storage.sync.get(['distilleryUrl'], async (result) => {
  if (result.distilleryUrl) {
    DISTILLERY_URL = result.distilleryUrl;
  } else {
    const detected = await detectDistilleryBinary();
    if (detected) {
      DISTILLERY_URL = detected;
      chrome.storage.sync.set({ distilleryUrl: detected, autoDetected: true });
    }
  }
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'send-to-distillery',
    title: 'Send to Distillery',
    contexts: ['link', 'page']
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== 'send-to-distillery') return;

  const url = info.linkUrl || info.pageUrl;
  if (!url || url.startsWith('chrome://') || url.startsWith('chrome-extension://')) {
    return;
  }

  try {
    const response = await fetch(`${DISTILLERY_URL}/fetch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    await chrome.tabs.create({
      url: `${DISTILLERY_URL}/#url=${encodeURIComponent(url)}`
    });
  } catch (err) {
    const isConnectionError = err.message.includes('fetch') ||
                              err.message.includes('Failed to fetch') ||
                              err.name === 'TypeError';

    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: 'Distillery Error',
      message: isConnectionError
        ? `Cannot connect to Distillery at ${DISTILLERY_URL}. Make sure the server is running or check your extension settings.`
        : `Error: ${err.message}`
    });
  }
});

// Listen for URL updates from options page
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'updateUrl') {
    DISTILLERY_URL = message.url;
    chrome.storage.sync.set({ distilleryUrl: message.url });
    sendResponse({ success: true });
  }
});
