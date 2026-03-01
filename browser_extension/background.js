/**
 * Membread Browser Extension — Background Service Worker
 *
 * Receives captured messages from content scripts and sends them
 * to the Membread API at /api/capture for central storage.
 */

const DEFAULT_API_URL = 'http://localhost:8000';

// ── Config helpers ───────────────────────────────────────────────

async function getConfig() {
  const result = await chrome.storage.local.get(['apiUrl', 'token', 'enabled', 'captureCount']);
  return {
    apiUrl: result.apiUrl || DEFAULT_API_URL,
    token: result.token || '',
    enabled: result.enabled !== false, // default on
    captureCount: result.captureCount || 0,
  };
}

async function incrementCapture() {
  const { captureCount } = await getConfig();
  await chrome.storage.local.set({ captureCount: captureCount + 1 });
}

// ── Dedup buffer (avoid sending duplicate messages within 30s) ──

const recentHashes = new Map(); // hash -> timestamp
const DEDUP_WINDOW_MS = 30_000;

function hashContent(text) {
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    const chr = text.charCodeAt(i);
    hash = ((hash << 5) - hash) + chr;
    hash |= 0; // 32-bit int
  }
  return hash.toString(36);
}

function isDuplicate(text) {
  const h = hashContent(text);
  const now = Date.now();

  // Clean old entries
  for (const [key, ts] of recentHashes) {
    if (now - ts > DEDUP_WINDOW_MS) recentHashes.delete(key);
  }

  if (recentHashes.has(h)) return true;
  recentHashes.set(h, now);
  return false;
}

// ── API sender ──────────────────────────────────────────────────

async function sendToApi(payload) {
  const config = await getConfig();

  if (!config.enabled) return { status: 'disabled' };
  if (!config.token) return { status: 'no-token', error: 'No API token configured' };
  if (isDuplicate(payload.content)) return { status: 'duplicate' };

  try {
    const response = await fetch(`${config.apiUrl}/api/capture`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${config.token}`,
      },
      body: JSON.stringify({
        content: payload.content,
        source: payload.source,
        url: payload.url,
        session_id: payload.sessionId,
        metadata: payload.metadata || {},
      }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      return { status: 'error', error: err.detail || response.statusText };
    }

    const data = await response.json();
    await incrementCapture();
    return { status: 'ok', data };
  } catch (err) {
    return { status: 'error', error: err.message };
  }
}

// ── Message listener (from content scripts) ─────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'MEMBREAD_CAPTURE') {
    sendToApi({
      content: message.content,
      source: message.source,
      url: sender.tab?.url || message.url || '',
      sessionId: message.sessionId,
      metadata: {
        tabId: sender.tab?.id,
        title: sender.tab?.title,
        ...message.metadata,
      },
    }).then(sendResponse);
    return true; // async response
  }

  if (message.type === 'MEMBREAD_GET_STATUS') {
    getConfig().then((config) => {
      sendResponse({ enabled: config.enabled, captureCount: config.captureCount, hasToken: !!config.token });
    });
    return true;
  }

  if (message.type === 'MEMBREAD_SET_CONFIG') {
    chrome.storage.local.set(message.config).then(() => {
      sendResponse({ status: 'ok' });
    });
    return true;
  }
});

console.log('[Membread] Background service worker loaded');
