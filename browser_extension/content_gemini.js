/**
 * Membread Content Script — Gemini (gemini.google.com)
 *
 * Captures conversation turns from Google Gemini.
 */

(function () {
  'use strict';

  const SOURCE = 'gemini';
  const SESSION_ID = `gemini-${Date.now().toString(36)}`;
  const CAPTURE_INTERVAL_MS = 3000;
  let lastCaptureTime = 0;
  let processedMessages = new Set();

  function extractMessages() {
    const messages = [];

    // Gemini uses model-response and user-query containers
    const userMsgs = document.querySelectorAll('.user-query, [class*="query-text"], [data-content-type="user"]');
    const modelMsgs = document.querySelectorAll('.model-response, [class*="response-text"], .markdown-main-panel, [data-content-type="model"]');

    // Fallback: conversation turn containers
    const turns = document.querySelectorAll('.conversation-turn, [class*="turn-content"]');

    if (userMsgs.length > 0 || modelMsgs.length > 0) {
      userMsgs.forEach((el) => {
        const text = el.innerText?.trim();
        if (text && text.length > 3) messages.push({ role: 'user', text: text.substring(0, 5000) });
      });
      modelMsgs.forEach((el) => {
        const text = el.innerText?.trim();
        if (text && text.length > 10) messages.push({ role: 'model', text: text.substring(0, 5000) });
      });
    } else if (turns.length > 0) {
      turns.forEach((el) => {
        const text = el.innerText?.trim();
        if (text && text.length > 10) {
          messages.push({ role: 'unknown', text: text.substring(0, 5000) });
        }
      });
    }

    return messages;
  }

  function captureNewMessages() {
    const now = Date.now();
    if (now - lastCaptureTime < CAPTURE_INTERVAL_MS) return;

    const messages = extractMessages();
    if (messages.length === 0) return;

    const newMessages = messages.filter((m) => {
      const key = `${m.role}:${m.text.substring(0, 100)}`;
      if (processedMessages.has(key)) return false;
      processedMessages.add(key);
      return true;
    });

    if (newMessages.length === 0) return;
    lastCaptureTime = now;

    const content = newMessages.map((m) =>
      `[${m.role}]: ${m.text}`
    ).join('\n\n---\n\n');

    chrome.runtime.sendMessage({
      type: 'MEMBREAD_CAPTURE',
      source: SOURCE,
      content: content,
      sessionId: SESSION_ID,
      metadata: { messageCount: newMessages.length, conversationUrl: window.location.href },
    });
  }

  const observer = new MutationObserver(() => {
    clearTimeout(window.__membreadGeminiTimer);
    window.__membreadGeminiTimer = setTimeout(captureNewMessages, 2000);
  });

  function startObserving() {
    const target = document.querySelector('main') || document.querySelector('chat-window') || document.body;
    observer.observe(target, { childList: true, subtree: true, characterData: true });
    console.log('[Membread] Gemini content script active');
  }

  if (document.readyState === 'complete') startObserving();
  else window.addEventListener('load', startObserving);
})();
