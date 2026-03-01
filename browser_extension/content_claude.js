/**
 * Membread Content Script — Claude (claude.ai)
 *
 * Observes DOM changes to capture conversation turns from Anthropic Claude.
 */

(function () {
  'use strict';

  const SOURCE = 'claude-web';
  const SESSION_ID = `claude-${Date.now().toString(36)}`;
  const CAPTURE_INTERVAL_MS = 3000;
  let lastCaptureTime = 0;
  let processedMessages = new Set();

  /**
   * Extract conversation messages from Claude's DOM.
   * Claude uses fieldset elements or div with specific data attributes for messages.
   */
  function extractMessages() {
    const messages = [];

    // Claude's message containers  
    const humanMsgs = document.querySelectorAll('[data-is-streaming="false"][class*="human"], .font-user-message, [data-testid="human-turn"]');
    const assistantMsgs = document.querySelectorAll('[data-is-streaming="false"][class*="assistant"], .font-claude-message, [data-testid="assistant-turn"]');

    // Fallback: general approach - find conversation containers
    const allTurns = document.querySelectorAll('.prose, [class*="ConversationItem"], [class*="Message"]');

    if (humanMsgs.length > 0 || assistantMsgs.length > 0) {
      humanMsgs.forEach((el) => {
        const text = el.innerText?.trim();
        if (text && text.length > 3) messages.push({ role: 'human', text: text.substring(0, 5000) });
      });
      assistantMsgs.forEach((el) => {
        const text = el.innerText?.trim();
        if (text && text.length > 3) messages.push({ role: 'assistant', text: text.substring(0, 5000) });
      });
    } else if (allTurns.length > 0) {
      // Heuristic: look at parent elements for role indicators
      allTurns.forEach((el) => {
        const text = el.innerText?.trim();
        if (!text || text.length < 10) return;

        // Try to determine role from parent classes
        const parent = el.closest('[class*="human"], [class*="Human"]');
        const role = parent ? 'human' : 'assistant';
        messages.push({ role, text: text.substring(0, 5000) });
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
      metadata: {
        messageCount: newMessages.length,
        conversationUrl: window.location.href,
      },
    });
  }

  const observer = new MutationObserver(() => {
    clearTimeout(window.__membreadClaudeTimer);
    window.__membreadClaudeTimer = setTimeout(captureNewMessages, 2000);
  });

  function startObserving() {
    const target = document.querySelector('main') || document.querySelector('[class*="conversation"]') || document.body;
    observer.observe(target, { childList: true, subtree: true, characterData: true });
    console.log('[Membread] Claude content script active');
  }

  if (document.readyState === 'complete') startObserving();
  else window.addEventListener('load', startObserving);
})();
