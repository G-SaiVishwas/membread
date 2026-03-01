/**
 * Membread Content Script — ChatGPT (chat.openai.com / chatgpt.com)
 *
 * Uses MutationObserver to detect new assistant messages in the DOM.
 * Captures both user prompts and assistant responses.
 */

(function () {
  'use strict';

  const SOURCE = 'chatgpt';
  const SESSION_ID = `chatgpt-${Date.now().toString(36)}`;
  const CAPTURE_INTERVAL_MS = 3000; // minimum between captures
  let lastCaptureTime = 0;
  let processedMessages = new Set();

  /**
   * Extract conversation turns from the ChatGPT DOM.
   * ChatGPT uses data-message-author-role attributes on message containers.
   */
  function extractMessages() {
    const messages = [];

    // Try modern ChatGPT DOM structure
    const articles = document.querySelectorAll('[data-message-author-role]');
    if (articles.length > 0) {
      articles.forEach((el) => {
        const role = el.getAttribute('data-message-author-role');
        const textEl = el.querySelector('.markdown, .whitespace-pre-wrap, [class*="markdown"]');
        const text = (textEl || el).innerText?.trim();
        if (text && text.length > 5) {
          messages.push({ role, text });
        }
      });
    } else {
      // Fallback: look for conversation turn containers
      const turns = document.querySelectorAll('[data-testid^="conversation-turn"]');
      turns.forEach((turn) => {
        const role = turn.querySelector('[data-message-author-role]')?.getAttribute('data-message-author-role') || 'unknown';
        const text = turn.innerText?.trim();
        if (text && text.length > 10) {
          messages.push({ role, text: text.substring(0, 5000) });
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

    // Only capture messages we haven't seen yet
    const newMessages = messages.filter((m) => {
      const key = `${m.role}:${m.text.substring(0, 100)}`;
      if (processedMessages.has(key)) return false;
      processedMessages.add(key);
      return true;
    });

    if (newMessages.length === 0) return;

    lastCaptureTime = now;

    // Format as conversation
    const content = newMessages.map((m) =>
      `[${m.role}]: ${m.text}`
    ).join('\n\n---\n\n');

    chrome.runtime.sendMessage({
      type: 'MEMBREAD_CAPTURE',
      source: SOURCE,
      content: content,
      sessionId: SESSION_ID,
      metadata: {
        messageCount: newMessages.length,
        conversationUrl: window.location.href,
      },
    });
  }

  // ── Observe DOM changes for new messages ───────────────────────

  const observer = new MutationObserver((mutations) => {
    let hasNewContent = false;
    for (const mutation of mutations) {
      if (mutation.addedNodes.length > 0 || mutation.type === 'characterData') {
        hasNewContent = true;
        break;
      }
    }
    if (hasNewContent) {
      // Debounce: wait for streaming to finish
      clearTimeout(window.__membreadTimer);
      window.__membreadTimer = setTimeout(captureNewMessages, 2000);
    }
  });

  // Start observing the main content area
  function startObserving() {
    const target = document.querySelector('main') || document.body;
    observer.observe(target, {
      childList: true,
      subtree: true,
      characterData: true,
    });
    console.log('[Membread] ChatGPT content script active');
  }

  // Wait for page to be ready
  if (document.readyState === 'complete') {
    startObserving();
  } else {
    window.addEventListener('load', startObserving);
  }
})();
