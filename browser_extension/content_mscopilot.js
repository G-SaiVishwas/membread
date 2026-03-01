/**
 * Membread Content Script — Microsoft Copilot (copilot.microsoft.com)
 *
 * Captures conversations from Microsoft Copilot.
 */

(function () {
  'use strict';

  const SOURCE = 'ms-copilot';
  const SESSION_ID = `mscopilot-${Date.now().toString(36)}`;
  const CAPTURE_INTERVAL_MS = 3000;
  let lastCaptureTime = 0;
  let processedMessages = new Set();

  function extractMessages() {
    const messages = [];

    // Microsoft Copilot uses specific turn containers  
    const userMsgs = document.querySelectorAll('[data-content="user-message"], [class*="user-message"], cib-message-group[source="user"]');
    const botMsgs = document.querySelectorAll('[data-content="ai-message"], [class*="bot-message"], cib-message-group[source="bot"]');

    // Fallback: general message containers
    const allMsgs = document.querySelectorAll('.message-content, [class*="ChatMessage"], [class*="turn"]');

    if (userMsgs.length > 0 || botMsgs.length > 0) {
      userMsgs.forEach((el) => {
        const text = el.innerText?.trim();
        if (text && text.length > 3) messages.push({ role: 'user', text: text.substring(0, 5000) });
      });
      botMsgs.forEach((el) => {
        const text = el.innerText?.trim();
        if (text && text.length > 10) messages.push({ role: 'copilot', text: text.substring(0, 5000) });
      });
    } else if (allMsgs.length > 0) {
      allMsgs.forEach((el) => {
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
    clearTimeout(window.__membreadMsCopilotTimer);
    window.__membreadMsCopilotTimer = setTimeout(captureNewMessages, 2000);
  });

  function startObserving() {
    const target = document.querySelector('main') || document.querySelector('#app') || document.body;
    observer.observe(target, { childList: true, subtree: true, characterData: true });
    console.log('[Membread] Microsoft Copilot content script active');
  }

  if (document.readyState === 'complete') startObserving();
  else window.addEventListener('load', startObserving);
})();
