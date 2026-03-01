/**
 * Membread Extension — Popup UI Controller
 */

document.addEventListener('DOMContentLoaded', async () => {
  const apiUrlInput = document.getElementById('apiUrl');
  const tokenInput = document.getElementById('token');
  const enableToggle = document.getElementById('enableToggle');
  const saveBtn = document.getElementById('saveBtn');
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const captureCountEl = document.getElementById('captureCount');

  let enabled = true;

  // Load saved config
  const config = await chrome.storage.local.get(['apiUrl', 'token', 'enabled', 'captureCount']);
  apiUrlInput.value = config.apiUrl || 'http://localhost:8000';
  tokenInput.value = config.token || '';
  enabled = config.enabled !== false;
  updateToggleUI();
  captureCountEl.textContent = `${config.captureCount || 0} captured`;

  // Check connection status
  updateStatus();

  // Toggle
  enableToggle.addEventListener('click', () => {
    enabled = !enabled;
    updateToggleUI();
  });

  // Save
  saveBtn.addEventListener('click', async () => {
    await chrome.storage.local.set({
      apiUrl: apiUrlInput.value.replace(/\/$/, ''),
      token: tokenInput.value,
      enabled: enabled,
    });
    saveBtn.textContent = 'Saved!';
    setTimeout(() => { saveBtn.textContent = 'Save Configuration'; }, 1500);
    updateStatus();
  });

  function updateToggleUI() {
    enableToggle.className = enabled ? 'toggle on' : 'toggle';
  }

  async function updateStatus() {
    if (!enabled) {
      statusDot.className = 'status-dot off';
      statusText.textContent = 'Capture disabled';
      return;
    }

    if (!tokenInput.value) {
      statusDot.className = 'status-dot off';
      statusText.textContent = 'No token configured';
      return;
    }

    try {
      const url = (apiUrlInput.value || 'http://localhost:8000').replace(/\/$/, '');
      const res = await fetch(`${url}/health`, { method: 'GET' });
      if (res.ok) {
        statusDot.className = 'status-dot on';
        statusText.textContent = 'Connected';
      } else {
        statusDot.className = 'status-dot off';
        statusText.textContent = 'API error';
      }
    } catch {
      statusDot.className = 'status-dot off';
      statusText.textContent = 'Cannot reach API';
    }
  }
});
