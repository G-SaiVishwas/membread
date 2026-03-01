/**
 * Membread Content Script — Perplexity (perplexity.ai)
 *
 * Captures search queries and AI-generated answers.
 */

(function () {
  'use strict';

  const SOURCE = 'perplexity';
  const SESSION_ID = `perplexity-${Date.now().toString(36)}`;
  const CAPTURE_INTERVAL_MS = 3000;
  let lastCaptureTime = 0;
  let processedMessages = new Set();

  function extractMessages() {
    const messages = [];

    // Perplexity uses prose containers for answers and specific query blocks
    const queryEls = document.querySelectorAll('[class*="query"], .whitespace-pre-wrap, [data-testid="user-message"]');
    const answerEls = document.querySelectorAll('.prose, [class*="answer"], [class*="AnswerText"], .markdown-body');

    if (queryEls.length > 0) {
      queryEls.forEach((el) => {
        const text = el.innerText?.trim();
        if (text && text.length > 3) messages.push({ role: 'query', text: text.substring(0, 5000) });
      });
    }

    if (answerEls.length > 0) {
      answerEls.forEach((el) => {
        const text = el.innerText?.trim();
        if (text && text.length > 20) messages.push({ role: 'answer', text: text.substring(0, 5000) });
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
    clearTimeout(window.__membreadPerplexityTimer);
    window.__membreadPerplexityTimer = setTimeout(captureNewMessages, 2500);
  });

  function startObserving() {
    const target = document.querySelector('main') || document.body;
    observer.observe(target, { childList: true, subtree: true, characterData: true });
    console.log('[Membread] Perplexity content script active');
  }

  if (document.readyState === 'complete') startObserving();
  else window.addEventListener('load', startObserving);
})();
