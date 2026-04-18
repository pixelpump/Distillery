// Default to localhost for development. Users can configure their hosted URL in options.
let DISTILLERY_URL = 'http://localhost:8000';

// Load saved URL from storage
chrome.storage.sync.get(['distilleryUrl'], (result) => {
  if (result.distilleryUrl) {
    DISTILLERY_URL = result.distilleryUrl;
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
