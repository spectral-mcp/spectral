/**
 * Popup entry point — wires event listeners and runs initialization.
 */

import { state, showError, updateUI } from './ui.js';
import { startCapture, stopCapture, startStatusPolling } from './capture.js';

// ============================================================================
// Connection footer
// ============================================================================

function renderConnectionFooter(connected) {
  const connEl = document.getElementById('connection-status');
  if (connected) {
    connEl.innerHTML = 'Connected to <code>spectral</code> CLI';
    connEl.classList.remove('connection-error');
  } else {
    const installCmd = `spectral extension install --extension-id ${chrome.runtime.id}`;
    connEl.innerHTML = `<code>spectral</code> CLI not connected. Run:<br><span class="install-cmd"><code>${installCmd}</code><button class="btn-copy" title="&#128461; command">&#128461;</button></span>`;
    connEl.classList.add('connection-error');
    connEl.querySelector('.btn-copy').addEventListener('click', () => {
      navigator.clipboard.writeText(installCmd).then(() => {
        const btn = connEl.querySelector('.btn-copy');
        btn.textContent = '\u2713';
        setTimeout(() => { btn.innerHTML = '&#128461;'; }, 1500);
      });
    });
  }
}

// ============================================================================
// Initialize
// ============================================================================

async function initialize() {
  const container = document.querySelector('.container');
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab) {
      showError('No active tab found');
      return;
    }

    if (tab.url.startsWith('chrome://') || tab.url.startsWith('chrome-extension://')) {
      showError('Cannot capture Chrome internal pages');
      document.getElementById('btn-start').disabled = true;
      return;
    }

    state.currentTabId = tab.id;

    const response = await chrome.runtime.sendMessage({ type: 'GET_STATUS' });

    // Apply connection state before any UI render
    state.hostConnected = response.hostConnected;
    renderConnectionFooter(response.hostConnected);

    // Apply persisted settings to checkboxes
    if (response.settings) {
      document.getElementById('setting-typename').checked = response.settings.injectTypename;
      document.getElementById('setting-apq').checked = response.settings.injectApqError;
    }

    if (response.state === 'capturing') {
      startStatusPolling();
      updateUI('capturing', response.stats);
    } else {
      if (response.stats && response.stats.trace_count > 0) {
        state.lastStats = response.stats;
      }
      updateUI('idle');
    }
  } catch (error) {
    showError(`Initialization error: ${error.message}`);
  } finally {
    container.classList.remove('hidden');
  }
}

// ============================================================================
// Event listeners
// ============================================================================

document.getElementById('btn-start').addEventListener('click', startCapture);
document.getElementById('btn-stop').addEventListener('click', stopCapture);
document.getElementById('btn-toggle-settings').addEventListener('click', () => {
  const drawer = document.getElementById('capture-settings');
  const toggle = document.getElementById('btn-toggle-settings');
  const expanded = toggle.getAttribute('aria-expanded') === 'true';
  toggle.setAttribute('aria-expanded', String(!expanded));
  drawer.classList.toggle('collapsed');
});

document.getElementById('setting-typename').addEventListener('change', (e) => {
  chrome.runtime.sendMessage({
    type: 'UPDATE_SETTINGS',
    settings: { injectTypename: e.target.checked },
  });
});

document.getElementById('setting-apq').addEventListener('change', (e) => {
  chrome.runtime.sendMessage({
    type: 'UPDATE_SETTINGS',
    settings: { injectApqError: e.target.checked },
  });
});

initialize();
