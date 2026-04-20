// Default ports to try for binary detection
const DEFAULT_PORTS = [8000, 8001, 8080, 3000];
let DISTILLERY_URL = 'http://localhost:8000';

// Try to auto-detect a running Distillery binary
async function detectDistilleryBinary() {
  console.log('[Distillery] Starting detection on ports:', DEFAULT_PORTS);
  for (const port of DEFAULT_PORTS) {
    for (const host of ['127.0.0.1', 'localhost']) {
      const url = `http://${host}:${port}`;
      try {
        console.log(`[Distillery] Trying ${url}/health...`);
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 1000);
        const response = await fetch(`${url}/health`, {
          signal: controller.signal,
          mode: 'cors'
        });
        clearTimeout(timeout);
        console.log(`[Distillery] ${url}/health response:`, response.status);
        if (response.ok) {
          console.log(`[Distillery] Found server at ${url}`);
          return url;
        }
      } catch (err) {
        console.log(`[Distillery] ${url} failed:`, err.name, err.message);
      }
    }
  }
  console.log('[Distillery] No server found on any port');
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

async function sendToDistillery(info) {
  const url = info.linkUrl || info.pageUrl;
  if (!url || url.startsWith('chrome://') || url.startsWith('chrome-extension://')) {
    return;
  }

  // Always auto-detect first - server location may have changed
  console.log('[Distillery] Auto-detecting server...');
  const detected = await detectDistilleryBinary();

  if (detected) {
    console.log('[Distillery] Found server at:', detected);
    // Update global URL
    DISTILLERY_URL = detected;
    chrome.storage.sync.set({ distilleryUrl: detected, autoDetected: true });
  } else {
    console.log('[Distillery] Server not found, falling back to:', DISTILLERY_URL);
  }

  const baseUrl = detected || DISTILLERY_URL;

  try {
    console.log('[Distillery] Queuing article:', url);
    // Use /queue endpoint to add to reading list
    const response = await fetch(`${baseUrl}/queue`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const data = await response.json();
    console.log('[Distillery] Queued:', data.title);

    // Open Distillery with queue param to show sidebar
    await chrome.tabs.create({
      url: `${baseUrl}/#url=${encodeURIComponent(url)}&queue=1`
    });
  } catch (err) {
    console.error('[Distillery] Queue failed:', err);
    const isConnectionError = err.message.includes('fetch') ||
                              err.message.includes('Failed to fetch') ||
                              err.name === 'TypeError';

    chrome.notifications.create({
      type: 'basic',
      iconUrl: 'icons/icon48.png',
      title: 'Distillery Error',
      message: isConnectionError
        ? `Cannot connect to Distillery at ${baseUrl}. Make sure the server is running.`
        : `Error: ${err.message}`
    });
  }
}

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'send-to-distillery') {
    sendToDistillery(info);
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
